#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 31 MASTER TEST RUNNER
Runs all Phase 31 Vernacular Clinical Voice-to-FHIR Scribe tests:
- Bengali transcript parsing & red flag detection
- Hindi transcript parsing & symptom extraction
- Standard HL7 FHIR R4 collection bundle generation
"""

import sys
import unittest

def run_phase31_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase31", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 31 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 31 Vernacular Voice-to-FHIR Scribe Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 31 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase31_master_suite())
