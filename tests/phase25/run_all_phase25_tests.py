#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 25 MASTER TEST RUNNER
Runs all Phase 25 route authorization, anti-tenant-tampering, edge fencing, and ABDM AES-GCM encryption test suites.
"""

import sys
import unittest

def run_phase25_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase25", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 25 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 25 Route Auth, Anti-Tenant-Tampering, Edge Fencing & ABDM AES-GCM Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 25 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase25_master_suite())
