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


def compute_aps(subjects: list[SubjectIn], method: str = "up_aps") -> int:
    """Compute a student's APS using the named university scoring method."""
    if method == "up_aps":
        return _up_aps(subjects)
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
    """Return the minimum percentage mark for a subject rule.
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


def _requirement_str(accepted: list[str], min_mark: int) -> str:
    if len(accepted) == 1:
        return f"{accepted[0]} {min_mark}%"
    return f"{' / '.join(accepted)} {min_mark}%"


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------


def evaluate(subjects: list[SubjectIn], aps: int, programme: Any) -> MatchResult:
    """Evaluate whether a student qualifies, is borderline, or does not yet
    meet the requirements of a programme.

    programme: any object with .min_aps (int | None) and .requirements (dict).
    requirements shape:
        {"subject_rules": [{"subjects": [...], "min_mark": int, "min_level"?: int}]}

    Status rules:
      qualifies  — all subject rules met AND aps >= min_aps
      borderline — (all subject rules met AND 0 < aps_gap <= APS_BORDERLINE_MARGIN)
                   OR (exactly 1 subject rule short by <= SUBJECT_BORDERLINE_MARGIN
                       AND aps_gap == 0)
      not_yet    — everything else
    """
    requirements: dict[str, Any] = programme.requirements or {}
    subject_rules: list[dict[str, Any]] = requirements.get("subject_rules", [])
    min_aps: int | None = programme.min_aps

    # Evaluate subject rules; collect failures as (UnmetRule, shortfall_pct).
    failed: list[tuple[UnmetRule, int]] = []
    for rule in subject_rules:
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
            failed.append((
                UnmetRule(
                    requirement=_requirement_str(accepted, min_mark),
                    have=have_str,
                    shortfall=f"{shortfall_pct}%",
                ),
                shortfall_pct,
            ))

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
