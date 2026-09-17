"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Master Verification Runner & Quality Gate Certifier
Runs:
  1. test_bed_census.py (State Machine, Checkout-to-Cleaning, Sanitization Gates)
  2. test_nursing_cockpit.py (Wristband eMAR, Fluid Balance, Risk Scales, ISBAR)
  3. test_hai_device_surveillance.py (Device-Days, Removal Counter Decrement, NHSN Rates)
  4. test_nurse_staffing_watchdog.py (Live Ratios, Acuity Standards, CNO Alerts)
"""

import unittest
import sys
import time
import os

# Add test directory and service directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from test_bed_census import TestBedCensusEngine
from test_nursing_cockpit import TestNursingCockpitEngine
from test_hai_device_surveillance import TestHAIDeviceSurveillanceEngine
from test_nurse_staffing_watchdog import TestNurseStaffingWatchdogEngine


def run_phase07_quality_gate():
    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 07 INPATIENT CORE SUITES")
    print("=" * 80)

    suites = [
        ("Bed Census Lifecycle, Checkout Auto-Cleaning & Sanitization Gate", TestBedCensusEngine),
        ("Nursing Station Cockpit, Bedside Wristband eMAR & ISBAR Handover", TestNursingCockpitEngine),
        ("HAI Device Surveillance, Device-Day Decrement & NHSN Benchmark Rates", TestHAIDeviceSurveillanceEngine),
        ("Nurse-to-Patient Ratio Live Watchdog & CNO Staffing Alerting", TestNurseStaffingWatchdogEngine),
    ]

    total_start = time.time()
    all_passed = True

    for name, test_case in suites:
        print(f"\n>>> RUNNING SUITE: {name} ...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
        start = time.time()
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)
        elapsed = round(time.time() - start, 2)

        if result.wasSuccessful():
            print(f"    RESULT: PASSED in {elapsed}s")
        else:
            print(f"    RESULT: FAILED in {elapsed}s with {len(result.failures)} failures and {len(result.errors)} errors")
            all_passed = False

    total_elapsed = round(time.time() - total_start, 2)
    print("\n" + "=" * 80)
    if all_passed:
        print(" [PHASE 07 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All 4 Test Suites Passed with 100% Compliance in {total_elapsed}s")
        print(" Sanitization Gate Active | Bedside Wristband Scan Enforced | Device-Days Tracked")
        print("=" * 80 + "\n")
        return 0
    else:
        print(" [PHASE 07 QUALITY GATE CERTIFICATION: FAILED]")
        print(" Critical test failures encountered. Phase 07 cannot be certified.")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase07_quality_gate())
