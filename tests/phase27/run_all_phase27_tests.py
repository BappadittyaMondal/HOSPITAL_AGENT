#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 27 MASTER TEST RUNNER
Runs all Phase 27 Pan-Institutional Clinical Knowledge Core (PICK-Core) test suites:
- Guideline Arbitration Engine (AIIMS, CMC Vellore, SSKM, Mayo, Cleveland, Hopkins, NCCN)
- Tropical Syndromic & Vector-Borne Deductive Engine (Platelet/Hematocrit titration, hemoconcentration)
- Hepatobiliary & Solid Tumor Oncology Engine (Child-Pugh, MELD-Na, AJCC TNM Staging)
- Rare Disease Phenotype Engine (Human Phenotype Ontology, multi-system syndrome match)
- Dual-Lens Presentation Agent (Local Actionable NLEM Generics vs Global Reference Benchmarks)
- FastAPI REST Endpoints and Auth & Audit Verification
"""

import sys
import unittest

def run_phase27_master_suite():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/phase27", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*80)
        print(" [PHASE 27 QUALITY GATE CERTIFICATION: PASSED]")
        print(" All Phase 27 Pan-Institutional Clinical Knowledge Core (PICK-Core) Tests Passed.")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print(" [PHASE 27 QUALITY GATE CERTIFICATION: FAILED]")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(run_phase27_master_suite())
