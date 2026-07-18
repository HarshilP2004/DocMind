import json
from typing import Generator, List, Optional
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.retrieval.retrieval_service import retrieval_service

class RAGService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def generate_streaming_response(
        self, 
        db: Session, 
        visitor_id: str, 
        query: str, 
        session_id: Optional[int] = None, 
        document_ids: Optional[List[int]] = None
    ) -> Generator[str, None, None]:
        """
        Retrieves relevant context, compiles the prompt, runs streaming Gemini inference,
        and yields structured tokens & citations.
        """
        # 1. Retrieve the top relevant chunks using the hybrid pipeline
        relevant_records = retrieval_service.retrieve_relevant_chunks(
            db, visitor_id=visitor_id, query=query, document_ids=document_ids
        )
        
        # Format citations to send to client
        citations = []
        context_blocks = []
        
        for record in relevant_records:
            chunk = record["chunk"]
            doc_name = record["document_name"]
            page_num = record["page_number"]
            
            # Format block for LLM prompt
            context_blocks.append(
                f"SOURCE DOCUMENT: {doc_name} | PAGE: {page_num if page_num else 'N/A'}\n"
                f"CONTENT:\n{chunk.content}\n"
                f"----------------------------------------"
            )
            
            # Save for client-side citation display
            citations.append({
                "document_name": doc_name,
                "page_number": page_num,
                "content": chunk.content
            })

        # Yield citations first as a metadata event
        yield f"event: citations\ndata: {json.dumps(citations)}\n\n"
        
        # 2. Build the system prompt enforcing strict groundedness
        context_text = "\n\n".join(context_blocks)
        
        system_prompt = (
            "You are a production-grade enterprise document assistant. "
            "Your sole objective is to answer the user's question using ONLY the provided Source Documents below. "
            "Strictly follow these guidelines:\n"
            "1. Answer the query truthfully and entirely based on the provided sources.\n"
            "2. For every statement or claim you make, cite the source document name and page number "
            "using brackets, e.g. [Document_Name.pdf, Page 3]. If page is null/N/A, write [Document_Name.pdf].\n"
            "3. Refuse to hallucinate: If the provided source documents do not contain the answer, "
            "you MUST state explicitly: 'I could not find the information in the uploaded documents.' "
            "Do not make up any facts or draw on external knowledge.\n"
            "4. Maintain a professional, concise tone.\n\n"
            f"SOURCE DOCUMENTS:\n{context_text}\n\n"
            f"USER QUERY: \"{query}\"\n"
            f"ANSWER:"
        )

        # 3. Stream the generation
        try:
            response = self.model.generate_content(system_prompt, stream=True)
            for chunk in response:
                try:
                    text_part = chunk.text
                    if text_part:
                        # Yield token events
                        yield f"event: token\ndata: {json.dumps({'token': text_part})}\n\n"
                except ValueError:
                    # Ignore final metadata chunks containing no text parts
                    pass
        except Exception as e:
            print(f"Error generating RAG response: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            
        yield "event: done\ndata: {}\n\n"

rag_service = RAGService()
