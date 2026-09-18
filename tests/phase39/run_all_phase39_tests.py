#!/usr/bin/env python3
"""
Phase 39 Master Quality Gate Runner
Executes all Phase 39 Operational Durability, NABH Emergency Break-Glass,
Jan Aushadhi Generics, and Tri-Lingual Vernacular Patient Guidance tests.
"""
import os
import sys
import unittest
import time

def run_all_phase39_tests():
    start = time.perf_counter()
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_file = os.path.join(os.path.dirname(__file__), "test_operational_durability_and_break_glass.py")
    module_dir = os.path.dirname(test_file)
    discovered = loader.discover(start_dir=module_dir, pattern="test_*.py")
    suite.addTests(discovered)

    print("=" * 80)
    print(" EXECUTING PHASE 39 MASTER QUALITY GATE (OPERATIONAL DURABILITY & BREAK-GLASS)")
    print("=" * 80)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start

    print("=" * 80)
    if result.wasSuccessful():
        print(f" PHASE 39 GATE PASSED: {result.testsRun} tests executed in {elapsed:.3f}s")
        print(" ZERO REGRESSIONS DETECTED. STATUS: 100% QUALITY PASS.")
        print("=" * 80)
        return 0
    else:
        print(f" PHASE 39 GATE FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(run_all_phase39_tests())
