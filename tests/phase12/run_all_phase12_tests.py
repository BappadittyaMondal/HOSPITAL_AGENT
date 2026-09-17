"""
PROJECT "HOSPITAL" — PHASE 12: HOSPITAL OPERATIONS
Master Quality Gate Verification Runner
Phase 12: Central Kitchen, Laundry, BMW, Supply Chain & Assets

Quality Gates Enforced & Verified:
  1. A patient marked NPO in pre-op is completely excluded from kitchen meal tray
     printing and distribution logs, and meal assembly/dispatch is mechanically blocked.
  2. Biomedical waste module generates complete SPCB annual report matching barcoded
     pickup weights with zero unaccounted waste and SHA-256 seal.
  3. Mobile crash cart moved outside Emergency Department perimeter triggers security
     console alarm in < 10 seconds SLA (GeofenceBreachSecurityAlarm).
"""

import os
import sys
import unittest
import time

# Ensure services directory is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))


def run_phase12_master_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_modules = [
        "test_kitchen_dietary",
        "test_linen_laundry",
        "test_biomedical_waste",
        "test_procurement_inventory",
        "test_asset_oxygen_telemetry",
    ]

    for mod_name in test_modules:
        mod = __import__(mod_name)
        suite.addTests(loader.loadTestsFromModule(mod))

    print("\n" + "=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 12 HOSPITAL OPERATIONS SUITES")
    print("=" * 80 + "\n")

    start_time = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 80)
    if result.wasSuccessful():
        print(f" [PHASE 12 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All {result.testsRun} Tests across {len(test_modules)} Suites Passed with 100% Compliance in {elapsed:.2f}s")
        print(" Gate 1: Pre-op NPO Meals Mechanically Blocked & Excluded from Logs [VERIFIED]")
        print(" Gate 2: SPCB Form IV Report Generated Matching Barcoded BMW Weights [VERIFIED]")
        print(" Gate 3: Mobile Crash Cart Geofence Breach Alarm Dispatched in < 10s SLA [VERIFIED]")
        print("=" * 80 + "\n")
        return 0
    else:
        print(f" [PHASE 12 QUALITY GATE CERTIFICATION: FAILED]")
        print(f" Failures: {len(result.failures)} | Errors: {len(result.errors)}")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase12_master_suite())
