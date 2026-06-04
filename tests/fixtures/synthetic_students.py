"""Synthetic (fake) student data for AI-layer tests.

Hard rule (plan §4 data hygiene): the AI layer is **never** exercised in dev or
CI with a real student's PII pulled from the database. Every AI test pulls from
here. None of this is real — the ID number is structurally plausible but fake.
"""

from uuid import UUID

from app.ai.schemas import PortalField, PortalFormSchema

SYNTHETIC_PROFILE = {
    "title": "Mr",
    "first_name": "Thabo",
    "middle_names": "Sipho",
    "last_name": "Mokoena",
    "id_number": "0512151234086",  # fake
    "date_of_birth": "2005-12-15",
    "phone": "0825550100",
    "street_address": "12 Acacia Street",
    "suburb": "Soshanguve",
    "city": "Pretoria",
    "province": "Gauteng",
    "postal_code": "0152",
    "nationality": "South African",
    "is_sa_citizen": True,
    "gender": "Male",
    "home_language": "Sepedi",
    "ethnicity": "African",
    "current_activity": "Currently in Grade 12",
}

SYNTHETIC_ACADEMIC_RECORDS = [
    {
        "record_type": "grade_11_final",
        "institution": "Soshanguve Secondary School",
        "year": 2023,
        "subjects": [
            {"name": "Mathematics", "mark": 72, "nsc_level": 6},
            {"name": "Physical Sciences", "mark": 68, "nsc_level": 5},
            {"name": "English First Additional Language", "mark": 75, "nsc_level": 6},
            {"name": "Life Orientation", "mark": 80, "nsc_level": 7},
        ],
    },
]

SYNTHETIC_DOCUMENTS = [
    {"type": "ID_COPY"},
    {"type": "GRADE11_RESULTS"},
]

# A small UJ-shaped form schema for tests.
SYNTHETIC_FORM = PortalFormSchema(
    university_id=UUID("00000000-0000-0000-0000-0000000000aa"),
    slug="uj",
    fields=[
        PortalField(field_id="surname", label="Surname", type="text", required=True),
        PortalField(
            field_id="first_names", label="First names", type="text", required=True
        ),
        PortalField(
            field_id="id_number", label="ID Number", type="text", required=True
        ),
        PortalField(
            field_id="home_language",
            label="Home language",
            type="select",
            required=True,
            options=["ENGLISH", "AFRIKAANS", "NORTHERN SOTHO", "ZULU"],
        ),
        PortalField(
            field_id="postal_code", label="Postal Code", type="lov", required=True
        ),
    ],
)
