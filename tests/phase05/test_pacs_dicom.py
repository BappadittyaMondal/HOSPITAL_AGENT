#!/usr/bin/env python3
"""
PACS / DICOM Server & AI Radiology Triage Verification Test Suite (Phase 05).
Tests DICOM ingestion, radiation dose tracking against AERB DRLs,
and AI critical finding triage prioritization (ICH bumped to STAT 10-min SLA).
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from pacs_dicom_engine import PACSDICOMEngine, PACSStudyPriority

def test_pacs_dicom():
    print("================================================================================")
    print(" [PACS & AI RADIOLOGY TRIAGE TEST] VERIFYING DOSE TRACKING & CRITICAL TRIAGE")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    pacs = PACSDICOMEngine(tenant_id=TENANT_ID)

    # 1. Ingest Routine Study (Chest X-Ray)
    study_routine = pacs.ingest_dicom_study(
        study_instance_uid="1.2.840.10008.1.101",
        patient_mrn="MRN-OPD-001",
        modality="CR",
        study_description="CHEST X-RAY PA VIEW"
    )
    assert study_routine["priority"] == PACSStudyPriority.ROUTINE
    assert study_routine["sla_minutes"] == 120
    print(" [PASS] Routine imaging study registered with 120-minute SLA.")

    # 2. Ingest CT with Radiation Dose Exceeding AERB DRL Ceiling (DLP 1250 mGy*cm > 1050 limit)
    study_high_dose = pacs.ingest_dicom_study(
        study_instance_uid="1.2.840.10008.1.102",
        patient_mrn="MRN-OPD-002",
        modality="CT",
        study_description="CT HEAD WITHOUT CONTRAST",
        dlp_mgy_cm=1250.0,
        ctdivol_mgy=68.0
    )
    assert study_high_dose["radiation_dose_alert"] is not None
    assert "AERB DRL EXCEEDED" in study_high_dose["radiation_dose_alert"]
    print(f" [PASS] Radiation safety gate: AERB DRL dose excess caught ({study_high_dose['radiation_dose_alert'][:60]}...).")

    # 3. Critical AI Triage: Head CT with Acute Intracranial Hemorrhage (ICH)
    study_critical_ich = pacs.ingest_dicom_study(
        study_instance_uid="1.2.840.10008.1.103",
        patient_mrn="MRN-EMR-TRAUMA-99",
        modality="CT",
        study_description="CT HEAD EMERGENCY",
        dlp_mgy_cm=980.0,
        ctdivol_mgy=52.0,
        ai_inference_findings=["ACUTE_INTRACRANIAL_HEMORRHAGE", "MIDLINE_SHIFT_5MM"]
    )
    assert study_critical_ich["priority"] == PACSStudyPriority.STAT_CRITICAL_AI_BUMPED
    assert study_critical_ich["sla_minutes"] == 10
    print(" [PASS] AI Radiology Triage: Acute Intracranial Hemorrhage bumped to STAT with 10-minute SLA.")

    # 4. Verify Radiologist Reading Worklist Ordering
    worklist = pacs.get_radiology_worklist()
    # The critical ICH study MUST be at the very top of the radiologist queue!
    assert worklist[0]["study_instance_uid"] == "1.2.840.10008.1.103"
    assert worklist[0]["priority"] == PACSStudyPriority.STAT_CRITICAL_AI_BUMPED
    print(" [PASS] Worklist queue prioritization verified: Critical trauma scan occupies Position #1.")

    print("================================================================================")
    print(" PACS DICOM ENGINE & AI RADIOLOGY TRIAGE FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_pacs_dicom())
