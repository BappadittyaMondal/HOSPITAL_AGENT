#!/usr/bin/env python3
"""
OPD Dynamic Queue, Multilingual Kiosk & Smart Paper QR Verification Test Suite (Phase 03).
Tests queue wait estimation, doctor emergency rebalancing, multilingual kiosk menus,
and tamper-evident Smart Paper QR verification.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from opd_queue_engine import OPDQueueEngine
from kiosk_smart_paper import KIOSK_LOCALIZED_MENUS, SmartPaperBridge

def test_opd_queue_kiosk():
    print("================================================================================")
    print(" [OPD QUEUE & KIOSK TEST SUITE] VERIFYING QUEUE, MULTILINGUAL KIOSK & QR CHIT")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    queue_engine = OPDQueueEngine(tenant_id=TENANT_ID, avg_consult_mins=10)

    # 1. Register Doctors in Cardiology
    queue_engine.register_doctor("DOC-CARD-01", "Dr. Debasis Bose", "CARDIOLOGY", "ROOM-101")
    queue_engine.register_doctor("DOC-CARD-02", "Dr. Sharmila Sen", "CARDIOLOGY", "ROOM-102")

    # 2. Issue tokens to Dr. Bose
    tok1 = queue_engine.issue_token("DOC-CARD-01", "MRN-001", "Animesh Roy", language="BENGALI")
    tok2 = queue_engine.issue_token("DOC-CARD-01", "MRN-002", "Dipankar Ghosh", language="BENGALI")
    tok3 = queue_engine.issue_token("DOC-CARD-01", "MRN-003", "Kalyan Mukherjee", language="BENGALI")

    assert tok1["token_number"] == 1 and tok1["est_wait_mins"] == 0
    assert tok2["token_number"] == 2 and tok2["est_wait_mins"] == 10
    assert "20 মিনিট" in tok3["notification_message"]
    print(" [PASS] Real-time token dispenser and Bengali wait anxiety notifications verified.")

    # 3. Emergency Absence Rebalancing:
    # Dr. Bose is called for emergency angioplasty / Code Blue
    reassigned = queue_engine.rebalance_queue_on_doctor_emergency("DOC-CARD-01")
    assert len(reassigned) == 3
    # Tokens should now be reassigned to Dr. Sharmila Sen
    assert all(t["doctor_id"] == "DOC-CARD-02" for t in reassigned)
    assert "জরুরী অপারেশনের জন্য ডাক পেয়েছেন" in reassigned[0]["notification_message"]
    print(f" [PASS] Doctor emergency queue rebalancing: {len(reassigned)} tokens reassigned to parallel chamber.")

    # 4. Multilingual Kiosk Menu Verification
    for lang in ["BENGALI", "HINDI", "ENGLISH"]:
        assert lang in KIOSK_LOCALIZED_MENUS
        assert len(KIOSK_LOCALIZED_MENUS[lang]["options"]) >= 4
        assert "voice_prompt" in KIOSK_LOCALIZED_MENUS[lang]["options"][0]
    print(" [PASS] Multilingual touch kiosk menus & voice prompts verified (Bengali/Hindi/English).")

    # 5. Smart Paper Bridge: Thermal Paper QR Chit Generation & Cryptographic Verification
    bridge = SmartPaperBridge()
    paper_token = bridge.generate_paper_token_qr_payload(
        tenant_id=TENANT_ID,
        mrn="MRN-RURAL-9912",
        token_number=14,
        department="CARDIOLOGY",
        chamber="ROOM-102"
    )

    qr_str = paper_token["qr_string"]
    assert qr_str.startswith("HOSP-V1:")

    # Scan and verify QR code at nursing workstation
    decoded = bridge.decode_and_verify_paper_qr(qr_str)
    assert decoded is not None
    assert decoded["mrn"] == "MRN-RURAL-9912"
    assert decoded["token_number"] == 14
    assert decoded["verified"] is True
    print(f" [PASS] Smart Paper QR generated and cryptographically verified offline: {decoded['mrn']}.")

    # Verify tamper detection on corrupted QR
    tampered_qr = qr_str[:-4] + "FFFF"
    tampered_decode = bridge.decode_and_verify_paper_qr(tampered_qr)
    assert tampered_decode is None
    print(" [PASS] Cryptographic tamper detection on corrupted paper QR token verified.")

    print("================================================================================")
    print(" OPD DYNAMIC QUEUE, KIOSK & SMART PAPER BRIDGE FULLY OPERATIONAL.")
    return 0

if __name__ == "__main__":
    sys.exit(test_opd_queue_kiosk())
