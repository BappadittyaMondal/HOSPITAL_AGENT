#!/usr/bin/env python3
"""
Legacy Data Migration & FHIR R4 ETL Pipeline (Gap 14).
Extracts legacy hospital records (paper registers / legacy software dumps),
cleanses demographic anomalies, normalizes Indian name variations,
and transforms them into compliant HL7 FHIR R4 Patient Resources.
"""
import re
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone

def cleanse_indian_phone(raw_phone: str) -> Optional[str]:
    """Cleanses varied Indian phone formats (+91, 0, spaces) to +91XXXXXXXXXX."""
    digits = re.sub(r"\D", "", raw_phone)
    if len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    elif len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return None

def normalize_name(raw_name: str) -> str:
    """Normalizes titles, whitespace, and capitalization for Indian names."""
    cleaned = raw_name.strip()
    cleaned = re.sub(r"^(dr\.|mr\.|mrs\.|ms\.|shri|smt\.)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title()

class LegacyPatientETL:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def transform_legacy_record_to_fhir(self, legacy_row: Dict) -> Dict:
        """
        Transforms messy legacy tabular record into an HL7 FHIR R4 Patient Resource.
        """
        raw_name = legacy_row.get("PatientName", "")
        clean_name = normalize_name(raw_name)
        parts = clean_name.split(" ", 1)
        given_name = parts[0] if parts else "Unknown"
        family_name = parts[1] if len(parts) > 1 else ""

        raw_phone = legacy_row.get("ContactPhone", "")
        clean_phone = cleanse_indian_phone(raw_phone)

        # Parse birth date
        raw_dob = legacy_row.get("DOB", "")
        clean_dob = "1970-01-01"
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(raw_dob.strip(), fmt)
                clean_dob = dt.strftime("%Y-%m-%d")
                break
            except (ValueError, AttributeError):
                continue

        # Standard FHIR R4 Patient Bundle Resource
        fhir_patient = {
            "resourceType": "Patient",
            "id": str(uuid.uuid4()),
            "meta": {
                "source": "urn:legacy:migration",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "tag": [
                    {"system": "https://hospital.local/tenant", "code": self.tenant_id}
                ]
            },
            "identifier": [
                {
                    "use": "usual",
                    "type": {
                        "coding": [
                            {"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}
                        ]
                    },
                    "system": f"https://hospital.local/mrn/{self.tenant_id}",
                    "value": legacy_row.get("OldMRN", f"MIG-{uuid.uuid4().hex[:8].upper()}")
                }
            ],
            "active": True,
            "name": [
                {
                    "use": "official",
                    "text": clean_name,
                    "family": family_name,
                    "given": [given_name]
                }
            ],
            "gender": legacy_row.get("Gender", "unknown").lower(),
            "birthDate": clean_dob,
            "telecom": []
        }

        if clean_phone:
            fhir_patient["telecom"].append({
                "system": "phone",
                "value": clean_phone,
                "use": "mobile"
            })

        return fhir_patient
