"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Master Verification Runner & Quality Gate Certifier
Runs:
  1. test_icu_telemetry.py (1Hz Telemetry, Collapse Detection < 5s, qSOFA, SIRS)
  2. test_ventilator_abg.py (RSBI Weaning Evaluator, Automated ABG Interpreter, Berlin ARDS)
  3. test_nicu_pediatric.py (Gram-Based Dosing, 10x Overdose Hard Block, Incubator Telemetry)
  4. test_dialysis_unit.py (HBsAg/HCV Isolation Gate, RO Water Safety, CRRT KDIGO Dose)
"""

import unittest
import sys
import time
import os

# Add test directory and service directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from test_icu_telemetry import TestICUTelemetrySepsisEngine
from test_ventilator_abg import TestVentilatorABGEngine
from test_nicu_pediatric import TestNICUPediatricEngine
from test_dialysis_unit import TestDialysisUnitEngine


def run_phase08_quality_gate():
    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 08 CRITICAL CARE SUITES")
    print("=" * 80)

    suites = [
        ("ICU Telemetry, Acute Hemodynamic Collapse (<5s SLA) & Sepsis EWS", TestICUTelemetrySepsisEngine),
        ("Mechanical Ventilation RSBI Weaning & Automated ABG Diagnostic Interpreter", TestVentilatorABGEngine),
        ("NICU Precision Gram Dosing, 10x Overdose Barrier & Incubator Telemetry", TestNICUPediatricEngine),
        ("Dialysis Machine Allocation, Viral Hepatitis Isolation & RO Water Quality", TestDialysisUnitEngine),
    ]

    total_start = time.time()
    all_passed = True

    for name, test_case in suites:
        print(f"\n>>> RUNNING SUITE: {name} ...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
        start = time.time()
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)
        elapsed = round(time.time() - start, 2)

        if result.wasSuccessful():
            print(f"    RESULT: PASSED in {elapsed}s")
        else:
            print(f"    RESULT: FAILED in {elapsed}s with {len(result.failures)} failures and {len(result.errors)} errors")
            all_passed = False

    total_elapsed = round(time.time() - total_start, 2)
    print("\n" + "=" * 80)
    if all_passed:
        print(" [PHASE 08 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All 4 Test Suites Passed with 100% Compliance in {total_elapsed}s")
        print(" Bedside STAT Alert < 5s | HepB Dialysis Isolated | Neonatal 10x Overdose Blocked")
        print("=" * 80 + "\n")
        return 0
    else:
        print(" [PHASE 08 QUALITY GATE CERTIFICATION: FAILED]")
        print(" Critical test failures encountered. Phase 08 cannot be certified.")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase08_quality_gate())
