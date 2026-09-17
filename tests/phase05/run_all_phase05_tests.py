#!/usr/bin/env python3
"""
MASTER PHASE 05 QUALITY GATE EXECUTOR.
Runs all Phase 05 Diagnostics verification test suites sequentially.
Zero tolerance: Every test suite must pass 100% to certify Phase 05 Diagnostics completion.
"""
import subprocess
import sys
import time

PHASE05_TEST_SUITES = [
    ("LIS Bedside PPID, Westgard Multi-Rule QC & Delta-Checks", ["python", "tests/phase05/test_lis_qc.py"]),
    ("Diagnostic Report Lifecycle & Closed-Loop Critical Values", ["python", "tests/phase05/test_diagnostic_reporting.py"]),
    ("PACS DICOM Radiation Dose Tracking & AI Critical Triage", ["python", "tests/phase05/test_pacs_dicom.py"]),
    ("Blood Bank Inviolable Transfusion Barrier & HvPI Reporting", ["python", "tests/phase05/test_blood_bank.py"]),
]

def run_all_tests():
    print("\n" + "=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 05 DIAGNOSTICS VERIFICATION SUITES")
    print("=" * 80 + "\n")

    overall_start = time.perf_counter()
    passed_suites = 0

    for name, cmd in PHASE05_TEST_SUITES:
        print(f">>> RUNNING SUITE: {name} ...")
        t0 = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.perf_counter() - t0

        if result.returncode == 0:
            passed_suites += 1
            print(f"    RESULT: PASSED in {elapsed:.2f}s\n")
        else:
            print(f"    RESULT: FAILED (Exit Code: {result.returncode})")
            print(result.stdout)
            print(result.stderr)
            print(f"\n[ABORT] Master Quality Gate failed at suite: {name}")
            return 1

    total_elapsed = time.perf_counter() - overall_start
    print("=" * 80)
    print(f" [PHASE 05 QUALITY GATE CERTIFICATION: PASSED]")
    print(f" All {passed_suites} Test Suites Passed with 100% Compliance in {total_elapsed:.2f}s")
    print(" Westgard Batch Halting Verified | Critical Read-Back Enforced | Incompatible Transfusion Blocked")
    print("=" * 80 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(run_all_tests())
