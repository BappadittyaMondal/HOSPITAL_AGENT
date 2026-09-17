#!/usr/bin/env python3
"""
MASTER PHASE 04 QUALITY GATE EXECUTOR.
Runs all Phase 04 Clinical Core verification test suites sequentially.
Zero tolerance: Every test suite must pass 100% to certify Phase 04 Clinical Core completion.
"""
import subprocess
import sys
import time

PHASE04_TEST_SUITES = [
    ("CPOE Sub-ms DRE & Cumulative Toxicity Limits", ["python", "tests/phase04/test_cpoe_dre.py"]),
    ("Medical Oncology & Dual-Nurse Chemotherapy Safety", ["python", "tests/phase04/test_chemotherapy_engine.py"]),
    ("Inpatient Nursing, Closed-Loop eMAR & NEWS2 Escalation", ["python", "tests/phase04/test_emar_nursing.py"]),
    ("Antimicrobial Stewardship (ASP) & HAI Surveillance", ["python", "tests/phase04/test_antimicrobial_hai.py"]),
]

def run_all_tests():
    print("\n" + "=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 04 CLINICAL CORE VERIFICATION SUITES")
    print("=" * 80 + "\n")

    overall_start = time.perf_counter()
    passed_suites = 0

    for name, cmd in PHASE04_TEST_SUITES:
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
    print(f" [PHASE 04 QUALITY GATE CERTIFICATION: PASSED]")
    print(f" All {passed_suites} Test Suites Passed with 100% Compliance in {total_elapsed:.2f}s")
    print(" Sub-ms DRE Verified | Dual-Nurse Chemo Gate Enforced | eMAR 5-Rights Active | WHO AWaRe Protected")
    print("=" * 80 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(run_all_tests())
