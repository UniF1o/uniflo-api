"""Truth-table tests for the APS scoring and programme-matching engine.

No DB, no network. All subject data is synthetic (see plan §4 data hygiene).
Programme fixtures mirror the UP BEng Civil 12136017 vs 12130017 example from
docs/phase-3/portal-research/up.md — the same pair the UP portal's live gate
verified (APS 34 accepted for 12136017, rejected for 12130017 with error 31100,501).
"""
from types import SimpleNamespace

import pytest

from app.api.academic_records.schemas import SubjectIn
from app.api.recommendations.scoring import (
    APS_BORDERLINE_MARGIN,
    compute_aps,
    evaluate,
)

# ---------------------------------------------------------------------------
# Programme fixtures (no DB — SimpleNamespace mirrors .min_aps / .requirements)
# ---------------------------------------------------------------------------


def _prog(min_aps, subject_rules):
    return SimpleNamespace(
        min_aps=min_aps,
        requirements={"subject_rules": subject_rules},
    )


_BENG_RULES = [
    {"subjects": ["Mathematics"], "min_mark": 65},
    {"subjects": ["Physical Sciences"], "min_mark": 65},
    {
        "subjects": ["English Home Language", "English First Additional Language"],
        "min_mark": 65,
    },
]

# UP 12136017 — 5-yr ENGAGE BEng Civil Engineering (min APS 33)
BENG_ENGAGE = _prog(33, _BENG_RULES)

# UP 12130017 — 4-yr BEng Civil Engineering (min APS 35)
BENG_CIVIL = _prog(35, _BENG_RULES)


# ---------------------------------------------------------------------------
# Subject fixtures
# ---------------------------------------------------------------------------

# Jane Doe — APS 34 (matches the portal-research live spike, Application ID T3989883).
# LO excluded; 6 eligible subjects: 6+5+6+5+6+6 = 34.
JANE_SUBJECTS = [
    SubjectIn(name="Mathematics", mark=72, nsc_level=6),
    SubjectIn(name="Physical Sciences", mark=68, nsc_level=5),
    SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
    SubjectIn(name="Life Sciences", mark=65, nsc_level=5),
    SubjectIn(name="Accounting", mark=70, nsc_level=6),
    SubjectIn(name="Geography", mark=72, nsc_level=6),
    SubjectIn(name="Life Orientation", mark=80, nsc_level=7),  # excluded
]

# Same as Jane but Maths 62% (level 5) — shortfall 3% on the Maths rule.
# APS: 5+5+6+5+6+6 = 33 (LO excluded). Meets BENG_ENGAGE APS (33 >= 33).
BORDERLINE_SUBJECT_SUBJECTS = [
    SubjectIn(name="Mathematics", mark=62, nsc_level=5),
    SubjectIn(name="Physical Sciences", mark=68, nsc_level=5),
    SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
    SubjectIn(name="Life Sciences", mark=65, nsc_level=5),
    SubjectIn(name="Accounting", mark=70, nsc_level=6),
    SubjectIn(name="Geography", mark=72, nsc_level=6),
    SubjectIn(name="Life Orientation", mark=80, nsc_level=7),
]

# Weaker student — APS 31 (shortfall 4 from BENG_CIVIL min 35), Maths 53%
# (shortfall 12%). Neither gap is within either borderline margin → not_yet.
# APS derivation (no nsc_level — percentage-only): 4+5+6+5+6+5 = 31.
NOT_YET_SUBJECTS = [
    SubjectIn(name="Mathematics", mark=53),  # → level 4 (derived)
    SubjectIn(name="Physical Sciences", mark=68),  # → level 5
    SubjectIn(name="English First Additional Language", mark=75),  # → level 6
    SubjectIn(name="Life Sciences", mark=65),  # → level 5
    SubjectIn(name="Accounting", mark=70),  # → level 6
    SubjectIn(name="Geography", mark=65),  # → level 5
    SubjectIn(name="Life Orientation", mark=80),  # excluded
]


