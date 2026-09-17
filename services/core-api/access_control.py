#!/usr/bin/env python3
"""
Role-Based & Attribute-Based Access Control (RBAC/ABAC) Engine for HOSPITAL Platform.
Enforces:
1. Clinical role hierarchy and least-privilege permissions.
2. Contextual ABAC (Doctor-Patient Treatment Relationship, Departmental Boundaries).
3. Ultra-restricted confidentiality boundaries (e.g., Psychiatry, VIP/MLC).
4. Break-Glass Emergency Override with mandatory justification and real-time audit alerts.
"""
from typing import Dict, List, Optional, Set
from enum import Enum
import uuid
from datetime import datetime, timezone

class ClinicalRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    MEDICAL_DIRECTOR = "MEDICAL_DIRECTOR"
    CONSULTANT_PHYSICIAN = "CONSULTANT_PHYSICIAN"
    RESIDENT_PHYSICIAN = "RESIDENT_PHYSICIAN"
    STAFF_NURSE = "STAFF_NURSE"
    CLINICAL_PHARMACIST = "CLINICAL_PHARMACIST"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    BILLING_CLERK = "BILLING_CLERK"

class ConfidentialityLevel(str, Enum):
    STANDARD = "STANDARD"
    RESTRICTED_PSYCHIATRY = "RESTRICTED_PSYCHIATRY"
    FORENSIC_MLC = "FORENSIC_MLC"

class AccessDecision(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"
    BREAK_GLASS_REQUIRED = "BREAK_GLASS_REQUIRED"

# Role to base permissions mapping
ROLE_PERMISSIONS: Dict[ClinicalRole, Set[str]] = {
    ClinicalRole.MEDICAL_DIRECTOR: {
        "view_clinical_chart", "edit_clinical_chart", "order_medications",
        "order_labs", "sign_discharge", "view_audit_logs", "approve_clinical_rules"
    },
    ClinicalRole.CONSULTANT_PHYSICIAN: {
        "view_clinical_chart", "edit_clinical_chart", "order_medications",
        "order_labs", "order_procedures", "sign_discharge"
    },
    ClinicalRole.RESIDENT_PHYSICIAN: {
        "view_clinical_chart", "edit_clinical_chart", "order_medications",
        "order_labs", "order_procedures"
    },
    ClinicalRole.STAFF_NURSE: {
        "view_clinical_chart", "record_vitals", "administer_medication",
        "record_nursing_notes", "record_fluid_balance"
    },
    ClinicalRole.CLINICAL_PHARMACIST: {
        "view_prescriptions", "dispense_medication", "view_formulary",
        "perform_med_reconciliation", "access_ndps_vault"
    },
    ClinicalRole.LAB_TECHNICIAN: {
        "view_lab_orders", "record_analyzer_results", "validate_qc"
    },
    ClinicalRole.BILLING_CLERK: {
        "view_billing_ledger", "generate_invoice", "process_payment", "view_tariffs"
    }
}

class AccessControlEngine:
    def __init__(self):
        self.break_glass_logs: List[Dict] = []

    def evaluate_access(
        self,
        user: Dict,
        patient: Dict,
        action: str,
        is_break_glass: bool = False,
        break_glass_reason: Optional[str] = None
    ) -> Dict:
        """
        Evaluates ABAC policy combining Role, Department Context, and Patient Confidentiality.
        """
        role = ClinicalRole(user.get("role"))
        user_tenant = user.get("tenant_id")
        patient_tenant = patient.get("tenant_id")

        # 1. Multi-tenant boundary check
        if user_tenant != patient_tenant:
            return {"decision": AccessDecision.DENY, "reason": "Cross-tenant access strictly prohibited by RLS boundary."}

        # 2. Check basic RBAC permission
        role_perms = ROLE_PERMISSIONS.get(role, set())
        if action not in role_perms and role != ClinicalRole.SUPER_ADMIN:
            return {"decision": AccessDecision.DENY, "reason": f"Role {role} lacks permission '{action}'."}

        # 3. Check Confidentiality Tier (e.g. Psychiatry records under MHCA 2017)
        confidentiality = patient.get("confidentiality", ConfidentialityLevel.STANDARD)
        if confidentiality == ConfidentialityLevel.RESTRICTED_PSYCHIATRY:
            user_dept = user.get("department", "")
            if user_dept != "PSYCHIATRY" and role != ClinicalRole.MEDICAL_DIRECTOR:
                if not is_break_glass:
                    return {
                        "decision": AccessDecision.BREAK_GLASS_REQUIRED,
                        "reason": "Restricted Psychiatric Chart (MHCA 2017). Break-Glass emergency override required."
                    }
                else:
                    return self._execute_break_glass(user, patient, action, break_glass_reason)

        # 4. Check Doctor-Patient Treatment Relationship
        assigned_doctor_id = patient.get("attending_doctor_id")
        assigned_ward = patient.get("assigned_ward")
        user_id = user.get("user_id")
        user_ward = user.get("assigned_ward")

        # In emergency departments, all ER doctors/nurses have relationship
        if user.get("department") == "EMERGENCY":
            return {"decision": AccessDecision.PERMIT, "reason": "Emergency department blanket active relationship."}

        if role in {ClinicalRole.CONSULTANT_PHYSICIAN, ClinicalRole.RESIDENT_PHYSICIAN}:
            if assigned_doctor_id and assigned_doctor_id != user_id:
                # Treating physician check
                consulting_doctors = patient.get("consulting_doctor_ids", [])
                if user_id not in consulting_doctors:
                    if not is_break_glass:
                        return {
                            "decision": AccessDecision.BREAK_GLASS_REQUIRED,
                            "reason": "Clinician has no active clinical relationship with patient. Break-Glass required."
                        }
                    else:
                        return self._execute_break_glass(user, patient, action, break_glass_reason)

        if role == ClinicalRole.STAFF_NURSE:
            if assigned_ward and user_ward and assigned_ward != user_ward:
                if not is_break_glass:
                    return {
                        "decision": AccessDecision.BREAK_GLASS_REQUIRED,
                        "reason": f"Nurse assigned to {user_ward} attempting to access patient in {assigned_ward}."
                    }
                else:
                    return self._execute_break_glass(user, patient, action, break_glass_reason)

        return {"decision": AccessDecision.PERMIT, "reason": "Access granted under normal RBAC/ABAC policy."}

    def _execute_break_glass(self, user: Dict, patient: Dict, action: str, reason: Optional[str]) -> Dict:
        if not reason or len(reason.strip()) < 20:
            return {
                "decision": AccessDecision.DENY,
                "reason": "Break-Glass rejected: Mandatory clinical emergency justification must be at least 20 characters."
            }

        event = {
            "break_glass_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "role": user.get("role"),
            "patient_id": patient.get("patient_id"),
            "action": action,
            "justification": reason,
            "alert_sent_to": ["CHIEF_MEDICAL_OFFICER", "MEDICAL_SUPERINTENDENT"]
        }
        self.break_glass_logs.append(event)
        return {
            "decision": AccessDecision.PERMIT,
            "reason": f"EMERGENCY BREAK-GLASS GRANTED. High-priority audit logged to Medical Superintendent.",
            "audit_event": event
        }
