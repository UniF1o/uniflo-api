"""APS scoring and programme-matching engine.

Pure module — no DB, no network. All functions are deterministic and
fully unit-testable with synthetic subject sets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.api.academic_records.schemas import SubjectIn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The one NSC subject excluded from APS across all UP-style best-6 universities.
_LIFE_ORIENTATION = "Life Orientation"

# APS within this many points below min_aps → borderline (all subject rules
# pass, only APS falls short).
APS_BORDERLINE_MARGIN = 2

# Exactly one subject rule short by at most this many percentage points →
# borderline, provided it is the only failing rule and APS is met.
SUBJECT_BORDERLINE_MARGIN = 5

# Minimum percentage mark corresponding to each NSC achievement level (bottom
# of the published CAPS band). Used to convert min_level rules to mark thresholds.
_LEVEL_MIN_MARK: dict[int, int] = {
    1: 0,
    2: 30,
    3: 40,
    4: 50,
    5: 60,
    6: 70,
    7: 80,
}

# ---------------------------------------------------------------------------
# APS computation
# ---------------------------------------------------------------------------


def _percentage_to_level(mark: int) -> int:
    """Standard NSC percentage → achievement level (CAPS bands, all provinces)."""
    if mark >= 80:
        return 7
    if mark >= 70:
        return 6
    if mark >= 60:
        return 5
    if mark >= 50:
        return 4
    if mark >= 40:
        return 3
    if mark >= 30:
        return 2
    return 1


def _subject_level(subject: SubjectIn) -> int:
    if subject.nsc_level is not None:
        return subject.nsc_level
    return _percentage_to_level(subject.mark)


def _up_aps(subjects: list[SubjectIn]) -> int:
    """UP APS: sum of NSC achievement levels for the best 6 subjects,
    excluding Life Orientation. Custom ("Other") subjects count toward APS —
    they are legitimate NSC subjects not in the canonical named list.
    Gracefully handles fewer than 6 subjects (sums what is there; caller can
    detect the provisional case by comparing the count to 6)."""
    eligible = [s for s in subjects if s.name != _LIFE_ORIENTATION]
    levels = sorted((_subject_level(s) for s in eligible), reverse=True)
    return sum(levels[:6])


# Subjects that earn Wits's +2 APS bonus (at >= 60%).
_WITS_BONUS_SUBJECTS = {
    "English Home Language",
    "English First Additional Language",
    "Mathematics",
}


def _wits_level(mark: int) -> int:
    """Wits uses an 8-point scale (90-100 -> 8); marks below 40% score 0."""
    if mark >= 90:
        return 8
    if mark >= 80:
        return 7
    if mark >= 70:
        return 6
    if mark >= 60:
        return 5
    if mark >= 50:
        return 4
    if mark >= 40:
        return 3
    return 0


def _wits_subject_points(name: str, mark: int) -> int:
    """Wits points for a non-LO subject: face-value level, +2 for English and
    Mathematics at >= 60% (the bonus does not apply below level 5)."""
    lvl = _wits_level(mark)
    if lvl == 0:
        return 0
    if name in _WITS_BONUS_SUBJECTS and mark >= 60:
        return lvl + 2
    return lvl


def _wits_lo_points(mark: int) -> int:
    """Life Orientation counts at a reduced weight: 8->4, 7->3, 6->2, 5->1, else 0."""
    return {8: 4, 7: 3, 6: 2, 5: 1}.get(_wits_level(mark), 0)


def _wits_aps(subjects: list[SubjectIn]) -> int:
    """Wits APS: best seven subjects INCLUDING Life Orientation. LO is always
    counted (at its reduced weight); the remaining slots take the best six of the
    other subjects, with the English/Mathematics +2 bonus applied. Marks drive the
    8-point scale, so nsc_level (max 7) is not used here."""
    lo = next((s for s in subjects if s.name == _LIFE_ORIENTATION), None)
    lo_points = _wits_lo_points(lo.mark) if lo else 0
    others = sorted(
        (_wits_subject_points(s.name, s.mark)
         for s in subjects if s.name != _LIFE_ORIENTATION),
        reverse=True,
    )
    return lo_points + sum(others[:6])


def compute_aps(subjects: list[SubjectIn], method: str = "up_aps") -> int:
    """Compute a student's APS using the named university scoring method."""
    if method == "up_aps":
        return _up_aps(subjects)
    if method == "wits_aps":
        return _wits_aps(subjects)
    raise ValueError(f"Unknown scoring method: {method!r}")


