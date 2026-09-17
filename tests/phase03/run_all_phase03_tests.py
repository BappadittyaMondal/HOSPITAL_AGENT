#!/usr/bin/env python3
"""
MASTER PHASE 03 QUALITY GATE EXECUTOR.
Runs all Phase 03 Front Door verification test suites sequentially.
Zero tolerance: Every test suite must pass 100% to certify Phase 03 Front Door completion.
"""
import subprocess
import sys
import time

PHASE03_TEST_SUITES = [
    ("Emergency Triage (ESI) & Inviolable Financial Decoupling", ["python", "tests/phase03/test_emergency_triage.py"]),
    ("OPD Dynamic Queue, Multilingual Kiosk & Smart Paper QR", ["python", "tests/phase03/test_opd_queue_kiosk.py"]),
    ("Telemedicine WebRTC Bandwidth Tiering & NMC 2020 Compliance", ["python", "tests/phase03/test_telemedicine_engine.py"]),
    ("Ambulance Fleet GPS, Visitor Quotas, Epidemic Lockdown & HICS", ["python", "tests/phase03/test_ambulance_fleet_hics.py"]),
]

def run_all_tests():
    print("\n" + "=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 03 FRONT DOOR VERIFICATION SUITES")
    print("=" * 80 + "\n")

    overall_start = time.perf_counter()
    passed_suites = 0

    for name, cmd in PHASE03_TEST_SUITES:
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
    print(f" [PHASE 03 QUALITY GATE CERTIFICATION: PASSED]")
    print(f" All {passed_suites} Test Suites Passed with 100% Compliance in {total_elapsed:.2f}s")
    print(" Emergency Registration < 1s | Zero Billing Blocks | Sub-10ms Ambulance Dispatch | NMC Telemedicine Enforced")
    print("=" * 80 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(run_all_tests())
