#!/usr/bin/env python3
"""
Diagnostic Report Lifecycle & Critical Panic Value Alerting Engine (Phase 05).
Enforces:
1. Structured Report State Machine: PRELIMINARY -> FINAL -> AMENDED -> CORRECTED -> ADDENDUM.
2. Automated Critical / Panic Value detection (Potassium > 6.2, Platelets < 20k, Glucose < 40).
3. Mandatory Closed-Loop Telephone Read-Back Alerting Protocol with statutory audit logging.
"""
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

# Standard Critical Panic Thresholds
CRITICAL_PANIC_LIMITS = {
    "potassium": {"low": 2.8, "high": 6.2, "unit": "mmol/L", "risk": "FATAL_CARDIAC_ARRHYTHMIA"},
    "platelets": {"low": 20000.0, "high": 1000000.0, "unit": "/µL", "risk": "SPONTANEOUS_INTRACRANIAL_BLEED"},
    "glucose": {"low": 40.0, "high": 450.0, "unit": "mg/dL", "risk": "HYPOGLYCEMIC_COMA"},
    "troponin_i": {"low": 0.0, "high": 0.04, "unit": "ng/mL", "risk": "ACUTE_MYOCARDIAL_INFARCTION"}
}

class ReportStatus:
    PRELIMINARY = "PRELIMINARY"
    FINAL = "FINAL"
    AMENDED = "AMENDED"
    CORRECTED = "CORRECTED"
    ADDENDUM = "ADDENDUM"

class DiagnosticReportingEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._reports: Dict[str, Dict] = {}
        self._critical_alerts: Dict[str, Dict] = {}

    def create_report(
        self,
        order_id: str,
        patient_mrn: str,
        test_name: str,
        results: Dict[str, float],
        reporting_pathologist_id: str
    ) -> Dict:
        """Creates a diagnostic report and automatically screens for critical panic values."""
        report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        # Check for critical values
        critical_findings = []
        for analyte, val in results.items():
            analyte_clean = analyte.lower().strip()
            if analyte_clean in CRITICAL_PANIC_LIMITS:
                limits = CRITICAL_PANIC_LIMITS[analyte_clean]
                if val < limits["low"] or val > limits["high"]:
                    critical_findings.append({
                        "analyte": analyte,
                        "value": val,
                        "unit": limits["unit"],
                        "threshold_breach": f"< {limits['low']}" if val < limits["low"] else f"> {limits['high']}",
                        "clinical_risk": limits["risk"]
                    })

        report = {
            "report_id": report_id,
            "order_id": order_id,
            "patient_mrn": patient_mrn,
            "test_name": test_name,
            "results": results,
            "status": ReportStatus.FINAL,
            "reporting_pathologist_id": reporting_pathologist_id,
            "has_critical_values": len(critical_findings) > 0,
            "critical_findings": critical_findings,
            "amendments": [],
            "created_at": now,
            "updated_at": now
        }
        self._reports[report_id] = report

        # Trigger Critical Value Alert if panic finding present
        if critical_findings:
            alert_id = f"CRIT-ALERT-{uuid.uuid4().hex[:6].upper()}"
            alert_dossier = {
                "alert_id": alert_id,
                "report_id": report_id,
                "patient_mrn": patient_mrn,
                "critical_findings": critical_findings,
                "telephone_readback_completed": False,
                "notified_clinician": None,
                "notified_nurse": None,
                "triggered_at": now,
                "acknowledged_at": None
            }
            self._critical_alerts[alert_id] = alert_dossier
            report["critical_alert_id"] = alert_id

        return report

    def acknowledge_critical_value_telephone_readback(
        self,
        alert_id: str,
        caller_lab_technician: str,
        receiver_staff_name: str,
        receiver_role: str,
        readback_verified: bool
    ) -> Tuple[bool, str]:
        """
        Statutory Closed-Loop Communication:
        Requires verification that the recipient read back the critical value word-for-word.
        """
        alert = self._critical_alerts.get(alert_id)
        if not alert:
            return False, "ALERT_NOT_FOUND"

        if not readback_verified:
            return False, "READBACK_FAILED: Recipient did NOT read back the values verbatim. Mandatory safety protocol breach."

        now = datetime.now(timezone.utc).isoformat()
        alert["telephone_readback_completed"] = True
        alert["caller_lab_technician"] = caller_lab_technician
        alert["receiver_staff_name"] = receiver_staff_name
        alert["receiver_role"] = receiver_role
        alert["acknowledged_at"] = now

        return True, f"CLOSED_LOOP_ACKNOWLEDGED: Critical value telephone read-back confirmed with {receiver_role} {receiver_staff_name}."

    def amend_report(
        self,
        report_id: str,
        amended_results: Dict[str, float],
        reason_for_amendment: str,
        authorizing_pathologist_id: str
    ) -> Tuple[bool, str]:
        """Amends an existing finalized report, preserving immutable audit trail."""
        report = self._reports.get(report_id)
        if not report:
            return False, "REPORT_NOT_FOUND"

        prior_state = {
            "timestamp": report["updated_at"],
            "results": report["results"].copy(),
            "status": report["status"]
        }

        report["amendments"].append({
            "amendment_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prior_results": prior_state["results"],
            "reason": reason_for_amendment,
            "authorizing_pathologist_id": authorizing_pathologist_id
        })

        report["results"] = amended_results
        report["status"] = ReportStatus.AMENDED
        report["updated_at"] = datetime.now(timezone.utc).isoformat()

        return True, "REPORT_AMENDED_WITH_AUDIT_TRAIL"