# ---------------------------------------------------------------------------
# Match result types
# ---------------------------------------------------------------------------


@dataclass
class UnmetRule:
    """A single unmet admission requirement, phrased for a student."""

    requirement: str  # e.g. "Mathematics 65%"  |  "APS 35"
    have: str  # e.g. "Mathematics 58%"  |  "APS 34"
    shortfall: str  # e.g. "7%"               |  "1 point"


@dataclass
class MatchResult:
    status: str  # "qualifies" | "borderline" | "not_yet"
    unmet_rules: list[UnmetRule] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Subject-rule helpers
# ---------------------------------------------------------------------------


def _effective_min_mark(rule: dict[str, Any]) -> int:
    """Return the minimum percentage mark for a subject rule (or one option).
    Uses min_mark directly; falls back to the bottom of min_level's band."""
    if "min_mark" in rule:
        return int(rule["min_mark"])
    if "min_level" in rule:
        return _LEVEL_MIN_MARK.get(int(rule["min_level"]), 0)
    return 0


def _best_for_rule(
    subjects: list[SubjectIn], accepted: list[str]
) -> tuple[str | None, int]:
    """(name, mark) for the student's best subject matching the rule, or
    (None, 0) if no matching subject is captured."""
    best_name: str | None = None
    best_mark = 0
    for s in subjects:
        if s.name in accepted and s.mark > best_mark:
            best_name = s.name
            best_mark = s.mark
    return best_name, best_mark


def _student_mark(subjects: list[SubjectIn], name: str) -> int | None:
    """The student's best captured mark for a named subject, or None."""
    marks = [s.mark for s in subjects if s.name == name]
    return max(marks) if marks else None


def _requirement_str(accepted: list[str], min_mark: int) -> str:
    if len(accepted) == 1:
        return f"{accepted[0]} {min_mark}%"
    return f"{' / '.join(accepted)} {min_mark}%"


def _eval_rule(
    subjects: list[SubjectIn], rule: dict[str, Any]
) -> tuple[bool, UnmetRule | None, int]:
    """Evaluate one subject rule. Returns (passed, unmet_or_None, shortfall_pct).

    Two rule shapes are supported:
      legacy  — {"subjects": [...], "min_mark"|"min_level"}: any listed subject
                satisfies the *shared* threshold.
      options — {"options": [{"subject": ..., "min_mark"|"min_level"}, ...]}: any
                option satisfies *its own* threshold (e.g. Maths 60% OR Maths Lit 50%).
    """
    if "options" in rule:
        options: list[dict[str, Any]] = rule["options"]
        req_parts: list[str] = []
        best_shortfall: int | None = None
        best_have: tuple[str, int] | None = None
        for opt in options:
            subj = opt["subject"]
            opt_min = _effective_min_mark(opt)
            req_parts.append(f"{subj} {opt_min}%")
            mark = _student_mark(subjects, subj)
            if mark is None:
                continue
            shortfall = max(0, opt_min - mark)
            if best_shortfall is None or shortfall < best_shortfall:
                best_shortfall = shortfall
                best_have = (subj, mark)
        requirement = " or ".join(req_parts)
        if best_shortfall == 0:
            return True, None, 0
        if best_have is not None:
            have = f"{best_have[0]} {best_have[1]}%"
            shortfall_pct = best_shortfall  # type: ignore[assignment]
        else:
            # None of the option subjects were captured.
            have = f"{options[0]['subject']} not captured"
            shortfall_pct = _effective_min_mark(options[0])
        return (
            False,
            UnmetRule(requirement=requirement, have=have, shortfall=f"{shortfall_pct}%"),
            shortfall_pct,
        )

    accepted: list[str] = rule.get("subjects", [])
    min_mark = _effective_min_mark(rule)
    best_name, best_mark = _best_for_rule(subjects, accepted)
    if best_mark < min_mark:
        shortfall_pct = min_mark - best_mark
        have_str = (
            f"{best_name} {best_mark}%"
            if best_name is not None
            else f"{accepted[0] if accepted else 'subject'} not captured"
        )
        return (
            False,
            UnmetRule(
                requirement=_requirement_str(accepted, min_mark),
                have=have_str,
                shortfall=f"{shortfall_pct}%",
            ),
            shortfall_pct,
        )
    return True, None, 0


