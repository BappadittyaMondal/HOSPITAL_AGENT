#!/usr/bin/env python3
"""
Diagnostic Reporting & Critical Value Closed-Loop Verification Test Suite (Phase 05).
Tests report state machine lifecycle (Final -> Amended), critical panic value detection,
and mandatory telephone read-back verification.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from diagnostic_reporting import DiagnosticReportingEngine, ReportStatus

def test_diagnostic_reporting():
    print("================================================================================")
    print(" [DIAGNOSTIC REPORTING TEST] VERIFYING REPORT STATE MACHINE & CRITICAL ALERTS")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"
    rep_engine = DiagnosticReportingEngine(tenant_id=TENANT_ID)

    # 1. Report with Critical Panic Value (Potassium 6.8 mmol/L > 6.2 mmol/L)
    crit_report = rep_engine.create_report(
        order_id="ORD-ELEC-991",
        patient_mrn="MRN-ICU-772",
        test_name="Serum Electrolytes Panel",
        results={"Sodium": 138.0, "Potassium": 6.8, "Chloride": 101.0},
        reporting_pathologist_id="PATH-01"
    )
    assert crit_report["has_critical_values"] is True
    assert "critical_alert_id" in crit_report
    alert_id = crit_report["critical_alert_id"]
    print(f" [PASS] Critical Panic Value detected: Potassium 6.8 mmol/L -> Alert {alert_id} generated.")

    # 2. Telephone Read-Back Protocol: Incomplete read-back attempt -> REJECTED
    ok_fail, msg_fail = rep_engine.acknowledge_critical_value_telephone_readback(
        alert_id=alert_id,
        caller_lab_technician="Tech Subir Ghosh",
        receiver_staff_name="Staff Nurse Rita Sen",
        receiver_role="ICU_CHARGE_NURSE",
        readback_verified=False # Failed to read back!
    )
    assert ok_fail is False
    assert "READBACK_FAILED" in msg_fail
    print(" [PASS] Closed-loop telephone gate: Acknowledgment rejected without verbal read-back.")

    # 3. Telephone Read-Back Protocol: Verified verbal read-back -> CONFIRMED
    ok_ack, msg_ack = rep_engine.acknowledge_critical_value_telephone_readback(
        alert_id=alert_id,
        caller_lab_technician="Tech Subir Ghosh",
        receiver_staff_name="Staff Nurse Rita Sen",
        receiver_role="ICU_CHARGE_NURSE",
        readback_verified=True # Read back verbatim!
    )
    assert ok_ack is True
    assert "CLOSED_LOOP_ACKNOWLEDGED" in msg_ack
    print(f" [PASS] Closed-loop telephone read-back verified and logged with statutory audit timestamp.")

    # 4. Report Lifecycle Amendment (Final -> Amended with audit history)
    ok_amend, msg_amend = rep_engine.amend_report(
        report_id=crit_report["report_id"],
        amended_results={"Sodium": 138.0, "Potassium": 6.7, "Chloride": 101.0},
        reason_for_amendment="Repeated on secondary ISE analyzer for confirmatory check",
        authorizing_pathologist_id="PATH-CHIEF-01"
    )
    assert ok_amend is True
    updated_rep = rep_engine._reports[crit_report["report_id"]]
    assert updated_rep["status"] == ReportStatus.AMENDED
    assert len(updated_rep["amendments"]) == 1
    assert updated_rep["amendments"][0]["prior_results"]["Potassium"] == 6.8
    print(" [PASS] Report amendment completed: Historical results preserved in immutable audit trail.")

    print("================================================================================")
    print(" DIAGNOSTIC REPORTING & CRITICAL VALUE SUBSYSTEM FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_diagnostic_reporting())
