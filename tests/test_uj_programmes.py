"""Faculty + eligible-programme resolution (app.automation.adapters.uj_programmes),
against the real harvested UJ faculty list + Science/Engineering programme rows."""

import pytest

from app.automation.adapters.uj_programmes import (
    BUSINESS,
    ENGINEERING,
    HUMANITIES,
    LAW,
    SCIENCE,
    best_programme_match,
    faculty_search_term,
    resolve_faculty,
)

# Real harvested rows (Engineering + Science), incl. ineligible -N rows.
ENG_ROWS = [
    "Choose a programme Description",
    "B6CS0Q (ELIGIBLE TO APPLY-Y) - B ENG IN CIVIL ENGINEERING",
    "B6CV3Q (ELIGIBLE TO APPLY-Y) - B ENG TECH IN CIVIL ENGINEERING",
    "B6CX3Q (ELIGIBLE TO APPLY-N) - B ENG TECH IN CIVIL ENGINEERING EXTENDED",
    "B6EL1Q (ELIGIBLE TO APPLY-Y) - B ENG TECH IN ELECTRICAL ENGINEERING",
    "B6CN0Q (ELIGIBLE TO APPLY-Y) - BACHELOR OF CONSTRUCTION",
]
SCI_ROWS = [
    "B2I02Q (ELIGIBLE TO APPLY-Y) - BSC COMPUTER SCIENCE & INFORMATICS",
    "B2I04Q (ELIGIBLE TO APPLY-N) - BSC COMPUTER SCIENCE & INFORMATICS AI",
    "B2M47Q (ELIGIBLE TO APPLY-Y) - BSC MATH (MATHS AND STATS)",
]


@pytest.mark.parametrize(
    "text,faculty",
    [
        ("BEng Civil Engineering", ENGINEERING),
        ("Civil Engineering", ENGINEERING),
        ("Bachelor of Construction", ENGINEERING),
        ("Computer Science", SCIENCE),
        ("BSc Mathematics", SCIENCE),
        ("BCom Accounting", BUSINESS),
        ("LLB", LAW),
        ("Bachelor of Laws", LAW),
        ("BA Psychology", HUMANITIES),
    ],
)
def test_resolve_faculty(text, faculty):
    assert resolve_faculty(text) == faculty


def test_resolve_faculty_unknown_returns_none():
    assert resolve_faculty("Underwater Basket Weaving") is None
    assert resolve_faculty("") is None


def test_faculty_search_term_leading_word():
    assert faculty_search_term(ENGINEERING) == "ENGINEERING"  # strips the &BUILT…
    assert faculty_search_term(SCIENCE) == "FACULTY"
    assert faculty_search_term("ART, DESIGN AND ARCHITECTURE") == "ART"


def test_best_programme_match_prefers_exact_eligible():
    # "Civil Engineering" → the plain eligible B ENG, not the Tech/Extended ones
    assert (
        best_programme_match("Civil Engineering", ENG_ROWS)
        == "B6CS0Q (ELIGIBLE TO APPLY-Y) - B ENG IN CIVIL ENGINEERING"
    )


def test_best_programme_match_skips_ineligible():
    # the only "AI" match is -N → no confident eligible match
    assert best_programme_match("Computer Science Informatics AI", SCI_ROWS) is None


def test_best_programme_match_smallest_superset():
    assert (
        best_programme_match("Computer Science", SCI_ROWS)
        == "B2I02Q (ELIGIBLE TO APPLY-Y) - BSC COMPUTER SCIENCE & INFORMATICS"
    )


def test_best_programme_match_no_match_returns_none():
    assert best_programme_match("Astrophysics", ENG_ROWS) is None
    assert best_programme_match("", ENG_ROWS) is None
