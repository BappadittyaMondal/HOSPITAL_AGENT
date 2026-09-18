#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 28 MASTER TEST RUNNER
"""
import sys
import unittest

def run_phase28_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase28", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 28 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 28 Core Remediation Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 28 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase28_master_suite())
