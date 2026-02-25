"""
schemas.py — MatcherAgent Pydantic v2 data contracts.

Defines:
  - CitationObject    (single legal citation with supporting excerpt)
  - ConfidenceLevel   enum (high / low — two levels only per CONTEXT.md)
  - ChatMessage       (single turn in conversation history)
  - QueryRequest      (incoming RAG query from client)
  - RAGResponse       (LLM answer with structured citations)

Citation format enforced downstream by llm_service.py:
  r'\[(?:Section|Rule)\s+[\w().,\s-]+,\s*(?:IT Act 1961|Income Tax Act|IT Rules 1962)\]'
"""
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    high = "high"   # All citations verified against retrieved chunks
    low = "low"     # No citations found, cross-check failed, or out-of-KB answer
    # 'medium' removed per CONTEXT.md — only two confidence levels in v1


# ---------------------------------------------------------------------------
# Citation object
# ---------------------------------------------------------------------------

class CitationObject(BaseModel):
    """A single legal citation extracted from a RAG answer, with supporting evidence."""
    model_config = ConfigDict(extra="forbid")

    section: str = Field(
        description="Cited section reference, e.g. 'Section 10(13A)'"
    )
    excerpt: str = Field(
        description=(
            "Short supporting text excerpt from the retrieved chunk where this citation "
            "was found. Empty string if citation cross-check failed (section not found in chunks)."
        )
    )


# ---------------------------------------------------------------------------
# Chat models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Single turn in a conversation history for a session."""
    model_config = ConfigDict(extra="forbid")

    role: str = Field(description="'user' or 'assistant'")
    content: str
    timestamp: Optional[str] = None  # ISO 8601 — set server-side


# ---------------------------------------------------------------------------
# QueryRequest — incoming client request
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """
    Incoming RAG query from the client.

    profile_id is optional — if provided, the LLM context includes a
    PII-stripped numeric profile summary for personalised answers.
    session_id is required for chat history tracking and FAQ cache keying.
    """
    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Tax question from the user. Must be at least 3 characters.",
    )
    profile_id: Optional[str] = None  # Links query to a financial profile for context
    session_id: str = Field(
        ...,
        min_length=1,
        description="Session identifier for chat history and FAQ cache.",
    )


# ---------------------------------------------------------------------------
# RAGResponse — LLM answer with structured citations
# ---------------------------------------------------------------------------

class SessionEventRequest(BaseModel):
    """Incoming UI interaction event from the frontend."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., min_length=1, description="Session identifier")
    event_type: str = Field(
        ...,
        description="Category of action: tab_click, page_view, pdf_download, regime_compare, chat_open",
    )
    payload: dict = Field(default_factory=dict, description="Structured event context — no PII")


class RAGResponse(BaseModel):
    """
    Output of MatcherAgent — LLM answer with structured legal citations.

    citations: list of CitationObject, each with 'section' and 'excerpt'.
    confidence='high' means at least one citation was found AND all citations
    were verified against retrieved chunks (section number exists verbatim in chunk text).
    confidence='low' means no citations, cross-check failed, or out-of-KB answer.

    cached=True means this answer was served from the Redis FAQ cache
    (TTL 1 hour) without calling the LLM.

    answer_mode='kb_grounded' means the answer used retrieved IT Act chunks.
    answer_mode='general' means no relevant chunks were found and Mistral answered
    from general knowledge (with a disclaimer appended).

    retrieved_chunks: only present when ?debug=true is set. Not part of
    the normal response contract — excluded from serialization by default.
    """
    model_config = ConfigDict(extra="ignore")  # allow retrieved_chunks to pass through

    answer: str
    citations: List[CitationObject] = Field(
        default_factory=list,
        description=(
            "Legal citations extracted from the answer. Each citation has 'section' "
            "(e.g. 'Section 10(13A)') and 'excerpt' (supporting chunk text). "
            "Validated via regex + cross-check against retrieved chunks."
        ),
    )
    confidence: ConfidenceLevel
    cached: bool = Field(
        default=False,
        description="True if this response was served from Redis FAQ cache.",
    )
    answer_mode: Literal["kb_grounded", "general"] = Field(
        default="kb_grounded",
        description="'kb_grounded' if answered from IT Act KB; 'general' if KB had no relevant chunks.",
    )


__all__ = [
    "CitationObject",
    "ConfidenceLevel",
    "ChatMessage",
    "QueryRequest",
    "RAGResponse",
    "SessionEventRequest",
]
