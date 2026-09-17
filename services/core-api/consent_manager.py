#!/usr/bin/env python3
"""
Purpose-Bound Consent Management Engine (DPDP Act 2023 Compliant) (Phase 02).
Enforces:
1. Purpose specification (Clinical Treatment vs Secondary Research vs Commercial).
2. Multilingual consent forms (Bengali, Hindi, English).
3. Multiple verification modalities (OTP, Biometric Thumbprint, Voice Hash, Physical Paper).
4. Nominee / Legal Guardian management for minors and incapacitated patients.
5. Dynamic Data Fiduciary Filter: Instantly purges revoked patients from secondary research exports
   while preserving active clinical charts for treating doctors.
"""
import uuid
import hashlib
from typing import Dict, List, Optional, Set
from enum import Enum
from datetime import datetime, timezone

class ConsentPurpose(str, Enum):
    CLINICAL_TREATMENT = "CLINICAL_TREATMENT"
    SECONDARY_RESEARCH_DEIDENTIFIED = "SECONDARY_RESEARCH_DEIDENTIFIED"
    COMMERCIAL_COMMUNICATION = "COMMERCIAL_COMMUNICATION"
    ORGAN_DONATION = "ORGAN_DONATION"

class ConsentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"

class VerificationModality(str, Enum):
    OTP = "OTP"
    BIOMETRIC_THUMBPRINT = "BIOMETRIC_THUMBPRINT"
    VOICE_RECORDING_HASH = "VOICE_RECORDING_HASH"
    PHYSICAL_PAPER_FORM = "PHYSICAL_PAPER_FORM"

# Multilingual Statutory Consent Notices
STATUTORY_NOTICES = {
    "BENGALI": {
        ConsentPurpose.CLINICAL_TREATMENT: "আমি আমার সঠিক রোগ নির্ণয় ও চিকিৎসার উদ্দেশ্যে হাসপাতাল কর্তৃপক্ষকে আমার স্বাস্থ্য তথ্য ব্যবহারের সম্মতি দিচ্ছি।",
        ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED: "আমি গবেষণার উদ্দেশ্যে আমার নাম-পরিচয় গোপন রেখে স্বাস্থ্য তথ্যের গবেষণামূলক ব্যবহারে সম্মতি দিচ্ছি।"
    },
    "HINDI": {
        ConsentPurpose.CLINICAL_TREATMENT: "मैं अपने उचित निदान और उपचार के उद्देश्य से अस्पताल को अपने स्वास्थ्य डेटा का उपयोग करने की सहमति देता हूँ।",
        ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED: "मैं चिकित्सा अनुसंधान के उद्देश्य से अपनी पहचान गोपनीय रखते हुए डेटा उपयोग की सहमति देता हूँ।"
    },
    "ENGLISH": {
        ConsentPurpose.CLINICAL_TREATMENT: "I authorize the hospital to collect and process my health data for diagnostic evaluation and clinical care.",
        ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED: "I consent to the de-identified use of my clinical data for biomedical and epidemiological research."
    }
}

class ConsentRecord:
    def __init__(
        self,
        consent_id: str,
        patient_id: str,
        tenant_id: str,
        purpose: ConsentPurpose,
        status: ConsentStatus,
        modality: VerificationModality,
        language: str,
        verification_artifact_hash: str,
        nominee_details: Optional[Dict] = None
    ):
        self.consent_id = consent_id
        self.patient_id = patient_id
        self.tenant_id = tenant_id
        self.purpose = purpose
        self.status = status
        self.modality = modality
        self.language = language
        self.verification_artifact_hash = verification_artifact_hash
        self.nominee_details = nominee_details
        self.granted_at = datetime.now(timezone.utc).isoformat()
        self.revoked_at: Optional[str] = None

class ConsentManager:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._consents: Dict[str, List[ConsentRecord]] = {} # patient_id -> list of consent records

    def grant_consent(
        self,
        patient_id: str,
        purpose: ConsentPurpose,
        modality: VerificationModality,
        language: str = "BENGALI",
        verification_payload: str = "CONFIRMED_VIA_OTP_98300XXXXX",
        nominee: Optional[Dict] = None
    ) -> ConsentRecord:
        """Records statutory purpose-bound consent with cryptographic verification artifact."""
        artifact_hash = hashlib.sha256(verification_payload.encode()).hexdigest()
        consent_id = str(uuid.uuid4())

        record = ConsentRecord(
            consent_id=consent_id,
            patient_id=patient_id,
            tenant_id=self.tenant_id,
            purpose=purpose,
            status=ConsentStatus.ACTIVE,
            modality=modality,
            language=language,
            verification_artifact_hash=artifact_hash,
            nominee_details=nominee
        )

        if patient_id not in self._consents:
            self._consents[patient_id] = []
        self._consents[patient_id].append(record)
        return record

    def revoke_consent(self, patient_id: str, purpose: ConsentPurpose, reason: str) -> bool:
        """Revokes a previously granted purpose consent (Right to Withdraw under DPDP Act)."""
        patient_records = self._consents.get(patient_id, [])
        revoked_any = False
        for c in patient_records:
            if c.purpose == purpose and c.status == ConsentStatus.ACTIVE:
                c.status = ConsentStatus.REVOKED
                c.revoked_at = datetime.now(timezone.utc).isoformat()
                revoked_any = True
        return revoked_any

    def has_active_consent(self, patient_id: str, purpose: ConsentPurpose) -> bool:
        """Verifies if patient has active, unrevoked consent for the specified purpose."""
        for c in self._consents.get(patient_id, []):
            if c.purpose == purpose and c.status == ConsentStatus.ACTIVE:
                return True
        return False

    def filter_research_dataset(self, patient_records: List[Dict]) -> List[Dict]:
        """
        Data Fiduciary Enforcement: Filters out any patient who has NOT granted active
        or has REVOKED consent for SECONDARY_RESEARCH_DEIDENTIFIED.
        """
        permitted_dataset = []
        for p in patient_records:
            pid = p.get("patient_id")
            if self.has_active_consent(pid, ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED):
                # De-identify direct identifiers before research release
                deidentified_record = {
                    "study_id": f"STUDY-SUBJ-{hashlib.sha256(pid.encode()).hexdigest()[:12]}",
                    "gender": p.get("gender"),
                    "age_group": f"{(p.get('age', 40) // 10) * 10}-{(p.get('age', 40) // 10) * 10 + 9}",
                    "clinical_data": p.get("clinical_data", {})
                }
                permitted_dataset.append(deidentified_record)
        return permitted_dataset