# ---------------------------------------------------------------------------
# APS computation tests
# ---------------------------------------------------------------------------


def test_compute_aps_jane_with_nsc_levels():
    """Known subject set with nsc_level supplied → APS 34."""
    assert compute_aps(JANE_SUBJECTS) == 34


def test_compute_aps_excludes_life_orientation():
    """Life Orientation must never contribute to APS even at level 7.

    Five regular subjects give APS 28 (6+5+6+5+6). If LO (level 7) were
    included it would displace the lowest subject, yielding a higher score —
    the assertion detects that mis-inclusion.
    """
    five_plus_lo = [
        SubjectIn(name="Mathematics", mark=72, nsc_level=6),
        SubjectIn(name="Physical Sciences", mark=68, nsc_level=5),
        SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
        SubjectIn(name="Life Sciences", mark=65, nsc_level=5),
        SubjectIn(name="Accounting", mark=70, nsc_level=6),
        SubjectIn(name="Life Orientation", mark=92, nsc_level=7),
    ]
    # Only 5 eligible subjects — sum all five.
    assert compute_aps(five_plus_lo) == 28


def test_compute_aps_best_6_of_7():
    """Seven eligible subjects — only the best 6 count; the 7th is dropped."""
    seven_subjects = [
        SubjectIn(name="Mathematics", mark=72, nsc_level=6),
        SubjectIn(name="Physical Sciences", mark=68, nsc_level=5),
        SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
        SubjectIn(name="Life Sciences", mark=65, nsc_level=5),
        SubjectIn(name="Accounting", mark=70, nsc_level=6),
        SubjectIn(name="Geography", mark=72, nsc_level=6),
        SubjectIn(name="History", mark=85, nsc_level=7),
    ]
    # Best 6 levels: 7+6+6+6+6+5 = 36 (Life Sciences level 5 is dropped).
    assert compute_aps(seven_subjects) == 36


def test_compute_aps_percentage_only_no_nsc_level():
    """APS derived from percentage when nsc_level is absent (NOT_YET_SUBJECTS)."""
    # 4+5+6+5+6+5 = 31 (LO excluded, levels derived from marks).
    assert compute_aps(NOT_YET_SUBJECTS) == 31


def test_compute_aps_fewer_than_6_subjects_no_error():
    """Fewer than 6 eligible subjects is handled gracefully (provisional result)."""
    three = [
        SubjectIn(name="Mathematics", mark=72, nsc_level=6),
        SubjectIn(name="Physical Sciences", mark=68, nsc_level=5),
        SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
    ]
    assert compute_aps(three) == 17  # 6+5+6


def test_compute_aps_unknown_method_raises():
    assert pytest.raises(ValueError, compute_aps, [], "unknown_method")


# ---------------------------------------------------------------------------
# evaluate — qualifies
# ---------------------------------------------------------------------------


def test_evaluate_qualifies_12136017():
    """Jane (APS 34) meets all rules and APS 34 >= 33 — qualifies for ENGAGE BEng.

    Mirrors the portal live spike: selecting 12136017 was accepted without the
    (31100, 501) minimum-admission rejection.
    """
    aps = compute_aps(JANE_SUBJECTS)
    result = evaluate(JANE_SUBJECTS, aps, BENG_ENGAGE)
    assert result.status == "qualifies"
    assert result.unmet_rules == []


# ---------------------------------------------------------------------------
# evaluate — borderline (APS)
# ---------------------------------------------------------------------------


def test_evaluate_borderline_aps_12130017():
    """Jane (APS 34) meets all subject rules but APS 34 < 35 by 1 point →
    borderline for 4-yr BEng Civil.

    Mirrors the portal live spike: selecting 12130017 triggered (31100, 501).
    """
    aps = compute_aps(JANE_SUBJECTS)
    result = evaluate(JANE_SUBJECTS, aps, BENG_CIVIL)
    assert result.status == "borderline"
    assert len(result.unmet_rules) == 1
    rule = result.unmet_rules[0]
    assert rule.requirement == "APS 35"
    assert rule.have == "APS 34"
    assert rule.shortfall == "1 point"


