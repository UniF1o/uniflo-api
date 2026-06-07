"""Resolve a student's free-form subject name to a portal LOV entry.

`academic_records.subjects` stores plain NSC names ("Mathematics", "English Home
Language") — and the backend is intentionally NOT authoritative on canonical NSC
spelling, so the input is free-form. UJ's subject LOV uses qualifier-tagged,
heavily-abbreviated variants ("MATHEMATICS (NSC/NCV/ISC)", "ENGLISH HOME LANG.
(NSC/NCV)", "AFRIKAANS 1ST AD LAN (NSC/NCV)").

Rather than a brittle exact map, we canonicalise BOTH sides to comparable token
lists — expanding abbreviations (1ST→first, AD→additional, LAN→language,
MATHS→mathematics, …) and dropping the (NSC/NCV/ISC/DR) qualifier tokens — then
score candidates and pick the best. Matching is done against the live LOV rows in
the adapter, so it tolerates the portal's idiosyncratic spelling.
"""

import re

# Qualifier tokens that tag a row's certificate type — not part of the name.
_QUALIFIERS = frozenset({"nsc", "ncv", "isc", "dr"})

# Abbreviation / variant → canonical token. Applied to both the student's name
# and the LOV row, so e.g. "1st ad lan" and "first additional language" collapse
# to the same tokens.
_TOKEN_ALIASES = {
    "1st": "first", "2nd": "second", "3rd": "third",
    "ad": "additional", "add": "additional", "addit": "additional",
    "lang": "language", "lan": "language", "langs": "language",
    "maths": "mathematics", "math": "mathematics",
    "lit": "literacy",
    "sci": "science", "sciences": "science",
    "geog": "geography",
}


def _tokens(name: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    out: list[str] = []
    for tok in cleaned.split():
        tok = _TOKEN_ALIASES.get(tok, tok)
        if tok and tok not in _QUALIFIERS:
            out.append(tok)
    return out


def subject_search_term(name: str) -> str:
    """A short, broad filter term to type into the LOV (the name's first word,
    upper-cased) — narrows the popup before we score the rows."""
    words = re.sub(r"[^A-Za-z0-9 ]", " ", name or "").split()
    return words[0].upper() if words else ""


def _score(target: list[str], cand: list[str]) -> int:
    if target == cand:
        return 100
    if not target or not cand or target[0] != cand[0]:
        # The leading word is the discriminator (english/afrikaans/life/…);
        # if it differs, don't risk a false match.
        return 0
    if cand[: len(target)] == target or target[: len(cand)] == cand:
        return 80  # one is a prefix of the other
    if set(target) <= set(cand) or set(cand) <= set(target):
        return 60  # one's tokens fully contained in the other
    return 0


def best_subject_match(name: str, rows: list[str]) -> str | None:
    """Pick the LOV row text best matching `name`, or None if nothing is a
    confident match (caller should flag for review rather than guess)."""
    target = _tokens(name)
    if not target:
        return None
    best: str | None = None
    best_score = 0
    for row in rows:
        score = _score(target, _tokens(row))
        if score and "nsc" in row.lower():
            score += 1  # tie-break toward the NSC-tagged entry (SA matric)
        if score > best_score:
            best_score, best = score, row
    return best if best_score >= 60 else None
