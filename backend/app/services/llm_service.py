"""LLM service for structured data extraction from OCR text"""
import json
import logging
from typing import Dict, Optional, Any
import re

logger = logging.getLogger(__name__)


class LLMService:
    """Service for extracting structured data using LLM"""

    def __init__(self, model_name: str = "llama3-8b", use_gpu: bool = True):
        """
        Initialize LLM service

        Args:
            model_name: Name of the LLM model to use
            use_gpu: Whether to use GPU acceleration
        """
        self.model_name = model_name
        self.use_gpu = use_gpu

        # NOTE: In production, initialize actual LLM here (e.g., using Ollama, vLLM, or Transformers)
        # For MVP, we'll use rule-based extraction
        logger.info(f"LLM Service initialized (Model: {model_name}, GPU: {use_gpu})")

    def extract_patient_demographics(self, text: str) -> Dict[str, Any]:
        """Extract patient demographic information"""
        demographics = {}

        # Extract patient name (look for common patterns)
        name_patterns = [
            r"Patient Name:\s*([A-Za-z\s]+)",
            r"Name:\s*([A-Za-z\s]+)",
            r"Pt\. Name:\s*([A-Za-z\s]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                demographics["patient_name"] = match.group(1).strip()
                break

        # Extract date of birth
        dob_patterns = [
            r"DOB:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Date of Birth:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Birth Date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                demographics["date_of_birth"] = match.group(1).strip()
                break

        # Extract gender
        if re.search(r"\b(male|M)\b", text, re.IGNORECASE) and not re.search(r"\bfemale\b", text, re.IGNORECASE):
            demographics["gender"] = "Male"
        elif re.search(r"\b(female|F)\b", text, re.IGNORECASE):
            demographics["gender"] = "Female"

        # Extract medical record number
        mrn_patterns = [
            r"MRN:\s*([A-Z0-9]+)",
            r"Medical Record #:\s*([A-Z0-9]+)",
            r"Record Number:\s*([A-Z0-9]+)",
        ]
        for pattern in mrn_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                demographics["medical_record_number"] = match.group(1).strip()
                break

        # Extract phone
        phone_pattern = r"\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})"
        match = re.search(phone_pattern, text)
        if match:
            demographics["phone"] = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"

        return demographics

    def extract_medical_information(self, text: str) -> Dict[str, Any]:
        """Extract medical information"""
        medical_info = {}

        # Extract primary diagnosis
        diagnosis_patterns = [
            r"Primary Diagnosis:\s*([^\n]+)",
            r"Diagnosis:\s*([^\n]+)",
            r"Principal Diagnosis:\s*([^\n]+)",
        ]
        for pattern in diagnosis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                medical_info["primary_diagnosis"] = match.group(1).strip()
                break

        # Extract allergies
        allergy_patterns = [
            r"Allergies:\s*([^\n]+)",
            r"Drug Allergies:\s*([^\n]+)",
            r"Allergy:\s*([^\n]+)",
        ]
        for pattern in allergy_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                allergies_text = match.group(1).strip()
                if allergies_text.lower() not in ["none", "nkda", "nka"]:
                    medical_info["allergies"] = [a.strip() for a in allergies_text.split(",")]
                else:
                    medical_info["allergies"] = []
                break

        # Extract DNR status
        if re.search(r"\bDNR\b|\bDo Not Resuscitate\b", text, re.IGNORECASE):
            medical_info["dnr_status"] = True
        elif re.search(r"\bFull Code\b", text, re.IGNORECASE):
            medical_info["dnr_status"] = False

        # Extract medications (simplified)
        medications = []
        medication_section = re.search(
            r"Medications?:\s*(.*?)(?=\n\n|\n[A-Z]|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if medication_section:
            med_text = medication_section.group(1)
            # Split by lines and parse each medication
            for line in med_text.split("\n"):
                line = line.strip()
                if line and not line.lower().startswith("medications"):
                    medications.append({"medication": line})

        if medications:
            medical_info["medications"] = medications

        return medical_info

    def extract_provider_information(self, text: str) -> Dict[str, Any]:
        """Extract healthcare provider information"""
        provider_info = {}

        # Extract physician name
        physician_patterns = [
            r"Attending Physician:\s*([^\n]+)",
            r"Physician:\s*([^\n]+)",
            r"Provider:\s*([^\n]+)",
            r"Dr\.\s+([A-Za-z\s]+)",
        ]
        for pattern in physician_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                provider_info["attending_physician"] = match.group(1).strip()
                break

        # Extract physician phone
        # Look for phone number near "physician" or "provider"
        text_lower = text.lower()
        physician_idx = text_lower.find("physician")
        if physician_idx != -1:
            surrounding_text = text[max(0, physician_idx-50):physician_idx+200]
            phone_match = re.search(r"\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})", surrounding_text)
            if phone_match:
                provider_info["physician_phone"] = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"

        return provider_info

    def extract_structured_data(
        self,
        text: str,
        schema_template: str = "medical_general"
    ) -> Dict[str, Any]:
        """
        Extract structured data from OCR text

        Args:
            text: Raw OCR text
            schema_template: Template to use for extraction

        Returns:
            Dictionary with extracted structured data
        """
        try:
            # Extract different sections
            demographics = self.extract_patient_demographics(text)
            medical = self.extract_medical_information(text)
            provider = self.extract_provider_information(text)

            # Combine into structured result
            result = {
                "patient_demographics": demographics if demographics else None,
                "medical_information": medical if medical else None,
                "provider_information": provider if provider else None,
            }

            # Calculate confidence scores (simplified)
            confidence_scores = self._calculate_confidence_scores(result)

            return {
                "extracted_data": result,
                "confidence_scores": confidence_scores,
                "schema_used": schema_template
            }

        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {
                "extracted_data": {},
                "confidence_scores": {},
                "error": str(e)
            }

    def _calculate_confidence_scores(self, data: Dict) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields"""
        scores = {}

        # Simple heuristic: if field is present and not empty, give it 0.85 confidence
        # In production, use actual model confidence scores
        for section_name, section_data in data.items():
            if section_data:
                for field_name, field_value in section_data.items():
                    if field_value:
                        scores[f"{section_name}.{field_name}"] = 0.85
                    else:
                        scores[f"{section_name}.{field_name}"] = 0.0

        return scores


# Singleton instance
_llm_service_instance = None


def get_llm_service(model_name: str = "llama3-8b", use_gpu: bool = True) -> LLMService:
    """Get or create LLM service singleton"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService(model_name=model_name, use_gpu=use_gpu)
    return _llm_service_instance
