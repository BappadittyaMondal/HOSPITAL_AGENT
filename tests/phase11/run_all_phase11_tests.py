"""
PROJECT "HOSPITAL" — PHASE 11: REVENUE CYCLE
Master Verification Runner & Quality Gate Certifier
Runs:
  1. test_dynamic_billing.py (Tiered Tariff, Pre-Treatment Estimates, 45-min Discharge SLA, Hash Chain)
  2. test_pmjay_nhcx.py (PM-JAY Bundled Packages, Anti-Breakage Consumable Block, NHCX Risk Scan)
  3. test_cost_accounting.py (Departmental Cost Center Ledger, Activity-Based Costing, Balanced P&L)
"""

import unittest
import sys
import time
import os

# Add test directory and service directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from test_dynamic_billing import TestDynamicBillingEngine
from test_pmjay_nhcx import TestPMJAYNHCXEngine
from test_cost_accounting import TestCostAccountingPnLEngine


def run_phase11_quality_gate():
    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 11 REVENUE CYCLE SUITES")
    print("=" * 80)

    suites = [
        ("Dynamic Tiered Billing, Parallel Discharge Settlement (<45m SLA) & Audit Chain", TestDynamicBillingEngine),
        ("Ayushman Bharat PM-JAY Package Engine & NHCX Claim Risk Pre-Screening", TestPMJAYNHCXEngine),
        ("Departmental Cost Accounting, Activity-Based Costing & Balanced P&L Analytics", TestCostAccountingPnLEngine),
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
        print(" [PHASE 11 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All 3 Test Suites Passed with 100% Compliance in {total_elapsed}s")
        print(" Discharge Settlement < 45m | PM-JAY Package Breakage Blocked | P&L Balanced")
        print("=" * 80 + "\n")
        return 0
    else:
        print(" [PHASE 11 QUALITY GATE CERTIFICATION: FAILED]")
        print(" Critical test failures encountered. Phase 11 cannot be certified.")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase11_quality_gate())
