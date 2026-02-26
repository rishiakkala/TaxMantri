"""
llm_service.py — Mistral async generation layer for TaxMantri RAG.

Components:
  SYSTEM_PROMPT       — unified tone/behavior constraint (handles both KB and user data)
  build_user_prompt() — context blocks + optional profile_summary + tax_result_summary
  build_profile_summary() — PII-stripped numeric-only summary for Mistral context
  build_tax_result_summary() — computed tax result summary for personalized answers
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
MISTRAL_MAX_TOKENS = 800    # Increased for fuller, more complete answers


# ---------------------------------------------------------------------------
# System prompt — unified prompt handling both KB context and user data
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are TaxMantri, an Indian income tax expert assistant for ITR-1 filers (AY 2025-26), powered by Mistral.

You have two types of information available:
  A. **IT Act Knowledge Base** — retrieved chunks of the Income Tax Act 1961, labelled [Context N — section_ref]. Use these for legal/factual questions.
  B. **User's personal tax data** — their profile (salary, deductions) and calculated tax result (regime recommendation, savings, breakdown), labelled under 'User profile' and 'User's calculated tax result'. Use this for personalised questions about their specific situation.

Rules you MUST follow:
1. Use BOTH types of information above. Do not refuse to answer if the information is present in either A or B.
2. For legal or factual claims from the IT Act (type A), you MUST cite every single claim using EXACTLY this format: [Section X, IT Act 1961] or [Rule X, IT Rules 1962]. Do not write citations any other way. Always include the brackets, the word Section or Rule, and the year. Examples: [Section 80C, IT Act 1961], [Section 10(13A), IT Act 1961], [Rule 2A, IT Rules 1962].
3. For personalised answers using the user's own data (type B), clearly prefix with "Based on your tax data:" and state the specific figures. You do NOT need IT Act citations for the user's own numbers, but DO cite the law when explaining how a deduction or slab is calculated.
4. If the answer is truly not available in either type A or B, respond: "I could not find a verified source for this — please consult a CA or the Income Tax portal."
5. For yes/no questions, begin with "Yes" or "No" before explaining.
6. Keep answers concise — 3 to 5 sentences. Show calculation formulas when relevant.
7. Write as a CA explaining to a client: accurate, warm, professional, no legal jargon."""


# ---------------------------------------------------------------------------
# Citation extraction regex
# ---------------------------------------------------------------------------

# Matches citation formats Mistral actually produces, e.g.:
#   [Section 80C, IT Act 1961]
#   [Section 10(13A), Income Tax Act, 1961]
#   [Rule 2A, IT Rules 1962]
#   [Sec. 80D, Income Tax Act 1961]
CITATION_REGEX = re.compile(
    r'\['
    r'(?:Section|Sec\.?|Rule|Regulation)\s+'
    r'([\w().,\d\s/-]+?)'
    r'(?:,\s*|\s+of\s+the\s+)'
    r'(?:IT Act|Income Tax Act|I\.T\. Act|IT Rules|Income Tax Rules)'
    r'[,\s\d]*'
    r'\]',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_user_prompt(
    question: str,
    chunks: list[dict],
    profile_summary: Optional[str],
    tax_result_summary: Optional[str] = None,
) -> str:
    """
    Build the user-turn prompt for Mistral.
    Chunks are numbered [Context N — section_ref] blocks.
    profile_summary is appended only if provided (PII-stripped numeric values only).
    tax_result_summary is appended if provided (regime recommendation, savings, breakdown).
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

    tax_result_section = (
        f"\n\nUser's calculated tax result (use this for personalised answers):\n{tax_result_summary}"
        if tax_result_summary else ""
    )

    return f"Context:\n{context_text}{profile_section}{tax_result_section}\n\nQuestion: {question}"


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


def build_tax_result_summary(tax_result) -> str:
    """
    Build a concise summary of the calculated tax result for Mistral context.
    Includes recommended regime, savings amount, and key breakdown figures
    for both old and new regimes so the chatbot can answer personalised questions.
    """
    if tax_result is None:
        return ""

    rec = tax_result.recommended_regime or "unknown"
    savings = int(tax_result.savings_amount or 0)

    old = tax_result.old_regime
    new = tax_result.new_regime

    parts = [
        f"Recommended regime: {rec} regime",
        f"Tax savings by choosing {rec} regime: ₹{savings:,}",
    ]

    if old:
        parts.append(
            f"Old Regime — Gross income: ₹{int(old.gross_income or 0):,}, "
            f"Total deductions: ₹{int(old.total_deductions or 0):,}, "
            f"Taxable income: ₹{int(old.taxable_income or 0):,}, "
            f"Total tax: ₹{int(old.total_tax or 0):,}"
        )
    if new:
        parts.append(
            f"New Regime — Gross income: ₹{int(new.gross_income or 0):,}, "
            f"Total deductions: ₹{int(new.total_deductions or 0):,}, "
            f"Taxable income: ₹{int(new.taxable_income or 0):,}, "
            f"Total tax: ₹{int(new.total_tax or 0):,}"
        )

    if tax_result.rationale:
        parts.append(f"AI rationale: {tax_result.rationale[:300]}")

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
    tax_result_summary: Optional[str] = None,
) -> dict:
    """
    Generate a grounded answer from Mistral API using the unified system prompt.

    The single SYSTEM_PROMPT handles both KB-grounded and personalised answers.
    Applies asyncio.Semaphore(2) for rate-limit protection.
    Validates citations after generation via validate_citations().

    Returns dict with keys: answer, citations, confidence, answer_mode
    (does NOT include 'cached' — caller sets that field)
    """
    use_kb = len(chunks) > 0 and any(c.get("text") for c in chunks)
    answer_mode = "kb_grounded" if use_kb else "general"

    prompt = build_user_prompt(question, chunks, profile_summary, tax_result_summary)

    logger.info(
        "Calling Mistral API model=%s chunks=%d answer_mode=%s",
        MISTRAL_MODEL, len(chunks), answer_mode,
    )

    async with semaphore:
        response = await client.chat.complete_async(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
