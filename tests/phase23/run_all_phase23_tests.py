#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 23 MASTER TEST RUNNER
Runs all Phase 23 diagnostic accuracy, multi-assertion finding graph, and conformal calibration test suites.
"""

import sys
import unittest

def run_phase23_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase23", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 23 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 23 Diagnostic Accuracy & Calibration Tests Passed with 100% Compliance.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 23 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase23_master_suite())
