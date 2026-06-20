"""Truth-table tests for the Wits APS scoring method (wits_aps).

Wits differs from the UP/UJ up_aps model:
- 8-point scale (90-100 -> 8)
- +2 bonus on English and Mathematics, only at >= 60%
- Life Orientation counted at a reduced weight (8->4, 7->3, 6->2, 5->1, else 0)
- APS = best seven subjects INCLUDING Life Orientation (LO + best 6 others)
"""
import pytest

from app.api.academic_records.schemas import SubjectIn
from app.api.recommendations.scoring import compute_aps


def _aps(subjects):
    return compute_aps(subjects, method="wits_aps")


def test_wits_aps_worked_example():
    """LO + best 6 others with English/Maths bonus.

    English HL 75 -> L6 +2 = 8; Maths 82 -> L7 +2 = 9; Phys Sci 68 -> 5;
    Life Sci 72 -> 6; Geography 65 -> 5; Accounting 55 -> 4; LO 85 -> 3.
    others = 8+9+5+6+5+4 = 37; +LO 3 = 40.
    """
    subjects = [
        SubjectIn(name="English Home Language", mark=75),
        SubjectIn(name="Mathematics", mark=82),
        SubjectIn(name="Physical Sciences", mark=68),
        SubjectIn(name="Life Sciences", mark=72),
        SubjectIn(name="Geography", mark=65),
        SubjectIn(name="Accounting", mark=55),
        SubjectIn(name="Life Orientation", mark=85),
    ]
    assert _aps(subjects) == 40


def test_wits_level_8_scale_and_bonus():
    """90%+ is level 8; English/Maths at level 8 score 10."""
    subjects = [
        SubjectIn(name="English Home Language", mark=92),  # L8 +2 = 10
        SubjectIn(name="Mathematics", mark=95),  # L8 +2 = 10
        SubjectIn(name="Physical Sciences", mark=91),  # L8 = 8
        SubjectIn(name="Life Sciences", mark=80),  # L7 = 7
        SubjectIn(name="Geography", mark=70),  # L6 = 6
        SubjectIn(name="Accounting", mark=60),  # L5 = 5
        SubjectIn(name="Life Orientation", mark=95),  # LO L8 = 4
    ]
    # others 10+10+8+7+6+5 = 46; +LO 4 = 50
    assert _aps(subjects) == 50


def test_wits_bonus_not_applied_below_60():
    """English/Maths at 50-59 (level 4) get no bonus."""
    subjects = [
        SubjectIn(name="English Home Language", mark=58),  # L4 = 4 (no bonus)
        SubjectIn(name="Mathematics", mark=55),  # L4 = 4 (no bonus)
        SubjectIn(name="Physical Sciences", mark=50),  # L4 = 4
        SubjectIn(name="Life Sciences", mark=50),  # 4
        SubjectIn(name="Geography", mark=50),  # 4
        SubjectIn(name="Accounting", mark=50),  # 4
        SubjectIn(name="Life Orientation", mark=80),  # LO L7 = 3
    ]
    # others 4*6 = 24; +LO 3 = 27
    assert _aps(subjects) == 27


def test_wits_lo_reduced_weight():
    """LO at 60-69 contributes only 1 point; the bonus subjects still count fully."""
    base = [
        SubjectIn(name="English Home Language", mark=70),  # 6+2=8
        SubjectIn(name="Mathematics", mark=70),  # 8
        SubjectIn(name="Physical Sciences", mark=70),  # 6
        SubjectIn(name="Life Sciences", mark=70),  # 6
        SubjectIn(name="Geography", mark=70),  # 6
        SubjectIn(name="Accounting", mark=70),  # 6
    ]
    others = 8 + 8 + 6 + 6 + 6 + 6  # 40
    assert _aps(base + [SubjectIn(name="Life Orientation", mark=65)]) == others + 1
    assert _aps(base + [SubjectIn(name="Life Orientation", mark=95)]) == others + 4
    # LO below 60 contributes 0
    assert _aps(base + [SubjectIn(name="Life Orientation", mark=55)]) == others


def test_wits_best_seven_including_lo_drops_lowest_other():
    """With 7 non-LO subjects, only the best 6 count; LO is always included."""
    subjects = [
        SubjectIn(name="English Home Language", mark=70),  # 8
        SubjectIn(name="Mathematics", mark=70),  # 8
        SubjectIn(name="Physical Sciences", mark=80),  # 7
        SubjectIn(name="Life Sciences", mark=70),  # 6
        SubjectIn(name="Geography", mark=60),  # 5
        SubjectIn(name="Accounting", mark=50),  # 4
        SubjectIn(name="History", mark=40),  # 3  (lowest other -> dropped)
        SubjectIn(name="Life Orientation", mark=85),  # LO 3
    ]
    # best 6 others: 8+8+7+6+5+4 = 38 (History 3 dropped); +LO 3 = 41
    assert _aps(subjects) == 41


def test_wits_maths_literacy_gets_no_bonus():
    """The +2 bonus is for Mathematics, not Mathematical Literacy."""
    subjects = [
        SubjectIn(name="Mathematical Literacy", mark=80),  # L7, no bonus = 7
        SubjectIn(name="English Home Language", mark=80),  # L7 +2 = 9
        SubjectIn(name="Geography", mark=80),  # 7
        SubjectIn(name="History", mark=80),  # 7
        SubjectIn(name="Accounting", mark=80),  # 7
        SubjectIn(name="Business Studies", mark=80),  # 7
        SubjectIn(name="Life Orientation", mark=80),  # LO 3
    ]
    # others 7+9+7+7+7+7 = 44; +LO 3 = 47
    assert _aps(subjects) == 47


def test_wits_unknown_method_still_raises():
    assert pytest.raises(ValueError, compute_aps, [], "nope")
