"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Master Verification Runner & Quality Gate Certifier
Runs:
  1. test_surgical_safety_ot.py (WHO Checklist, Count Discrepancy Hard Stop, UDI Tracking)
  2. test_anesthesia_pacu.py (Pre-Anesthetic PAC Assessment, Aldrete Discharge Score >= 9)
  3. test_cssd_sterilization.py (Autoclave Cycle, Spore Indicator Failure Tray Recall Lock)
  4. test_transfusion_transplant.py (Bedside Blood Mismatch Siren, THOTA 6-Hour Interval, CIT Viability)
"""

import unittest
import sys
import time
import os

# Add test directory and service directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from test_surgical_safety_ot import TestSurgicalSafetyOTEngine
from test_anesthesia_pacu import TestAnesthesiaPACUEngine
from test_cssd_sterilization import TestCSSDSterilizationEngine
from test_transfusion_transplant import TestTransfusionTransplantEngine


def run_phase09_quality_gate():
    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 09 SURGICAL & PROCEDURAL SUITES")
    print("=" * 80)

    suites = [
        ("Surgical Safety Checklist, Dual-Nurse Count Reconciliation & UDI Implants", TestSurgicalSafetyOTEngine),
        ("Anesthesia Information, Airway PAC Assessment & PACU Aldrete Scoring Gate", TestAnesthesiaPACUEngine),
        ("CSSD Closed-Loop Sterilization, Spore Failure Recall & Unsterile Issue Locks", TestCSSDSterilizationEngine),
        ("Bedside Blood Transfusion Mismatch Siren & Statutory THOTA Transplant Protocols", TestTransfusionTransplantEngine),
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
        print(" [PHASE 09 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All 4 Test Suites Passed with 100% Compliance in {total_elapsed}s")
        print(" Sponge Discrepancy Blocked | Transfusion Siren Active | Spore Failure Trays Recalled")
        print("=" * 80 + "\n")
        return 0
    else:
        print(" [PHASE 09 QUALITY GATE CERTIFICATION: FAILED]")
        print(" Critical test failures encountered. Phase 09 cannot be certified.")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase09_quality_gate())
