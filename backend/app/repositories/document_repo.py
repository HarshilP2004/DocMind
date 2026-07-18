from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any
from app.models.models import Document, DocumentMetadata, Chunk

class DocumentRepository:
    @staticmethod
    def create_document(db: Session, visitor_id: str, filename: str, file_type: str, file_path: str) -> Document:
        db_doc = Document(
            visitor_id=visitor_id,
            filename=filename,
            file_type=file_type,
            file_path=file_path,
            status="uploaded"
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        return db_doc

    @staticmethod
    def update_document(
        db: Session, 
        doc_id: int, 
        status: Optional[str] = None, 
        total_chunks: Optional[int] = None, 
        ocr_used: Optional[bool] = None
    ) -> Optional[Document]:
        db_doc = db.query(Document).filter(Document.id == doc_id).first()
        if not db_doc:
            return None
        if status is not None:
            db_doc.status = status
        if total_chunks is not None:
            db_doc.total_chunks = total_chunks
        if ocr_used is not None:
            db_doc.ocr_used = ocr_used
        db.commit()
        db.refresh(db_doc)
        return db_doc

    @staticmethod
    def get_by_id(db: Session, doc_id: int) -> Optional[Document]:
        return db.query(Document).filter(Document.id == doc_id).first()

    @staticmethod
    def list_by_visitor(db: Session, visitor_id: str) -> List[Document]:
        return db.query(Document).filter(Document.visitor_id == visitor_id).order_by(Document.created_at.desc()).all()

    @staticmethod
    def delete(db: Session, doc_id: int) -> bool:
        db_doc = db.query(Document).filter(Document.id == doc_id).first()
        if db_doc:
            db.delete(db_doc)
            db.commit()
            return True
        return False

    @staticmethod
    def create_metadata(db: Session, document_id: int, doc_type: str, extracted_data: Dict[str, Any]) -> DocumentMetadata:
        # Check if metadata already exists
        db_meta = db.query(DocumentMetadata).filter(DocumentMetadata.document_id == document_id).first()
        if db_meta:
            db_meta.doc_type = doc_type
            db_meta.extracted_data = extracted_data
        else:
            db_meta = DocumentMetadata(
                document_id=document_id,
                doc_type=doc_type,
                extracted_data=extracted_data
            )
            db.add(db_meta)
        db.commit()
        db.refresh(db_meta)
        return db_meta

    @staticmethod
    def get_metadata(db: Session, document_id: int) -> Optional[DocumentMetadata]:
        return db.query(DocumentMetadata).filter(DocumentMetadata.document_id == document_id).first()

    @staticmethod
    def bulk_create_chunks(db: Session, chunks_data: List[Dict[str, Any]]):
        chunks = [
            Chunk(
                document_id=c["document_id"],
                page_number=c.get("page_number"),
                content=c["content"],
                embedding=c["embedding"],
                chunk_metadata=c.get("chunk_metadata", {})
            )
            for c in chunks_data
        ]
        db.bulk_save_objects(chunks)
        db.commit()

    @staticmethod
    def search_vector(db: Session, embedding_vector: List[float], visitor_id: str, limit: int = 20, document_ids: Optional[List[int]] = None) -> List[Chunk]:
        # Filter chunks by documents owned by the visitor
        query = db.query(Chunk).join(Document).filter(Document.visitor_id == visitor_id)
        if document_ids:
            query = query.filter(Chunk.document_id.in_(document_ids))
        
        # pgvector similarity search order by distance
        return query.order_by(Chunk.embedding.cosine_distance(embedding_vector)).limit(limit).all()

    @staticmethod
    def get_all_chunks_for_bm25(db: Session, visitor_id: str, document_ids: Optional[List[int]] = None) -> List[Chunk]:
        query = db.query(Chunk).join(Document).filter(Document.visitor_id == visitor_id)
        if document_ids:
            query = query.filter(Chunk.document_id.in_(document_ids))
        return query.all()

document_repo = DocumentRepository()
