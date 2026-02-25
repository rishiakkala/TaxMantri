"""
llm_service.py — Mistral async generation layer for TaxMantri RAG.

Components:
  SYSTEM_PROMPT       — all 6 locked tone/behavior constraints from CONTEXT.md
  build_user_prompt() — context blocks + optional profile_summary + question
  build_profile_summary() — PII-stripped numeric-only summary for Mistral context
  validate_citations() — regex extraction + cross-check against retrieved chunks
  generate_answer()   — async Mistral call wrapped in asyncio.Semaphore(2)

No module-level asyncio.Semaphore — semaphore is created in main.py lifespan
and passed as a parameter (avoids RuntimeError: no running event loop at import).

No HTTPException anywhere — this is pure business logic, HTTP layer is routes.py.
"""
import asyncio
import logging
import re
from typing import TYPE_CHECKING, Optional

from mistralai import Mistral

if TYPE_CHECKING:
    from backend.agents.input_agent.schemas import UserFinancialProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mistral API constants
# ---------------------------------------------------------------------------

MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_TEMPERATURE = 0.1   # Low temperature for citation compliance
MISTRAL_MAX_TOKENS = 512


# ---------------------------------------------------------------------------
# System prompts — grounded (KB chunks available) and open (no relevant chunks)
# ---------------------------------------------------------------------------

# Used when FAISS + BM25 retrieval returned relevant IT Act chunks.
SYSTEM_PROMPT_GROUNDED = """You are TaxMantri, an Indian income tax expert for ITR-1 filers (AY 2025-26).

Rules you MUST follow:
1. Answer ONLY from the context provided. Do not use outside knowledge.
2. If the answer is not in the context, respond with exactly this phrase: "I could not find a verified source for this in my knowledge base." Then add: "Note: This answer is not from my verified knowledge base — please verify independently with a CA or official source."
3. For yes/no questions, begin your answer with "Yes" or "No" before explaining.
4. Cite every factual claim using the format: [Section X, IT Act 1961] or [Rule X, IT Rules 1962]. Example: [Section 10(13A), IT Act 1961]. You MUST cite every factual claim — if you cannot cite it, do not state it.
5. Keep your answer concise — 2 to 4 sentences maximum.
6. Show formulas when they help. For HRA questions, include the Rule 2A min-of-3 formula.
7. Write as a CA explaining to a client — accurate, warm, professional, no legal jargon."""

# Used when retrieval found no relevant chunks — open general-knowledge fallback.
SYSTEM_PROMPT_OPEN = """You are TaxMantri, an Indian income tax expert for ITR-1 filers (AY 2025-26).

Rules you MUST follow:
1. Answer using your general knowledge of Indian income tax law and ITR-1 filing.
2. Keep your answer concise — 2 to 4 sentences maximum.
3. For yes/no questions, begin your answer with "Yes" or "No" before explaining.
4. Show formulas when they help.
5. Always end your answer with this disclaimer on a new line: "Note: This answer is based on general knowledge — please verify with a CA or the Income Tax Department before filing."
6. Write as a CA explaining to a client — accurate, warm, professional, no legal jargon."""


# ---------------------------------------------------------------------------
# Citation extraction regex
# ---------------------------------------------------------------------------

