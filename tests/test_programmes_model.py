from app.models import Faculty, Programme
from app.models.university import University


def test_model_imports():
    assert Faculty.__tablename__ == "faculties"
    assert Programme.__tablename__ == "programmes"
    assert hasattr(University, "scoring_method")
