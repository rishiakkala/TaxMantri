"""
retriever.py — TaxRetriever: hybrid FAISS + BM25 retrieval with RRF fusion.

Loaded ONCE at FastAPI startup (lifespan event). Stored on app.state.retriever.
If Phase 4 indexes are not found, raises FileNotFoundError — caller in main.py
catches this and sets app.state.retriever = None for graceful 503 degradation.

Retrieval strategy:
  - Dense:  FAISS IndexFlatIP (cosine similarity via normalize_embeddings=True)
  - Sparse: BM25Okapi reconstructed from chunks.pkl at startup (never pickled separately)
  - Fusion: Reciprocal Rank Fusion score = sum(1/(60+rank+1)) across both result lists
            where rank is 0-indexed (rank=0 → 1/61, matching 1-indexed 1/(60+rank) formula)
  - Dedup:  chunk_id-keyed dict ensures scores are summed, not duplicated
"""
import logging
import pickle
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Paths relative to project root (D:/TaxMantri/) — FastAPI is run from there
FAISS_PATH = Path("knowledge_base/indexes/kb.faiss")
CHUNKS_PATH = Path("knowledge_base/indexes/chunks.pkl")
EMBED_MODEL = "BAAI/bge-m3"


class TaxRetriever:
    """
    Hybrid retriever for the TaxMantri knowledge base.

    Attributes:
        index:  FAISS IndexFlatIP loaded from kb.faiss
        chunks: List of chunk dicts from chunks.pkl
        bm25:   BM25Okapi reconstructed from chunk texts at startup
        model:  SentenceTransformer for query embedding (same model as build_index.py)
    """

    def __init__(self) -> None:
        # --- FAISS dense index ---
        if not FAISS_PATH.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {FAISS_PATH}. "
                "Run: python -m backend.agents.matcher_agent.build_index"
            )
        logger.info("Loading FAISS index from %s", FAISS_PATH)
        self.index: faiss.IndexFlatIP = faiss.read_index(str(FAISS_PATH))
        logger.info(
            "FAISS index loaded: %d vectors, d=%d", self.index.ntotal, self.index.d
        )

        # --- Chunks (metadata + text) ---
        if not CHUNKS_PATH.exists():
            raise FileNotFoundError(
                f"Chunks file not found at {CHUNKS_PATH}. "
                "Run: python -m backend.agents.matcher_agent.build_index"
            )
        logger.info("Loading chunks from %s", CHUNKS_PATH)
        with open(CHUNKS_PATH, "rb") as f:
            self.chunks: list[dict] = pickle.load(f)
        logger.info("Loaded %d chunks", len(self.chunks))

        # --- BM25 sparse index — reconstructed at startup, never pickled ---
        logger.info(
            "Building BM25 index from %d chunks (reconstructing at startup)",
            len(self.chunks),
        )
        tokenized = [c["text"].lower().split() for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)
        logger.info("BM25 index built")

        # --- Embedding model (same as build_index.py — dimension must match FAISS) ---
        logger.info("Loading embedding model: %s", EMBED_MODEL)
        self.model = SentenceTransformer(EMBED_MODEL)
        embed_dim = self.model.get_sentence_embedding_dimension()
        assert embed_dim == self.index.d, (
            f"Embedding model dimension mismatch: model produces {embed_dim}-dim vectors "
            f"but FAISS index expects {self.index.d}-dim. "
            "Ensure retriever.py uses the same model as build_index.py."
        )
        logger.info(
            "TaxRetriever ready: model_dim=%d, chunks=%d", embed_dim, len(self.chunks)
        )

    def dense_search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        """
        Embed query with BGE-M3 and search FAISS index.
        Returns list of (chunk_index, cosine_score) pairs, top_k results.
        Uses normalize_embeddings=True for cosine similarity via inner product.
        """
        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        embedding_np = np.array(embedding, dtype=np.float32)
        scores, indices = self.index.search(embedding_np, top_k)
        return [
            (int(idx), float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx >= 0  # FAISS returns -1 for empty slots
        ]

    def sparse_search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        """
        Tokenize query and search BM25 index.
        Returns list of (chunk_index, bm25_score) pairs, top_k results.
        """
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices]

    def hybrid_search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Reciprocal Rank Fusion of dense + sparse results.

        Formula: score(chunk) = sum(1 / (60 + rank + 1)) across both result lists
        where rank is 0-indexed position in each list.
        (rank=0 → 1/61, equivalent to 1-indexed 1/(60+rank) with rank=1 → 1/61)

        Deduplication: chunk_id-keyed dict accumulates scores.
        A chunk appearing in both lists gets scores SUMMED, not duplicated.

        Returns: top_k chunk dicts from chunks.pkl, sorted by RRF score descending.
        """
        dense_results = self.dense_search(query, top_k=20)
        sparse_results = self.sparse_search(query, top_k=20)

        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, dict] = {}

        # Dense results — rank 0 = best match
        for rank, (chunk_idx, _score) in enumerate(dense_results):
            chunk = self.chunks[chunk_idx]
            cid = chunk["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (60 + rank + 1)
            chunk_map[cid] = chunk

        # Sparse results — scores ACCUMULATED (not overwritten) for shared chunk_ids
        for rank, (chunk_idx, _score) in enumerate(sparse_results):
            chunk = self.chunks[chunk_idx]
            cid = chunk["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (60 + rank + 1)
            chunk_map[cid] = chunk

        # Sort by RRF score DESC; use chunk_id as deterministic tie-breaker
        sorted_ids = sorted(
            rrf_scores.keys(), key=lambda cid: (-rrf_scores[cid], cid)
        )
        return [chunk_map[cid] for cid in sorted_ids[:top_k]]
