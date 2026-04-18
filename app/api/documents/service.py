import uuid
from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.models.document import Document
from app.models.student_profile import StudentProfile
from app.api.profiles.service import get_profile
from app.supabase_client import supabase
from app.config import settings


ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

async def upload_document(
    session: Session,
    user_id: str,
    document_type: str,
    file: UploadFile
) -> Document:
    # validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"File type not allowed. Accepted types: PDF, JPEG, PNG"
        )

    # read file and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail="File too large. Maximum size is 10MB"
        )

    # get student profile
    profile = get_profile(session, user_id)

    # build storage path — user_id/document_type/filename
    file_path = f"{user_id}/{document_type}/{file.filename}"

    # upload to Supabase Storage
    response = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        path=file_path,
        file=contents,
        file_options={"content-type": file.content_type, "upsert": "true"}
    )

    # build public URL
    storage_url = supabase.storage.from_(
        settings.SUPABASE_STORAGE_BUCKET
    ).get_public_url(file_path)

    # save document record to database
    document = Document(
        student_id=profile.id,
        type=document_type,
        storage_url=storage_url
    )

    session.add(document)
    session.commit()
    session.refresh(document)

    return document


def get_documents(session: Session, user_id: str) -> list[Document]:
    profile = get_profile(session, user_id)

    statement = select(Document).where(Document.student_id == profile.id)
    return session.exec(statement).all()


def delete_document(session: Session, user_id: str, document_id: uuid.UUID) -> None:
    profile = get_profile(session, user_id)

    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # verify document belongs to this student
    if document.student_id != profile.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # extract file path from storage URL for deletion
    file_path = f"{user_id}/{document.type}/{document.storage_url.split('/')[-1]}"

    # delete from Supabase Storage
    supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([file_path])

    # delete from database
    session.delete(document)
    session.commit()