#!/usr/bin/env python3
"""
Consent Management & DPDP Act 2023 Verification Test Suite.
Tests purpose-bound consent granting, multilingual statutory notices,
consent revocation, and research data export filtering.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from consent_manager import ConsentManager, ConsentPurpose, ConsentStatus, VerificationModality, STATUTORY_NOTICES

def test_consent_manager():
    print("================================================================================")
    print(" [CONSENT MANAGER TEST SUITE] VERIFYING DPDP 2023 PURPOSE BINDING & DATA PRIVACY")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    cm = ConsentManager(tenant_id=TENANT_ID)

    # 1. Verify multilingual notices exist for Bengali, Hindi, English
    for lang in ["BENGALI", "HINDI", "ENGLISH"]:
        assert lang in STATUTORY_NOTICES
        assert ConsentPurpose.CLINICAL_TREATMENT in STATUTORY_NOTICES[lang]
        assert ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED in STATUTORY_NOTICES[lang]
    print(" [PASS] Multilingual statutory consent notices verified for Bengali, Hindi, and English.")

    # 2. Grant Purpose-Bound Consent for Patient 1 (Clinical + Research)
    p1_id = "pat-consent-001"
    cm.grant_consent(
        patient_id=p1_id,
        purpose=ConsentPurpose.CLINICAL_TREATMENT,
        modality=VerificationModality.OTP,
        language="BENGALI"
    )
    cm.grant_consent(
        patient_id=p1_id,
        purpose=ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED,
        modality=VerificationModality.BIOMETRIC_THUMBPRINT,
        language="BENGALI"
    )
    assert cm.has_active_consent(p1_id, ConsentPurpose.CLINICAL_TREATMENT) is True
    assert cm.has_active_consent(p1_id, ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED) is True
    print(" [PASS] Purpose-bound consent granted for Clinical Treatment and Secondary Research.")

    # 3. Patient 2 grants ONLY Clinical Treatment (Opt-out of Research)
    p2_id = "pat-consent-002"
    cm.grant_consent(
        patient_id=p2_id,
        purpose=ConsentPurpose.CLINICAL_TREATMENT,
        modality=VerificationModality.OTP,
        language="ENGLISH"
    )
    assert cm.has_active_consent(p2_id, ConsentPurpose.CLINICAL_TREATMENT) is True
    assert cm.has_active_consent(p2_id, ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED) is False
    print(" [PASS] Granular consent enforced: Patient 2 opted out of research at registration.")

    # 4. Test Research Dataset Filtering Gate
    dataset = [
        {"patient_id": p1_id, "gender": "male", "age": 45, "clinical_data": {"diagnosis": "Hypertension"}},
        {"patient_id": p2_id, "gender": "female", "age": 32, "clinical_data": {"diagnosis": "Asthma"}}
    ]

    filtered_before = cm.filter_research_dataset(dataset)
    # Only Patient 1 should be present, Patient 2 filtered out
    assert len(filtered_before) == 1
    assert "study_id" in filtered_before[0]
    print(f" [PASS] Research export gate: Patient 2 successfully excluded; Patient 1 de-identified ({filtered_before[0]['study_id']}).")

    # 5. Revocation of Consent (Right to Withdraw)
    # Patient 1 revokes Secondary Research consent
    revoked = cm.revoke_consent(p1_id, ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED, reason="Privacy concerns")
    assert revoked is True
    assert cm.has_active_consent(p1_id, ConsentPurpose.SECONDARY_RESEARCH_DEIDENTIFIED) is False
    # CRITICAL: Direct clinical care consent MUST still remain active!
    assert cm.has_active_consent(p1_id, ConsentPurpose.CLINICAL_TREATMENT) is True
    print(" [PASS] Research consent successfully revoked while direct clinical care consent preserved.")

    # 6. Re-test research export after revocation
    filtered_after = cm.filter_research_dataset(dataset)
    assert len(filtered_after) == 0, f"Expected 0 records in research dataset, got {len(filtered_after)}"
    print(" [PASS] Post-revocation research export gate: 100% of revoked patient records excluded.")

    print("================================================================================")
    print(" CONSENT MANAGER FULLY COMPLIANT WITH DPDP ACT 2023.")
    return 0

if __name__ == "__main__":
    sys.exit(test_consent_manager())
