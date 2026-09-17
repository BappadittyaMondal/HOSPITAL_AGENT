"""
PROJECT "HOSPITAL" — PHASE 13: PATIENT EXPERIENCE
Master Quality Gate Verification Runner
Phase 13: Vernacular Guidance, Discharge, Grievance & Chronic Care

Quality Gates Enforced & Verified:
  1. Vernacular translated prescription matches doctor's signed orders with 100.00%
     pharmacological accuracy in automated back-translation tests.
  2. Patient grievance filed via WhatsApp escalates automatically to Department Head if unresolved after 4 hours.
  3. Patient indicating "worse fever" on post-discharge WhatsApp check-in generates
     an immediate nurse callback task on the ward dashboard.
"""

import os
import sys
import unittest
import time

# Ensure services directory is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))


def run_phase13_master_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_modules = [
        "test_vernacular_discharge",
        "test_post_discharge_chronic",
        "test_grievance_nps",
    ]

    for mod_name in test_modules:
        mod = __import__(mod_name)
        suite.addTests(loader.loadTestsFromModule(mod))

    print("\n" + "=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 13 PATIENT EXPERIENCE SUITES")
    print("=" * 80 + "\n")

    start_time = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 80)
    if result.wasSuccessful():
        print(f" [PHASE 13 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All {result.testsRun} Tests across {len(test_modules)} Suites Passed with 100% Compliance in {elapsed:.2f}s")
        print(" Gate 1: 100.00% Pharmacological Back-Translation Accuracy Certified [VERIFIED]")
        print(" Gate 2: WhatsApp Grievance 4h SLA Escalation to HOD [VERIFIED]")
        print(" Gate 3: 'Worse Fever' WhatsApp Trigger Schedules STAT Nurse Callback [VERIFIED]")
        print("=" * 80 + "\n")
        return 0
    else:
        print(f" [PHASE 13 QUALITY GATE CERTIFICATION: FAILED]")
        print(f" Failures: {len(result.failures)} | Errors: {len(result.errors)}")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase13_master_suite())