CITATION_REGEX = re.compile(
    r'\[(?:Section|Rule)\s+([\w().,\s-]+),\s*(?:IT Act 1961|Income Tax Act|IT Rules 1962)\]',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_user_prompt(
    question: str,
    chunks: list[dict],
    profile_summary: Optional[str],
    session_context: Optional[str] = None,
) -> str:
    """
    Build the user-turn prompt for Mistral (KB-grounded path).
    Chunks are numbered [Context N — section_ref] blocks.
    profile_summary is appended only if provided (PII-stripped numeric values only).
    session_context is appended only if provided (derived session metrics, no PII).
    """
    context_blocks = []
    for i, chunk in enumerate(chunks, 1):
        context_blocks.append(
            f"[Context {i} — {chunk['section_ref']}]\n{chunk['text']}"
        )
    context_text = "\n\n".join(context_blocks)

    profile_section = (
        f"\n\nUser profile (numeric summary — no PII):\n{profile_summary}"
        if profile_summary else ""
    )

    session_section = (
        f"\n\nSession context:\n{session_context}"
        if session_context else ""
    )

    return f"Context:\n{context_text}{profile_section}{session_section}\n\nQuestion: {question}"


def build_open_prompt(
    question: str,
    profile_summary: Optional[str],
    session_context: Optional[str] = None,
) -> str:
    """
    Build the user-turn prompt for the open/general fallback path (no KB chunks).
    """
    profile_section = (
        f"\n\nUser profile (numeric summary — no PII):\n{profile_summary}"
        if profile_summary else ""
    )
    session_section = (
        f"\n\nSession context:\n{session_context}"
        if session_context else ""
    )
    return f"{profile_section}{session_section}\n\nQuestion: {question}".lstrip()


def build_profile_summary(profile: "UserFinancialProfile") -> str:
    """
    Build a PII-stripped numeric summary for Mistral context.
    CLAUDE.md rule: only numeric values — no name, PAN, email, or phone.
    """
    parts = [
        f"Annual basic salary: {int(profile.basic_salary):,}",
        f"HRA received (annual): {int(profile.hra_received or 0):,}",
        f"Monthly rent paid: {int(profile.monthly_rent_paid or 0):,}",
        f"City type: {profile.city_type.value}",
        f"Age bracket: {profile.age_bracket.value}",
        f"80C investments: {int(profile.investments_80c or 0):,}",
        f"80D self insurance: {int(profile.health_insurance_self or 0):,}",
        f"Home loan interest: {int(profile.home_loan_interest or 0):,}",
        f"NPS employee (80CCD1B): {int(profile.employee_nps_80ccd1b or 0):,}",
    ]
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------

def validate_citations(
    answer: str,
    chunks: list[dict],
) -> tuple[list[dict], str]:
    """
    Extract [Section X, IT Act 1961] / [Rule X, IT Rules 1962] citations from
    answer text and cross-check that each section reference appears verbatim
    in at least one of the retrieved chunks.

    Returns:
        citations:  List of {section: str, excerpt: str} dicts (CitationObject shape)
        confidence: "high" if at least one citation found AND all pass cross-check
                    "low"  if no citations, any cross-check fails, or out-of-KB fallback
    """
    matches = CITATION_REGEX.findall(answer)

    if not matches:
        return [], "low"

    citations = []
    all_verified = True

    for raw_section in matches:
        section_ref = raw_section.strip()

        # Cross-check: section string must appear verbatim in at least one chunk text.
        # Also try a loose match (strip internal spaces/periods) to handle formatting
        # differences like "80C. (2)(a)" vs "80C(2)(a)".
        section_stripped = re.sub(r"[\s.]", "", section_ref)

        supporting_chunk = next(
            (
                c for c in chunks
                if section_ref in c["text"]
                or section_stripped in re.sub(r"[\s.]", "", c["text"])
            ),
            None,
        )

        if supporting_chunk is None:
            all_verified = False
            citations.append({"section": f"Section {section_ref}", "excerpt": ""})
        else:
            # Extract a short excerpt around the match
            text = supporting_chunk["text"]
            idx = text.find(section_ref)
            if idx == -1:
                idx = 0  # loose match succeeded — use beginning as fallback
            start = max(0, idx - 30)
            end = min(len(text), idx + len(section_ref) + 100)
            citations.append({
                "section": f"Section {section_ref}",
                "excerpt": text[start:end].strip(),
            })

    confidence = "high" if (citations and all_verified) else "low"
    return citations, confidence


# ---------------------------------------------------------------------------
# Main async generation function
# ---------------------------------------------------------------------------

async def generate_answer(
    client: Mistral,
    question: str,
    chunks: list[dict],
    profile_summary: Optional[str],
    semaphore: asyncio.Semaphore,
    session_context: Optional[str] = None,
) -> dict:
    """
    Generate a grounded or open answer from Mistral API.

    Routing:
      - chunks present → KB-grounded path: SYSTEM_PROMPT_GROUNDED + IT Act context blocks
      - no chunks      → open fallback path: SYSTEM_PROMPT_OPEN + general knowledge

    Applies asyncio.Semaphore(2) for rate-limit protection.
    Validates citations after generation via validate_citations().

    Returns dict with keys: answer, citations, confidence, answer_mode
    (does NOT include 'cached' — caller sets that field)
    """
    use_kb = len(chunks) > 0 and any(c.get("text") for c in chunks)

    if use_kb:
        system_prompt = SYSTEM_PROMPT_GROUNDED
        prompt = build_user_prompt(question, chunks, profile_summary, session_context)
        answer_mode = "kb_grounded"
    else:
        system_prompt = SYSTEM_PROMPT_OPEN
        prompt = build_open_prompt(question, profile_summary, session_context)
        answer_mode = "general"

    logger.info(
        "Calling Mistral API model=%s chunks=%d answer_mode=%s",
        MISTRAL_MODEL, len(chunks), answer_mode,
    )

    async with semaphore:
        response = await client.chat.complete_async(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=MISTRAL_TEMPERATURE,
            max_tokens=MISTRAL_MAX_TOKENS,
        )

    answer_text: str = response.choices[0].message.content or ""
    logger.info("Mistral response received answer_len=%d answer_mode=%s", len(answer_text), answer_mode)

    citations, confidence = validate_citations(answer_text, chunks)
    logger.info(
        "Citation validation: citations=%d confidence=%s", len(citations), confidence
    )

    return {
        "answer": answer_text,
        "citations": citations,
        "confidence": confidence,
        "answer_mode": answer_mode,
    }
