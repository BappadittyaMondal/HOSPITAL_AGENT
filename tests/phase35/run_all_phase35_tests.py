#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 35 TEST SUITE RUNNER
====================================================================================================
Runs all Phase 35 unit tests for End-to-End Clinical Pipeline, STG Prescribing, and Context-Aware CPOE.
====================================================================================================
"""

import sys
import os
import unittest
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from test_end_to_end_pipeline_and_stg import TestPhase35EndToEndPipelineAndSTG


def run_suite():
    print("=" * 80)
    print("RUNNING PHASE 35: END-TO-END PIPELINE & STG PRESCRIPTION TESTS")
    print("=" * 80)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhase35EndToEndPipelineAndSTG)

    t0 = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - t0

    print("-" * 80)
    print(f"Ran {result.testsRun} tests in {elapsed:.3f}s")
    if result.wasSuccessful():
        print("[PASS] All Phase 35 tests passed successfully!")
        return 0
    else:
        print(f"[FAIL] {len(result.failures)} failures, {len(result.errors)} errors.")
        return 1


if __name__ == "__main__":
    sys.exit(run_suite())
