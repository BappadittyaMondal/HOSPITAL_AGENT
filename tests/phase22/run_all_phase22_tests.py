#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 22 MASTER TEST RUNNER
Runs all Phase 22 concurrent audit ledger and cryptographic persistence test suites.
"""

import sys
import unittest

def run_phase22_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase22", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 22 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 22 Concurrent Audit & Persistence Tests Passed with 100% Compliance.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 22 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase22_master_suite())
