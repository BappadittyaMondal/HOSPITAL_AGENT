#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 30 MASTER TEST RUNNER
Runs all Phase 30 Full-Graph Local Ontological Index tests:
- Vernacular & colloquial alias resolution (Bengali/Hindi/English)
- Transitive hierarchical DAG subsumption traversal
- Accurate ICD-11 MMS cross-mapping
"""

import sys
import unittest

def run_phase30_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase30", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 30 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 30 Full-Graph Ontological Index Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 30 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase30_master_suite())
