#!/usr/bin/env python3
"""
Inpatient Nursing & Closed-Loop eMAR Verification Test Suite (Phase 04).
Tests 5 Rights bedside medication administration verification and
NEWS2 clinical early warning score calculation with emergency escalation.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from emar_nursing_engine import ClosedLoopEMAREngine, calculate_news2_score

def test_emar_nursing():
    print("================================================================================")
    print(" [eMAR & NURSING AUTOMATION TEST] VERIFYING 5 RIGHTS & NEWS2 CLINICAL ESCALATION")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    emar = ClosedLoopEMAREngine(tenant_id=TENANT_ID)

    # 1. Test NEWS2 Normal Vitals (RR 16, SpO2 98%, no O2, BP 120, Pulse 72, Alert, Temp 36.8)
    news_normal, risk_normal = calculate_news2_score(
        respiratory_rate=16,
        spo2_percent=98.0,
        on_supplemental_oxygen=False,
        systolic_bp=120,
        pulse_rate=72,
        consciousness_level="ALERT",
        temperature_celsius=36.8
    )
    assert news_normal == 0
    assert risk_normal == "NORMAL"
    print(f" [PASS] Normal vitals NEWS2 score: {news_normal} ({risk_normal}).")

    # 2. Test NEWS2 Critical Deterioration (RR 28, SpO2 88%, on O2, BP 85, Pulse 135, Unresponsive, Temp 39.5)
    news_crit, risk_crit = calculate_news2_score(
        respiratory_rate=28,
        spo2_percent=88.0,
        on_supplemental_oxygen=True,
        systolic_bp=85,
        pulse_rate=135,
        consciousness_level="UNRESPONSIVE",
        temperature_celsius=39.5
    )
    assert news_crit >= 7
    assert risk_crit == "HIGH_RISK_EMERGENCY_ESCALATION"
    print(f" [PASS] Deteriorating patient NEWS2 score: {news_crit} ({risk_crit}) -> Triggers Medical Emergency Team dispatch.")

    # 3. Closed-Loop eMAR: Bedside 5 Rights Verification (Legitimate administration)
    ok_admin, msg_admin = emar.verify_5_rights_bedside_administration(
        order_patient_mrn="MRN-IPD-001",
        scanned_wristband_mrn="MRN-IPD-001",
        order_drug_barcode="BC-CEFTRIAXONE-1G",
        scanned_vial_barcode="BC-CEFTRIAXONE-1G",
        order_dose=1000.0,
        administered_dose=1000.0,
        order_route="IV",
        administered_route="IV",
        nurse_id="NURSE-ICU-09"
    )
    assert ok_admin is True
    print(f" [PASS] Bedside administration approved under 5 Rights protocol: {msg_admin}")

    # 4. Wrong-Patient Safety Block: Mismatched wristband barcode
    ok_wp, msg_wp = emar.verify_5_rights_bedside_administration(
        order_patient_mrn="MRN-IPD-001",
        scanned_wristband_mrn="MRN-IPD-999", # WRONG PATIENT!
        order_drug_barcode="BC-CEFTRIAXONE-1G",
        scanned_vial_barcode="BC-CEFTRIAXONE-1G",
        order_dose=1000.0,
        administered_dose=1000.0,
        order_route="IV",
        administered_route="IV",
        nurse_id="NURSE-ICU-09"
    )
    assert ok_wp is False
    assert "WRONG_PATIENT_SAFETY_BLOCK" in msg_wp
    print(f" [PASS] Inviolable eMAR Safety Gate: Wrong patient wristband intercepted ({msg_wp})")

    # 5. Wrong-Drug Safety Block: Mismatched medication ampoule
    ok_wd, msg_wd = emar.verify_5_rights_bedside_administration(
        order_patient_mrn="MRN-IPD-001",
        scanned_wristband_mrn="MRN-IPD-001",
        order_drug_barcode="BC-CEFTRIAXONE-1G",
        scanned_vial_barcode="BC-POTASSIUM-CHLORIDE-IV", # FATAL WRONG VIAL!
        order_dose=1000.0,
        administered_dose=1000.0,
        order_route="IV",
        administered_route="IV",
        nurse_id="NURSE-ICU-09"
    )
    assert ok_wd is False
    assert "WRONG_DRUG_SAFETY_BLOCK" in msg_wd
    print(f" [PASS] Inviolable eMAR Safety Gate: Wrong medication vial intercepted ({msg_wd})")

    print("================================================================================")
    print(" INPATIENT NURSING AUTOMATION & CLOSED-LOOP eMAR VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_emar_nursing())
