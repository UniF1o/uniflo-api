import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


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


class StudentProfileCreate(BaseModel):
    first_name: str
    last_name: str
    id_number: str
    date_of_birth: date
    phone: str
    address: str
    nationality: str
    gender: GenderEnum
    home_language: HomeLanguageEnum


class StudentProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    nationality: Optional[str] = None
    gender: Optional[GenderEnum] = None
    home_language: Optional[HomeLanguageEnum] = None


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    first_name: str
    last_name: str
    id_number: str
    date_of_birth: date
    phone: str
    address: str
    nationality: str
    gender: GenderEnum
    home_language: HomeLanguageEnum
    updated_at: Optional[datetime] = None
