#!/usr/bin/env python3
"""
Mother-Baby Linkage & Pediatric Safeguarding Verification Test Suite (Gaps 2, 27).
Tests mother-baby biological linkage, twin handling, RFID anti-abduction alarms,
statutory Form 1 birth reporting, unaccompanied minor triage, and NAT child abuse screening.
"""
import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from mother_baby_linkage import MotherBabyLinkageEngine
from pediatric_safeguarding import PediatricSafeguardingEngine, SafeguardingAlertLevel

def test_mother_baby_pediatric():
    print("================================================================================")
    print(" [MOTHER-BABY & PEDIATRIC SAFEGUARDING] VERIFYING ANTI-ABDUCTION & CHILD SAFETY")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    mb_engine = MotherBabyLinkageEngine(tenant_id=TENANT_ID)
    peds_engine = PediatricSafeguardingEngine(tenant_id=TENANT_ID)

    # 1. Register Obstetric Mother
    mother_mrn = "MRN-MOM-2026-001"
    mb_engine.register_mother(
        mother_mrn=mother_mrn,
        full_name="Smt. Swagata Bhattacharya",
        rfid_wristband="RFID-MOM-9921"
    )

    # 2. Record Delivery (Twin A and Twin B)
    now = datetime.now(timezone.utc)
    twin_a = mb_engine.record_birth(
        mother_mrn=mother_mrn,
        birth_order=1,
        delivery_timestamp=now,
        gender="female",
        birth_weight_grams=2450,
        gestational_age_weeks=37.2,
        apgar_1min=8,
        apgar_5min=9,
        delivery_type="EMERGENCY_LSCS",
        baby_rfid_tag="RFID-BABY-A-101"
    )
    assert twin_a.neonatal_temp_mrn == "BABY-OF-MRN-MOM-2026-001-1"

    twin_b = mb_engine.record_birth(
        mother_mrn=mother_mrn,
        birth_order=2,
        delivery_timestamp=now,
        gender="male",
        birth_weight_grams=2300,
        gestational_age_weeks=37.2,
        apgar_1min=7,
        apgar_5min=9,
        delivery_type="EMERGENCY_LSCS",
        baby_rfid_tag="RFID-BABY-B-102"
    )
    assert twin_b.neonatal_temp_mrn == "BABY-OF-MRN-MOM-2026-001-B"
    print(f" [PASS] Mother-Baby biological link established for twins: {twin_a.neonatal_temp_mrn}, {twin_b.neonatal_temp_mrn}")

    # 3. Test RFID Anti-Abduction Ward Exit Clearance
    # Case A: Legitimate exit with biological mother
    ok, msg = mb_engine.verify_ward_exit_clearance("RFID-BABY-A-101", "RFID-MOM-9921")
    assert ok is True
    print(f" [PASS] Anti-abduction gate: Legitimate exit authorized ({msg})")

    # Case B: Abduction attempt with wrong/unauthorized RFID tag
    ok, alert_msg = mb_engine.verify_ward_exit_clearance("RFID-BABY-A-101", "RFID-STRANGER-000")
    assert ok is False
    assert "ABDUCTION_RISK" in alert_msg
    print(f" [PASS] Anti-abduction gate: Mismatched tag triggers immediate security alarm ({alert_msg})")

    # 4. Generate Statutory Form 1 Birth Notification
    form_1 = mb_engine.generate_statutory_form_1(twin_a.newborn_id)
    assert form_1["form"] == "FORM_1_LEGAL_BIRTH_NOTIFICATION"
    assert form_1["mother_name"] == "Smt. Swagata Bhattacharya"
    assert form_1["weight_kg"] == 2.45
    print(" [PASS] Statutory Form 1 birth notification generated under Registration of Births and Deaths Act.")

    # 5. Pediatric Safeguards: Unaccompanied Minor
    can_reg, alert_lvl, peds_msg = peds_engine.evaluate_registration_safeguard(
        patient_age_years=9,
        is_accompanied=False
    )
    assert alert_lvl == SafeguardingAlertLevel.CONCERN_SOCIAL_WORK_REVIEW
    assert "UNACCOMPANIED_MINOR" in peds_msg
    assert len(peds_engine.safeguarding_dossiers) >= 1
    print(f" [PASS] Unaccompanied minor safeguard: Medical Social Work dispatched while emergency care proceeds.")

    # 6. Pediatric Safeguards: Non-Accidental Trauma (NAT) Child Abuse Screening
    nat_findings = [
        "MULTIPLE_FRACTURES_DIFFERING_HEALING_STAGES",
        "CIGARETTE_OR_IMMERSION_BURNS"
    ]
    nat_triggered, nat_lvl, nat_report = peds_engine.screen_non_accidental_trauma(
        patient_age_years=4,
        clinical_findings=nat_findings,
        injury_mechanism_stated="Fell off sofa"
    )
    assert nat_triggered is True
    assert nat_lvl == SafeguardingAlertLevel.CRITICAL_MANDATORY_STATUTORY_ALERT
    assert "STATUTORY_NOTIFICATION_CHILDLINE_1098" in nat_report["immediate_actions"]
    print(" [PASS] Non-Accidental Trauma (NAT) screening: Mandatory Childline (1098) statutory report triggered.")

    print("================================================================================")
    print(" MOTHER-BABY LINKAGE & PEDIATRIC SAFEGUARDING ENGINES VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_mother_baby_pediatric())
