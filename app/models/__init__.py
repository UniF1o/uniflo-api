from app.models.academic_record import AcademicRecord
from app.models.application import Application
from app.models.application_choice import ApplicationChoice
from app.models.application_job import ApplicationJob
from app.models.contact import Contact
from app.models.document import Document
from app.models.student_profile import StudentProfile
from app.models.university import University
from app.models.user import User

__all__ = [
    "StudentProfile",
    "AcademicRecord",
    "Contact",
    "Document",
    "User",
    "University",
    "Application",
    "ApplicationChoice",
    "ApplicationJob",
]
