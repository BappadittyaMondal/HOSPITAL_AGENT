#!/usr/bin/env python3
"""
LIS, Westgard QC & Delta-Check Verification Test Suite (Phase 05).
Tests bedside phlebotomy PPID, Westgard multi-rule violations halting batch auto-verification,
and Delta-Check anomaly specimen holds.
"""
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from lis_qc_engine import LISQualityControlEngine, WestgardStatus

def test_lis_qc():
    print("================================================================================")
    print(" [LIS & WESTGARD QC TEST SUITE] VERIFYING PPID, QC RULES & DELTA-CHECKS")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    lis = LISQualityControlEngine(tenant_id=TENANT_ID)

    # 1. Bedside Phlebotomy PPID Verification
    # Legitimate collection
    ok_ppid, msg_ppid = lis.verify_bedside_phlebotomy_ppid(
        order_patient_mrn="MRN-LAB-001",
        scanned_wristband_mrn="MRN-LAB-001",
        order_tube_barcode="TUBE-CBC-8812",
        scanned_tube_barcode="TUBE-CBC-8812",
        phlebotomist_id="PHLEB-01"
    )
    assert ok_ppid is True
    print(" [PASS] Bedside phlebotomy positive patient identification (PPID) verified.")

    # Wrong tube scanned
    fail_ppid, msg_fail = lis.verify_bedside_phlebotomy_ppid(
        order_patient_mrn="MRN-LAB-001",
        scanned_wristband_mrn="MRN-LAB-001",
        order_tube_barcode="TUBE-CBC-8812",
        scanned_tube_barcode="TUBE-WRONG-9999", # WRONG TUBE!
        phlebotomist_id="PHLEB-01"
    )
    assert fail_ppid is False
    assert "PPID_VIOLATION_WRONG_TUBE" in msg_fail
    print(f" [PASS] Phlebotomy safety gate: Wrong tube barcode rejected ({msg_fail})")

    # 2. Westgard Statistical Quality Control (Glucose Control Target: Mean 100 mg/dL, SD 4.0 mg/dL)
    lis.configure_qc_target(analyte="GLUCOSE", mean=100.0, sd=4.0)

    # Run A: Normal QC value (102 mg/dL -> z = +0.5) -> PASS
    rule_a, halted_a, msg_a = lis.evaluate_westgard_qc("ANALYZER-BIO-01", "GLUCOSE", 102.0)
    assert rule_a == WestgardStatus.PASSED
    assert halted_a is False
    print(f" [PASS] Westgard in-control measurement passed: {msg_a}")

    # Run B: Extreme Outlier (115 mg/dL -> z = +3.75 > 3.0 SD) -> REJECT 1-3s & HALT BATCH
    rule_b, halted_b, msg_b = lis.evaluate_westgard_qc("ANALYZER-BIO-01", "GLUCOSE", 115.0)
    assert rule_b == WestgardStatus.REJECT_1_3S
    assert halted_b is True
    assert lis._analyzer_status["ANALYZER-BIO-01"] == "HALTED_QC_VIOLATION"
    print(f" [PASS] Westgard 1-3s multi-rule rejection verified: Batch auto-verification HALTED ({msg_b}).")

    # 3. Delta-Check Anomaly Detection
    # Baseline: Patient Hemoglobin is 13.5 g/dL at 08:00
    t_base = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
    ok_base, _ = lis.evaluate_delta_check("MRN-IPD-DELTA-01", "HEMOGLOBIN", 13.5, t_base)
    assert ok_base is True

    # Sudden Drop: Next day at 08:00 (24h later), Hemoglobin is 9.0 g/dL (Drop of 4.5 g/dL > 3.0 g/dL limit)
    t_next = t_base + timedelta(hours=24)
    ok_delta, msg_delta = lis.evaluate_delta_check("MRN-IPD-DELTA-01", "HEMOGLOBIN", 9.0, t_next)
    assert ok_delta is False
    assert "DELTA_CHECK_VIOLATION_HOLD" in msg_delta
    print(f" [PASS] Delta-Check anomaly caught: Specimen held for redraw verification ({msg_delta[:80]}...).")

    print("================================================================================")
    print(" LIS, WESTGARD QC & DELTA-CHECK ENGINES FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_lis_qc())
