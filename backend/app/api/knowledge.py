from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db import get_db
from app.models import KnowledgeChunk, KnowledgeDocument, User
from app.schemas import KnowledgeCreate, KnowledgeResponse
from app.services.rag import create_document as create_knowledge_document, rag_service

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/documents", response_model=list[KnowledgeResponse])
def list_documents(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(KnowledgeDocument).where(KnowledgeDocument.business_id == user.business_id).order_by(KnowledgeDocument.created_at.desc())).all()


@router.post("/documents", response_model=KnowledgeResponse, status_code=201)
def create_document(payload: KnowledgeCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF")), database: Session = Depends(get_db)):
    return create_knowledge_document(database, user.business_id, payload.title, payload.content, payload.category)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER")), database: Session = Depends(get_db)):
    document = database.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id, KnowledgeDocument.business_id == user.business_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    database.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id, KnowledgeChunk.business_id == user.business_id).delete()
    database.delete(document)
    database.commit()


@router.get("/search")
def search_knowledge(q: str, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    answer = rag_service.answer(database, user.business_id, q)
    return {"query": q, "answer": answer}
