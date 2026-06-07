"""Resolve a free-text programme choice to a UJ faculty + an eligible LOV entry.

`application.programme` is free text ("Civil Engineering", "Computer Science",
"BCom Accounting"). UJ's Page E needs (1) one of its eight faculties, then (2) a
programme picked from that faculty's LOV, whose rows are
`CODE (ELIGIBLE TO APPLY-Y/N) - DESCRIPTION` — UJ precomputes eligibility from the
captured marks, and we must never submit an ineligible (`-N`) programme.

`resolve_faculty` keyword-maps the text to a faculty; `best_programme_match`
scores the free text against the live LOV descriptions, considering **eligible
rows only**, and returns the row to click (or None → flag for review rather than
guess). The faculty list was harvested live 2026-06-06.
"""

import re

# Exact faculty LOV strings (harvested).
ART_DESIGN = "ART, DESIGN AND ARCHITECTURE"
BUSINESS = "COLLEGE OF BUSINESS &ECONOMICS"
EDUCATION = "EDUCATION"
ENGINEERING = "ENGINEERING&BUILT ENVIRONMENT"
SCIENCE = "FACULTY OF SCIENCE"
HEALTH = "HEALTH SCIENCES"
HUMANITIES = "HUMANITIES"
LAW = "LAW"

UJ_FACULTIES = frozenset(
    {ART_DESIGN, BUSINESS, EDUCATION, ENGINEERING, SCIENCE, HEALTH, HUMANITIES, LAW}
)

# Keyword → faculty, checked IN ORDER (first substring hit wins), so the more
# discriminating keywords come before generic degree words like "bsc"/"ba".
_FACULTY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("architecture", ART_DESIGN), ("design", ART_DESIGN), ("fine art", ART_DESIGN),
    ("fashion", ART_DESIGN), ("jewellery", ART_DESIGN), ("multimedia", ART_DESIGN),
    ("graphic", ART_DESIGN),
    ("llb", LAW), ("laws", LAW), ("law", LAW),
    ("education", EDUCATION), ("teaching", EDUCATION), ("foundation phase", EDUCATION),
    ("bed", EDUCATION),
    ("nursing", HEALTH), ("biomedical", HEALTH), ("medical", HEALTH),
    ("optometry", HEALTH), ("podiatry", HEALTH), ("chiropractic", HEALTH),
    ("radiography", HEALTH), ("emergency medical", HEALTH), ("sport", HEALTH),
    ("health", HEALTH),
    ("engineering", ENGINEERING), ("built environment", ENGINEERING),
    ("construction", ENGINEERING), ("quantity survey", ENGINEERING),
    ("mine survey", ENGINEERING), ("mining", ENGINEERING), ("surveying", ENGINEERING),
    ("urban", ENGINEERING),
    ("accounting", BUSINESS), ("bcom", BUSINESS), ("commerce", BUSINESS),
    ("economics", BUSINESS), ("econometrics", BUSINESS), ("finance", BUSINESS),
    ("business", BUSINESS), ("management", BUSINESS), ("marketing", BUSINESS),
    ("logistics", BUSINESS), ("human resource", BUSINESS), ("hospitality", BUSINESS),
    ("tourism", BUSINESS),
    ("computer science", SCIENCE), ("informatics", SCIENCE), ("physics", SCIENCE),
    ("chemistry", SCIENCE), ("biochem", SCIENCE), ("zoology", SCIENCE),
    ("botany", SCIENCE), ("geology", SCIENCE), ("mathematics", SCIENCE),
    ("statistics", SCIENCE), ("actuarial", SCIENCE), ("biology", SCIENCE),
    ("environmental management", SCIENCE), ("geography", SCIENCE), ("bsc", SCIENCE),
    ("psychology", HUMANITIES), ("social work", HUMANITIES), ("politics", HUMANITIES),
    ("philosophy", HUMANITIES), ("sociology", HUMANITIES), ("journalism", HUMANITIES),
    ("communication", HUMANITIES), ("language", HUMANITIES), ("linguistics", HUMANITIES),
    ("history", HUMANITIES), ("anthropology", HUMANITIES), ("humanities", HUMANITIES),
    ("arts", HUMANITIES), ("ba", HUMANITIES),
)


def resolve_faculty(programme_text: str) -> str | None:
    """Best-guess UJ faculty for a free-text programme, or None if unrecognised.
    Keywords match on word boundaries so short ones ("ba", "law") don't fire
    inside other words ("basket", "lawnmower")."""
    text = (programme_text or "").lower()
    for keyword, faculty in _FACULTY_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            return faculty
    return None


def faculty_search_term(faculty: str) -> str:
    """Leading word of a faculty name, to filter the faculty LOV (e.g.
    'ENGINEERING&BUILT ENVIRONMENT' → 'ENGINEERING')."""
    m = re.match(r"[A-Za-z]+", faculty or "")
    return m.group(0) if m else ""


# Degree/structural words that aren't discriminating, dropped before scoring.
_PROG_STOPWORDS = frozenset({
    "b", "ba", "bsc", "bcom", "beng", "bed", "bachelor", "of", "in", "the", "and",
    "a", "an", "to", "with", "ext", "extended", "hons", "honours", "degree",
})
_PROG_ALIASES = {
    "comp": "computer", "sc": "science", "sci": "science", "sciences": "science",
    "maths": "mathematics", "math": "mathematics", "eng": "engineering",
    "env": "environmental", "enviro": "environmental", "mgt": "management",
    "econ": "economics", "biochem": "biochemistry", "info": "informatics",
    "tech": "technology", "stats": "statistics",
}

_ROW_RE = re.compile(r"\(ELIGIBLE TO APPLY-([YN])\)\s*-?\s*(.*)$", re.IGNORECASE)


def _prog_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for tok in re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split():
        tok = _PROG_ALIASES.get(tok, tok)
        if tok and tok not in _PROG_STOPWORDS:
            out.add(tok)
    return out


def _parse_row(row: str) -> tuple[bool, str] | None:
    """(eligible, description) for a programme LOV row, or None for a header."""
    m = _ROW_RE.search(row or "")
    if not m:
        return None
    return m.group(1).upper() == "Y", m.group(2).strip()


def best_programme_match(programme_text: str, rows: list[str]) -> str | None:
    """Pick the LOV row (full text) that best matches `programme_text` among the
    **eligible** rows, or None if none confidently covers the request. A match
    must contain every distinctive token of the request; ties prefer an exact
    token-set, then the fewest extra tokens (the tightest programme)."""
    target = _prog_tokens(programme_text)
    if not target:
        return None
    best: str | None = None
    best_key: tuple[int, int] | None = None
    for row in rows:
        parsed = _parse_row(row)
        if not parsed:
            continue
        eligible, desc = parsed
        if not eligible:
            continue
        cand = _prog_tokens(desc)
        if not target <= cand:  # must cover the whole request
            continue
        key = (1 if cand == target else 0, -len(cand - target))
        if best_key is None or key > best_key:
            best_key, best = key, row
    return best
