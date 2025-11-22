"""EHR Integration service

Provides HL7 v2 message generation, FHIR R4 resource creation, and EHR connectors.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class EHRStandard(Enum):
    """EHR standards"""
    HL7_V2 = "hl7_v2"
    FHIR_R4 = "fhir_r4"
    CDA = "cda"  # Clinical Document Architecture


@dataclass
class HL7Segment:
    """HL7 v2 segment"""
    segment_type: str
    fields: List[str]

    def to_string(self) -> str:
        """Convert segment to HL7 format"""
        return f"{self.segment_type}|" + "|".join(self.fields)


@dataclass
class HL7Message:
    """HL7 v2 message"""
    message_type: str  # ADT, ORU, etc.
    segments: List[HL7Segment]
    message_control_id: Optional[str] = None

    def to_string(self) -> str:
        """Convert message to HL7 format"""
        return "\r".join([seg.to_string() for seg in self.segments])


class HL7MessageBuilder:
    """Builder for HL7 v2 messages"""

    def __init__(self):
        self.segments = []

    def add_msh_segment(
        self,
        sending_application: str = "SaaS-OCR",
        sending_facility: str = "OCR",
        receiving_application: str = "EHR",
        receiving_facility: str = "HOSPITAL",
        message_type: str = "ORU",
        trigger_event: str = "R01",
        message_control_id: Optional[str] = None
    ):
        """Add MSH (Message Header) segment"""
        if not message_control_id:
            message_control_id = datetime.now().strftime("%Y%m%d%H%M%S")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        fields = [
            "^~\\&",  # Encoding characters
            sending_application,
            sending_facility,
            receiving_application,
            receiving_facility,
            timestamp,
            "",  # Security
            f"{message_type}^{trigger_event}",
            message_control_id,
            "P",  # Processing ID
            "2.5",  # Version
        ]

        self.segments.append(HL7Segment("MSH", fields))
        return self

    def add_pid_segment(
        self,
        patient_id: str,
        patient_name: str,
        dob: Optional[str] = None,
        gender: Optional[str] = None,
        address: Optional[str] = None
    ):
        """Add PID (Patient Identification) segment"""
        # Split name into components
        name_parts = patient_name.split()
        if len(name_parts) >= 2:
            last_name = name_parts[-1]
            first_name = " ".join(name_parts[:-1])
        else:
            last_name = patient_name
            first_name = ""

        fields = [
            "1",  # Set ID
            "",  # Patient ID (external)
            patient_id,  # Patient ID (internal)
            "",  # Alternate patient ID
            f"{last_name}^{first_name}",  # Patient name
            "",  # Mother's maiden name
            dob or "",  # Date of birth
            gender or "",  # Gender
            "",  # Patient alias
            "",  # Race
            address or "",  # Patient address
        ]

        self.segments.append(HL7Segment("PID", fields))
        return self

    def add_obr_segment(
        self,
        order_id: str,
        service_id: str = "OCR",
        service_name: str = "Document OCR",
        observation_datetime: Optional[str] = None
    ):
        """Add OBR (Observation Request) segment"""
        if not observation_datetime:
            observation_datetime = datetime.now().strftime("%Y%m%d%H%M%S")

        fields = [
            "1",  # Set ID
            order_id,  # Placer order number
            "",  # Filler order number
            f"{service_id}^{service_name}",  # Universal service ID
            "",  # Priority
            "",  # Requested date/time
            observation_datetime,  # Observation date/time
        ]

        self.segments.append(HL7Segment("OBR", fields))
        return self

    def add_obx_segment(
        self,
        set_id: int,
        observation_id: str,
        observation_name: str,
        value: str,
        value_type: str = "ST"  # ST = String, NM = Numeric, etc.
    ):
        """Add OBX (Observation/Result) segment"""
        fields = [
            str(set_id),  # Set ID
            value_type,  # Value type
            f"{observation_id}^{observation_name}",  # Observation identifier
            "",  # Observation sub-ID
            str(value),  # Observation value
            "",  # Units
            "",  # References range
            "",  # Abnormal flags
            "",  # Probability
            "",  # Nature of abnormal test
            "F",  # Observation result status (F = Final)
        ]

        self.segments.append(HL7Segment("OBX", fields))
        return self

    def build(self, message_type: str = "ORU") -> HL7Message:
        """Build HL7 message"""
        return HL7Message(
            message_type=message_type,
            segments=self.segments
        )


class FHIRResourceBuilder:
    """Builder for FHIR R4 resources"""

    @staticmethod
    def create_patient_resource(
        patient_id: str,
        given_name: str,
        family_name: str,
        dob: Optional[str] = None,
        gender: Optional[str] = None,
        mrn: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create FHIR Patient resource"""
        resource = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [
                {
                    "use": "official",
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                "code": "MR",
                                "display": "Medical Record Number"
                            }
                        ]
                    },
                    "value": mrn or patient_id
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": family_name,
                    "given": [given_name]
                }
            ]
        }

        if dob:
            resource["birthDate"] = dob

        if gender:
            # Map common gender values to FHIR codes
            gender_map = {
                "M": "male",
                "F": "female",
                "O": "other",
                "U": "unknown"
            }
            resource["gender"] = gender_map.get(gender.upper(), "unknown")

        return resource

    @staticmethod
    def create_document_reference_resource(
        document_id: str,
        patient_id: str,
        document_type: str = "medical-record",
        content_base64: Optional[str] = None,
        content_type: str = "application/pdf",
        extracted_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create FHIR DocumentReference resource"""
        resource = {
            "resourceType": "DocumentReference",
            "id": document_id,
            "status": "current",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11488-4",
                        "display": "Consultation note"
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "date": datetime.now().isoformat(),
            "content": []
        }

        # Add content if provided
        if content_base64:
            resource["content"].append({
                "attachment": {
                    "contentType": content_type,
                    "data": content_base64
                }
            })

        # Add extracted data as contained resource
        if extracted_data:
            resource["contained"] = [{
                "resourceType": "Parameters",
                "parameter": [
                    {
                        "name": key,
                        "valueString": str(value)
                    }
                    for key, value in extracted_data.items()
                ]
            }]

        return resource

    @staticmethod
    def create_observation_resource(
        observation_id: str,
        patient_id: str,
        code: str,
        display: str,
        value: Any,
        value_type: str = "string"
    ) -> Dict[str, Any]:
        """Create FHIR Observation resource"""
        resource = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": code,
                        "display": display
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": datetime.now().isoformat()
        }

        # Add value based on type
        if value_type == "string":
            resource["valueString"] = str(value)
        elif value_type == "quantity":
            resource["valueQuantity"] = {
                "value": float(value)
            }
        elif value_type == "boolean":
            resource["valueBoolean"] = bool(value)

        return resource

    @staticmethod
    def create_bundle_resource(
        resources: List[Dict[str, Any]],
        bundle_type: str = "transaction"
    ) -> Dict[str, Any]:
        """Create FHIR Bundle containing multiple resources"""
        entries = []
        for resource in resources:
            entry = {
                "resource": resource,
                "request": {
                    "method": "POST",
                    "url": resource["resourceType"]
                }
            }
            entries.append(entry)

        bundle = {
            "resourceType": "Bundle",
            "type": bundle_type,
            "entry": entries
        }

        return bundle


class EHRConnector:
    """Base connector for EHR systems"""

    def __init__(
        self,
        ehr_standard: EHRStandard,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        """
        Initialize EHR connector

        Args:
            ehr_standard: EHR standard to use
            endpoint_url: EHR API endpoint
            api_key: API key for authentication
            client_id: OAuth client ID
            client_secret: OAuth client secret
        """
        self.ehr_standard = ehr_standard
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.client_id = client_id
        self.client_secret = client_secret

    def convert_extracted_data_to_hl7(
        self,
        extracted_data: Dict[str, Any],
        patient_id: str = "UNK"
    ) -> HL7Message:
        """
        Convert extracted data to HL7 v2 message

        Args:
            extracted_data: Extracted data dictionary
            patient_id: Patient ID

        Returns:
            HL7Message object
        """
        builder = HL7MessageBuilder()

        # Add MSH segment
        builder.add_msh_segment()

        # Add PID segment
        patient_name = extracted_data.get("patient_name", "Unknown")
        dob = extracted_data.get("date_of_birth", "")
        gender = extracted_data.get("gender", "")

        builder.add_pid_segment(
            patient_id=patient_id,
            patient_name=patient_name,
            dob=dob,
            gender=gender
        )

        # Add OBR segment
        builder.add_obr_segment(
            order_id=f"OCR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        # Add OBX segments for each extracted field
        obx_counter = 1
        for key, value in extracted_data.items():
            if value and key not in ["patient_name", "date_of_birth", "gender"]:
                builder.add_obx_segment(
                    set_id=obx_counter,
                    observation_id=key.upper(),
                    observation_name=key.replace("_", " ").title(),
                    value=str(value)
                )
                obx_counter += 1

        return builder.build()

    def convert_extracted_data_to_fhir(
        self,
        extracted_data: Dict[str, Any],
        patient_id: str = "unknown",
        document_id: str = "doc-001"
    ) -> Dict[str, Any]:
        """
        Convert extracted data to FHIR Bundle

        Args:
            extracted_data: Extracted data dictionary
            patient_id: Patient ID
            document_id: Document ID

        Returns:
            FHIR Bundle resource
        """
        resources = []

        # Create Patient resource
        patient_name = extracted_data.get("patient_name", "Unknown")
        name_parts = patient_name.split()
        given_name = name_parts[0] if name_parts else "Unknown"
        family_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        patient_resource = FHIRResourceBuilder.create_patient_resource(
            patient_id=patient_id,
            given_name=given_name,
            family_name=family_name,
            dob=extracted_data.get("date_of_birth"),
            gender=extracted_data.get("gender"),
            mrn=extracted_data.get("medical_record_number")
        )
        resources.append(patient_resource)

        # Create DocumentReference resource
        doc_ref = FHIRResourceBuilder.create_document_reference_resource(
            document_id=document_id,
            patient_id=patient_id,
            extracted_data=extracted_data
        )
        resources.append(doc_ref)

        # Create Observation resources for key findings
        obs_counter = 1
        for key, value in extracted_data.items():
            if value and key not in ["patient_name", "date_of_birth", "gender", "medical_record_number"]:
                obs = FHIRResourceBuilder.create_observation_resource(
                    observation_id=f"obs-{obs_counter}",
                    patient_id=patient_id,
                    code=key.upper(),
                    display=key.replace("_", " ").title(),
                    value=value
                )
                resources.append(obs)
                obs_counter += 1

        # Create Bundle
        bundle = FHIRResourceBuilder.create_bundle_resource(resources)

        return bundle

    def send_to_ehr(self, data: Any) -> Dict[str, Any]:
        """
        Send data to EHR system

        Args:
            data: HL7 message or FHIR resource

        Returns:
            Response from EHR system
        """
        if not self.endpoint_url:
            raise ValueError("EHR endpoint URL not configured")

        try:
            import requests

            headers = {}

            # Add authentication
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Determine content type
            if self.ehr_standard == EHRStandard.HL7_V2:
                headers["Content-Type"] = "x-application/hl7-v2+er7"
                payload = data.to_string() if isinstance(data, HL7Message) else str(data)
            elif self.ehr_standard == EHRStandard.FHIR_R4:
                headers["Content-Type"] = "application/fhir+json"
                payload = json.dumps(data)
            else:
                raise ValueError(f"Unsupported EHR standard: {self.ehr_standard}")

            # Send request
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                data=payload,
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"Successfully sent data to EHR: {response.status_code}")

            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json() if response.content else {}
            }

        except Exception as e:
            logger.error(f"Failed to send data to EHR: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instances
_ehr_connector = None


def get_ehr_connector(
    ehr_standard: EHRStandard = EHRStandard.FHIR_R4,
    endpoint_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> EHRConnector:
    """Get or create EHR connector"""
    global _ehr_connector
    if _ehr_connector is None:
        _ehr_connector = EHRConnector(
            ehr_standard=ehr_standard,
            endpoint_url=endpoint_url,
            api_key=api_key
        )
    return _ehr_connector
