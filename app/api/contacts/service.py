import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.contacts.schemas import ContactWrite
from app.models.contact import Contact
from app.models.student_profile import StudentProfile


def _require_profile(session: Session, user_id: str) -> StudentProfile:
    # Mirrors academic_records: a write needs the student_profiles FK target.
    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == uuid.UUID(user_id))
    ).first()
    if profile is None:
        raise HTTPException(status_code=403, detail="profile_not_found")
    return profile


def list_contacts(session: Session, user_id: str) -> list[Contact]:
    profile = _require_profile(session, user_id)
    statement = select(Contact).where(Contact.student_id == profile.id)
    return list(session.exec(statement).all())


def upsert_contact(session: Session, user_id: str, data: ContactWrite) -> Contact:
    profile = _require_profile(session, user_id)
    contact_type = data.contact_type.value

    statement = select(Contact).where(
        Contact.student_id == profile.id,
        Contact.contact_type == contact_type,
    )
    contact = session.exec(statement).first()

    payload = data.model_dump(exclude_unset=True)
    payload["contact_type"] = contact_type  # store the enum value, not the member

    if contact:
        for field, value in payload.items():
            setattr(contact, field, value)
    else:
        contact = Contact(student_id=profile.id, **payload)
        session.add(contact)

    session.commit()
    session.refresh(contact)
    return contact


def delete_contact(session: Session, user_id: str, contact_type: str) -> None:
    profile = _require_profile(session, user_id)
    statement = select(Contact).where(
        Contact.student_id == profile.id,
        Contact.contact_type == contact_type,
    )
    contact = session.exec(statement).first()
    if contact is None:
        raise HTTPException(status_code=404, detail="contact_not_found")

    session.delete(contact)
    session.commit()
