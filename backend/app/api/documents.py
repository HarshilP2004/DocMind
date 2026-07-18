import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status, Header
from sqlalchemy.orm import Session
from pypdf import PdfReader
from pdf2image import convert_from_path

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Document
from app.repositories.document_repo import document_repo
from app.schemas.schemas import DocumentResponse, DocumentMetadataResponse
from app.services.ocr.ocr_service import ocr_service
from app.services.metadata.metadata_extractor import metadata_extractor
from app.utils.chunker import IntelligentChunker
from app.services.embeddings.embedding_service import embedding_service

router = APIRouter()

# Dependency to extract anonymous visitor ID from the request header
def get_visitor_id(x_visitor_id: Optional[str] = Header(None, alias="X-Visitor-ID")) -> str:
    return x_visitor_id or "default_visitor"

def process_document_task(doc_id: int, file_path: str, file_type: str, db_session_factory):
    """
    Background worker function that runs the document intelligence pipeline.
    """
    db: Session = db_session_factory()
    try:
        # 1. Update status to processing
        document_repo.update_document(db, doc_id, status="processing")
        
        extracted_text = ""
        ocr_used = False
        
        # 2. Extract text directly if it is a digital PDF
        if file_type == "pdf":
            try:
                reader = PdfReader(file_path)
                pages_text = []
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages_text.append(f"[PAGE_{i+1}]\n{page_text}")
                
                combined_text = "\n\n".join(pages_text)
                
                # Check if we got substantial text directly
                if len(combined_text.strip()) > 100:
                    extracted_text = combined_text
                else:
                    # PDF contains no selectable text (scanned PDF) -> Run OCR
                    ocr_used = True
            except Exception as e:
                print(f"Error reading PDF direct text: {e}. Falling back to OCR.")
                ocr_used = True
                
            if ocr_used:
                # Convert PDF pages to images
                try:
                    images = convert_from_path(file_path, dpi=150)
                    pages_text = []
                    for i, img in enumerate(images):
                        temp_page_path = settings.UPLOAD_DIR / f"temp_page_{doc_id}_{i+1}.png"
                        img.save(temp_page_path, "PNG")
                        
                        # Perform OCR
                        page_text = ocr_service.extract_text_from_image(temp_page_path)
                        pages_text.append(f"[PAGE_{i+1}]\n{page_text}")
                        
                        # Clean up temp image
                        os.remove(temp_page_path)
                    extracted_text = "\n\n".join(pages_text)
                except Exception as e:
                    print(f"Failed to perform OCR on PDF: {e}")
                    raise e
        else:
            # File is an image (png, jpg, jpeg) -> Run OCR directly
            ocr_used = True
            try:
                img_path = Path(file_path)
                text = ocr_service.extract_text_from_image(img_path)
                extracted_text = f"[PAGE_1]\n{text}"
            except Exception as e:
                print(f"Failed to perform OCR on Image: {e}")
                raise e

        if not extracted_text.strip():
            raise ValueError("No text could be extracted or OCR'd from the document.")

        # 3. Classify document type & extract structured metadata (Gemini)
        doc_type = metadata_extractor.detect_document_type(extracted_text)
        metadata_dict = metadata_extractor.extract_metadata(extracted_text, doc_type)
        
        # Save metadata to DB
        document_repo.create_metadata(db, document_id=doc_id, doc_type=doc_type, extracted_data=metadata_dict)
        
        # 4. Chunk text intelligently
        chunks = IntelligentChunker.chunk_text(extracted_text, document_id=doc_id)
        
        # 5. Generate embeddings in bulk
        chunk_contents = [c["content"] for c in chunks]
        embeddings = embedding_service.get_embeddings_bulk(chunk_contents)
        
        # Add embeddings to chunk data
        for chunk_data, emb in zip(chunks, embeddings):
            chunk_data["embedding"] = emb
            
        # 6. Bulk save chunks to database
        document_repo.bulk_create_chunks(db, chunks)
        
        # 7. Update status to completed
        document_repo.update_document(
            db, 
            doc_id, 
            status="completed", 
            total_chunks=len(chunks), 
            ocr_used=ocr_used
        )
        
    except Exception as e:
        print(f"Error processing document {doc_id}: {str(e)}")
        document_repo.update_document(db, doc_id, status="failed")
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    Upload a document and trigger async pipeline.
    """
    # Validate file type
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["pdf", "png", "jpg", "jpeg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload PDF, PNG, JPG, or JPEG files."
        )
        
    # Generate local path
    import uuid
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = settings.UPLOAD_DIR / unique_filename
    
    # Save file to uploads directory
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to disk: {str(e)}"
        )
        
    # Create DB entry
    db_doc = document_repo.create_document(
        db, 
        visitor_id=visitor_id, 
        filename=filename, 
        file_type=ext, 
        file_path=str(file_path)
    )
    
    # Trigger background tasks
    from app.db.session import SessionLocal
    background_tasks.add_task(
        process_document_task, 
        db_doc.id, 
        str(file_path), 
        ext, 
        SessionLocal
    )
    
    return db_doc


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db), 
    visitor_id: str = Depends(get_visitor_id)
):
    """
    List all documents for the visitor.
    """
    return document_repo.list_by_visitor(db, visitor_id=visitor_id)


@router.get("/{doc_id}/metadata", response_model=DocumentMetadataResponse)
def get_document_metadata(
    doc_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    Get structured metadata for a document.
    """
    doc = document_repo.get_by_id(db, doc_id)
    if not doc or doc.visitor_id != visitor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    meta = document_repo.get_metadata(db, document_id=doc_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata has not been extracted yet or extraction failed."
        )
    return meta


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    Delete a document from DB and disk.
    """
    doc = document_repo.get_by_id(db, doc_id)
    if not doc or doc.visitor_id != visitor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    # Delete from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            print(f"Error removing physical file: {e}")
            
    # Delete from DB
    success = document_repo.delete(db, doc_id)
    if not success:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete document."
        )
    return {"detail": "Document successfully deleted"}
