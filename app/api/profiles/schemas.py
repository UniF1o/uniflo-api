import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
    model_validator,
)


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


class TitleEnum(str, Enum):
    MR = "Mr"
    MRS = "Mrs"
    MS = "Ms"
    MISS = "Miss"
    DR = "Dr"
    PROF = "Prof"
    MX = "Mx"
    OTHER = "Other"


class CitizenshipStatusEnum(str, Enum):
    # Full residency taxonomy — mirrors UCT's Step-2 citizenship set. Drives the
    # SA-ID-vs-passport branch on the portals and in profile setup.
    SA_CITIZEN = "SA Citizen"
    PERMANENT_RESIDENT = "Permanent Resident"
    REFUGEE = "Refugee"
    ASYLUM_SEEKER = "Asylum Seeker"
    INTERNATIONAL = "International"


class StudyPermitTypeEnum(str, Enum):
    # UJ's oapStudyPermit LOV (17 options) — the canonical study-permit / visa
    # vocabulary. Values are the portal's visible row text; the adapter
    # fuzzy-matches them to the live LOV at fill time.
    ASYLUM_SEEKER_PERMIT = "Asylum Seeker Permit"
    BUSINESS_VISA = "Business Visa With Endorsement"
    CRITICAL_SKILLS_VISA = "Critical Skills Visa"
    DIPLOMATIC_PERMIT = "Diplomatic Permit"
    EXCHANGE_STUDENT = "Exchange Student"
    EXPERIENTIAL_LEARNING = "Experiential Learning"
    EXTRA_CURRICULAR = "Extra Curricular"
    LIMITED_CONTACT_SESSIONS = "Limited Contact Sessions"
    ONLINE_PROGRAMME = "Online Programme - Not Applicable"
    OTHER = "Other"
    PERMANENT_RESIDENCE = "Permanent Residence Status"
    QUOTA_WORK_VISA = "Quota Work Visa With Endorsement"
    REFUGEES_PERMIT = "Refugees Permit"
    RELATIVES_VISA = "Relatives Visa With Endorsement"
    STUDY_VISA = "Study Visa"
    VISITORS_VISA = "Visitor's Visa"
    WORK_VISA = "Work Visa With Endorsement"


