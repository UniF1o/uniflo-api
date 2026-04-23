import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlmodel import Session

from app.api.documents import service
from app.api.documents.schemas import DocumentResponse, DocumentType
from app.db import get_session

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return await service.upload_document(session, user_id, document_type.value, file)


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return service.get_documents(session, user_id)


@router.delete("/{document_id}", status_code=200)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    service.delete_document(session, user_id, document_id)
    return {"status": "ok"}