"""
graph.py — TaxMantri LangGraph StateGraph orchestrator.

Builds and compiles the three-agent pipeline:
  InputAgent → MatcherAgent → EvaluatorAgent

Also acts as the singleton registry for shared resources (retriever, Mistral client,
semaphore) that are set at FastAPI startup and accessed by tool functions.

Usage:
    from backend.graph.graph import build_graph, set_resources

    # At FastAPI startup:
    set_resources(retriever=app.state.retriever,
                  mistral_client=app.state.mistral,
                  rag_semaphore=app.state.rag_semaphore)
    app.state.tax_graph = build_graph()

    # At request time:
    result = await app.state.tax_graph.ainvoke(initial_state)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton resource registry — set during FastAPI lifespan, read by tools
# ---------------------------------------------------------------------------

_retriever: Any = None
_mistral_client: Any = None
_rag_semaphore: Optional[asyncio.Semaphore] = None
_llm: Any = None  # Optional ChatMistralAI for agent use


def set_resources(
    retriever: Any = None,
    mistral_client: Any = None,
    rag_semaphore: Optional[asyncio.Semaphore] = None,
) -> None:
    """
    Called at FastAPI startup (lifespan) to register shared resources.
    All tools access these via get_* functions below.
    """
    global _retriever, _mistral_client, _rag_semaphore, _llm
    _retriever = retriever
    _mistral_client = mistral_client
    _rag_semaphore = rag_semaphore

    # Build a ChatMistralAI wrapper for LangChain tool-calling if possible
    if mistral_client is not None:
        try:
            from langchain_mistralai import ChatMistralAI
            from backend.config import settings
            _llm = ChatMistralAI(
                model="mistral-small-latest",
                mistral_api_key=settings.mistral_api_key,
                temperature=0.1,
            )
            logger.info("ChatMistralAI LangChain wrapper initialized")
        except Exception as exc:
            logger.warning("Could not init ChatMistralAI wrapper: %s", exc)
            _llm = None

    logger.info(
        "Graph resources set: retriever=%s mistral=%s semaphore=%s",
        "ok" if retriever else "none",
        "ok" if mistral_client else "none",
        "ok" if rag_semaphore else "none",
    )


def get_retriever() -> Any:
    return _retriever


def get_mistral_client() -> Any:
    return _mistral_client


def get_rag_semaphore() -> asyncio.Semaphore:
    """Returns the semaphore, creating a default one if not yet set."""
    global _rag_semaphore
    if _rag_semaphore is None:
        try:
            _rag_semaphore = asyncio.get_event_loop().run_until_complete(
                asyncio.coroutine(lambda: asyncio.Semaphore(2))()
            )
        except Exception:
            _rag_semaphore = asyncio.Semaphore(2)
    return _rag_semaphore


def get_llm() -> Any:
    return _llm


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph():
    """
    Builds and compiles the TaxMantri LangGraph StateGraph.

    Node execution order:
      input_agent → (conditional) → matcher_agent → evaluator_agent → END

    Conditional edge after input_agent:
      - "error": goes to END (returns input_errors in state)
      - "matcher": continues to matcher_agent
    """
    from langgraph.graph import StateGraph, END
    from backend.graph.state import TaxMantriState
    from backend.graph.agents.input_agent import input_agent_node, route_after_input
    from backend.graph.agents.matcher_agent import matcher_agent_node
    from backend.graph.agents.evaluator_agent import evaluator_agent_node

    # ---- Error passthrough node (stops graph on InputAgent failure) ----
    async def error_node(state: TaxMantriState) -> dict:
        """Passthrough node that marks pipeline as stopped."""
        logger.info("Graph stopped at error_node: %s", state.get("input_errors"))
        return {"current_agent": "error", "should_stop": True}

    # ---- Build StateGraph ----
    workflow = StateGraph(TaxMantriState)

    workflow.add_node("input_agent", input_agent_node)
    workflow.add_node("matcher_agent", matcher_agent_node)
    workflow.add_node("evaluator_agent", evaluator_agent_node)
    workflow.add_node("error", error_node)

    # Entry point
    workflow.set_entry_point("input_agent")

    # Conditional routing after InputAgent
    workflow.add_conditional_edges(
        "input_agent",
        route_after_input,
        {
            "error": "error",
            "matcher": "matcher_agent",
        },
    )

    # Linear edges: matcher → evaluator → END
    workflow.add_edge("matcher_agent", "evaluator_agent")
    workflow.add_edge("evaluator_agent", END)
    workflow.add_edge("error", END)

    compiled = workflow.compile()
    logger.info("TaxMantri LangGraph compiled successfully")
    return compiled
