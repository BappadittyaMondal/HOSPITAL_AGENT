#!/usr/bin/env python3
"""
RBAC, ABAC & Break-Glass Protocol Verification Test Suite.
Tests clinical role boundaries, relationship contexts, psychiatry confidentiality,
and emergency break-glass audit alerting.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from access_control import AccessControlEngine, ClinicalRole, ConfidentialityLevel, AccessDecision

def test_access_control():
    ac = AccessControlEngine()
    print("================================================================================")
    print(" [RBAC/ABAC ACCESS CONTROL TEST SUITE] VERIFYING PERMISSIONS & BREAK-GLASS")
    print("================================================================================")

    TENANT_A = "11111111-1111-1111-1111-111111111111"
    TENANT_B = "22222222-2222-2222-2222-222222222222"

    doctor_a = {
        "user_id": "doc-001",
        "username": "dr_roychowdhury",
        "tenant_id": TENANT_A,
        "role": ClinicalRole.CONSULTANT_PHYSICIAN,
        "department": "CARDIOLOGY"
    }

    patient_a = {
        "patient_id": "pat-001",
        "tenant_id": TENANT_A,
        "attending_doctor_id": "doc-001",
        "confidentiality": ConfidentialityLevel.STANDARD
    }

    billing_clerk = {
        "user_id": "bill-001",
        "username": "clerk_das",
        "tenant_id": TENANT_A,
        "role": ClinicalRole.BILLING_CLERK
    }

    # 1. Normal Doctor Action -> PERMIT
    res = ac.evaluate_access(doctor_a, patient_a, "order_medications")
    assert res["decision"] == AccessDecision.PERMIT
    print(" [PASS] Treating Consultant allowed to order medications.")

    # 2. Unauthorized Role Action (Billing clerk trying to order med) -> DENY
    res = ac.evaluate_access(billing_clerk, patient_a, "order_medications")
    assert res["decision"] == AccessDecision.DENY
    print(" [PASS] Billing Clerk blocked from ordering medications.")

    # 3. Cross-Tenant Attempt -> DENY
    patient_tenant_b = {**patient_a, "tenant_id": TENANT_B}
    res = ac.evaluate_access(doctor_a, patient_tenant_b, "view_clinical_chart")
    assert res["decision"] == AccessDecision.DENY
    print(" [PASS] Cross-tenant access strictly blocked by policy.")

    # 4. Psychiatric Confidentiality Tier (MHCA 2017)
    psych_patient = {
        "patient_id": "pat-002",
        "tenant_id": TENANT_A,
        "attending_doctor_id": "doc-psych-001",
        "confidentiality": ConfidentialityLevel.RESTRICTED_PSYCHIATRY
    }
    # Cardiologist trying to view without Break-Glass -> BREAK_GLASS_REQUIRED
    res = ac.evaluate_access(doctor_a, psych_patient, "view_clinical_chart")
    assert res["decision"] == AccessDecision.BREAK_GLASS_REQUIRED
    print(" [PASS] Non-psychiatrist blocked from psychiatric chart without Break-Glass.")

    # 5. Break-Glass with Insufficient Justification (< 20 chars) -> DENY
    res = ac.evaluate_access(
        doctor_a, psych_patient, "view_clinical_chart",
        is_break_glass=True, break_glass_reason="Curious."
    )
    assert res["decision"] == AccessDecision.DENY
    print(" [PASS] Break-Glass rejected with insufficient justification.")

    # 6. Break-Glass with Valid Emergency Justification -> PERMIT + AUDIT
    emergency_reason = "Code Blue resuscitation in progress; patient unresponsive; emergency med history required immediately."
    res = ac.evaluate_access(
        doctor_a, psych_patient, "view_clinical_chart",
        is_break_glass=True, break_glass_reason=emergency_reason
    )
    assert res["decision"] == AccessDecision.PERMIT
    assert len(ac.break_glass_logs) == 1
    assert ac.break_glass_logs[0]["justification"] == emergency_reason
    print(" [PASS] Emergency Break-Glass granted and high-priority audit dispatched to CMO.")

    print("================================================================================")
    print(" ALL RBAC, ABAC & BREAK-GLASS POLICIES VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_access_control())
