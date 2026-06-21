"""Unit tests for seed_programmes pure helpers (no DB)."""
import importlib.util
import os
from types import SimpleNamespace

# Load scripts/seed_programmes.py as a module (scripts/ is not a package).
_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts", "seed_programmes.py",
)
_spec = importlib.util.spec_from_file_location("seed_programmes", _PATH)
seed_programmes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_programmes)


def _prog(name, code=None, is_active=True):
    return SimpleNamespace(name=name, qualification_code=code, is_active=is_active)


def test_missing_programmes_flags_removed_active_rows():
    existing = [
        _prog("Bachelor of Science (BSc)"),                 # umbrella — removed
        _prog("Bachelor of Science: Computer Science"),     # still in file
        _prog("Old Diploma", is_active=False),              # already inactive — skip
    ]
    file_entries = [
        {"name": "Bachelor of Science: Computer Science", "qualification_code": None},
        {"name": "Bachelor of Science: Physics", "qualification_code": None},
    ]
    missing = seed_programmes._missing_programmes(existing, file_entries)
    names = [p.name for p in missing]
    assert names == ["Bachelor of Science (BSc)"]  # only the removed active row


def test_missing_programmes_matches_on_code_then_name():
    existing = [_prog("BEng Civil", code="B6CS0Q"), _prog("BEng Mech", code="B6MS0Q")]
    file_entries = [{"name": "BEng Civil", "qualification_code": "B6CS0Q"}]
    missing = seed_programmes._missing_programmes(existing, file_entries)
    assert [p.name for p in missing] == ["BEng Mech"]


def test_missing_programmes_none_when_all_present():
    existing = [_prog("A"), _prog("B")]
    file_entries = [{"name": "A", "qualification_code": None},
                    {"name": "B", "qualification_code": None}]
    assert seed_programmes._missing_programmes(existing, file_entries) == []