def test_evaluate_borderline_aps_exactly_at_margin():
    """APS exactly APS_BORDERLINE_MARGIN (2) below min_aps → borderline."""
    aps = compute_aps(JANE_SUBJECTS)  # 34
    prog = _prog(34 + APS_BORDERLINE_MARGIN, _BENG_RULES)  # min_aps = 36
    result = evaluate(JANE_SUBJECTS, aps, prog)
    assert result.status == "borderline"


def test_evaluate_not_yet_aps_just_outside_margin():
    """APS exactly APS_BORDERLINE_MARGIN + 1 below min_aps → not_yet."""
    aps = compute_aps(JANE_SUBJECTS)  # 34
    prog = _prog(34 + APS_BORDERLINE_MARGIN + 1, _BENG_RULES)  # min_aps = 37
    result = evaluate(JANE_SUBJECTS, aps, prog)
    assert result.status == "not_yet"


# ---------------------------------------------------------------------------
# evaluate — borderline (subject)
# ---------------------------------------------------------------------------


def test_evaluate_borderline_subject_maths_3pct_short():
    """Student with Maths 62% (shortfall 3%) meets APS and all other rules
    → borderline on the one subject."""
    aps = compute_aps(BORDERLINE_SUBJECT_SUBJECTS)  # 33
    result = evaluate(BORDERLINE_SUBJECT_SUBJECTS, aps, BENG_ENGAGE)
    assert result.status == "borderline"
    assert len(result.unmet_rules) == 1
    rule = result.unmet_rules[0]
    assert rule.requirement == "Mathematics 65%"
    assert rule.have == "Mathematics 62%"
    assert rule.shortfall == "3%"


def test_evaluate_borderline_subject_exactly_at_margin():
    """Subject shortfall exactly SUBJECT_BORDERLINE_MARGIN (5%) → borderline."""
    subjects = [
        SubjectIn(name="Mathematics", mark=60),  # 65 - 5 = 60; shortfall 5%
        SubjectIn(name="Physical Sciences", mark=68, nsc_level=5),
        SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
        SubjectIn(name="Life Sciences", mark=65, nsc_level=5),
        SubjectIn(name="Accounting", mark=70, nsc_level=6),
        SubjectIn(name="Geography", mark=72, nsc_level=6),
    ]
    aps = compute_aps(subjects)
    result = evaluate(subjects, aps, BENG_ENGAGE)
    assert result.status == "borderline"
    assert result.unmet_rules[0].shortfall == "5%"


def test_evaluate_not_yet_subject_just_outside_margin():
    """Subject shortfall SUBJECT_BORDERLINE_MARGIN + 1 (6%) → not_yet."""
    subjects = [
        SubjectIn(name="Mathematics", mark=59),  # shortfall 6%
        SubjectIn(name="Physical Sciences", mark=68, nsc_level=5),
        SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
        SubjectIn(name="Life Sciences", mark=65, nsc_level=5),
        SubjectIn(name="Accounting", mark=70, nsc_level=6),
        SubjectIn(name="Geography", mark=72, nsc_level=6),
    ]
    aps = compute_aps(subjects)
    result = evaluate(subjects, aps, BENG_ENGAGE)
    assert result.status == "not_yet"


# ---------------------------------------------------------------------------
# evaluate — not_yet (multiple failures)
# ---------------------------------------------------------------------------


def test_evaluate_not_yet_subject_and_aps_gap():
    """Weaker student: Maths 53% (shortfall 12%) and APS 31 (shortfall 4 from
    BENG_CIVIL min 35) → not_yet. Both gap strings are asserted."""
    aps = compute_aps(NOT_YET_SUBJECTS)  # 31 (derived from %)
    assert aps == 31

    result = evaluate(NOT_YET_SUBJECTS, aps, BENG_CIVIL)
    assert result.status == "not_yet"
    assert len(result.unmet_rules) == 2

    maths_rule = result.unmet_rules[0]
    assert maths_rule.requirement == "Mathematics 65%"
    assert maths_rule.have == "Mathematics 53%"
    assert maths_rule.shortfall == "12%"

    aps_rule = result.unmet_rules[1]
    assert aps_rule.requirement == "APS 35"
    assert aps_rule.have == "APS 31"
    assert aps_rule.shortfall == "4 points"


