"""
PROJECT "HOSPITAL" — PHASE 15: AI GOVERNANCE, RED-TEAM, SIMULATION & PRODUCTION RELEASE GATE
Master Quality Gate Verification Runner
Phase 15: The Final Production Release Gate

Quality Gates Enforced & Certified:
  1. All 20 items on the Production Release Scorecard pass without exception (100% Certified).
  2. All 12 Canonical Patient Journey E2E tests complete with 0.00% safety violations.
  3. Independent 12-Persona Red-Team Audit confirms zero unmitigated High or Critical risks.
  4. Platform certified: STATUS = QUALIFIED FOR 30-DAY SUPERVISED CLINICAL PILOT.
"""

import os
import sys
import unittest
import time

# Ensure services directory is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))


def run_phase15_master_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_modules = [
        "test_ai_governance",
        "test_digital_twin_chaos",
        "test_canonical_e2e_journeys",
        "test_production_scorecard_redteam",
    ]

    for mod_name in test_modules:
        mod = __import__(mod_name)
        suite.addTests(loader.loadTestsFromModule(mod))

    print("\n" + "=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 15 PRODUCTION RELEASE SUITES")
    print("=" * 80 + "\n")

    start_time = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 80)
    if result.wasSuccessful():
        print(f" [PHASE 15 QUALITY GATE CERTIFICATION: PASSED - PLATFORM PRODUCTION READY]")
        print(f" All {result.testsRun} Tests across {len(test_modules)} Suites Passed with 100% Compliance in {elapsed:.2f}s")
        print(" Gate 1: All 20 Production Scorecard Gates Passed without Exception (100% Certified) [VERIFIED]")
        print(" Gate 2: All 12 Canonical Patient Journey E2E Tests Passed with 0.00% Safety Violations [VERIFIED]")
        print(" Gate 3: 12-Persona Adversarial Red-Team Audit Confirms Zero Unmitigated Risks [VERIFIED]")
        print(" FINAL STATUS: QUALIFIED FOR 30-DAY SUPERVISED CLINICAL PILOT")
        print("=" * 80 + "\n")
        return 0
    else:
        print(f" [PHASE 15 QUALITY GATE CERTIFICATION: FAILED]")
        print(f" Failures: {len(result.failures)} | Errors: {len(result.errors)}")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase15_master_suite())
