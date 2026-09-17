"""
Global Multi-Phase Regression Runner
Discovers and executes all test suites across all phases (Phase 01 to Phase 20).
"""

import os
import sys
import unittest
import time

def run_all_phases():
    base_dir = os.path.dirname(__file__)
    loader = unittest.TestLoader()
    master_suite = unittest.TestSuite()

    phase_dirs = sorted([d for d in os.listdir(base_dir) if d.startswith("phase") and os.path.isdir(os.path.join(base_dir, d))])
    total_suites = 0

    for pd in phase_dirs:
        phase_path = os.path.join(base_dir, pd)
        tests = loader.discover(start_dir=phase_path, pattern="test_*.py")
        master_suite.addTests(tests)
        total_suites += 1

    print(f"\nDiscovered test directories: {phase_dirs}")
    print("=" * 80)
    print(f" EXECUTING COMPREHENSIVE REGRESSION RUN ACROSS ALL {len(phase_dirs)} PHASES ({phase_dirs[0]} to {phase_dirs[-1]})")
    print("=" * 80)

    start = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(master_suite)
    elapsed = time.perf_counter() - start

    print("=" * 80)
    if result.wasSuccessful():
        print(f" ALL TESTS PASSED: {result.testsRun} tests executed across {total_suites} phases in {elapsed:.3f}s")
        print(" ZERO REGRESSIONS DETECTED.")
        print("=" * 80)
        return 0
    else:
        print(f" REGRESSIONS DETECTED: {len(result.failures)} failures, {len(result.errors)} errors")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(run_all_phases())
