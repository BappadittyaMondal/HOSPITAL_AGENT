"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Module: psychiatry_mhca_engine.py
Operational Scope:
  - Mental Healthcare Act (MHCA 2017) Statutory Compliance Workflows
  - Quality Gate 2: Involuntary/Supported Admission (Sec 89/90) Auto-Generates Form & 72-Hour Review Board Dossier
  - Statutory Advance Directive (AD) & Nominated Representative (NR) Verification
  - Section 23 Ultra-Restricted Psychiatric Notes Access Control Barrier
  - Substance Withdrawal Scoring: CIWA-Ar (Alcohol) & COWS (Opioid)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any


class MHCAComplianceError(Exception):
    """Base exception for Mental Healthcare Act statutory violations."""
    pass


class PsychiatricRecordPrivacyError(MHCAComplianceError):
    """Raised when an unprivileged user attempts to access protected mental health notes."""
    pass


@dataclass
class MHCAAdmissionDossier:
    dossier_id: str
    patient_id: str
    admission_type: str             # INDEPENDENT (Sec 85/86), SUPPORTED_INVOLUNTARY (Sec 89/90)
    primary_psychiatrist_id: str
    secondary_evaluator_id: str
    nominated_representative_id: str
    nominated_representative_name: str
    nominated_representative_consent: bool
    advance_directive_registered: bool
    admitted_at: datetime
    review_board_deadline_72h: datetime
    statutory_form_name: str        # e.g., "MHCA_FORM_4_SUPPORTED_ADMISSION"
    dossier_status: str             # PENDING_DISPATCH, DISPATCHED_TO_MHRB, CONFIRMED
    clinical_justification: str


@dataclass
class CIWAArAssessment:
    assessment_id: str
    patient_id: str
    total_score: int                # 0 - 67
    severity: str                   # MILD (<10), MODERATE (10-18), SEVERE (>18)
    benzodiazepine_protocol_indicated: bool
    assessed_by: str
    assessed_at: str


@dataclass
class COWSAssessment:
    assessment_id: str
    patient_id: str
    total_score: int                # 0 - 48
    severity: str                   # MILD (5-12), MODERATE (13-24), MODERATELY_SEVERE (25-36), SEVERE (>36)
    assessed_by: str
    assessed_at: str


