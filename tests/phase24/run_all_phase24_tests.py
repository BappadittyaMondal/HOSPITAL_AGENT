#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 24 MASTER TEST RUNNER
Runs all Phase 24 clinical semantic anti-fabrication, mathematical calibration, and CSB authorization test suites.
"""

import sys
import unittest

def run_phase24_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase24", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 24 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 24 Clinical Semantic Anti-Fabrication & Math Calibration Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 24 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase24_master_suite())
