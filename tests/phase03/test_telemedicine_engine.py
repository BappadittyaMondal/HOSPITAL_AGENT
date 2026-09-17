#!/usr/bin/env python3
"""
Telemedicine Consultation & NMC 2020 Verification Test Suite (Phase 03).
Tests WebRTC bandwidth tiering (HD -> 3G -> 2G audio fallback),
patient OTP verification, and NMC Telemedicine 2020 prescription gates.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from telemedicine_engine import TelemedicineEngine, TelemedSessionTier, TelemedConsultType

def test_telemedicine():
    print("================================================================================")
    print(" [TELEMEDICINE TEST SUITE] VERIFYING BANDWIDTH ADAPTATION & NMC 2020 GATES")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    tele = TelemedicineEngine(tenant_id=TENANT_ID)

    # 1. Start Teleconsultation Session
    session = tele.start_teleconsult_session(
        appointment_id="APP-TELE-001",
        patient_mrn="MRN-PAT-TELE-991",
        doctor_id="DOC-TELE-01",
        consult_type=TelemedConsultType.FIRST_CONSULTATION
    )
    sess_id = session["session_id"]
    assert session["status"] == "WAITING_ROOM"
    print(" [PASS] Telemedicine session created in virtual waiting room.")

    # 2. Test Bandwidth Adaptation
    # 4G / High Bandwidth (1500 kbps)
    tier_4g = tele.adapt_stream_to_bandwidth(sess_id, 1500)
    assert tier_4g == TelemedSessionTier.FULL_HD_VIDEO
    # 3G Network (400 kbps)
    tier_3g = tele.adapt_stream_to_bandwidth(sess_id, 400)
    assert tier_3g == TelemedSessionTier.LOW_FPS_VIDEO
    # 2G Degraded Rural Network (80 kbps) -> Falls back to Audio-Only
    tier_2g = tele.adapt_stream_to_bandwidth(sess_id, 80)
    assert tier_2g == TelemedSessionTier.AUDIO_ONLY_FALLBACK
    print(" [PASS] Dynamic bandwidth adaptation verified: 4G (HD) -> 3G (Low-FPS) -> 2G (Audio-Only).")

    # 3. Pre-session Patient Identity Verification
    # Attempt prescription before identity verification -> BLOCKED
    ok_unverified, msg_unverified = tele.validate_nmc_tele_prescription(sess_id, "Paracetamol 650mg")
    assert ok_unverified is False
    assert "NMC_VIOLATION" in msg_unverified
    print(" [PASS] NMC Identity Gate: Prescription blocked before patient verification.")

    # Verify patient with valid 6-digit OTP
    verified = tele.verify_patient_identity(sess_id, otp_code="784921", photo_hash="PHOTO_HASH_SHA256_A91F")
    assert verified is True
    print(" [PASS] Patient identity verified with statutory OTP & photo hash.")

    # 4. NMC 2020 Prescription Verification:
    # A: Allowed oral medication (List O / List A)
    ok_oral, msg_oral = tele.validate_nmc_tele_prescription(sess_id, "Paracetamol 650mg", route="ORAL")
    assert ok_oral is True
    assert "NMC_APPROVED" in msg_oral
    print(f" [PASS] Permitted oral medication authorized: {msg_oral}")

    # B: Schedule X Narcotic (Morphine) -> BLOCKED
    ok_morphine, msg_morphine = tele.validate_nmc_tele_prescription(sess_id, "Morphine Sulfate 10mg", route="ORAL")
    assert ok_morphine is False
    assert "Schedule X" in msg_morphine
    print(f" [PASS] NMC Prohibition: Schedule X narcotic strictly blocked ({msg_morphine})")

    # C: Injectable Medication on First Remote Consultation -> BLOCKED
    ok_inj, msg_inj = tele.validate_nmc_tele_prescription(sess_id, "Ceftriaxone 1g", route="IV")
    assert ok_inj is False
    assert "Injectable medication" in msg_inj
    print(f" [PASS] NMC Prohibition: Injectable medication on first consult blocked ({msg_inj})")

    print("================================================================================")
    print(" TELEMEDICINE SUBSYSTEM & NMC 2020 GOVERNANCE FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_telemedicine())
