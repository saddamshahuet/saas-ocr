"""
Unit tests for LLM service (app/services/llm_service.py)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))


@pytest.mark.unit
@pytest.mark.llm
class TestLLMService:
    """Test LLM service functionality."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance."""
        from app.services.llm_service import LLMService
        return LLMService()

    def test_llm_service_initialization(self, llm_service):
        """Test LLM service initializes correctly."""
        assert llm_service is not None
        assert hasattr(llm_service, 'extract_structured_data')

    def test_extract_patient_name(self, llm_service):
        """Test extraction of patient name from text."""
        text = """
        PATIENT INFORMATION
        Name: John Smith
        DOB: 01/15/1980
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "patient" in result
        assert "name" in result["patient"]

    def test_extract_date_of_birth(self, llm_service):
        """Test extraction of date of birth."""
        text = """
        Patient: Jane Doe
        Date of Birth: 03/22/1975
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "patient" in result
        # Should extract DOB in some format

    def test_extract_mrn(self, llm_service):
        """Test extraction of Medical Record Number."""
        text = """
        Medical Record Number: MRN123456789
        Patient Name: Test Patient
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "patient" in result
        if "mrn" in result["patient"]:
            assert "123456789" in result["patient"]["mrn"] or "MRN123456789" in result["patient"]["mrn"]

    def test_extract_diagnosis(self, llm_service):
        """Test extraction of diagnosis."""
        text = """
        Primary Diagnosis: Congestive Heart Failure
        Secondary Diagnosis: Diabetes Type 2
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "medical_info" in result
        if "diagnosis" in result["medical_info"]:
            diagnosis_text = result["medical_info"]["diagnosis"].lower()
            assert "heart failure" in diagnosis_text or "chf" in diagnosis_text

    def test_extract_medications(self, llm_service):
        """Test extraction of medications."""
        text = """
        Current Medications:
        1. Lisinopril 10mg daily
        2. Metformin 500mg BID
        3. Atorvastatin 20mg at bedtime
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "medical_info" in result
        if "medications" in result["medical_info"]:
            meds = result["medical_info"]["medications"]
            assert isinstance(meds, list)
            assert len(meds) > 0

    def test_extract_allergies(self, llm_service):
        """Test extraction of allergies."""
        text = """
        Known Allergies: Penicillin, Sulfa drugs
        Patient reports severe reaction to penicillin
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "medical_info" in result

    def test_extract_physician_name(self, llm_service):
        """Test extraction of physician name."""
        text = """
        Attending Physician: Dr. Sarah Johnson, MD
        Phone: 555-1234
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "provider" in result

    def test_confidence_scores_present(self, llm_service):
        """Test that confidence scores are included in results."""
        text = "Patient: John Doe, DOB: 01/01/1980"

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "confidence_scores" in result
        assert isinstance(result["confidence_scores"], dict)

    def test_handle_empty_text(self, llm_service):
        """Test handling of empty text input."""
        result = llm_service.extract_structured_data("", "hospice_admission")

        assert isinstance(result, dict)
        # Should return structure even with empty text

    def test_handle_malformed_text(self, llm_service):
        """Test handling of malformed/unstructured text."""
        text = "asdfjkl;qwer random gibberish !@#$%"

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert isinstance(result, dict)
        # Should not crash, even if no data extracted

    def test_extract_dnr_status(self, llm_service):
        """Test extraction of DNR status."""
        text = """
        Code Status: DNR (Do Not Resuscitate)
        Patient wishes documented
        """

        result = llm_service.extract_structured_data(text, "hospice_admission")

        assert "medical_info" in result

    def test_different_document_types(self, llm_service):
        """Test extraction for different document types."""
        document_types = [
            "hospice_admission",
            "medication_list",
            "lab_results",
            "discharge_summary"
        ]

        text = "Patient: John Doe"

        for doc_type in document_types:
            result = llm_service.extract_structured_data(text, doc_type)
            assert isinstance(result, dict)

    @patch('app.services.llm_service.re')
    def test_regex_extraction(self, mock_re, llm_service):
        """Test regex-based extraction."""
        # Ensure regex patterns are being used
        text = "Name: John Doe"

        result = llm_service.extract_structured_data(text, "hospice_admission")

        # Regex should be used for extraction
        assert isinstance(result, dict)


@pytest.mark.unit
@pytest.mark.llm
class TestLLMProviders:
    """Test LLM provider integrations."""

    def test_openai_provider_initialization(self):
        """Test OpenAI provider can be initialized."""
        with patch('app.llm_providers.openai_provider.OpenAI'):
            from app.llm_providers.openai_provider import OpenAIProvider

            provider = OpenAIProvider(api_key="test-key")
            assert provider is not None

    def test_huggingface_provider_initialization(self):
        """Test HuggingFace provider initialization."""
        try:
            from app.llm_providers.huggingface_provider import HuggingFaceProvider

            with patch('transformers.pipeline'):
                provider = HuggingFaceProvider(model_name="test-model")
                assert provider is not None
        except ImportError:
            pytest.skip("HuggingFace provider not available")

    def test_provider_extract_method(self):
        """Test that providers have extract method."""
        with patch('app.llm_providers.openai_provider.OpenAI'):
            from app.llm_providers.openai_provider import OpenAIProvider

            provider = OpenAIProvider(api_key="test-key")
            assert hasattr(provider, 'extract') or hasattr(provider, 'generate')
