import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import google.generativeai as genai
from app.core.config import settings
from datetime import datetime
from app.utils.schema_helper import get_clean_schema

class QueryAnalysisResult(BaseModel):
    search_mode: str = Field(
        ..., 
        description="The query mode: 'semantic' (general RAG), 'metadata_filter' (specific SQL conditions like invoices > 50k, expiry dates), 'comparative' (compare A and B), 'summarize' (summarize a doc)"
    )
    doc_type_filter: Optional[str] = Field(
        None, 
        description="Target document type: 'Invoice', 'Contract', 'Medical Report', 'ID', 'Passport', 'Receipt', 'Policy', 'Manual', 'Employee Document' or null if general"
    )
    search_query: str = Field(
        ..., 
        description="A cleaned semantic query optimized for vector and keyword search (removing conversational filler like 'please find me')"
    )
    targeted_documents: List[str] = Field(
        default=[], 
        description="List of specific filenames or entities mentioned in the query (e.g., ['Contract A', 'Invoice 102'])"
    )
    # Structured SQL filter criteria
    amount_threshold: Optional[float] = Field(None, description="A numeric amount threshold if searching invoices/receipts (e.g., 50000.0)")
    amount_operator: Optional[str] = Field(None, description="Comparison operator: '>', '<', '=' or null")
    expiry_date_threshold: Optional[str] = Field(None, description="ISO Date threshold for contract expiry or report date (YYYY-MM-DD) if mentioned")
    expiry_date_operator: Optional[str] = Field(None, description="Comparison operator: '>', '<', '=' or null")
    vendor: Optional[str] = Field(None, description="Name of the vendor/merchant if specified")
    parties: Optional[str] = Field(None, description="Names of contracting parties if specified")
    gst_mentioned: Optional[bool] = Field(None, description="True if query explicitly asks about GST or tax-related documents")


class QueryAnalyzer:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def analyze_query(self, user_query: str) -> QueryAnalysisResult:
        """
        Parses user query into structured search commands and parameters.
        """
        # Default fallback in case LLM is offline
        fallback = QueryAnalysisResult(
            search_mode="semantic",
            search_query=user_query
        )
        
        if not settings.GEMINI_API_KEY or not user_query.strip():
            return fallback

        current_date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        try:
            prompt = (
                f"Analyze the following search query and extract structured filter parameters. "
                f"The current reference date is {current_date_str} (today). "
                f"Use this date to resolve terms like 'next month', 'expired', or 'expiring next month'. "
                f"For example, if today is 2026-07-17, 'next month' contracts expire between 2026-08-01 and 2026-08-31.\n\n"
                f"User Query: \"{user_query}\""
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": get_clean_schema(QueryAnalysisResult)
                }
            )
            
            return QueryAnalysisResult.model_validate_json(response.text)
        except Exception as e:
            print(f"Error in query analysis: {e}")
            return fallback

query_analyzer = QueryAnalyzer()
