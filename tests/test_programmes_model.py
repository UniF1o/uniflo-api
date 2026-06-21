from app.models import Faculty, Programme
from app.models.university import University


def test_model_imports():
    assert Faculty.__tablename__ == "faculties"
    assert Programme.__tablename__ == "programmes"
    assert hasattr(University, "scoring_method")


def test_programme_has_qualification_type_and_duration():
    assert hasattr(Programme, "qualification_type")
    assert hasattr(Programme, "duration_years")


def test_programme_has_combination():
    assert hasattr(Programme, "combination")
