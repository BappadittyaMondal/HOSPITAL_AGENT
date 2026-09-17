"""
Test Suite: test_nabh_epidemic_surveillance.py
Phase 14: Resilience & Compliance — NABH Readiness, IDSP Surveillance & Pandemic Surge
Mandates:
  - NABH 5th Edition Accreditation Readiness Engine (10 Core Chapters).
  - Statutory Integrated Disease Surveillance Programme (IDSP) Pincode Cluster Detector (Gap 32).
  - Weekly IDSP Form S (Syndromic), Form P (Presumptive), Form L (Laboratory confirmed) generation.
  - Pandemic Surge Tier 3 (Code Black) Elective Surgery Suspension Cascade (Gap 33).
  - PPE Consumable Burn-Rate and Stock Autonomy Days Calculator.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from nabh_epidemic_surveillance import (
    NABHEpidemicSurveillanceEngine,
    PandemicSurgeTier,
    SurveillanceError,
)


class TestNABHEpidemicSurveillance(unittest.TestCase):

    def setUp(self):
        self.engine = NABHEpidemicSurveillanceEngine()

    def test_nabh_accreditation_readiness_audit(self):
        """Tests NABH 5th Edition hospital readiness audit across 10 chapters."""
        audit = self.engine.generate_nabh_readiness_audit()
        self.assertEqual(audit["standard"], "NABH_5TH_EDITION_HOSPITAL_STANDARDS")
        self.assertEqual(len(audit["chapter_breakdown"]), 10)
        self.assertEqual(audit["overall_readiness_pct"], 100.0)
        self.assertTrue(audit["accreditation_ready"])

        # Update MOM chapter to partial compliance
        self.engine.update_nabh_chapter_compliance("MOM", total_elements=10, compliant_elements=8)
        updated_audit = self.engine.generate_nabh_readiness_audit()
        self.assertEqual(updated_audit["overall_readiness_pct"], 98.0)

    def test_idsp_pincode_cluster_detection_and_weekly_report(self):
        """
        Tests statutory IDSP surveillance:
        Detects outbreak cluster when >= 5 cases occur in the same pincode within 7 days.
        Generates Form S, P, L statutory report.
        """
        now = datetime.now(timezone.utc)
        target_pincode = "700029"  # South Kolkata pincode

        # Record 5 cases of Dengue in pincode 700029
        for i in range(1, 6):
            self.engine.record_disease_case(
                report_id=f"REP-DEN-{i}",
                patient_id=f"PAT-DEN-{i}",
                pincode=target_pincode,
                disease_name="Dengue",
                case_type="L" if i > 2 else "P",  # 2 Presumptive, 3 Lab confirmed (NS1 antigen)
                reported_at=now - timedelta(days=i),
            )

        # Record 2 cases of Cholera in another pincode (below threshold of 5)
        self.engine.record_disease_case("REP-CHOL-1", "PAT-1", "700001", "Cholera", "S", now)
        self.engine.record_disease_case("REP-CHOL-2", "PAT-2", "700001", "Cholera", "S", now)

        # Detect Outbreak Clusters
        clusters = self.engine.detect_pincode_disease_clusters(lookback_days=7)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["alert"], "STATUTORY_EPIDEMIC_OUTBREAK_CLUSTER_DETECTED")
        self.assertEqual(clusters[0]["pincode"], target_pincode)
        self.assertEqual(clusters[0]["disease"], "Dengue")
        self.assertEqual(clusters[0]["cases_in_7_days"], 5)

        # Generate Weekly IDSP Report
        idsp_report = self.engine.generate_weekly_idsp_report(reporting_week_num=38, reporting_year=2026)
        self.assertEqual(idsp_report["reporting_program"], "INTEGRATED_DISEASE_SURVEILLANCE_PROGRAMME_IDSP")
        self.assertEqual(idsp_report["form_l_laboratory_confirmed"]["Dengue"], 3)
        self.assertEqual(idsp_report["form_p_presumptive"]["Dengue"], 2)
        self.assertEqual(idsp_report["form_s_syndromic"]["Cholera"], 2)
        self.assertEqual(idsp_report["total_cases_reported"], 7)

    def test_pandemic_code_black_elective_surgery_suspension(self):
        """
        Tests Pandemic Surge Tier 3 (Code Black):
        Automatically suspends elective surgeries to free up ventilators and beds,
        while strictly preserving emergency trauma/life-saving surgeries.
        """
        now = datetime.now(timezone.utc)

        # Schedule 2 elective and 1 emergency surgery
        self.engine.register_scheduled_surgery(
            surgery_id="SURG-ELEC-01",
            patient_id="PAT-E1",
            procedure_name="Total Knee Arthroplasty",
            is_emergency=False,
            scheduled_date=now + timedelta(days=1),
        )
        self.engine.register_scheduled_surgery(
            surgery_id="SURG-ELEC-02",
            patient_id="PAT-E2",
            procedure_name="Rhinoplasty / Septoplasty",
            is_emergency=False,
            scheduled_date=now + timedelta(days=2),
        )
        self.engine.register_scheduled_surgery(
            surgery_id="SURG-EMERG-03",
            patient_id="PAT-EM1",
            procedure_name="Emergency Craniotomy for Extradural Hematoma",
            is_emergency=True,
            scheduled_date=now,
        )

        # Escalate to Pandemic Tier 3 (Code Black)
        surge_res = self.engine.escalate_pandemic_surge_tier(PandemicSurgeTier.TIER_3_CODE_BLACK)

        self.assertTrue(surge_res["is_code_black"])
        self.assertEqual(surge_res["elective_surgeries_suspended_count"], 2)
        self.assertEqual(surge_res["emergency_surgeries_preserved"], 1)

    def test_ppe_burn_rate_and_autonomy_calculator(self):
        """Tests PPE consumable burn rate calculation and autonomy estimation."""
        ppe_data = self.engine.calculate_ppe_burn_rate_and_autonomy(
            active_isolation_patients=40,
            staff_per_shift=30,
            shifts_per_day=3,
            current_n95_stock=3600,
            current_ppe_coverall_stock=1800,
        )

        # Daily N95 burn = (30 * 3 * 2) + (40 * 1) = 180 + 40 = 220 masks/day
        # N95 autonomy = 3600 / 220 = 16.4 days
        self.assertEqual(ppe_data["daily_n95_burn_rate"], 220)
        self.assertEqual(ppe_data["n95_autonomy_days"], 16.4)

        # Daily Coveralls = 30 * 3 * 1.5 = 135 suits/day
        # Coverall autonomy = 1800 / 135 = 13.3 days
        self.assertEqual(ppe_data["daily_coverall_burn_rate"], 135)
        self.assertEqual(ppe_data["coverall_autonomy_days"], 13.3)
        self.assertFalse(ppe_data["is_critically_low_supply"])


if __name__ == "__main__":
    unittest.main()
