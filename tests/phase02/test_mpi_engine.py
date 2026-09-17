#!/usr/bin/env python3
"""
Master Patient Index (MPI) Verification Test Suite.
Tests Fellegi-Sunter probabilistic linkage, Indian surname phonetic clusters,
ABHA validation, and reversible unmerge audit engine.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from mpi_engine import MasterPatientIndex, indian_phonetic_match, jaro_winkler_similarity

def test_mpi():
    print("================================================================================")
    print(" [MPI ENGINE TEST SUITE] VERIFYING FELLEGI-SUNTER & INDIAN PHONETIC LINKAGE")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    mpi = MasterPatientIndex(tenant_id=TENANT_ID)

    # 1. Phonetic cluster matching tests
    assert indian_phonetic_match("Banerjee", "Bandopadhyay") >= 0.90
    assert indian_phonetic_match("Chatterjee", "Chattopadhyay") >= 0.90
    assert indian_phonetic_match("Mukherjee", "Mukhopadhyay") >= 0.90
    assert indian_phonetic_match("Ganguly", "Gangopadhyay") >= 0.90
    assert indian_phonetic_match("Debnath", "Deb") >= 0.90
    print(" [PASS] Indian surname phonetic clusters recognized with high equivalence.")

    # 2. Register first patient: "Subhash Bandopadhyay"
    p1 = {
        "mrn": "MRN-KOL-1001",
        "first_name": "Subhash",
        "last_name": "Bandopadhyay",
        "dob": "1980-05-12",
        "gender": "male",
        "primary_phone": "9830012345"
    }
    mrn1, status1 = mpi.register_patient(p1)
    assert mrn1 == "MRN-KOL-1001"
    assert status1 == "UNIQUE_PATIENT_REGISTERED"
    print(f" [PASS] Registered base patient: {mrn1} ({p1['first_name']} {p1['last_name']})")

    # 3. Register near-duplicate: "Subhas Banerjee" (same phone, same DOB, phonetic variant)
    p2 = {
        "mrn": "MRN-KOL-1002",
        "first_name": "Subhas",
        "last_name": "Banerjee",
        "dob": "1980-05-12",
        "gender": "male",
        "primary_phone": "+91 98300 12345"
    }
    mrn2, status2 = mpi.register_patient(p2)
    assert "DUPLICATE" in status2
    assert mrn2 == "MRN-KOL-1001" # Automatically matched to original record
    print(f" [PASS] Fellegi-Sunter duplicate detection: {status2}")

    # 4. Register distinctly different patient
    p3 = {
        "mrn": "MRN-KOL-1003",
        "first_name": "Aparna",
        "last_name": "Sen",
        "dob": "1992-11-20",
        "gender": "female",
        "primary_phone": "9831198311"
    }
    mrn3, status3 = mpi.register_patient(p3)
    assert mrn3 == "MRN-KOL-1003"
    assert status3 == "UNIQUE_PATIENT_REGISTERED"
    print(f" [PASS] Distinct patient recognized without false merge: {mrn3}")

    # 5. Test Merge and Reversible Unmerge
    # Register candidate for manual merge
    p4 = {
        "mrn": "MRN-KOL-1004",
        "first_name": "Aparna",
        "last_name": "Sengupta", # Variant of Sen
        "dob": "1992-11-20",
        "gender": "female",
        "primary_phone": "9832298322"
    }
    mpi.register_patient(p4)

    # Perform Merge
    merged = mpi.merge_patient_records(
        primary_mrn="MRN-KOL-1003",
        secondary_mrn="MRN-KOL-1004",
        authorized_by="MRD_SUPERVISOR_01",
        reason="Verified identity document confirms same individual"
    )
    assert merged is True
    assert mpi._patients["MRN-KOL-1004"]["status"] == "MERGED"
    print(" [PASS] Manual record merge executed with audit logging.")

    # Perform Unmerge (Rollback)
    unmerged = mpi.unmerge_patient_records(
        secondary_mrn="MRN-KOL-1004",
        authorized_by="MRD_SUPERVISOR_01",
        reason="Erroneous merge discovered by clinician; unlinking charts"
    )
    assert unmerged is True
    assert mpi._patients["MRN-KOL-1004"]["status"] == "ACTIVE"
    assert mpi._patients["MRN-KOL-1004"]["merged_into"] is None
    print(" [PASS] Deterministic unmerge rollback verified: secondary chart restored to ACTIVE.")

    # 6. Test ABHA Linkage
    abha_linked = mpi.validate_and_link_abha("MRN-KOL-1001", "12-3456-7890-1234", "subhash@abdm")
    assert abha_linked is True
    assert mpi._patients["MRN-KOL-1001"]["abha_id"] == "12-3456-7890-1234"
    print(" [PASS] ABDM 14-digit ABHA validation and linkage verified.")

    print("================================================================================")
    print(" MASTER PATIENT INDEX (MPI) LINKAGE ENGINE FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_mpi())
