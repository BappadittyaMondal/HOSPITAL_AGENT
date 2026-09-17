#!/usr/bin/env python3
"""
Staff Credentialing & Privileging Verification Test Suite (Gaps 6, 28).
Tests mandatory onboarding login gate, procedure privileging matrix,
and automated 90/60/30/7-day credential expiry alerts.
"""
import sys
import os
from datetime import date, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from staff_credentialing import CredentialingRegistry, StaffProfile, CredentialStatus

def test_staff_credentialing():
    print("================================================================================")
    print(" [STAFF CREDENTIALING TEST SUITE] VERIFYING PRIVILEGING & EXPIRY ALERTING")
    print("================================================================================")

    registry = CredentialingRegistry()
    today = date(2026, 9, 17)

    # 1. New Doctor with Incomplete Onboarding
    doc_new = StaffProfile(
        staff_id="DOC-NEW-001",
        full_name="Tanmoy Mukherjee",
        role="RESIDENT_PHYSICIAN",
        department="GENERAL_SURGERY",
        council_registration_number="WBMC-78901",
        council_name="West Bengal Medical Council",
        registration_expiry=today + timedelta(days=365),
        mandatory_trainings={
            "FIRE_SAFETY": True,
            "BIOMEDICAL_WASTE_RULES_2016": False, # INCOMPLETE
            "INFECTION_PREVENTION": False,        # INCOMPLETE
            "BLS_CERTIFICATION": True
        }
    )
    registry.register_staff(doc_new)

    can_login, login_msg = registry.can_login("DOC-NEW-001")
    assert can_login is False
    assert "BIOMEDICAL_WASTE_RULES_2016" in login_msg
    print(f" [PASS] Onboarding Gate: Login locked for incomplete safety training ({login_msg}).")

    # Complete training
    doc_new.mandatory_trainings["BIOMEDICAL_WASTE_RULES_2016"] = True
    doc_new.mandatory_trainings["INFECTION_PREVENTION"] = True
    can_login, login_msg = registry.can_login("DOC-NEW-001")
    assert can_login is True
    print(" [PASS] Onboarding Gate: Login unlocked after all mandatory training verified.")

    # 2. Senior Surgeon with Laparoscopic Privileges (but NOT Cardiac Surgery)
    surgeon = StaffProfile(
        staff_id="SURG-001",
        full_name="Dr. Arundhati Roy Chowdhury",
        role="CONSULTANT_PHYSICIAN",
        department="SURGICAL_GASTROENTEROLOGY",
        council_registration_number="WBMC-45123",
        council_name="West Bengal Medical Council",
        registration_expiry=today + timedelta(days=200),
        privileged_procedures={"SURG:LAP_CHOLECYSTECTOMY", "SURG:APPENDECTOMY", "SURG:HERNIA_REPAIR"}
    )
    # Mark trainings complete
    surgeon.mandatory_trainings = {k: True for k in surgeon.mandatory_trainings}
    registry.register_staff(surgeon)

    # Test authorized procedure: Lap Cholecystectomy
    auth_ok, auth_msg = registry.authorize_procedure("SURG-001", "SURG:LAP_CHOLECYSTECTOMY")
    assert auth_ok is True
    print(f" [PASS] Privileged procedure authorized: {auth_msg}")

    # Test unauthorized procedure: CABG (Cardiac surgery)
    auth_fail, fail_msg = registry.authorize_procedure("SURG-001", "SURG:CARDIAC_CABG")
    assert auth_fail is False
    assert "NOT privileged" in fail_msg
    print(f" [PASS] Uncredentialed procedure blocked by safety matrix: {fail_msg}")

    # 3. Doctor with Credential Expiring in 25 Days (30-day alert tier)
    doc_expiring = StaffProfile(
        staff_id="DOC-EXP-001",
        full_name="Dr. Bikramjit Das",
        role="CONSULTANT_PHYSICIAN",
        department="INTERNAL_MEDICINE",
        council_registration_number="WBMC-22334",
        council_name="West Bengal Medical Council",
        registration_expiry=today + timedelta(days=25)
    )
    doc_expiring.mandatory_trainings = {k: True for k in doc_expiring.mandatory_trainings}
    registry.register_staff(doc_expiring)

    alerts = registry.get_expiry_alerts(current_date=today)
    assert len(alerts) >= 1
    exp_alert = next(a for a in alerts if a["staff_id"] == "DOC-EXP-001")
    assert exp_alert["alert_tier"] == CredentialStatus.EXPIRING_30_DAYS
    assert exp_alert["days_remaining"] == 25
    print(f" [PASS] 30-Day credential expiry alert generated ({exp_alert['days_remaining']} days remaining).")

    # 4. Doctor with Expired Credential (-5 days)
    doc_expired = StaffProfile(
        staff_id="DOC-EXPIRED-001",
        full_name="Dr. Somnath Sen",
        role="CONSULTANT_PHYSICIAN",
        department="ORTHOPEDICS",
        council_registration_number="WBMC-11002",
        council_name="West Bengal Medical Council",
        registration_expiry=today - timedelta(days=5),
        privileged_procedures={"ORTHO:TOTAL_KNEE_REPLACEMENT"}
    )
    doc_expired.mandatory_trainings = {k: True for k in doc_expired.mandatory_trainings}
    registry.register_staff(doc_expired)

    # Test Login with expired credential -> BLOCKED
    login_ok, exp_login_msg = registry.can_login("DOC-EXPIRED-001")
    assert login_ok is False
    assert "EXPIRED" in exp_login_msg
    print(f" [PASS] Expired credential blocks clinician login: {exp_login_msg}")

    # Test Procedure with expired credential -> BLOCKED
    proc_ok, exp_proc_msg = registry.authorize_procedure("DOC-EXPIRED-001", "ORTHO:TOTAL_KNEE_REPLACEMENT")
    assert proc_ok is False
    assert "expired" in exp_proc_msg.lower()
    print(f" [PASS] Expired credential blocks procedure performance: {exp_proc_msg}")

    print("================================================================================")
    print(" STAFF CREDENTIALING & PRIVILEGING MATRIX FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_staff_credentialing())
