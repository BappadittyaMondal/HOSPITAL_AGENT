#!/usr/bin/env python3
"""
Antimicrobial Stewardship (ASP) & HAI Surveillance Verification Test Suite (Gaps 17, 18) (Phase 04).
Tests WHO AWaRe antibiotic tiering, Reserve antibiotic specialist approval,
48-hour antimicrobial timeout alerts, and algorithmic HAI CAUTI surveillance.
"""
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from antimicrobial_hai_engine import AntimicrobialHAIEngine, WHOAWaReTier

def test_antimicrobial_hai():
    print("================================================================================")
    print(" [ANTIMICROBIAL STEWARDSHIP & HAI TEST] VERIFYING AWaRe, TIMEOUT & CAUTI")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    asp = AntimicrobialHAIEngine(tenant_id=TENANT_ID)
    now = datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)

    # 1. Test WHO AWaRe Tier Classification
    # Access: Amoxicillin
    rx_access = asp.prescribe_antibiotic("PAT-ASP-01", "Amoxicillin", "DOC-01", "Community Pneumonia", now)
    assert rx_access["aware_tier"] == WHOAWaReTier.ACCESS
    assert rx_access["status"] == "ACTIVE_APPROVED"
    print(" [PASS] WHO Access antibiotic authorized immediately.")

    # Reserve: Colistin (Last resort polymyxin) -> PENDING_ID_APPROVAL
    rx_reserve = asp.prescribe_antibiotic("PAT-ASP-02", "Colistin", "DOC-01", "MDR Klebsiella Sepsis", now)
    assert rx_reserve["aware_tier"] == WHOAWaReTier.RESERVE
    assert rx_reserve["status"] == "PENDING_ID_APPROVAL"
    print(" [PASS] WHO Reserve antibiotic (Colistin) locked pending Infectious Disease consultant sign-off.")

    # 2. Infectious Disease Specialist Approval
    approved = asp.approve_reserve_antibiotic(rx_reserve["rx_id"], id_consultant_id="DOC-ID-SPEC-01")
    assert approved is True
    assert asp._antibiotic_prescriptions[rx_reserve["rx_id"]]["status"] == "ACTIVE_APPROVED"
    print(" [PASS] Infectious Disease consultant signed off on Reserve antibiotic.")

    # 3. Test 48-Hour Antimicrobial Timeout
    # At 24 hours: Still within safe initial empirical window
    t_24h = now + timedelta(hours=24)
    timeout_24, _ = asp.check_48hr_antimicrobial_timeout(rx_access["rx_id"], t_24h)
    assert timeout_24 is False

    # At 50 hours: Mandatory 48-72h de-escalation timeout triggered!
    t_50h = now + timedelta(hours=50)
    timeout_50, msg_timeout = asp.check_48hr_antimicrobial_timeout(rx_access["rx_id"], t_50h)
    assert timeout_50 is True
    assert "ASP 48-HOUR TIMEOUT ALERT" in msg_timeout
    print(f" [PASS] 48-Hour ASP Timeout verified: {msg_timeout[:70]}...")

    # 4. Test HAI CAUTI Surveillance Algorithm
    # Patient with Foley catheter 5 days, Fever 38.8°C, Urine culture 150,000 CFU/mL E. coli
    flagged, hai_dossier = asp.screen_hai_cauti(
        patient_id="PAT-ICU-088",
        catheter_duration_days=5,
        fever_temp_celsius=38.8,
        urine_culture_cfu_ml=150000
    )
    assert flagged is True
    assert hai_dossier["infection_type"] == "CAUTI"
    assert "Immediate catheter removal prompt" in hai_dossier["action"]
    print(" [PASS] Algorithmic HAI Surveillance: CAUTI detected and infection control alert dispatched.")

    print("================================================================================")
    print(" ANTIMICROBIAL STEWARDSHIP & HAI SURVEILLANCE ENGINES VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_antimicrobial_hai())
