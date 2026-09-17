#!/usr/bin/env python3
"""
Medical Oncology & Chemotherapy Verification Test Suite (Gap 3) (Phase 04).
Tests Mosteller BSA calculation, pre-chemo hematologic safety gates (ANC < 1000, Platelets < 50,000),
and mandatory independent dual-nurse sign-off workflow.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from chemotherapy_engine import ChemotherapySafetyEngine, calculate_bsa_mosteller

def test_chemotherapy():
    print("================================================================================")
    print(" [CHEMOTHERAPY SUBSYSTEM TEST] VERIFYING BSA, LAB GATES & DUAL-NURSE SIGNOFF")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    chemo = ChemotherapySafetyEngine(tenant_id=TENANT_ID)

    # 1. Test BSA Calculation (Height 165 cm, Weight 65 kg -> sqrt(165*65/3600) = ~1.73 m2)
    bsa = calculate_bsa_mosteller(height_cm=165.0, weight_kg=65.0)
    assert bsa == 1.73
    print(f" [PASS] Mosteller Body Surface Area (BSA) computed accurately: {bsa} m2.")

    # 2. Test Pre-Chemotherapy Lab Safety Gates
    # Scenario A: Patient with severe neutropenia (ANC 650/µL < 1000) -> BLOCKED
    safe_anc, blocks_anc = chemo.evaluate_pre_chemo_lab_thresholds(
        anc_per_ul=650.0,
        platelets_per_ul=180000.0,
        hemoglobin_g_dl=11.2,
        serum_creatinine_mg_dl=0.9
    )
    assert safe_anc is False
    assert any("Severe Neutropenia" in b for b in blocks_anc)
    print(f" [PASS] Pre-chemo safety gate: Infusion blocked for low ANC ({blocks_anc[0]}).")

    # Scenario B: Patient with severe thrombocytopenia (Platelets 35,000/µL < 50,000) -> BLOCKED
    safe_plt, blocks_plt = chemo.evaluate_pre_chemo_lab_thresholds(
        anc_per_ul=2500.0,
        platelets_per_ul=35000.0,
        hemoglobin_g_dl=10.5,
        serum_creatinine_mg_dl=1.0
    )
    assert safe_plt is False
    assert any("Severe Thrombocytopenia" in b for b in blocks_plt)
    print(f" [PASS] Pre-chemo safety gate: Infusion blocked for low Platelets ({blocks_plt[0]}).")

    # 3. Create Chemotherapy Order (FOLFOX - Oxaliplatin 85 mg/m2 * 1.73 m2 = 147.1 mg)
    order = chemo.create_chemotherapy_order(
        patient_id="PAT-ONC-001",
        regimen_name="mFOLFOX6",
        drug_name="Oxaliplatin IV",
        dose_per_m2=85.0,
        height_cm=165.0,
        weight_kg=65.0,
        prescribing_oncologist_id="DOC-ONC-01"
    )
    assert order["calculated_total_dose"] == 147.1
    order_id = order["order_id"]

    # Bedside infusion initially blocked
    assert chemo.can_infuse(order_id) is False
    print(" [PASS] Unverified chemotherapy order strictly locked prior to dual-nurse sign-off.")

    # 4. Nurse 1 Sign-Off (Preparation Nurse)
    ok_n1, msg_n1 = chemo.signoff_nurse_verification(
        order_id=order_id,
        nurse_id="NURSE-ONC-01",
        nurse_role_position=1,
        verified_independent_dose=147.1
    )
    assert ok_n1 is True
    assert chemo.can_infuse(order_id) is False # Still blocked awaiting Nurse 2!
    print(f" [PASS] Nurse 1 sign-off recorded: {msg_n1}")

    # 5. Independent Check Violation: Same nurse attempts Nurse 2 sign-off -> BLOCKED
    ok_same, msg_same = chemo.signoff_nurse_verification(
        order_id=order_id,
        nurse_id="NURSE-ONC-01", # SAME NURSE!
        nurse_role_position=2,
        verified_independent_dose=147.1
    )
    assert ok_same is False
    assert "INDEPENDENT_CHECK_VIOLATION" in msg_same
    print(" [PASS] Dual-nurse safety violation intercepted: Nurse 2 cannot be the same individual as Nurse 1.")

    # 6. Independent Nurse 2 Sign-Off
    ok_n2, msg_n2 = chemo.signoff_nurse_verification(
        order_id=order_id,
        nurse_id="NURSE-ONC-02", # INDEPENDENT NURSE
        nurse_role_position=2,
        verified_independent_dose=147.1
    )
    assert ok_n2 is True
    assert chemo.can_infuse(order_id) is True # Now unlocked!
    print(f" [PASS] Independent Nurse 2 sign-off verified: Chemotherapy unlocked for infusion ({msg_n2}).")

    print("================================================================================")
    print(" MEDICAL ONCOLOGY & CHEMOTHERAPY SAFETY SUBSYSTEM VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_chemotherapy())
