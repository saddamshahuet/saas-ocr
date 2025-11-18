"""Extraction result schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class FieldConfidence(BaseModel):
    """Confidence score for an extracted field"""
    value: Any
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    source: str = Field(..., description="Source of the extraction (ocr, llm, etc.)")


class PatientDemographics(BaseModel):
    """Patient demographic information"""
    patient_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    medical_record_number: Optional[str] = None


class MedicalInformation(BaseModel):
    """Medical information"""
    primary_diagnosis: Optional[str] = None
    secondary_diagnoses: Optional[list[str]] = None
    medications: Optional[list[Dict[str, str]]] = None
    allergies: Optional[list[str]] = None
    dnr_status: Optional[bool] = None


class ProviderInformation(BaseModel):
    """Healthcare provider information"""
    attending_physician: Optional[str] = None
    physician_phone: Optional[str] = None
    referring_facility: Optional[str] = None


class ExtractionResult(BaseModel):
    """Complete extraction result"""
    patient_demographics: Optional[PatientDemographics] = None
    medical_information: Optional[MedicalInformation] = None
    provider_information: Optional[ProviderInformation] = None
    raw_text: Optional[str] = None
    confidence_scores: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None
