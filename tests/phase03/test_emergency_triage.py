#!/usr/bin/env python3
"""
Emergency Triage & Financial Decoupling Verification Test Suite (Phase 03).
Tests 5-tier ESI algorithm, instant temporary emergency registration (< 1s),
and hard architectural financial decoupling for emergency care.
"""
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from emergency_triage import EmergencyTriageEngine, ESILevel

def test_emergency_triage():
    print("================================================================================")
    print(" [EMERGENCY TRIAGE TEST SUITE] VERIFYING ESI & FINANCIAL DECOUPLING")
    print("================================================================================")

    triage = EmergencyTriageEngine(tenant_id="11111111-1111-1111-1111-111111111111")

    # 1. Test ESI Level 1 (Cardiac arrest / Pulseless) -> ESI 1
    esi_1 = triage.calculate_esi(
        requires_immediate_lifesaving=True,
        is_high_risk_or_confused_or_severe_pain=False,
        predicted_resources_count=3
    )
    assert esi_1 == ESILevel.LEVEL_1_RESUSCITATION
    print(" [PASS] ESI-1 Resuscitation triage scored accurately.")

    # 2. Test ESI Level 2 (Severe chest pain / danger zone vitals) -> ESI 2
    esi_2 = triage.calculate_esi(
        requires_immediate_lifesaving=False,
        is_high_risk_or_confused_or_severe_pain=True,
        predicted_resources_count=2
    )
    assert esi_2 == ESILevel.LEVEL_2_EMERGENT
    print(" [PASS] ESI-2 Emergent triage scored accurately.")

    # 3. Test ESI Level 3, 4, 5 resource tiers
    esi_3 = triage.calculate_esi(False, False, predicted_resources_count=2, danger_zone_vitals=False)
    esi_4 = triage.calculate_esi(False, False, predicted_resources_count=1)
    esi_5 = triage.calculate_esi(False, False, predicted_resources_count=0)
    assert esi_3 == ESILevel.LEVEL_3_URGENT
    assert esi_4 == ESILevel.LEVEL_4_LESS_URGENT
    assert esi_5 == ESILevel.LEVEL_5_NON_URGENT
    print(" [PASS] ESI-3, ESI-4, and ESI-5 resource tiers scored accurately.")

    # 4. Benchmark Instant Emergency Registration (< 1s requirement)
    t0 = time.perf_counter()
    enc = triage.fast_register_emergency_patient(
        esi_level=ESILevel.LEVEL_1_RESUSCITATION,
        chief_complaint="Unconscious male pulled from road accident; severe head trauma",
        estimated_age=40,
        gender="MALE"
    )
    reg_elapsed_ms = (time.perf_counter() - t0) * 1000
    assert enc["temp_mrn"].startswith("TEMP-EMR-")
    assert enc["assigned_bay"] == "RESUSCITATION_BAY_1"
    print(f" [PASS] Instant Emergency Registration completed in {reg_elapsed_ms:.2f} ms ({enc['temp_mrn']}).")
    assert reg_elapsed_ms < 100.0, f"Registration latency {reg_elapsed_ms}ms exceeded 100ms budget!"

    # 5. Test INVIOLABLE FINANCIAL DECOUPLING:
    # Doctor orders emergency blood and IV resuscitation meds on unbilled/unregistered trauma patient
    order_item = {
        "name": "O-Negative Uncrossed Packed Red Blood Cells (2 Units)",
        "type": "BLOOD_PRODUCT"
    }
    success, msg, executed = triage.execute_clinical_order_with_financial_decoupling(
        encounter_id=enc["encounter_id"],
        order_item=order_item,
        clinician_id="DOC-TRAUMA-DUTY-01"
    )
    assert success is True
    assert executed["billing_decoupled"] is True
    assert executed["clinical_execution_status"] == "EXECUTED_IMMEDIATELY"
    print(f" [PASS] Financial Decoupling Verified: {msg} ({executed['item_name']}).")

    print("================================================================================")
    print(" EMERGENCY TRIAGE & FINANCIAL DECOUPLING FULLY OPERATIONAL.")
    return 0

if __name__ == "__main__":
    sys.exit(test_emergency_triage())
