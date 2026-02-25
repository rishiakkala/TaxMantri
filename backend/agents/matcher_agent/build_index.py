"""
build_index.py — Phase 4 RAG Knowledge Base Ingestion Pipeline
===============================================================
Reads raw .txt files from knowledge_base/raw/, chunks them using the
BGE-M3 tokenizer (500-token chunks, 50-token overlap), embeds with
BAAI/bge-m3, builds FAISS IndexFlatIP (cosine-similarity ready), and
serialises chunk metadata as chunks.pkl for BM25 + retrieval.

Usage (from TaxMantri/ project root):
    python -m backend.agents.matcher_agent.build_index

Outputs:
    knowledge_base/indexes/kb.faiss
    knowledge_base/indexes/chunks.pkl

Requirements (already pinned in requirements.txt):
    sentence-transformers>=3.3.1
    faiss-cpu>=1.9.0
    rank-bm25>=0.2.2
    numpy<2.0
"""

from __future__ import annotations

import logging
import pickle
import sys
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths (resolved relative to this file so the script works from any cwd)
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent.parent  # TaxMantri/

RAW_DIR: Path = _PROJECT_ROOT / "knowledge_base" / "raw"
INDEX_DIR: Path = _PROJECT_ROOT / "knowledge_base" / "indexes"

# ---------------------------------------------------------------------------
# Chunking hyper-parameters (from 04-RESEARCH.md spec)
# ---------------------------------------------------------------------------
CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50
MODEL_NAME = "BAAI/bge-m3"

# ---------------------------------------------------------------------------
# Source file catalogue
# Maps filename stem → section_ref (used in chunk metadata)
# ---------------------------------------------------------------------------
FILE_CATALOGUE: dict[str, str] = {
    "section_15": "IT Act S.15",
    "section_16": "IT Act S.16",
    "section_10_13a": "IT Act S.10(13A)",
    "section_10_5": "IT Act S.10(5)",
    "section_10_10d": "IT Act S.10(10D)",
    "section_24": "IT Act S.24",
    "section_80c": "IT Act S.80C",
    "section_80d": "IT Act S.80D",
    "section_80ccd": "IT Act S.80CCD",
    "section_80e": "IT Act S.80E",
    "section_80g": "IT Act S.80G",
    "section_80tta": "IT Act S.80TTA",
    "section_87a": "IT Act S.87A",
    "section_89a": "IT Act S.89A",
    "section_115bac": "IT Act S.115BAC",
    "hra_rule_2a": "IT Rules Rule 2A",
    "budget_2025_amendments": "Budget 2025",
    "itr1_instructions": "ITR-1 Instructions",
    "form16_guide": "Form 16 Guide",
}

ASSESSMENT_YEAR = "AY2025-26"


# ---------------------------------------------------------------------------
# Preflight: verify every source file exists
# ---------------------------------------------------------------------------
def _preflight_check() -> list[Path]:
    """Confirm all expected source files are present; exit loudly if not."""
    missing: list[str] = []
    found: list[Path] = []
    for stem in FILE_CATALOGUE:
        path = RAW_DIR / f"{stem}.txt"
        if path.is_file():
            found.append(path)
        else:
            missing.append(str(path))
    if missing:
        log.error("Preflight FAILED — %d missing file(s):", len(missing))
        for m in missing:
            log.error("  MISSING: %s", m)
        sys.exit(1)
    log.info("Preflight OK — %d source files found.", len(found))
    return found


# ---------------------------------------------------------------------------
# Tokeniser-aware chunking
# ---------------------------------------------------------------------------
def _chunk_text(
    text: str,
    tokenizer: Any,
    chunk_size: int = CHUNK_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[str]:
    """
    Split *text* into overlapping token windows using *tokenizer*.

    Returns a list of decoded text chunks. Each chunk contains at most
    *chunk_size* tokens, and consecutive chunks share *overlap* tokens.
    """
    token_ids: list[int] = tokenizer.encode(text, add_special_tokens=False)
    chunks: list[str] = []
    start = 0
    while start < len(token_ids):
        end = min(start + chunk_size, len(token_ids))
        chunk_ids = token_ids[start:end]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        chunks.append(chunk_text.strip())
        if end == len(token_ids):
            break
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main(raw_dir: Path = RAW_DIR, index_dir: Path = INDEX_DIR) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Preflight
    # ------------------------------------------------------------------
    source_files = _preflight_check()

    # ------------------------------------------------------------------
    # 2. Load model (downloads on first run; cached thereafter)
    # ------------------------------------------------------------------
    log.info("Loading model: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)
    tokenizer = model.tokenizer
    log.info("Model loaded. Embedding dimension: %d", model.get_sentence_embedding_dimension())

    # ------------------------------------------------------------------
    # 3. Read, chunk, attach metadata
    # ------------------------------------------------------------------
    all_chunks: list[dict[str, Any]] = []

    for path in sorted(source_files, key=lambda p: list(FILE_CATALOGUE.keys()).index(p.stem)):
        stem = path.stem
        section_ref = FILE_CATALOGUE[stem]
        raw_text = path.read_text(encoding="utf-8")

        text_chunks = _chunk_text(raw_text, tokenizer)
        log.info("  %s → %d chunk(s)", stem, len(text_chunks))

        for idx, chunk_text in enumerate(text_chunks):
            chunk_id = f"{stem}_chunk_{idx:03d}"
            all_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source_file": path.name,
                    "section_ref": section_ref,
                    "assessment_year": ASSESSMENT_YEAR,
                    "chunk_index": idx,
                    "text": chunk_text,
                }
            )

    total_chunks = len(all_chunks)
    log.info("Total chunks: %d", total_chunks)

    # Sanity: duplicate chunk_id check
    chunk_ids = [c["chunk_id"] for c in all_chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        duplicates = [cid for cid in chunk_ids if chunk_ids.count(cid) > 1]
        log.error("Duplicate chunk IDs detected: %s", set(duplicates))
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Embed all chunks
    # ------------------------------------------------------------------
    log.info("Embedding %d chunks (this may take a few minutes)...", total_chunks)
    texts = [c["text"] for c in all_chunks]
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,   # L2-normalise for cosine via dot product
        convert_to_numpy=True,
    )
    embeddings = embeddings.astype("float32")
    log.info("Embeddings shape: %s", embeddings.shape)

    # ------------------------------------------------------------------
    # 5. Build FAISS IndexFlatIP (inner-product on L2-normed = cosine)
    # ------------------------------------------------------------------
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    log.info("FAISS index built — %d vectors, dimension %d", index.ntotal, dim)

    faiss_path = index_dir / "kb.faiss"
    faiss.write_index(index, str(faiss_path))
    log.info("FAISS index saved → %s", faiss_path)

    # ------------------------------------------------------------------
    # 6. Pickle chunk metadata (used for BM25 + retrieval)
    # ------------------------------------------------------------------
    pkl_path = index_dir / "chunks.pkl"
    with open(pkl_path, "wb") as fh:
        pickle.dump(all_chunks, fh)
    log.info("Chunk metadata saved → %s", pkl_path)

    log.info(
        "✓ Phase 4 indexing complete: %d chunks, FAISS=%s, PKL=%s",
        total_chunks,
        faiss_path,
        pkl_path,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
