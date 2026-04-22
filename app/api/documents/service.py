import os
import uuid

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.api.documents.schemas import DocumentResponse, DocumentType
from app.api.profiles.service import get_profile
from app.config import settings
from app.models.document import Document
from app.supabase_client import get_supabase

ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SIGNED_URL_TTL_SECONDS = 60 * 60  # 1 hour


def _safe_extension(filename: str | None) -> str:
    if not filename:
        return ""
    ext = os.path.splitext(filename)[1].lower()
    if not ext or not ext[1:].isalnum():
        return ""
    return ext


def _create_signed_url(storage_path: str) -> str:
    """Generate a short-lived signed URL for a private-bucket object."""
    result = get_supabase().storage.from_(
        settings.SUPABASE_STORAGE_BUCKET
    ).create_signed_url(storage_path, SIGNED_URL_TTL_SECONDS)
    # storage3 returns a TypedDict; key casing varies across versions.
    return (
        result.get("signedURL")
        or result.get("signedUrl")
        or result.get("signed_url")
        or ""
    )


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        student_id=document.student_id,
        type=DocumentType(document.type),
        storage_url=_create_signed_url(document.storage_path),
        uploaded_at=document.uploaded_at,
    )


async def upload_document(
    session: Session,
    user_id: str,
    document_type: str,
    file: UploadFile,
) -> DocumentResponse:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail="File type not allowed. Accepted types: PDF, JPEG, PNG",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail="File too large. Maximum size is 10MB",
        )

    profile = get_profile(session, user_id)

    document_id = uuid.uuid4()
    extension = _safe_extension(file.filename)
    storage_path = f"{user_id}/{document_type}/{document_id}{extension}"

    get_supabase().storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        path=storage_path,
        file=contents,
        file_options={"content-type": file.content_type, "upsert": "true"},
    )

    document = Document(
        id=document_id,
        student_id=profile.id,
        type=document_type,
        storage_path=storage_path,
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    return _to_response(document)


def get_documents(session: Session, user_id: str) -> list[DocumentResponse]:
    profile = get_profile(session, user_id)

    statement = select(Document).where(Document.student_id == profile.id)
    documents = session.exec(statement).all()
    return [_to_response(d) for d in documents]


def delete_document(session: Session, user_id: str, document_id: uuid.UUID) -> None:
    profile = get_profile(session, user_id)

    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.student_id != profile.id:
        raise HTTPException(status_code=403, detail="Access denied")

    get_supabase().storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove(
        [document.storage_path]
    )

    session.delete(document)
    session.commit()
