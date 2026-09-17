"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Master Verification Runner & Quality Gate Certifier
Runs:
  1. test_obstetrics_labor.py (Partograph Action Line Alert, Category 1 C-Section DDI)
  2. test_psychiatry_mhca.py (MHCA Involuntary Admission, 72h Review Board Dossier, Sec 23 Privacy)
  3. test_oncology_daycare.py (Pre-Chemotherapy ANC/Platelet Halts, Extravasation Antidotes)
  4. test_rehab_physiotherapy.py (Barthel Index ADL, Goniometric ROM, Cardiac Rehab)
"""

import unittest
import sys
import time
import os

# Add test directory and service directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from test_obstetrics_labor import TestObstetricsLaborEngine
from test_psychiatry_mhca import TestPsychiatryMHCAEngine
from test_oncology_daycare import TestOncologyDayCareEngine
from test_rehab_physiotherapy import TestRehabPhysiotherapyEngine


def run_phase10_quality_gate():
    print("=" * 80)
    print(" [MASTER QUALITY GATE] EXECUTING ALL PHASE 10 SPECIALTY DEPARTMENTS SUITES")
    print("=" * 80)

    suites = [
        ("Obstetrics Labor Ward, WHO Partograph Action Line & DDI Countdown", TestObstetricsLaborEngine),
        ("Psychiatry MHCA 2017 Compliance, Involuntary Admission & Privacy Gates", TestPsychiatryMHCAEngine),
        ("Medical Oncology Day Care, Pre-Chemo Lab Gates & Extravasation Protocols", TestOncologyDayCareEngine),
        ("Rehabilitation & Physical Medicine, Barthel Index & Functional Outcomes", TestRehabPhysiotherapyEngine),
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
        print(" [PHASE 10 QUALITY GATE CERTIFICATION: PASSED]")
        print(f" All 4 Test Suites Passed with 100% Compliance in {total_elapsed}s")
        print(" Partograph Alert Active | MHCA 72h Dossier Enforced | Chemo Lab Gate Halts Low ANC")
        print("=" * 80 + "\n")
        return 0
    else:
        print(" [PHASE 10 QUALITY GATE CERTIFICATION: FAILED]")
        print(" Critical test failures encountered. Phase 10 cannot be certified.")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_phase10_quality_gate())
