#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 26 MASTER TEST RUNNER
Runs all Phase 26 sequential elicitation, partial-intake fallback, cutaneous archetype, and socket health test suites.
"""

import sys
import unittest

def run_phase26_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase26", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 26 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 26 Sequential Elicitation, Partial-Intake Fallback & Socket Health Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 26 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase26_master_suite())
