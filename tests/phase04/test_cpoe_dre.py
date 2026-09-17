#!/usr/bin/env python3
"""
CPOE & Deterministic Rule Engine (DRE) Verification Test Suite (Phase 04).
Tests sub-millisecond DRE checks, CKD-EPI eGFR calculation,
and cumulative lifetime anthracycline cardiotoxicity limits.
"""
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from cpoe_dre_engine import CPOEDREEngine, calculate_ckd_epi_egfr

def test_cpoe_dre():
    print("================================================================================")
    print(" [CPOE DRE TEST SUITE] VERIFYING SUB-MS DRE, eGFR & LIFETIME TOXICITY")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    dre = CPOEDREEngine(tenant_id=TENANT_ID)

    # 1. Benchmark Sub-Millisecond DRE Evaluation (< 1ms SLA)
    t0 = time.perf_counter()
    res = dre.evaluate_order(
        patient_id="PAT-DRE-001",
        drug_name="Amoxicillin 500mg",
        prescribed_dose=500.0,
        route="ORAL",
        patient_weight_kg=70.0,
        patient_bsa_m2=1.8,
        serum_creatinine=0.9,
        patient_age=50,
        is_female=False,
        current_medications=["Paracetamol"],
        known_allergies=[]
    )
    eval_time_us = (time.perf_counter() - t0) * 1_000_000
    assert res["status"] == "APPROVED"
    print(f" [PASS] DRE evaluation executed in {eval_time_us:.1f} µs ({eval_time_us/1000.0:.4f} ms). Sub-1ms SLA met.")
    assert eval_time_us < 1000.0, "DRE exceeded 1ms SLA threshold!"

    # 2. Test CKD-EPI eGFR calculation & Metformin Renal Contraindication
    # Patient with severe renal impairment (Creatinine 2.8, Age 68 -> eGFR < 30)
    egfr_val = calculate_ckd_epi_egfr(serum_creatinine=2.8, age=68, is_female=True)
    assert egfr_val < 30.0
    print(f" [PASS] CKD-EPI formula computed eGFR: {egfr_val} mL/min/1.73m2.")

    res_metformin = dre.evaluate_order(
        patient_id="PAT-RENAL-002",
        drug_name="Metformin 1000mg",
        prescribed_dose=1000.0,
        route="ORAL",
        patient_weight_kg=65.0,
        patient_bsa_m2=1.65,
        serum_creatinine=2.8,
        patient_age=68,
        is_female=True,
        current_medications=[],
        known_allergies=[]
    )
    assert res_metformin["status"] == "BLOCKED"
    assert any("RENAL CONTRAINDICATION" in s for s in res_metformin["hard_stops"])
    print(" [PASS] Metformin order strictly blocked in severe renal impairment (eGFR < 30).")

    # 3. Test Cumulative Lifetime Toxicity Limit (Doxorubicin Cardiotoxicity)
    # Patient has already received 400 mg/m2 Doxorubicin (Max ceiling is 450 mg/m2)
    pat_cancer = "PAT-ONC-DOX-99"
    dre.record_administered_dose(pat_cancer, "doxorubicin", 400.0)

    # Doctor orders another 100 mg/m2 -> Would bring total to 500 mg/m2 (> 450 max) -> HARD STOP
    res_dox = dre.evaluate_order(
        patient_id=pat_cancer,
        drug_name="Doxorubicin",
        prescribed_dose=100.0, # 100 mg/m2
        route="IV",
        patient_weight_kg=60.0,
        patient_bsa_m2=1.0, # BSA = 1.0 for simple calculation
        serum_creatinine=0.8,
        patient_age=45,
        is_female=True,
        current_medications=[],
        known_allergies=[]
    )
    assert res_dox["status"] == "BLOCKED"
    assert any("CUMULATIVE TOXICITY CEILING EXCEEDED" in s for s in res_dox["hard_stops"])
    print(" [PASS] Anthracycline cumulative cardiotoxicity ceiling strictly enforced (> 450 mg/m2 blocked).")

    print("================================================================================")
    print(" CPOE DETERMINISTIC RULE ENGINE FULLY OPERATIONAL.")
    return 0

if __name__ == "__main__":
    sys.exit(test_cpoe_dre())
