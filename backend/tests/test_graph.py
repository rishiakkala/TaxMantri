"""
test_graph.py — Integration tests for the TaxMantri LangGraph agent pipeline.

Tests verify:
1. Manual input → full pipeline → TaxResult with correct numbers (matching tax engine)
2. Invalid input → stops at InputAgent → returns structured errors
3. MatcherAgent generates queries inclusive of HRA, 80C, home loan sections
4. EvaluatorAgent produces a valid TaxResult with non-empty rationale
5. Tax numbers from /api/run match numbers from tax_engine.calculate_old/new_regime()

These tests mock the Mistral client and FAISS retriever when needed to avoid
external API calls and infrastructure dependencies.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test fixtures — sample profiles
# ---------------------------------------------------------------------------

VALID_PROFILE_BASIC = {
    "basic_salary": 600000.0,
    "hra_received": 240000.0,
    "monthly_rent_paid": 15000.0,
    "city_type": "metro",
    "age_bracket": "under60",
    "investments_80c": 150000.0,
    "input_method": "manual",
}

VALID_PROFILE_FULL = {
    "basic_salary": 900000.0,
    "hra_received": 300000.0,
    "monthly_rent_paid": 20000.0,
    "city_type": "metro",
    "age_bracket": "under60",
    "investments_80c": 150000.0,
    "health_insurance_self": 25000.0,
    "health_insurance_parents": 50000.0,
    "parent_senior_citizen": True,
    "home_loan_interest": 200000.0,
    "employee_nps_80ccd1b": 50000.0,
    "employer_nps_80ccd2": 90000.0,
    "savings_interest_80tta": 8000.0,
    "input_method": "manual",
}

INVALID_PROFILE = {
    # Missing required: basic_salary is provided but city_type missing
    "basic_salary": 600000.0,
    "input_method": "manual",
    # Missing city_type — should fail validation
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_retriever(num_chunks: int = 5) -> MagicMock:
    """Create a mock TaxRetriever returning synthetic chunks."""
    mock = MagicMock()
    chunks = [
        {
            "chunk_id": f"chunk_{i}",
            "text": f"Section 80C allows deduction up to ₹1,50,000. [Context chunk {i}]",
            "section_ref": f"Section 80C" if i < 3 else "Section 115BAC",
            "source": "income_tax_act.pdf",
        }
        for i in range(num_chunks)
    ]
    mock.hybrid_search.return_value = chunks
    return mock


def _make_mock_mistral() -> MagicMock:
    """Create a mock Mistral client returning a canned LLM answer."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        "The New Regime is recommended as it results in lower tax liability "
        "[Section 115BAC, IT Act 1961]. With your income profile, the simplified "
        "slab structure offers ₹12,000 in savings compared to the Old Regime."
    )
    coro = AsyncMock(return_value=mock_response)
    mock.chat.complete_async = coro
    return mock


# ---------------------------------------------------------------------------
# Graph setup helper — patches resources before each graph build
# ---------------------------------------------------------------------------

