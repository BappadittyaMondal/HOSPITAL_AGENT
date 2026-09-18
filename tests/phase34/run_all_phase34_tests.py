#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 34 MASTER TEST RUNNER
Runs all Phase 34 Clinical Precision, Semantic Disambiguation & Persistence Lifecycle tests:
- Part 1: SNOMED-CT Semantic Disambiguation & Rule-Out Key Normalization
- Part 2: NLEM Formulary O(1) Hash Screening, Calcium Gluconate & High-Alert Alerting
- Part 3: Patient Store Longitudinal Observation Recall & State Lifecycle
"""

import sys
import unittest

def run_phase34_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase34", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 34 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 34 Clinical Precision & Persistence Lifecycle Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 34 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase34_master_suite())
