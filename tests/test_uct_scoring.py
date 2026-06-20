"""Tests for UCT's Faculty Points Score (uct_fps).

UCT differs fundamentally from up/wits (which sum achievement levels):
- APS = sum of PERCENTAGES: English + 5 best other subjects, excluding Life
  Orientation; marks < 40% score 0; out of 600.
- FPS is per-faculty: Commerce/Eng/Hum/Law = APS; Science doubles Maths +
  Physical Sciences (/800); Health = APS + NBT (uncomputable -> subjects only).
- Required subjects are force-included in the best-5.

Worked examples mirror the prospectus (p17).
"""
from types import SimpleNamespace

from app.api.academic_records.schemas import SubjectIn
from app.api.recommendations.scoring import (
    aps_margin_for,
    compute_aps,
    evaluate,
)

# Prospectus p17 subject set (APS = 463). The second language is a non-English
# FAL (isiXhosa), counted as an "other" — English is the single English slot.
_P17 = [
    SubjectIn(name="English Home Language", mark=75),
    SubjectIn(name="isiXhosa First Additional Language", mark=70),
    SubjectIn(name="Mathematics", mark=84),
    SubjectIn(name="Physical Sciences", mark=86),
    SubjectIn(name="Geography", mark=79),
    SubjectIn(name="Accounting", mark=69),
    SubjectIn(name="Life Orientation", mark=80),  # excluded
]


def _aps(subjects):
    return compute_aps(subjects, method="uct_fps")


def _prog(min_aps, subject_rules, fps=None):
    req = {"subject_rules": subject_rules}
    if fps is not None:
        req["fps"] = fps
    return SimpleNamespace(min_aps=min_aps, requirements=req)


def test_uct_base_aps_sum_of_percentages():
    # English HL 75 + best 5 others (86,84,79,70,69) = 463; LO excluded.
    assert _aps(_P17) == 463


def test_uct_marks_below_40_score_zero():
    subjects = [
        SubjectIn(name="English Home Language", mark=80),
        SubjectIn(name="Mathematics", mark=35),  # < 40 -> 0
        SubjectIn(name="Physical Sciences", mark=60),
        SubjectIn(name="Geography", mark=50),
        SubjectIn(name="History", mark=50),
        SubjectIn(name="Accounting", mark=50),
    ]
    # 80 + (60+50+50+50+0) = 290
    assert _aps(subjects) == 290


def test_uct_science_fps_doubles_maths_and_physci():
    """Science FPS = APS + Maths + Physical Sciences (p17 example 3 = 633)."""
    fps = {"required": ["Mathematics", "Physical Sciences"],
           "double": ["Mathematics", "Physical Sciences"]}
    prog = _prog(600, [], fps=fps)  # min_aps high so we read it via unmet rule
    result = evaluate(_P17, _aps(_P17), prog, aps_margin=aps_margin_for("uct_fps"))
    # effective FPS = 463 + 84 + 86 = 633; min 600 -> qualifies
    assert result.status == "qualifies"


def test_uct_required_subject_is_force_included():
    """A required subject below the natural top-5 is still counted."""
    subjects = [
        SubjectIn(name="English Home Language", mark=80),
        SubjectIn(name="Mathematics", mark=45),  # required, low
        SubjectIn(name="History", mark=90),
        SubjectIn(name="Geography", mark=90),
        SubjectIn(name="Accounting", mark=90),
        SubjectIn(name="Tourism", mark=90),
        SubjectIn(name="Business Studies", mark=90),
    ]
    fps = {"required": ["Mathematics"]}
    # Force-include Maths(45): English80 + [45,90,90,90,90] = 485
    prog = _prog(485, [], fps=fps)
    result = evaluate(subjects, _aps(subjects), prog, aps_margin=aps_margin_for("uct_fps"))
    assert result.status == "qualifies"
    # Without forcing, the natural best-5 (90*5)+80 = 530 would wrongly clear a 530 cutoff.
    prog_high = _prog(486, [], fps=fps)
    assert evaluate(subjects, _aps(subjects), prog_high,
                    aps_margin=aps_margin_for("uct_fps")).status != "qualifies"


def test_uct_fps_cutoff_qualifies_and_borderline():
    """Commerce-style: FPS = APS, cutoff gating with the 5-point UCT margin."""
    rules = [{"subjects": ["Mathematics"], "min_mark": 60},
             {"subjects": ["English Home Language",
                           "English First Additional Language"], "min_mark": 50}]
    fps = {"required": ["Mathematics"]}
    margin = aps_margin_for("uct_fps")
    # _P17 FPS = 463.
    assert evaluate(_P17, _aps(_P17), _prog(435, rules, fps), aps_margin=margin).status == "qualifies"
    # 4 short (within 5) -> borderline
    r = evaluate(_P17, _aps(_P17), _prog(467, rules, fps), aps_margin=margin)
    assert r.status == "borderline"
    assert r.unmet_rules[0].requirement == "APS 467"
    assert r.unmet_rules[0].have == "APS 463"
    # 6 short (outside margin) -> not_yet
    assert evaluate(_P17, _aps(_P17), _prog(469, rules, fps), aps_margin=margin).status == "not_yet"


def test_uct_health_subjects_only_no_fps():
    """Health programmes carry no min_aps/fps; they gate on subjects only."""
    rules = [{"subjects": ["Mathematics"], "min_mark": 60},
             {"subjects": ["Life Sciences"], "min_mark": 60}]
    subjects = [
        SubjectIn(name="English Home Language", mark=80),
        SubjectIn(name="Mathematics", mark=70),
        SubjectIn(name="Life Sciences", mark=70),
        SubjectIn(name="Physical Sciences", mark=70),
    ]
    prog = _prog(None, rules)  # no fps, no min_aps
    assert evaluate(subjects, _aps(subjects), prog).status == "qualifies"


def test_uct_margin_is_five():
    assert aps_margin_for("uct_fps") == 5
    assert aps_margin_for("up_aps") == 2
