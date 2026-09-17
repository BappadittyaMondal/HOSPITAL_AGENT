#!/usr/bin/env python3
"""
MASTER PHASE 02 QUALITY GATE EXECUTOR.
Runs all Phase 02 Identity verification test suites sequentially.
Zero tolerance: Every test suite must pass 100% to certify Phase 02 Identity completion.
"""
import subprocess
import sys
import time

PHASE02_TEST_SUITES = [
    ("Master Patient Index (MPI) & Fellegi-Sunter Linkage", ["python", "tests/phase02/test_mpi_engine.py"]),
    ("DPDP Act 2023 Purpose-Bound Consent & Research Filter", ["python", "tests/phase02/test_consent_manager.py"]),
    ("Staff Credentialing, Privileging Matrix & Expiry Watchdog", ["python", "tests/phase02/test_staff_credentialing.py"]),
    ("Mother-Baby Linkage, Anti-Abduction & Pediatric Safeguards", ["python", "tests/phase02/test_mother_baby_pediatric.py"]),
]

def run_all_tests():
    print("\n" + "=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 02 IDENTITY VERIFICATION SUITES")
    print("=" * 80 + "\n")

    overall_start = time.perf_counter()
    passed_suites = 0

    for name, cmd in PHASE02_TEST_SUITES:
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
    print(f" [PHASE 02 QUALITY GATE CERTIFICATION: PASSED]")
    print(f" All {passed_suites} Test Suites Passed with 100% Compliance in {total_elapsed:.2f}s")
    print(" Zero False Merges | Unprivileged Surgeries Blocked | DPDP Research Privacy Enforced")
    print("=" * 80 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(run_all_tests())
