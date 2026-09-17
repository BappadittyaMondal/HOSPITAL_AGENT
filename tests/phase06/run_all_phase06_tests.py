"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Master Verification Runner & Quality Gate Certifier
Runs:
  1. test_pharmacy_inventory.py (Formulary, LASA Warnings, FEFO, Cold-Chain, ROP)
  2. test_closed_loop_dispensing.py (Barcode Verification, Expired Batch Hard Stop, ISMP Dual-Check)
  3. test_ndps_narcotics_vault.py (Dual-Biometric Verification, Perpetual Ledger, Hash Chain Integrity)
  4. test_med_reconciliation.py (Care Transitions, Discrepancies, Antibiogram, DDD Metrics)
"""

import unittest
import sys
import time
import os

# Add test directory and service directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from test_pharmacy_inventory import TestPharmacyInventoryEngine
from test_closed_loop_dispensing import TestClosedLoopDispensingEngine
from test_ndps_narcotics_vault import TestNDPSNarcoticsVaultEngine
from test_med_reconciliation import TestMedicationReconciliationEngine


def run_phase06_quality_gate():
    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 06 PHARMACY & MEDICATION SUITES")
    print("=" * 80)

    suites = [
        ("Pharmacy Formulary, LASA Tall Man, FEFO Stock & Cold-Chain", TestPharmacyInventoryEngine),
        ("Closed-Loop Barcode Dispensing, Expired Batch Hard Stop & ISMP Checks", TestClosedLoopDispensingEngine),
        ("NDPS Controlled Substance Vault, Dual-Biometric Sign-off & Perpetual Ledger", TestNDPSNarcoticsVaultEngine),
        ("Medication Reconciliation, Discrepancy Alerts, Antibiogram & DDD Metrics", TestMedicationReconciliationEngine),
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
        print(" [PHASE 06 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All 4 Test Suites Passed with 100% Compliance in {total_elapsed}s")
        print(" Expired Batch Hard Stop Active | Dual-Biometric Vault Enforced | Med Rec Engine Online")
        print("=" * 80 + "\n")
        return 0
    else:
        print(" [PHASE 06 QUALITY GATE CERTIFICATION: FAILED]")
        print(" Critical test failures encountered. Phase 06 cannot be certified.")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase06_quality_gate())