class CurrentActivityEnum(str, Enum):
    # What the applicant is doing this year — maps to each portal's "current
    # activity" dropdown (UJ "GRADE 12 PUPIL", Wits "School", UP "still in high
    # school", etc.). Grade 8-11 are profile-only (can't apply yet).
    GRADE_8 = "In Grade 8"
    GRADE_9 = "In Grade 9"
    GRADE_10 = "In Grade 10"
    GRADE_11 = "In Grade 11"
    IN_SCHOOL = "Currently in Grade 12"
    UPGRADING = "Upgrading matric"
    GAP_YEAR = "Gap year"
    EMPLOYED = "Employed"
    UNIVERSITY = "At university"
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
    title: Optional[TitleEnum] = None
    first_name: Optional[str] = None
    middle_names: Optional[str] = None
    last_name: Optional[str] = None
    maiden_name: Optional[str] = None
    preferred_name: Optional[str] = None
    id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    # Residential / home address.
    street_address: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    # Postal / mailing address (when it differs from the home address).
    mailing_same_as_residential: Optional[bool] = None
    mailing_street_address: Optional[str] = None
    mailing_suburb: Optional[str] = None
    mailing_city: Optional[str] = None
    mailing_province: Optional[str] = None
    mailing_postal_code: Optional[str] = None
    nationality: Optional[str] = None
    is_sa_citizen: Optional[bool] = None
    citizenship_status: Optional[CitizenshipStatusEnum] = None
    passport_number: Optional[str] = None
    study_permit_type: Optional[StudyPermitTypeEnum] = None
    gender: Optional[GenderEnum] = None
    home_language: Optional[HomeLanguageEnum] = None
    religion: Optional[ReligionEnum] = None
    disability: Optional[DisabilityEnum] = None
    disability_detail: Optional[str] = None
    disability_assistance: Optional[str] = None
    marital_status: Optional[MaritalStatusEnum] = None
    ethnicity: Optional[EthnicityEnum] = None
    current_activity: Optional[CurrentActivityEnum] = None
    subject_choices: Optional[list[str]] = None
    exam_number: Optional[str] = None
    sport: Optional[str] = None
    wants_residence: Optional[bool] = None
    preferred_residence: Optional[str] = None
    applying_nsfas: Optional[bool] = None
    applying_institutional_funding: Optional[bool] = None
    nbt_reference: Optional[str] = None
    nbt_year: Optional[int] = None
    nbt_date: Optional[date] = None
    redress_factors: Optional[dict[str, Any]] = None
    guardian_consent_at: Optional[datetime] = None
    guardian_consent_by: Optional[str] = None
    guardian_relationship: Optional[str] = None

    @field_validator("postal_code", "mailing_postal_code")
    @classmethod
    def validate_postal_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v.isdigit() or len(v) != 4):
            raise ValueError("Postal code must be exactly 4 digits")
        return v

    @field_validator("nbt_year")
    @classmethod
    def validate_nbt_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 2000 <= v <= 2100:
            raise ValueError("nbt_year must be between 2000 and 2100")
        return v

    @model_validator(mode="after")
    def validate_citizenship(self) -> "StudentProfileWrite":
        # Non-SA-citizen applicants must supply a passport (the portals swap the
        # SA-ID field for it); International status additionally needs the permit
        # type. SA citizens are unaffected. Only enforced when citizenship_status
        # is explicitly set, so partial upserts of other fields are not blocked.
        needs_passport = {
            CitizenshipStatusEnum.PERMANENT_RESIDENT,
            CitizenshipStatusEnum.REFUGEE,
            CitizenshipStatusEnum.ASYLUM_SEEKER,
            CitizenshipStatusEnum.INTERNATIONAL,
        }
        if self.citizenship_status in needs_passport and not self.passport_number:
            raise ValueError(
                "passport_number is required for non-SA-citizen applicants"
            )
        if (
            self.citizenship_status == CitizenshipStatusEnum.INTERNATIONAL
            and not self.study_permit_type
        ):
            raise ValueError(
                "study_permit_type is required for international applicants"
            )
        return self


# Create and update use the same shape (all fields optional, upsert semantics).
StudentProfileCreate = StudentProfileWrite
StudentProfileUpdate = StudentProfileWrite


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[TitleEnum] = None
    first_name: Optional[str] = None
    middle_names: Optional[str] = None
    last_name: Optional[str] = None
    maiden_name: Optional[str] = None
    preferred_name: Optional[str] = None
    id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    mailing_same_as_residential: Optional[bool] = None
    mailing_street_address: Optional[str] = None
    mailing_suburb: Optional[str] = None
    mailing_city: Optional[str] = None
    mailing_province: Optional[str] = None
    mailing_postal_code: Optional[str] = None
    nationality: Optional[str] = None
    is_sa_citizen: Optional[bool] = None
    citizenship_status: Optional[CitizenshipStatusEnum] = None
    passport_number: Optional[str] = None
    study_permit_type: Optional[StudyPermitTypeEnum] = None
    gender: Optional[GenderEnum] = None
    home_language: Optional[HomeLanguageEnum] = None
    religion: Optional[ReligionEnum] = None
    disability: Optional[DisabilityEnum] = None
    disability_detail: Optional[str] = None
    disability_assistance: Optional[str] = None
    marital_status: Optional[MaritalStatusEnum] = None
    ethnicity: Optional[EthnicityEnum] = None
    current_activity: Optional[CurrentActivityEnum] = None
    subject_choices: Optional[list[str]] = None
    exam_number: Optional[str] = None
    sport: Optional[str] = None
    wants_residence: Optional[bool] = None
    preferred_residence: Optional[str] = None
    applying_nsfas: Optional[bool] = None
    applying_institutional_funding: Optional[bool] = None
    nbt_reference: Optional[str] = None
    nbt_year: Optional[int] = None
    nbt_date: Optional[date] = None
    redress_factors: Optional[dict[str, Any]] = None
    guardian_consent_at: Optional[datetime] = None
    guardian_consent_by: Optional[str] = None
    guardian_relationship: Optional[str] = None
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def is_complete(self) -> bool:
        return all(getattr(self, f) is not None for f in REQUIRED_PROFILE_FIELDS)
