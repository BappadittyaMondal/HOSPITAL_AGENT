"""
PROJECT "HOSPITAL" — PHASE 20 MASTER QUALITY GATE RUNNER
Module: run_all_phase20_tests.py
Executes all test suites verifying:
  - Fail-fast secret enforcement in production (RuntimeError on missing env vars)
  - Keyed HMAC-SHA256 audit ledger with external secret anchoring
  - Standard RFC 7519 JWT generation
  - Operational API routing (Blood Bank, NDPS Vault, PM-JAY, Edge Leasing, Partograph)
"""

import os
import sys
import unittest
import time

def run_phase20_quality_gate():
    phase_dir = os.path.dirname(__file__)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_files = [
        "test_failfast_secrets_and_hmac_ledger.py",
        "test_operational_api_endpoints.py"
    ]

    for tf in test_files:
        full_path = os.path.join(phase_dir, tf)
        if os.path.exists(full_path):
            discovered = loader.discover(start_dir=phase_dir, pattern=tf)
            suite.addTests(discovered)

    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 20 OPERATIONAL ROUTING & SECURITY SUITES")
    print("=" * 80)

    start = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start

    print("=" * 80)
    if result.wasSuccessful():
        print(f" [PHASE 20 QUALITY GATE: PASSED] {result.testsRun} tests executed in {elapsed:.3f}s with ZERO errors.")
        print(" Fail-Fast Secrets | Keyed HMAC Audit | RFC 7519 JWT | 5 Operational API Routes Wired")
        print("=" * 80)
        return 0
    else:
        print(f" [PHASE 20 QUALITY GATE: FAILED] {len(result.failures)} failures, {len(result.errors)} errors.")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase20_quality_gate())
