#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 36 MASTER RUNNER
====================================================================================================
Runs all Phase 36 unit and integration tests:
- Multi-Contraindication Cascading
- Negative & Zero Weight Sanitization
- Pediatric Dose Ceiling Capping
- NLEM Formulary Engine Allergy Surveillance
- Context-Aware CPOE Chart Allergy Extraction
- Full REST Ingestion Lifecycle
====================================================================================================
"""

import sys
import os
import unittest
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from test_contraindication_cascade_and_allergy_gating import TestPhase36ContraindicationCascadeAndAllergyGating


def run_phase36_tests() -> int:
    print("=" * 80)
    print("RUNNING PHASE 36: CONTRAINDICATION CASCADING, ALLERGY GATING & REST INGESTION")
    print("=" * 80)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase36ContraindicationCascadeAndAllergyGating)
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start_time
    
    print("-" * 80)
    print(f"Ran {result.testsRun} tests in {duration:.3f}s")
    
    if result.wasSuccessful():
        print("[PASS] All Phase 36 tests passed successfully!")
        return 0
    else:
        print(f"[FAIL] {len(result.failures)} failures, {len(result.errors)} errors encountered.")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase36_tests())
