"""
Test Suite: test_canonical_e2e_journeys.py
Phase 15: AI Governance, Red-Team, Simulation & Production Release Gate
Mandate / Quality Gate 2:
  - Inviolable Quality Gate 2: All 12 Canonical Patient Journey E2E tests complete
    with 0.00% safety violations.
  - [1] Routine OPD walk-in consult with lab order, prescription, and billing.
  - [2] Emergency Level 1 trauma resuscitation with temporary ID and bypass billing.
  - [3] Pediatric patient with guardian verification and Broselow weight-based dosing.
  - [4] Elderly polypharmacy patient screened against Beers Criteria.
  - [5] Inpatient admission with ward transfer, eMAR administration, and diet order.
  - [6] ICU admission with 1Hz telemetry, sepsis warning, and arterial blood gas.
  - [7] Surgical OT case with WHO checklist, implant UDI scan, and CSSD tray receipt.
  - [8] Chronic disease follow-up with WhatsApp check-in and telemedicine consult.
  - [9] Cashless PM-JAY and TPA insurance patient with parallel pre-discharge.
  - [10] Telemedicine remote consult with restricted e-prescription and payment.
  - [11] Uploaded messy handwritten prescription and external PDF lab OCR ingestion.
  - [12] 72-hour network outage occurring during active emergency surgery.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from canonical_e2e_journeys import (
    CanonicalE2EJourneysEngine,
    JourneyExecutionResult,
)


class TestCanonicalE2EJourneys(unittest.TestCase):

    def setUp(self):
        self.engine = CanonicalE2EJourneysEngine()

    def test_quality_gate_2_all_12_canonical_journeys_zero_safety_violations(self):
        """
        Quality Gate 2:
        Executes all 12 Canonical Patient Journeys.
        Certifies 100% completion with 0.00% safety violations.
        """
        summary = self.engine.execute_all_12_canonical_journeys()

        self.assertEqual(summary["total_canonical_journeys_tested"], 12)
        self.assertEqual(summary["journeys_passed"], 12)
        self.assertEqual(summary["total_safety_violations"], 0)
        self.assertEqual(summary["safety_violation_rate_pct"], 0.00)
        self.assertTrue(summary["canonical_e2e_gate_certified"])

        # Check individual journeys
        journeys = summary["journeys"]
        self.assertEqual(len(journeys), 12)

        # Verify Journey 2: Emergency Trauma
        j2 = next(j for j in journeys if j["journey_id"] == 2)
        self.assertIn("TRAUMA-TEMP", j2["patient_id"])
        self.assertTrue(any("decoupled" in s.lower() for s in j2["safety_checks_verified"]))

        # Verify Journey 7: Surgical OT Safety
        j7 = next(j for j in journeys if j["journey_id"] == 7)
        self.assertTrue(any("sponge count" in s.lower() for s in j7["safety_checks_verified"]))

        # Verify Journey 9: Cashless PM-JAY
        j9 = next(j for j in journeys if j["journey_id"] == 9)
        self.assertTrue(any("breakage barrier" in s.lower() for s in j9["safety_checks_verified"]))

        # Verify Journey 12: 72h Offline Surgery
        j12 = next(j for j in journeys if j["journey_id"] == 12)
        self.assertTrue(any("72h" in s.lower() for s in j12["safety_checks_verified"]))


if __name__ == "__main__":
    unittest.main()
