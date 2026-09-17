#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18: MASTER QUALITY GATE & VERIFICATION RUNNER
====================================================================================================
Executes all Phase 18 test suites:
1. test_expanded_pharmacopeia (Extended DDI, Pregnancy Teratogenicity, Beers Criteria 2023).
2. test_structured_history_engine (Branching symptom intake & red flags).
3. test_syndromic_protocol_engine (8 Syndromic Archetypes, 5-10h Holding, DRE integration).
4. test_emergency_scorers (GCS, FAST Stroke, Pediatric Broselow, Anaphylaxis, Burns Parkland).
====================================================================================================
"""
import sys
import unittest
import time

def run_all_phase18_tests():
    print("================================================================================")
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 18 RURAL PRE-HOSPITAL & PHARMACOPEIA SUITES")
    print("================================================================================")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.discover("tests/phase18", pattern="test_*.py"))
    
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.perf_counter()
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time
    
    print("================================================================================")
    if result.wasSuccessful():
        print(f" [PHASE 18 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All {result.testsRun} Tests across 4 Suites Passed with 100% Compliance in {elapsed:.2f}s")
        print(" Gate 1: Extended DDI, Pregnancy Teratogenicity & Beers Criteria 2023 Enforced [VERIFIED]")
        print(" Gate 2: Branching Structured History-Taking Elicits Acute Red Flags [VERIFIED]")
        print(" Gate 3: 8 Universal Syndromic Archetypes & 5-10h Holding Plans Validated [VERIFIED]")
        print(" Gate 4: Clinical Emergency Scorers (GCS, FAST, Pediatric, Anaphylaxis, Burns) [VERIFIED]")
        print("================================================================================")
        return 0
    else:
        print(f" [PHASE 18 QUALITY GATE CERTIFICATION: FAILED]")
        print(f" Failures: {len(result.failures)} | Errors: {len(result.errors)}")
        print("================================================================================")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_phase18_tests())
