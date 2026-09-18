#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 33 MASTER TEST RUNNER
Runs all Phase 33 Clinical Foundation Realization tests:
- S-01: Disease Knowledge Registry (120+ clinical entities & Bayesian likelihood evaluation)
- S-02: NLEM 2022 Drug Formulary & 500+ DDI Engine (Sub-millisecond lethal DDI & teratogen blocks)
- S-03: Persistent Patient & Longitudinal Record Store (True cross-session patient memory)
"""

import sys
import unittest

def run_phase33_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase33", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 33 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 33 Clinical Foundation Realization (S-01, S-02, S-03) Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 33 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase33_master_suite())
