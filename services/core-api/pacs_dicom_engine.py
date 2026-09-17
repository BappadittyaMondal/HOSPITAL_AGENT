#!/usr/bin/env python3
"""
PACS / DICOM Server & AI Radiology Triage Engine (Phase 05).
Enforces:
1. DICOM metadata ingestion and study registration.
2. Radiation dose tracking (DLP, CTDIvol) against Diagnostic Reference Levels (DRLs).
3. AI Radiology Triage Prioritization: Immediately bumps acute intracranial hemorrhage (ICH)
   and tension pneumothorax studies to the top of the radiologist queue (STAT 10-min SLA).
"""
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

# Standard Diagnostic Reference Levels (DRL) for Adult CT Exams (AERB / ICRP)
DRL_RADIATION_LIMITS = {
    "CT_HEAD": {"max_dlp_mgy_cm": 1050.0, "max_ctdivol_mgy": 60.0},
    "CT_CHEST": {"max_dlp_mgy_cm": 450.0, "max_ctdivol_mgy": 15.0},
    "CT_ABDOMEN_PELVIS": {"max_dlp_mgy_cm": 750.0, "max_ctdivol_mgy": 18.0}
}

class PACSStudyPriority:
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT_CRITICAL_AI_BUMPED = "STAT_CRITICAL_AI_BUMPED"

class PACSDICOMEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._studies: Dict[str, Dict] = {}

    def ingest_dicom_study(
        self,
        study_instance_uid: str,
        patient_mrn: str,
        modality: str,
        study_description: str,
        dlp_mgy_cm: Optional[float] = None,
        ctdivol_mgy: Optional[float] = None,
        ai_inference_findings: Optional[List[str]] = None
    ) -> Dict:
        """
        Ingests DICOM metadata, tracks radiation dose, and runs AI triage prioritization.
        """
        now = datetime.now(timezone.utc).isoformat()
        priority = PACSStudyPriority.ROUTINE
        ai_flags = ai_inference_findings or []

        # 1. Critical AI Triage Scan
        # If AI detects Acute Intracranial Hemorrhage or Tension Pneumothorax -> BUMP TO STAT
        critical_ai_conditions = {
            "ACUTE_INTRACRANIAL_HEMORRHAGE",
            "TENSION_PNEUMOTHORAX",
            "AORTIC_DISSECTION",
            "LARGE_VESSEL_OCCLUSION"
        }
        detected_critical = [c for c in ai_flags if c in critical_ai_conditions]
        if detected_critical:
            priority = PACSStudyPriority.STAT_CRITICAL_AI_BUMPED

        # 2. Radiation Dose DRL Evaluation
        radiation_alert = None
        study_key = study_description.upper().replace(" ", "_")
        for drl_key, limits in DRL_RADIATION_LIMITS.items():
            if drl_key in study_key and dlp_mgy_cm:
                if dlp_mgy_cm > limits["max_dlp_mgy_cm"]:
                    radiation_alert = (
                        f"AERB DRL EXCEEDED: DLP {dlp_mgy_cm} mGy*cm exceeds reference ceiling {limits['max_dlp_mgy_cm']} mGy*cm. "
                        "Medical Physicist dose optimization review required."
                    )

        study = {
            "study_instance_uid": study_instance_uid,
            "patient_mrn": patient_mrn,
            "modality": modality,
            "study_description": study_description,
            "priority": priority,
            "sla_minutes": 10 if priority == PACSStudyPriority.STAT_CRITICAL_AI_BUMPED else 120,
            "dlp_mgy_cm": dlp_mgy_cm,
            "ctdivol_mgy": ctdivol_mgy,
            "radiation_dose_alert": radiation_alert,
            "ai_inference_findings": ai_flags,
            "detected_critical_findings": detected_critical,
            "ingested_at": now
        }

        self._studies[study_instance_uid] = study
        return study

    def get_radiology_worklist(self) -> List[Dict]:
        """Returns radiologist reading queue sorted strictly by priority (STAT first)."""
        sorted_studies = list(self._studies.values())
        priority_order = {
            PACSStudyPriority.STAT_CRITICAL_AI_BUMPED: 0,
            PACSStudyPriority.URGENT: 1,
            PACSStudyPriority.ROUTINE: 2
        }
        sorted_studies.sort(key=lambda s: (priority_order.get(s["priority"], 99), s["ingested_at"]))
        return sorted_studies
