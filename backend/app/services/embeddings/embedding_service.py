import google.generativeai as genai
from typing import List
from app.core.config import settings

class EmbeddingService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = "models/text-embedding-004"

    def get_embedding(self, text: str, is_query: bool = False) -> List[float]:
        """
        Generates embedding using Gemini Embeddings API (models/text-embedding-004).
        """
        if not settings.GEMINI_API_KEY:
            # Fallback mock for local development without key
            return [0.0] * 768

        try:
            # Determine correct task type for embeddings
            task_type = "retrieval_query" if is_query else "retrieval_document"
            result = genai.embed_content(
                model=self.model_name,
                contents=text,
                task_type=task_type,
                title="Query" if is_query else "Document Chunk"
            )
            return result["embedding"]
        except Exception as e:
            print(f"Error calling Gemini Embedding API: {e}")
            return [0.0] * 768

    def get_embeddings_bulk(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings in bulk using Gemini Embeddings API.
        """
        if not texts:
            return []
        if not settings.GEMINI_API_KEY:
            return [[0.0] * 768 for _ in texts]

        try:
            result = genai.embed_content(
                model=self.model_name,
                contents=texts,
                task_type="retrieval_document"
            )
            return result["embedding"]
        except Exception as e:
            print(f"Error calling Gemini Bulk Embedding API: {e}")
            return [[0.0] * 768 for _ in texts]

embedding_service = EmbeddingService()
