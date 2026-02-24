"""
test_index_verification.py — Phase 4 RAG Index Integrity Tests
===============================================================
Verifies that running build_index.py produces a correct FAISS index
and chunk metadata pickle that satisfy all Phase 4 success criteria.

Run from TaxMantri/ project root:
    pytest backend/tests/test_index_verification.py -v

Prerequisites:
    The build_index.py script must have been run first to generate:
        knowledge_base/indexes/kb.faiss
        knowledge_base/indexes/chunks.pkl

These tests do NOT re-run the build; they validate its output.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pytest
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths (resolved relative to this file → TaxMantri/knowledge_base/indexes/)
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_PROJECT_ROOT = _THIS.parent.parent.parent  # TaxMantri/
INDEX_DIR = _PROJECT_ROOT / "knowledge_base" / "indexes"
RAW_DIR = _PROJECT_ROOT / "knowledge_base" / "raw"
FAISS_PATH = INDEX_DIR / "kb.faiss"
PKL_PATH = INDEX_DIR / "chunks.pkl"

# Expected source files
EXPECTED_FILES = [
    "section_15.txt",
    "section_16.txt",
    "section_10_13a.txt",
    "section_10_5.txt",
    "section_10_10d.txt",
    "section_24.txt",
    "section_80c.txt",
    "section_80d.txt",
    "section_80ccd.txt",
    "section_80e.txt",
    "section_80g.txt",
    "section_80tta.txt",
    "section_87a.txt",
    "section_89a.txt",
    "section_115bac.txt",
    "hra_rule_2a.txt",
    "budget_2025_amendments.txt",
    "itr1_instructions.txt",
    "form16_guide.txt",
]

# Expected section refs present in chunks
EXPECTED_SECTION_REFS = {
    "IT Act S.15",
    "IT Act S.16",
    "IT Act S.10(13A)",
    "IT Act S.10(5)",
    "IT Act S.10(10D)",
    "IT Act S.24",
    "IT Act S.80C",
    "IT Act S.80D",
    "IT Act S.80CCD",
    "IT Act S.80E",
    "IT Act S.80G",
    "IT Act S.80TTA",
    "IT Act S.87A",
    "IT Act S.89A",
    "IT Act S.115BAC",
    "IT Rules Rule 2A",
    "Budget 2025",
    "ITR-1 Instructions",
    "Form 16 Guide",
}

MODEL_NAME = "BAAI/bge-m3"


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def chunks() -> list[dict[str, Any]]:
    assert PKL_PATH.is_file(), (
        f"chunks.pkl not found at {PKL_PATH}. Run build_index.py first."
    )
    with open(PKL_PATH, "rb") as fh:
        data = pickle.load(fh)
    assert isinstance(data, list), "chunks.pkl must contain a list"
    assert len(data) > 0, "chunks.pkl is empty"
    return data


@pytest.fixture(scope="session")
def faiss_index() -> faiss.IndexFlatIP:
    assert FAISS_PATH.is_file(), (
        f"kb.faiss not found at {FAISS_PATH}. Run build_index.py first."
    )
    idx = faiss.read_index(str(FAISS_PATH))
    return idx


@pytest.fixture(scope="session")
def bm25(chunks: list[dict[str, Any]]) -> BM25Okapi:
    corpus = [c["text"].lower().split() for c in chunks]
    return BM25Okapi(corpus)


@pytest.fixture(scope="session")
def model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------


class TestFileExistence:
    def test_faiss_file_exists(self) -> None:
        assert FAISS_PATH.is_file(), f"kb.faiss missing at {FAISS_PATH}"

    def test_pkl_file_exists(self) -> None:
        assert PKL_PATH.is_file(), f"chunks.pkl missing at {PKL_PATH}"

    def test_all_raw_source_files_exist(self) -> None:
        missing = [f for f in EXPECTED_FILES if not (RAW_DIR / f).is_file()]
        assert not missing, f"Missing raw files: {missing}"


# ---------------------------------------------------------------------------
# 2. Chunk count and metadata integrity
# ---------------------------------------------------------------------------


class TestChunkIntegrity:
    def test_minimum_chunk_count(self, chunks: list[dict[str, Any]]) -> None:
        """19 files × at least 1 chunk each = minimum 19 chunks."""
        assert len(chunks) >= 19, f"Expected at least 19 chunks, got {len(chunks)}"

    def test_chunk_ids_are_unique(self, chunks: list[dict[str, Any]]) -> None:
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Duplicate chunk_id values found"

    def test_chunk_id_pattern(self, chunks: list[dict[str, Any]]) -> None:
        """chunk_id must match pattern: <stem>_chunk_<NNN>"""
        import re

        pattern = re.compile(r"^[a-z0-9_]+_chunk_\d{3}$")
        bad = [c["chunk_id"] for c in chunks if not pattern.match(c["chunk_id"])]
        assert not bad, f"Malformed chunk_ids: {bad[:5]}"

    def test_required_metadata_keys(self, chunks: list[dict[str, Any]]) -> None:
        required = {"chunk_id", "source_file", "section_ref", "assessment_year", "chunk_index", "text"}
        for chunk in chunks:
            missing = required - set(chunk.keys())
            assert not missing, f"Chunk {chunk.get('chunk_id')} missing keys: {missing}"

    def test_all_chunks_have_non_empty_text(self, chunks: list[dict[str, Any]]) -> None:
        empty = [c["chunk_id"] for c in chunks if not c["text"].strip()]
        assert not empty, f"Chunks with empty text: {empty}"

    def test_all_section_refs_present(self, chunks: list[dict[str, Any]]) -> None:
        found_refs = {c["section_ref"] for c in chunks}
        missing_refs = EXPECTED_SECTION_REFS - found_refs
        assert not missing_refs, f"Missing section refs in chunks: {missing_refs}"

    def test_assessment_year_label(self, chunks: list[dict[str, Any]]) -> None:
        bad = [c["chunk_id"] for c in chunks if c.get("assessment_year") != "AY2025-26"]
        assert not bad, f"Chunks with wrong assessment_year: {bad[:5]}"


# ---------------------------------------------------------------------------
# 3. FAISS index integrity
# ---------------------------------------------------------------------------


class TestFAISSIndex:
    def test_faiss_ntotal_matches_chunks(
        self, faiss_index: faiss.IndexFlatIP, chunks: list[dict[str, Any]]
    ) -> None:
        assert faiss_index.ntotal == len(chunks), (
            f"FAISS ntotal={faiss_index.ntotal} != chunks={len(chunks)}"
        )

    def test_faiss_is_flatip(self, faiss_index: faiss.IndexFlatIP) -> None:
        assert isinstance(faiss_index, faiss.IndexFlatIP), (
            "Expected IndexFlatIP; got different index type"
        )

    def test_faiss_dimension_matches_bge_m3(self, faiss_index: faiss.IndexFlatIP) -> None:
        # BAAI/bge-m3 produces 1024-dimensional embeddings
        assert faiss_index.d == 1024, f"Expected dimension 1024, got {faiss_index.d}"

    def test_faiss_search_returns_valid_results(
        self, faiss_index: faiss.IndexFlatIP, model: SentenceTransformer
    ) -> None:
        query = "standard deduction Section 16"
        vec = model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        distances, indices = faiss_index.search(vec, k=5)
        assert indices.shape == (1, 5)
        assert all(i >= 0 for i in indices[0]), "FAISS returned invalid (negative) index"
        assert all(d >= -1.01 and d <= 1.01 for d in distances[0]), (
            "Cosine scores out of expected range [-1, 1]"
        )


# ---------------------------------------------------------------------------
# 4. BM25 search quality
# ---------------------------------------------------------------------------


class TestBM25Search:
    def test_bm25_search_80c(
        self, chunks: list[dict[str, Any]], bm25: BM25Okapi
    ) -> None:
        query_tokens = "section 80c deduction one lakh fifty thousand".split()
        scores = bm25.get_scores(query_tokens)
        top_idx = int(np.argmax(scores))
        assert "80C" in chunks[top_idx]["text"] or "80c" in chunks[top_idx]["text"].lower(), (
            "BM25 top result for '80C' query does not contain '80C'"
        )

    def test_bm25_search_hra(
        self, chunks: list[dict[str, Any]], bm25: BM25Okapi
    ) -> None:
        query_tokens = "hra house rent allowance exempt".split()
        scores = bm25.get_scores(query_tokens)
        top_idx = int(np.argmax(scores))
        top_text = chunks[top_idx]["text"].lower()
        assert "hra" in top_text or "house rent" in top_text or "10(13a)" in top_text, (
            "BM25 top result for HRA query does not mention HRA-related content"
        )

    def test_bm25_search_standard_deduction(
        self, chunks: list[dict[str, Any]], bm25: BM25Okapi
    ) -> None:
        query_tokens = "standard deduction fifty thousand salary".split()
        scores = bm25.get_scores(query_tokens)
        top_idx = int(np.argmax(scores))
        top_text = chunks[top_idx]["text"].lower()
        assert "standard deduction" in top_text or "section 16" in top_text, (
            "BM25 top result for standard deduction query lacks relevant content"
        )


# ---------------------------------------------------------------------------
# 5. Critical content verification — Section 87A (dual regime)
# ---------------------------------------------------------------------------


class TestCriticalContent87A:
    def test_87a_contains_old_regime_threshold(self, chunks: list[dict[str, Any]]) -> None:
        """Section 87A chunk must mention ₹5,00,000 old regime threshold."""
        s87a_chunks = [c for c in chunks if c["source_file"] == "section_87a.txt"]
        assert s87a_chunks, "No chunks found for section_87a.txt"
        combined = " ".join(c["text"] for c in s87a_chunks)
        assert "5,00,000" in combined or "500000" in combined or "five lakh" in combined.lower(), (
            "section_87a.txt does not mention old regime ₹5,00,000 threshold"
        )

    def test_87a_contains_new_regime_threshold(self, chunks: list[dict[str, Any]]) -> None:
        """Section 87A chunk must mention ₹12,00,000 new regime threshold."""
        s87a_chunks = [c for c in chunks if c["source_file"] == "section_87a.txt"]
        combined = " ".join(c["text"] for c in s87a_chunks)
        assert "12,00,000" in combined or "1200000" in combined or "twelve lakh" in combined.lower(), (
            "section_87a.txt does not mention new regime ₹12,00,000 threshold"
        )

    def test_87a_mentions_marginal_relief(self, chunks: list[dict[str, Any]]) -> None:
        s87a_chunks = [c for c in chunks if c["source_file"] == "section_87a.txt"]
        combined = " ".join(c["text"] for c in s87a_chunks).lower()
        assert "marginal relief" in combined, (
            "section_87a.txt does not mention marginal relief"
        )


# ---------------------------------------------------------------------------
# 6. Critical content verification — Section 115BAC (new regime slabs)
# ---------------------------------------------------------------------------


class TestCriticalContent115BAC:
    def test_115bac_contains_ay2025_26_slabs(self, chunks: list[dict[str, Any]]) -> None:
        bac_chunks = [c for c in chunks if c["source_file"] == "section_115bac.txt"]
        assert bac_chunks, "No chunks found for section_115bac.txt"
        combined = " ".join(c["text"] for c in bac_chunks)
        # The new AY2025-26 slab has 3,00,000 basic exemption and 7,00,000 first bracket
        assert "3,00,000" in combined or "300000" in combined, (
            "section_115bac.txt does not mention ₹3,00,000 basic exemption"
        )

    def test_115bac_mentions_standard_deduction_75000(self, chunks: list[dict[str, Any]]) -> None:
        bac_chunks = [c for c in chunks if c["source_file"] == "section_115bac.txt"]
        combined = " ".join(c["text"] for c in bac_chunks)
        assert "75,000" in combined or "seventy-five thousand" in combined.lower(), (
            "section_115bac.txt does not mention ₹75,000 standard deduction"
        )

    def test_115bac_lists_unavailable_deductions(self, chunks: list[dict[str, Any]]) -> None:
        bac_chunks = [c for c in chunks if c["source_file"] == "section_115bac.txt"]
        combined = " ".join(c["text"] for c in bac_chunks).lower()
        assert "80c" in combined and "not available" in combined, (
            "section_115bac.txt does not mention 80C unavailability under new regime"
        )


# ---------------------------------------------------------------------------
# 7. FAISS semantic search quality spot-check
# ---------------------------------------------------------------------------


class TestFAISSSemanticSearch:
    def test_faiss_top_result_for_nps_query(
        self,
        faiss_index: faiss.IndexFlatIP,
        chunks: list[dict[str, Any]],
        model: SentenceTransformer,
    ) -> None:
        """Query about NPS 80CCD(1B) ₹50,000 should surface the 80CCD file."""
        query = "NPS additional deduction 50000 80CCD 1B"
        vec = model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        _, indices = faiss_index.search(vec, k=10)
        top_sources = [chunks[i]["source_file"] for i in indices[0] if i >= 0]
        assert "section_80ccd.txt" in top_sources, (
            f"NPS query top-10 FAISS results do not include section_80ccd.txt. Got: {top_sources}"
        )

    def test_faiss_top_result_for_hra_query(
        self,
        faiss_index: faiss.IndexFlatIP,
        chunks: list[dict[str, Any]],
        model: SentenceTransformer,
    ) -> None:
        query = "HRA exemption metro city rent allowance calculation"
        vec = model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        _, indices = faiss_index.search(vec, k=10)
        top_sources = [chunks[i]["source_file"] for i in indices[0] if i >= 0]
        hra_files = {"section_10_13a.txt", "hra_rule_2a.txt"}
        assert hra_files.intersection(top_sources), (
            f"HRA query top-10 FAISS results do not include HRA files. Got: {top_sources}"
        )