def _effective_min_aps(
    subjects: list[SubjectIn], requirements: dict[str, Any], default_min_aps: int | None
) -> int | None:
    """Resolve the APS threshold, honouring a conditional aps_rule if present.

    aps_rule shape:
        {"alternatives": [{"with_subject": "Mathematics", "min_aps": 25},
                          {"with_subject": "Mathematical Literacy", "min_aps": 26}]}
    Picks the most favourable (lowest) threshold among alternatives whose
    with_subject the student holds. Falls back to the programme's stored min_aps
    when the student holds none of the conditioning subjects (the subject rules
    will flag the missing maths separately)."""
    aps_rule = requirements.get("aps_rule")
    if not aps_rule:
        return default_min_aps
    alternatives: list[dict[str, Any]] = aps_rule.get("alternatives", [])
    applicable = [
        int(alt["min_aps"])
        for alt in alternatives
        if alt.get("with_subject") is None
        or _student_mark(subjects, alt["with_subject"]) is not None
    ]
    if applicable:
        return min(applicable)
    if default_min_aps is not None:
        return default_min_aps
    return max((int(a["min_aps"]) for a in alternatives), default=None)


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------


def evaluate(subjects: list[SubjectIn], aps: int, programme: Any) -> MatchResult:
    """Evaluate whether a student qualifies, is borderline, or does not yet
    meet the requirements of a programme.

    programme: any object with .min_aps (int | None) and .requirements (dict).
    requirements shape:
        {"subject_rules": [
            {"subjects": [...], "min_mark": int, "min_level"?: int}
            | {"options": [{"subject": ..., "min_mark"|"min_level"}, ...]}
         ],
         "aps_rule"?: {"alternatives": [{"with_subject": ..., "min_aps": int}, ...]}}

    Status rules:
      qualifies  — all subject rules met AND aps >= min_aps
      borderline — (all subject rules met AND 0 < aps_gap <= APS_BORDERLINE_MARGIN)
                   OR (exactly 1 subject rule short by <= SUBJECT_BORDERLINE_MARGIN
                       AND aps_gap == 0)
      not_yet    — everything else
    """
    requirements: dict[str, Any] = programme.requirements or {}
    subject_rules: list[dict[str, Any]] = requirements.get("subject_rules", [])
    min_aps: int | None = _effective_min_aps(subjects, requirements, programme.min_aps)

    # Evaluate subject rules; collect failures as (UnmetRule, shortfall_pct).
    failed: list[tuple[UnmetRule, int]] = []
    for rule in subject_rules:
        passed, unmet, shortfall_pct = _eval_rule(subjects, rule)
        if not passed and unmet is not None:
            failed.append((unmet, shortfall_pct))

    aps_shortfall = max(0, (min_aps - aps) if min_aps is not None else 0)
    subjects_pass = not failed

    # qualifies
    if subjects_pass and aps_shortfall == 0:
        return MatchResult(status="qualifies")

    # borderline — only APS is short, within margin
    if subjects_pass and 0 < aps_shortfall <= APS_BORDERLINE_MARGIN:
        pts = "point" if aps_shortfall == 1 else "points"
        return MatchResult(
            status="borderline",
            unmet_rules=[
                UnmetRule(
                    requirement=f"APS {min_aps}",
                    have=f"APS {aps}",
                    shortfall=f"{aps_shortfall} {pts}",
                )
            ],
        )

    # borderline — exactly one subject short within margin, APS passes
    if len(failed) == 1 and failed[0][1] <= SUBJECT_BORDERLINE_MARGIN and aps_shortfall == 0:
        return MatchResult(status="borderline", unmet_rules=[failed[0][0]])

    # not_yet — collect all unmet rules (subjects first, APS last)
    unmet = [rule for rule, _ in failed]
    if aps_shortfall > 0:
        pts = "point" if aps_shortfall == 1 else "points"
        unmet.append(
            UnmetRule(
                requirement=f"APS {min_aps}",
                have=f"APS {aps}",
                shortfall=f"{aps_shortfall} {pts}",
            )
        )
    return MatchResult(status="not_yet", unmet_rules=unmet)
