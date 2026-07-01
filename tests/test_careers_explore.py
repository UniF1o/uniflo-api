"""Careers explore mode for younger learners (no marks / subject choices only).

Verifies:
- subject_requirements() emits marks-free requirement strings.
- _student_subjects() sources names from subject_choices and/or a record.
- list_careers() returns the full browse set (explore=True) when the learner
  has no subjects, and a subject-matched shortlist once subjects exist.
"""

from app.api.careers.service import _career_to_read, _student_subjects, list_careers
from app.api.recommendations.scoring import subject_requirements


class _Prog:
    def __init__(self, requirements):
        self.requirements = requirements


class _Career:
    def __init__(self, slug, subject_rule, tvet=False, recommended=None):
        self.id = slug
        self.slug = slug
        self.title = slug.title()
        self.industry = "Engineering"
        self.description = "x"
        self.compensation = {}
        self.employability = {"tvet_only": tvet}
        self.subject_rule = subject_rule
        self.recommended_subjects = recommended


class _Profile:
    def __init__(self, subject_choices=None):
        self.id = "00000000-0000-0000-0000-000000000000"
        self.subject_choices = subject_choices


class _Result:
    def __init__(self, first=None, all_=None):
        self._first = first
        self._all = all_ or []

    def first(self):
        return self._first

    def all(self):
        return self._all


class _FakeSession:
    """First exec() resolves the profile; subsequent .first() calls resolve the
    (absent) academic record; .all() resolves the careers list."""

    def __init__(self, profile, careers, record=None):
        self._profile = profile
        self._careers = careers
        self._record = record
        self._calls = 0

    def exec(self, _stmt):
        self._calls += 1
        if self._calls == 1:
            return _Result(first=self._profile)
        return _Result(first=self._record, all_=self._careers)


def test_subject_requirements_legacy_and_options():
    prog = _Prog({
        "subject_rules": [
            {"subjects": ["Mathematics"], "min_level": 5},
            {"options": [
                {"subject": "English Home Language", "min_mark": 50},
                {"subject": "English First Additional Language", "min_mark": 60},
            ]},
        ]
    })
    reqs = subject_requirements(prog)
    assert "Mathematics 60%" in reqs  # level 5 -> 60%
    assert "English Home Language 50% or English First Additional Language 60%" in reqs


def test_subject_requirements_empty_when_no_rules():
    assert subject_requirements(_Prog({})) == []
    assert subject_requirements(_Prog(None)) == []


def test_student_subjects_merges_choices_and_record():
    profile = _Profile(subject_choices=["Mathematics", "Life Sciences"])
    record = type("R", (), {"subjects": [{"name": "Physical Sciences", "mark": 70}]})()
    assert _student_subjects(profile, record) == {
        "Mathematics", "Life Sciences", "Physical Sciences",
    }


def test_student_subjects_from_choices_only():
    assert _student_subjects(_Profile(["Accounting"]), None) == {"Accounting"}


def test_career_to_read_exposes_subject_guidance():
    career = _Career(
        "actuary",
        {"all_of": ["Mathematics"], "any_of": ["Accounting", "Economics"]},
        recommended=["Information Technology"],
    )
    read = _career_to_read(career)
    assert read.required_subjects == ["Mathematics"]
    assert read.any_of_subjects == ["Accounting", "Economics"]
    assert read.recommended_subjects == ["Information Technology"]


def test_list_careers_explore_mode_when_no_subjects():
    careers = [
        _Career("civil-engineer", {"all_of": ["Mathematics", "Physical Sciences"]}),
        _Career("plumber", {"all_of": []}, tvet=True),  # filtered out
    ]
    session = _FakeSession(_Profile(subject_choices=None), careers, record=None)
    resp = list_careers(session, "11111111-1111-1111-1111-111111111111")
    assert resp.explore is True
    slugs = {c.slug for c in resp.careers}
    assert slugs == {"civil-engineer"}  # tvet_only excluded


def test_list_careers_matches_when_subjects_present():
    careers = [
        _Career("civil-engineer", {"all_of": ["Mathematics", "Physical Sciences"]}),
        _Career("doctor", {"all_of": ["Life Sciences"]}),
    ]
    profile = _Profile(subject_choices=["Mathematics", "Physical Sciences"])
    session = _FakeSession(profile, careers, record=None)
    resp = list_careers(session, "11111111-1111-1111-1111-111111111111")
    assert resp.explore is False
    assert {c.slug for c in resp.careers} == {"civil-engineer"}
