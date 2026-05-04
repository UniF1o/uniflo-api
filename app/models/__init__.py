from app.models.academic_record import AcademicRecord
from app.models.document import Document
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.models.university import University
from app.models.application import Application
from app.models.application_job import ApplicationJob

__all__ = [
            "StudentProfile", 
            "AcademicRecord", 
            "Document", 
            "User",
            "University",
            "Application",
            "ApplicationJob"
            ]