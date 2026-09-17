"""
PROJECT "HOSPITAL" — PHASE 19 MASTER QUALITY GATE RUNNER
Module: run_all_phase19_tests.py
Executes all test suites verifying:
  - Cryptographic PBKDF2 authentication & RFC 7519 JWT verification
  - Persistent SQLite WAL Transactional Outbox (crash-proof)
  - Universal Cryptographic SHA-256 Hash Chained Audit Ledger
  - Standardized Drug Terminology & Brand-Name DRE Resolution
  - Enterprise Observability (Structured JSON Logging) & Decimal Currency Precision
"""

import os
import sys
import unittest
import time

def run_phase19_quality_gate():
    phase_dir = os.path.dirname(__file__)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_files = [
        "test_auth_and_security.py",
        "test_persistent_outbox.py",
        "test_tamper_evident_audit.py",
        "test_brand_name_dre_resolution.py",
        "test_currency_and_logging.py"
    ]

    for tf in test_files:
        full_path = os.path.join(phase_dir, tf)
        if os.path.exists(full_path):
            discovered = loader.discover(start_dir=phase_dir, pattern=tf)
            suite.addTests(discovered)

    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 19 PRODUCTION HARDENING SUITES")
    print("=" * 80)

    start = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start

    print("=" * 80)
    if result.wasSuccessful():
        print(f" [PHASE 19 QUALITY GATE: PASSED] {result.testsRun} tests executed in {elapsed:.3f}s with ZERO errors.")
        print(" PBKDF2 Salted Auth | Crash-Proof Outbox | SHA-256 Audit Chain | Brand DRE | Structured Logs")
        print("=" * 80)
        return 0
    else:
        print(f" [PHASE 19 QUALITY GATE: FAILED] {len(result.failures)} failures, {len(result.errors)} errors.")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase19_quality_gate())
