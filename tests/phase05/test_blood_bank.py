#!/usr/bin/env python3
"""
Blood Bank Hemovigilance & Transfusion Safety Verification Test Suite (Gaps 4, 30) (Phase 05).
Tests ABO/Rh crossmatch compatibility, inviolable transfusion mismatch barrier,
and Hemovigilance Programme of India (HvPI) adverse event reporting.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from blood_bank_engine import BloodBankEngine

def test_blood_bank():
    print("================================================================================")
    print(" [BLOOD BANK & HEMOVIGILANCE TEST] VERIFYING TRANSFUSION BARRIER & HvPI LOGGING")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    bb = BloodBankEngine(tenant_id=TENANT_ID)

    # 1. Register Blood Units in Inventory
    # Unit A: O-Negative (Universal PRBC donor)
    bb.register_blood_unit("BAG-O-NEG-001", "O-", "PRBC")
    # Unit B: B-Positive
    bb.register_blood_unit("BAG-B-POS-002", "B+", "PRBC")

    # 2. Test Compatible Crossmatch: O- Unit to A+ Recipient -> APPROVED
    ok_compat, msg_compat = bb.verify_and_crossmatch_unit(
        recipient_mrn="MRN-PAT-A-POS",
        recipient_blood_group="A+",
        unit_barcode="BAG-O-NEG-001",
        transfusion_order_id="ORD-TX-01"
    )
    assert ok_compat is True
    assert "CROSSMATCH_COMPATIBLE_APPROVED" in msg_compat
    print(f" [PASS] Compatible transfusion crossmatch authorized: {msg_compat}")

    # 3. INVIOLABLE TRANSFUSION BARRIER:
    # Attempt to issue B+ Unit to A+ Recipient -> HARD STOP BLOCKED
    ok_mismatch, msg_mismatch = bb.verify_and_crossmatch_unit(
        recipient_mrn="MRN-PAT-A-POS",
        recipient_blood_group="A+",
        unit_barcode="BAG-B-POS-002", # B+ to A+ mismatch!
        transfusion_order_id="ORD-TX-02"
    )
    assert ok_mismatch is False
    assert "FATAL_TRANSFUSION_MISMATCH_BLOCKED" in msg_mismatch
    assert "IMMUNOLOGICALLY INCOMPATIBLE" in msg_mismatch
    print(f" [PASS] Inviolable Transfusion Barrier: Fatal ABO mismatch blocked ({msg_mismatch[:80]}...).")

    # 4. Statutory Hemovigilance Programme of India (HvPI) Adverse Reaction Logging
    reaction_dossier = bb.log_adverse_transfusion_reaction(
        transfusion_order_id="ORD-TX-01",
        reaction_type="FEBRILE_NON_HEMOLYTIC",
        symptoms=["Chills", "Fever 38.9°C", "Mild rigors 15 minutes into transfusion"],
        blood_bank_officer_id="BBO-DR-01"
    )
    assert reaction_dossier["hvpi_id"].startswith("HVPI-ALERT-")
    assert "STOP_TRANSFUSION_IMMEDIATELY" in reaction_dossier["immediate_clinical_action"]
    assert "NATIONAL_BLOOD_TRANSFUSION_COUNCIL" in reaction_dossier["statutory_report_to"]
    print(f" [PASS] HvPI Statutory Transfusion Incident Logged: {reaction_dossier['hvpi_id']} ({reaction_dossier['reaction_type']}).")

    print("================================================================================")
    print(" BLOOD BANK & HEMOVIGILANCE ENGINES FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_blood_bank())
