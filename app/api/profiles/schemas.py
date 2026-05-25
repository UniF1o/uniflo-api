import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field, field_validator


class GenderEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    # All SA universities follow HEMIS reporting, so non-binary is not an option yet.


class HomeLanguageEnum(str, Enum):
    ENGLISH = "English"
    AFRIKAANS = "Afrikaans"
    ZULU = "isiZulu"
    XHOSA = "isiXhosa"
    SOTHO = "Sesotho"
    TSWANA = "Setswana"
    PEDI = "Sepedi"
    VENDA = "Tshivenda"
    TSONGA = "Xitsonga"
    SWATI = "siSwati"
    NDEBELE = "isiNdebele"


class ReligionEnum(str, Enum):
    NONE = "None"
    CHRISTIANITY = "Christianity"
    ISLAM = "Islam"
    HINDUISM = "Hinduism"
    JUDAISM = "Judaism"
    AFRICAN_TRADITIONAL = "African Traditional Religion"
    BUDDHISM = "Buddhism"
    OTHER = "Other"


class DisabilityEnum(str, Enum):
    NONE = "None"
    VISUAL = "Visual impairment"
    HEARING = "Hearing impairment"
    PHYSICAL = "Physical/mobility impairment"
    INTELLECTUAL = "Intellectual disability"
    LEARNING = "Learning disability"
    MENTAL_HEALTH = "Mental health condition"
    OTHER = "Other"


class MaritalStatusEnum(str, Enum):
    SINGLE = "Single"
    MARRIED = "Married"
    DIVORCED = "Divorced"
    WIDOWED = "Widowed"
    OTHER = "Other"


class EthnicityEnum(str, Enum):
    AFRICAN = "African"
    COLOURED = "Coloured"
    INDIAN = "Indian"
    ASIAN = "Asian"
    WHITE = "White"
    OTHER = "Other"


# Single source of truth for profile completeness — also used by create_application
# to guard submission and by StudentProfileResponse.is_complete.
REQUIRED_PROFILE_FIELDS: tuple[str, ...] = (
    "first_name", "last_name", "id_number", "date_of_birth",
    "phone", "street_address", "city", "province", "postal_code",
    "nationality", "gender", "home_language",
    "religion", "disability", "marital_status", "ethnicity",
)


class StudentProfileWrite(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    nationality: Optional[str] = None
    gender: Optional[GenderEnum] = None
    home_language: Optional[HomeLanguageEnum] = None
    religion: Optional[ReligionEnum] = None
    disability: Optional[DisabilityEnum] = None
    marital_status: Optional[MaritalStatusEnum] = None
    ethnicity: Optional[EthnicityEnum] = None

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v.isdigit() or len(v) != 4):
            raise ValueError("Postal code must be exactly 4 digits")
        return v


# Create and update use the same shape (all fields optional, upsert semantics).
StudentProfileCreate = StudentProfileWrite
StudentProfileUpdate = StudentProfileWrite


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    nationality: Optional[str] = None
    gender: Optional[GenderEnum] = None
    home_language: Optional[HomeLanguageEnum] = None
    religion: Optional[ReligionEnum] = None
    disability: Optional[DisabilityEnum] = None
    marital_status: Optional[MaritalStatusEnum] = None
    ethnicity: Optional[EthnicityEnum] = None
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def is_complete(self) -> bool:
        return all(getattr(self, f) is not None for f in REQUIRED_PROFILE_FIELDS)
