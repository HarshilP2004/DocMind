import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai
from app.core.config import settings
from app.utils.schema_helper import get_clean_schema

# --- Type-Specific Pydantic Schemas for Structured LLM Outputs ---

class DocumentClassifier(BaseModel):
    document_type: str = Field(
        ..., 
        description="Categorize the document into one of: 'Invoice', 'Contract', 'Medical Report', 'ID', 'Passport', 'Receipt', 'Policy', 'Manual', 'Employee Document', 'Generic'"
    )


class InvoiceMetadata(BaseModel):
    vendor: str = Field(..., description="Name of the vendor/seller")
    invoice_number: str = Field(..., description="Invoice identifier/number")
    date: str = Field(..., description="Date of the invoice (YYYY-MM-DD or original text)")
    gst: Optional[str] = Field(None, description="GSTIN/Tax Registration Number of the vendor or buyer")
    amount: float = Field(..., description="Total invoice amount (numeric value only)")
    currency: str = Field("INR", description="Currency of the invoice (e.g., INR, USD, EUR)")


class ContractMetadata(BaseModel):
    parties: List[str] = Field(..., description="Names of the parties signing the contract")
    effective_date: str = Field(..., description="Contract commencement/effective date")
    expiry_date: Optional[str] = Field(None, description="Contract expiry/termination date if mentioned")
    governing_law: Optional[str] = Field(None, description="Jurisdiction or governing law of the contract")


class MedicalReportMetadata(BaseModel):
    patient_name: str = Field(..., description="Name of the patient")
    report_date: str = Field(..., description="Date the medical report was issued")
    diagnosis: Optional[str] = Field(None, description="Primary clinical diagnosis or summary of results")
    doctor_name: Optional[str] = Field(None, description="Name of the attending physician/lab tester")


class IDPassportMetadata(BaseModel):
    full_name: str = Field(..., description="Full name of the document holder")
    id_number: str = Field(..., description="Passport or Identification number")
    issue_date: Optional[str] = Field(None, description="Date of document issue")
    expiry_date: Optional[str] = Field(None, description="Date of document expiry")
    nationality: Optional[str] = Field(None, description="Nationality of the holder")


class ReceiptMetadata(BaseModel):
    merchant: str = Field(..., description="Name of the merchant/store")
    date: str = Field(..., description="Date of the purchase")
    amount: float = Field(..., description="Total transaction amount")
    items: List[str] = Field(default=[], description="List of items or services purchased")


class GeneralMetadata(BaseModel):
    title: str = Field(..., description="Descriptive title of the document")
    version: Optional[str] = Field(None, description="Version or policy revision number")
    effective_date: Optional[str] = Field(None, description="Date the policy/manual takes effect")
    department: Optional[str] = Field(None, description="Department responsible for this document")


class MetadataExtractor:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def detect_document_type(self, doc_text: str) -> str:
        """
        Uses Gemini to classify the document type based on its extracted text.
        """
        if not settings.GEMINI_API_KEY or not doc_text.strip():
            return "Generic"
            
        try:
            prompt = (
                f"Analyze the following document text and classify its type:\n\n"
                f"{doc_text[:3000]}\n\n"
                f"Classify strictly into one of the allowed categories: "
                f"'Invoice', 'Contract', 'Medical Report', 'ID', 'Passport', 'Receipt', 'Policy', 'Manual', 'Employee Document', 'Generic'."
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": get_clean_schema(DocumentClassifier)
                }
            )
            
            result = json.loads(response.text)
            return result.get("document_type", "Generic")
        except Exception as e:
            print(f"Error classifying document type: {e}")
            return "Generic"

    def extract_metadata(self, doc_text: str, doc_type: str) -> Dict[str, Any]:
        """
        Extracts structured metadata depending on the classified document type.
        """
        if not settings.GEMINI_API_KEY or not doc_text.strip():
            return {}

        # Select schema based on document type
        schema_map = {
            "Invoice": InvoiceMetadata,
            "Contract": ContractMetadata,
            "Medical Report": MedicalReportMetadata,
            "ID": IDPassportMetadata,
            "Passport": IDPassportMetadata,
            "Receipt": ReceiptMetadata,
            "Policy": GeneralMetadata,
            "Manual": GeneralMetadata,
            "Employee Document": GeneralMetadata,
        }
        
        schema = schema_map.get(doc_type, GeneralMetadata)
        
        try:
            prompt = (
                f"Extract structured metadata from the following {doc_type} text. "
                f"Fill in the fields accurately based on the contents. If a field is not present, return null.\n\n"
                f"{doc_text[:6000]}"
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": get_clean_schema(schema)
                }
            )
            
            return json.loads(response.text)
        except Exception as e:
            print(f"Error extracting metadata for {doc_type}: {e}")
            return {"title": "Extraction Failed", "error": str(e)}

metadata_extractor = MetadataExtractor()
