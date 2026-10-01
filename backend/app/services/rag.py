import re
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeChunk, KnowledgeDocument

UNKNOWN_ANSWER = "I don't have that information right now. I can connect you with our staff."


class KnowledgeRetriever(Protocol):
    def answer(self, database: Session, business_id: int, question: str) -> str: ...


def split_into_chunks(content: str, size: int = 900, overlap: int = 120) -> list[str]:
    text = content.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


class LexicalKnowledgeRetriever:
    def answer(self, database: Session, business_id: int, question: str) -> str:
        documents = database.scalars(select(KnowledgeDocument).where(KnowledgeDocument.business_id == business_id)).all()
        chunks = database.scalars(select(KnowledgeChunk).where(KnowledgeChunk.business_id == business_id)).all()
        if not chunks and documents:
            sources = [(document.title, document.content) for document in documents]
        else:
            titles = {document.id: document.title for document in documents}
            sources = [(titles.get(chunk.document_id, ""), chunk.content) for chunk in chunks]
        terms = {term for term in re.findall(r"[\w\u0B80-\u0BFF]+", question.lower()) if len(term) > 2}
        ranked = sorted(sources, key=lambda source: sum(term in f"{source[0]} {source[1]}".lower() for term in terms), reverse=True)
        if not ranked or not terms or not any(term in f"{ranked[0][0]} {ranked[0][1]}".lower() for term in terms):
            return UNKNOWN_ANSWER
        return ranked[0][1]


rag_service: KnowledgeRetriever = LexicalKnowledgeRetriever()


def create_document(database: Session, business_id: int, title: str, content: str, category: str) -> KnowledgeDocument:
    document = KnowledgeDocument(business_id=business_id, title=title, content=content, category=category)
    database.add(document)
    database.flush()
    database.add_all([
        KnowledgeChunk(business_id=business_id, document_id=document.id, chunk_index=index, content=chunk)
        for index, chunk in enumerate(split_into_chunks(content))
    ])
    database.commit()
    database.refresh(document)
    return document
