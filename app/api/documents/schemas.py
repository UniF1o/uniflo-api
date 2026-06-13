import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentType(str, Enum):
    ID_COPY = "ID_COPY"
    MATRIC_RESULTS = "MATRIC_RESULTS"
    TRANSCRIPT = "TRANSCRIPT"
    GRADE12_APRIL = "GRADE12_APRIL"
    # UP accepts Grade 11 final results in lieu of a Grade 12 certificate.
    GRADE11_RESULTS = "GRADE11_RESULTS"


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    type: DocumentType
    storage_url: str
    # Display-only upload name. Null for legacy rows uploaded before this was
    # captured, and for uploads that arrived without a filename.
    original_filename: Optional[str] = None
    uploaded_at: datetime
