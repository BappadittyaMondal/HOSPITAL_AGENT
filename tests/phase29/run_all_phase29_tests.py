#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 29 MASTER TEST RUNNER
Runs all Phase 29 Multi-Modal Bedside Diagnostic Signal Engine tests:
- Bazett & Fridericia QTc calculations
- Anterior STEMI & LAD culprit detection
- Inferior STEMI & Nitrate preload contraindication hard-stop
- Cath Lab emergency activation & Door-to-Balloon countdown
"""

import sys
import unittest

def run_phase29_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase29", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 29 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 29 Multi-Modal Diagnostic Signal Engine Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 29 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase29_master_suite())
