import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ContactType(str, Enum):
    """One captured contact covers all portals (the automation layer resolves
    roles through fallback chains) — the frontend should ask for ONE
    parent/guardian and offer a separate fee payer only as an opt-in
    ("someone else pays my fees"); never ask for an emergency contact
    (no portal needs a distinct person — Wits copies the next of kin)."""

    NEXT_OF_KIN = "next_of_kin"
    FEE_PAYER = "fee_payer"
    GUARDIAN = "guardian"
    EMERGENCY = "emergency"


class ContactWrite(BaseModel):
    contact_type: ContactType
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    relationship: Optional[str] = None
    id_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    contact_type: ContactType
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    relationship: Optional[str] = None
    id_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    updated_at: Optional[datetime] = None