class PsychiatryMHCAEngine:
    """
    MHCA 2017 legal compliance engine managing involuntary admission dossiers,
    Review Board notifications, protected privacy records, and withdrawal scales.
    """

    def __init__(self):
        self.dossiers: Dict[str, MHCAAdmissionDossier] = {}
        self.ciwa_assessments: List[CIWAArAssessment] = []
        self.cows_assessments: List[COWSAssessment] = []
        # Confidential psychiatric clinical notes
        self.protected_clinical_notes: Dict[str, List[Dict[str, Any]]] = {}

    def process_supported_involuntary_admission(
        self,
        patient_id: str,
        primary_psychiatrist_id: str,
        secondary_evaluator_id: str,
        nominated_representative_id: str,
        nominated_representative_name: str,
        nominated_rep_consent: bool,
        advance_directive_registered: bool,
        clinical_justification: str,
        admission_time: Optional[datetime] = None
    ) -> MHCAAdmissionDossier:
        """
        Quality Gate 2:
        Involuntary psychiatric admission auto-generates statutory MHCA Form and
        schedules Review Board dossier dispatch within 72 hours.
        Under Section 89 of MHCA 2017:
        - Two medical practitioners (at least one psychiatrist).
        - Nominated representative application/consent.
        - Notice to Mental Health Review Board within 72 hours.
        """
        if admission_time is None:
            admission_time = datetime.now(timezone.utc)

        if primary_psychiatrist_id == secondary_evaluator_id:
            raise MHCAComplianceError("MHCA Sec 89 violation: Independent evaluation requires two distinct medical practitioners.")

        if not nominated_rep_consent:
            raise MHCAComplianceError("MHCA Sec 89 violation: Nominated representative written consent is mandatory for supported admission.")

        deadline_72h = admission_time + timedelta(hours=72)
        dossier_id = f"MHCA-SEC89-{patient_id}-{int(admission_time.timestamp())}"

        dossier = MHCAAdmissionDossier(
            dossier_id=dossier_id,
            patient_id=patient_id,
            admission_type="SUPPORTED_INVOLUNTARY",
            primary_psychiatrist_id=primary_psychiatrist_id,
            secondary_evaluator_id=secondary_evaluator_id,
            nominated_representative_id=nominated_representative_id,
            nominated_representative_name=nominated_representative_name,
            nominated_representative_consent=nominated_rep_consent,
            advance_directive_registered=advance_directive_registered,
            admitted_at=admission_time,
            review_board_deadline_72h=deadline_72h,
            statutory_form_name="MHCA_FORM_4_SUPPORTED_ADMISSION",
            dossier_status="PENDING_DISPATCH",
            clinical_justification=clinical_justification
        )
        self.dossiers[patient_id] = dossier
        return dossier

    def verify_psychiatric_note_access(self, requesting_role: str, user_id: str) -> bool:
        """
        Section 23 of MHCA 2017: Strict confidentiality of mental health records.
        Only PSYCHIATRIST, CLINICAL_PSYCHOLOGIST, PSYCHIATRIC_SOCIAL_WORKER, or CMO can access.
        """
        authorized_roles = {"PSYCHIATRIST", "CLINICAL_PSYCHOLOGIST", "PSYCHIATRIC_SOCIAL_WORKER", "CHIEF_MEDICAL_OFFICER"}
        if requesting_role.upper() not in authorized_roles:
            raise PsychiatricRecordPrivacyError(
                f"STATUTORY PRIVACY VIOLATION (MHCA 2017 Sec 23): User '{user_id}' with role '{requesting_role}' "
                f"is strictly barred from accessing protected psychiatric clinical notes."
            )
        return True

    def calculate_ciwa_ar(
        self,
        patient_id: str,
        scores: Dict[str, int],  # 10 items: nausea, tremor, sweats, anxiety, agitation, tactile, auditory, visual, headache, orientation
        assessed_by: str
    ) -> CIWAArAssessment:
        """
        Calculates CIWA-Ar alcohol withdrawal score (0 - 67).
        Score >= 15 indicates moderate/severe withdrawal requiring protocolized benzodiazepines.
        """
        total = sum(scores.values())
        if total <= 9:
            severity = "MILD"
        elif total <= 18:
            severity = "MODERATE"
        else:
            severity = "SEVERE"

        benzodiazepine = total >= 15

        rec = CIWAArAssessment(
            assessment_id=f"CIWA-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            patient_id=patient_id,
            total_score=total,
            severity=severity,
            benzodiazepine_protocol_indicated=benzodiazepine,
            assessed_by=assessed_by,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.ciwa_assessments.append(rec)
        return rec

    def calculate_cows(
        self,
        patient_id: str,
        scores: Dict[str, int],  # 11 items: resting pulse, sweating, restlessness, pupil size, bone aches, runny nose, GI upset, tremor, yawn, gooseflesh, anxiety
        assessed_by: str
    ) -> COWSAssessment:
        """
        Clinical Opiate Withdrawal Scale (COWS) score (0 - 48).
        """
        total = sum(scores.values())
        if total <= 12:
            severity = "MILD"
        elif total <= 24:
            severity = "MODERATE"
        elif total <= 36:
            severity = "MODERATELY_SEVERE"
        else:
            severity = "SEVERE"

        rec = COWSAssessment(
            assessment_id=f"COWS-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            patient_id=patient_id,
            total_score=total,
            severity=severity,
            assessed_by=assessed_by,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.cows_assessments.append(rec)
        return rec