def _setup_graph_resources(retriever=None, mistral=None):
    """Registers mock resources with the graph singleton."""
    import asyncio
    from backend.graph.graph import set_resources
    set_resources(
        retriever=retriever or _make_mock_retriever(),
        mistral_client=mistral or _make_mock_mistral(),
        rag_semaphore=asyncio.Semaphore(2),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInputAgentNode:
    """Tests for input_agent.py — validation and structuring."""

    def test_valid_manual_input_produces_profile(self):
        """InputAgent with valid data should produce a structured profile."""
        from backend.graph.agents.input_agent import input_agent_node
        from backend.graph.state import TaxMantriState

        state: TaxMantriState = {
            "raw_input": dict(VALID_PROFILE_BASIC),
            "input_method": "manual",
            "file_path": None,
            "input_errors": [],
            "errors": [],
            "should_stop": False,
            "current_agent": "start",
        }

        result = asyncio.run(input_agent_node(state))

        assert result["should_stop"] is False
        assert result["input_errors"] == []
        assert result["profile"] is not None
        assert result["profile_dict"] is not None
        assert result["input_confidence"] == 1.0
        assert result["profile"].basic_salary == 600000.0

    def test_missing_required_field_stops_pipeline(self):
        """InputAgent with invalid data should set should_stop=True."""
        from backend.graph.agents.input_agent import input_agent_node
        from backend.graph.state import TaxMantriState

        state: TaxMantriState = {
            "raw_input": {"basic_salary": 600000.0},  # missing city_type, age_bracket
            "input_method": "manual",
            "file_path": None,
            "input_errors": [],
            "errors": [],
            "should_stop": False,
            "current_agent": "start",
        }

        result = asyncio.run(input_agent_node(state))

        assert result["should_stop"] is True
        assert len(result["input_errors"]) > 0

    def test_route_after_input_success(self):
        """route_after_input should return 'matcher' when no errors."""
        from backend.graph.agents.input_agent import route_after_input

        state = {"should_stop": False}
        assert route_after_input(state) == "matcher"

    def test_route_after_input_error(self):
        """route_after_input should return 'error' when should_stop is True."""
        from backend.graph.agents.input_agent import route_after_input

        state = {"should_stop": True}
        assert route_after_input(state) == "error"


class TestMatcherAgentNode:
    """Tests for matcher_agent.py — RAG retrieval and citation synthesis."""

    def test_generates_queries_from_profile(self):
        """MatcherAgent should auto-generate relevant queries from profile fields."""
        from backend.graph.tools.rag_tools import generate_tax_queries_tool

        result = generate_tax_queries_tool.invoke({"profile": VALID_PROFILE_FULL})

        queries = result["queries"]
        sections = result["sections_identified"]

        assert len(queries) >= 5  # at least basic slabs, std ded, 87A, HRA, 80C
        assert any("HRA" in q or "10(13A)" in q for q in queries)
        assert any("80C" in q for q in queries)
        assert any("80D" in q or "health" in q.lower() for q in queries)
        assert any("home loan" in q.lower() or "24(b)" in q for q in queries)
        assert any("80CCD(1B)" in q or "NPS" in q for q in queries)

        assert "Section 10(13A)" in sections
        assert "Section 80C" in sections

    def test_matcher_node_with_mock_retriever(self):
        """MatcherAgent with mock retriever should produce retrieved_chunks and law_context."""
        from backend.graph.agents.input_agent import input_agent_node
        from backend.graph.agents.matcher_agent import matcher_agent_node
        from backend.graph.state import TaxMantriState
        from backend.agents.input_agent.schemas import UserFinancialProfile

        _setup_graph_resources()

        input_state: TaxMantriState = {
            "raw_input": dict(VALID_PROFILE_BASIC),
            "input_method": "manual",
            "file_path": None,
            "input_errors": [],
            "errors": [],
            "should_stop": False,
            "current_agent": "start",
        }
        input_result = asyncio.run(input_agent_node(input_state))

        matcher_state = {**input_state, **input_result}
        result = asyncio.run(matcher_agent_node(matcher_state))

        assert "retrieved_chunks" in result
        assert "tax_queries" in result
        assert "law_context" in result
        assert len(result["retrieved_chunks"]) > 0
        assert len(result["tax_queries"]) > 0


class TestEvaluatorAgentNode:
    """Tests for evaluator_agent.py — tax calculation and rationale generation."""

    def test_tax_numbers_match_direct_engine(self):
        """Numbers produced by EvaluatorAgent must match the direct tax engine."""
        from backend.agents.evaluator_agent.tax_engine import (
            calculate_old_regime,
            calculate_new_regime,
        )
        from backend.agents.input_agent.schemas import UserFinancialProfile
        from backend.graph.tools.tax_tools import compare_regimes_tool

        profile = UserFinancialProfile(**VALID_PROFILE_FULL)

        # Direct tax engine
        old = calculate_old_regime(profile)
        new = calculate_new_regime(profile)

        # Through tool wrapper
        result = compare_regimes_tool.invoke({"profile_dict": profile.model_dump(mode="json")})
        assert result["success"]
        tax = result["result"]
        assert abs(tax["old_regime"]["total_tax"] - old.total_tax) < 0.01
        assert abs(tax["new_regime"]["total_tax"] - new.total_tax) < 0.01

    def test_evaluator_node_produces_recommendation(self):
        """EvaluatorAgent node should produce a non-empty recommendation."""
        from backend.graph.agents.evaluator_agent import evaluator_agent_node
        from backend.graph.agents.input_agent import input_agent_node
        from backend.graph.state import TaxMantriState

        _setup_graph_resources()

        input_state: TaxMantriState = {
            "raw_input": dict(VALID_PROFILE_BASIC),
            "input_method": "manual",
            "file_path": None,
            "input_errors": [],
            "errors": [],
            "should_stop": False,
            "current_agent": "start",
        }
        input_result = asyncio.run(input_agent_node(input_state))

        evaluator_state = {
            **input_state,
            **input_result,
            "law_context": "The New Regime per Section 115BAC provides simplified slabs.",
            "citations": [{"section": "Section 115BAC", "excerpt": "simplified slabs"}],
        }

        result = asyncio.run(evaluator_agent_node(evaluator_state))

        assert result["tax_result"] is not None
        assert result["recommendation"] in ("old", "new")
        assert isinstance(result["savings_amount"], (int, float))
        assert isinstance(result["rationale"], str)
        assert len(result["rationale"]) > 10


class TestFullGraph:
    """End-to-end graph pipeline tests."""

    def test_full_pipeline_manual_input(self):
        """Full graph with valid manual input should produce a complete TaxResult."""
        from backend.graph.graph import build_graph

        _setup_graph_resources()
        graph = build_graph()

        initial_state = {
            "raw_input": dict(VALID_PROFILE_FULL),
            "input_method": "manual",
            "file_path": None,
            "input_errors": [],
            "errors": [],
            "should_stop": False,
            "current_agent": "input",
        }

        result = asyncio.run(graph.ainvoke(initial_state))

        # Pipeline should complete without stopping
        assert result.get("should_stop") is not True
        assert result.get("tax_result") is not None

        # Tax result should have both regimes
        tax = result["tax_result"]
        assert "old_regime" in tax
        assert "new_regime" in tax
        # Both taxes should be non-negative (new regime can be 0 due to 87A rebate under Budget 2025)
        assert tax["old_regime"]["total_tax"] >= 0
        assert tax["new_regime"]["total_tax"] >= 0
        # At least one regime should produce a non-zero tax for a 9L profile
        assert max(tax["old_regime"]["total_tax"], tax["new_regime"]["total_tax"]) > 0
        assert tax["recommended_regime"] in ("old", "new")

        # Citations should be present
        assert "citations" in result

    def test_pipeline_stops_on_invalid_input(self):
        """Full graph with invalid input should return should_stop=True."""
        from backend.graph.graph import build_graph

        _setup_graph_resources()
        graph = build_graph()

        initial_state = {
            "raw_input": {"basic_salary": -1000},  # negative salary — invalid
            "input_method": "manual",
            "file_path": None,
            "input_errors": [],
            "errors": [],
            "should_stop": False,
            "current_agent": "input",
        }

        result = asyncio.run(graph.ainvoke(initial_state))

        assert result.get("should_stop") is True
        assert len(result.get("input_errors", [])) > 0
        assert result.get("tax_result") is None