# ---------------------------------------------------------------------------
# evaluate — edge cases
# ---------------------------------------------------------------------------


def test_evaluate_two_failed_subjects_is_not_yet():
    """Two subject rules failing (even within margin each) → not_yet, not borderline."""
    subjects = [
        SubjectIn(name="Mathematics", mark=62),  # shortfall 3%
        SubjectIn(name="Physical Sciences", mark=62),  # shortfall 3%
        SubjectIn(name="English First Additional Language", mark=75, nsc_level=6),
        SubjectIn(name="Life Sciences", mark=65, nsc_level=5),
        SubjectIn(name="Accounting", mark=70, nsc_level=6),
        SubjectIn(name="Geography", mark=72, nsc_level=6),
    ]
    aps = compute_aps(subjects)
    result = evaluate(subjects, aps, BENG_ENGAGE)
    assert result.status == "not_yet"
    assert len(result.unmet_rules) == 2


def test_evaluate_no_min_aps_only_subject_rules():
    """Programme with no min_aps (None) — APS check is skipped entirely."""
    prog = _prog(None, [{"subjects": ["Mathematics"], "min_mark": 65}])
    subjects = [SubjectIn(name="Mathematics", mark=70)]
    result = evaluate(subjects, 0, prog)
    assert result.status == "qualifies"


def test_evaluate_english_fal_satisfies_hl_or_fal_rule():
    """A rule accepting HL or FAL is satisfied by FAL."""
    prog = _prog(30, [
        {
            "subjects": ["English Home Language", "English First Additional Language"],
            "min_mark": 65,
        }
    ])
    subjects = [
        SubjectIn(name="English First Additional Language", mark=70),
        SubjectIn(name="Mathematics", mark=70, nsc_level=6),
        SubjectIn(name="Physical Sciences", mark=70, nsc_level=6),
        SubjectIn(name="Life Sciences", mark=70, nsc_level=6),
        SubjectIn(name="Accounting", mark=70, nsc_level=6),
        SubjectIn(name="Geography", mark=70, nsc_level=6),
    ]
    aps = compute_aps(subjects)
    result = evaluate(subjects, aps, prog)
    assert result.status == "qualifies"


def test_evaluate_mathematical_literacy_does_not_satisfy_mathematics_rule():
    """Mathematical Literacy must never be treated as Mathematics."""
    prog = _prog(30, [{"subjects": ["Mathematics"], "min_mark": 65}])
    subjects = [
        SubjectIn(name="Mathematical Literacy", mark=90),
        SubjectIn(name="Physical Sciences", mark=70, nsc_level=6),
        SubjectIn(name="English First Additional Language", mark=70, nsc_level=6),
        SubjectIn(name="Life Sciences", mark=70, nsc_level=6),
        SubjectIn(name="Accounting", mark=70, nsc_level=6),
        SubjectIn(name="Geography", mark=70, nsc_level=6),
    ]
    aps = compute_aps(subjects)
    result = evaluate(subjects, aps, prog)
    assert result.status != "qualifies"
    assert any("not captured" in r.have for r in result.unmet_rules)


def test_evaluate_subject_rule_via_min_level():
    """Rules expressed as min_level (not min_mark) are honoured."""
    # min_level 5 → min_mark 60%
    prog = _prog(None, [{"subjects": ["Mathematics"], "min_level": 5}])
    subjects_pass = [SubjectIn(name="Mathematics", mark=60)]
    subjects_fail = [SubjectIn(name="Mathematics", mark=59)]
    assert evaluate(subjects_pass, 0, prog).status == "qualifies"
    assert evaluate(subjects_fail, 0, prog).status != "qualifies"
