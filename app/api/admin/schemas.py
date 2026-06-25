import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApplicationStatusCount(BaseModel):
    status: str
    count: int


class AdminStatsResponse(BaseModel):
    total_students: int
    active_universities: int
    applications_by_status: list[ApplicationStatusCount]


class AdminStudentRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    profile_complete: bool
    application_count: int
    created_at: datetime


class AdminStudentsResponse(BaseModel):
    items: list[AdminStudentRow]
    total: int
    page: int
    per_page: int


class AdminApplicationRow(BaseModel):
    id: uuid.UUID
    student_email: str
    student_name: Optional[str]
    university_name: str
    programme: str
    status: Optional[str]
    created_at: datetime


class AdminApplicationsResponse(BaseModel):
    items: list[AdminApplicationRow]
    total: int
    page: int
    per_page: int


class UniversityCreate(BaseModel):
    name: str
    website: str
    portal_url: str
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    is_active: bool = False
    scoring_method: Optional[str] = None


class UniversityUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    portal_url: Optional[str] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    is_active: Optional[bool] = None
    scoring_method: Optional[str] = None
