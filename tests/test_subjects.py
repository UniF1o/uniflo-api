"""The free-form-subject → portal-LOV resolver (app.automation.subjects),
scored against the real harvested UJ subject-LOV rows."""

import pytest

from app.automation.subjects import (
    best_subject_match,
    subject_search_term,
)

# Real rows dumped from UJ's #oapMSubj LOV (various searches), incl. the
# near-collisions the resolver must NOT pick.
UJ_ROWS = [
    "ENGLISH HOME LANG. (NSC/NCV)",
    "ENGLISH 1ST ADD LANG (NSC/NCV)",
    "ENGLISH 2ND ADD LANG (NSC/NCV)",
    "AFRIKAANS 1ST AD LAN (NSC/NCV)",
    "AFRIKAANS HOME LANG.(NSC/NCV)",
    "AFRIKAANS(2ND ADD LANG NSC/NCV",
    "MATHEMATICS (NSC/NCV/ISC)",
    "MATHEMATICAL LIT. (NSC/NCV)",
    "ABITUR MATHEMATICS (NSC)",
    "MATHEMATICS (THIRD PAPER) (NSC",
    "PHYSICAL SCIENCES(NSC/NCV/ISC)",
    "PHYSICAL EDUCATION (NSC/NCV)",
    "LIFE SCIENCES (NSC)",
    "GEOGRAPHY (NSC/NCV/ ISC)",
    "LIFE ORIENTATION (NSC/NCV/DR)",
]


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Mathematics", "MATHEMATICS (NSC/NCV/ISC)"),
        ("Mathematical Literacy", "MATHEMATICAL LIT. (NSC/NCV)"),
        ("English Home Language", "ENGLISH HOME LANG. (NSC/NCV)"),
        ("English First Additional Language", "ENGLISH 1ST ADD LANG (NSC/NCV)"),
        ("Afrikaans First Additional Language", "AFRIKAANS 1ST AD LAN (NSC/NCV)"),
        ("Afrikaans Home Language", "AFRIKAANS HOME LANG.(NSC/NCV)"),
        ("Physical Sciences", "PHYSICAL SCIENCES(NSC/NCV/ISC)"),
        ("Life Sciences", "LIFE SCIENCES (NSC)"),
        ("Life Orientation", "LIFE ORIENTATION (NSC/NCV/DR)"),
        ("Geography", "GEOGRAPHY (NSC/NCV/ ISC)"),
        # already-canonical (e.g. from a previous mapping) still resolves
        ("MATHEMATICS (NSC/NCV/ISC)", "MATHEMATICS (NSC/NCV/ISC)"),
        # common abbreviation
        ("Maths", "MATHEMATICS (NSC/NCV/ISC)"),
    ],
)
def test_best_subject_match_resolves(name, expected):
    assert best_subject_match(name, UJ_ROWS) == expected


def test_life_orientation_not_confused_with_life_sciences():
    assert best_subject_match("Life Orientation", UJ_ROWS) == "LIFE ORIENTATION (NSC/NCV/DR)"
    assert best_subject_match("Life Sciences", UJ_ROWS) == "LIFE SCIENCES (NSC)"


def test_no_confident_match_returns_none():
    assert best_subject_match("Quantum Underwater Basketweaving", UJ_ROWS) is None
    assert best_subject_match("", UJ_ROWS) is None


def test_search_term_is_first_word_upper():
    assert subject_search_term("Physical Sciences") == "PHYSICAL"
    assert subject_search_term("life orientation") == "LIFE"
    assert subject_search_term("MATHEMATICS (NSC/NCV/ISC)") == "MATHEMATICS"
    assert subject_search_term("") == ""
