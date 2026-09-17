"""
Test Suite: test_kitchen_dietary.py
Phase 12: Hospital Operations — Central Kitchen & Dietary Distribution Subsystem
Mandate / Quality Gate 1:
  - Aggregation of clinical ward diet orders into kitchen production batches.
  - Inviolable Quality Gate 1: A patient marked NPO in pre-op is completely excluded
    from meal tray printing/distribution logs, and any attempt to assemble or dispatch
    a meal tray for an NPO patient is mechanically blocked with NPOPatientMealBlockError.
  - Bedside dual-scan barcode verification (wristband MRN vs tray barcode).
  - Allergen safety conflict prevention.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from kitchen_dietary_engine import (
    KitchenDietaryEngine,
    DietType,
    MealSlot,
    TrayStatus,
    NPOPatientMealBlockError,
    DietaryAllergenConflictError,
    BedsideMealMismatchError,
    DietaryError,
)


class TestKitchenDietaryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = KitchenDietaryEngine()

        # Register regular patient
        self.patient_reg = self.engine.register_patient_profile(
            patient_id="PAT-GEN-101",
            mrn="MRN-882101",
            bed_id="BED-WARD-204",
            ward="WARD_5B",
            allergies={"peanuts", "shellfish"},
            is_npo=False,
        )

        # Register pre-op patient scheduled for surgery (Strict NPO)
        self.patient_preop = self.engine.register_patient_profile(
            patient_id="PAT-SURG-202",
            mrn="MRN-994202",
            bed_id="BED-PREOP-03",
            ward="OT_HOLDING",
            is_npo=True,
            npo_reason="Laparoscopic Appendectomy at 08:00 AM",
        )

        # Register diabetic patient
        self.patient_diabetic = self.engine.register_patient_profile(
            patient_id="PAT-ENDO-303",
            mrn="MRN-773303",
            bed_id="BED-MED-108",
            ward="MED_WARD_1",
            is_npo=False,
        )

    def test_quality_gate_1_npo_exclusion_and_mechanical_block(self):
        """
        Quality Gate 1:
        1. Ordering active oral meal for an NPO patient is strictly blocked.
        2. Aggregation excludes NPO patients from kitchen meal counts.
        3. Attempt to assemble/print tray for NPO patient raises NPOPatientMealBlockError.
        """
        # 1. Attempt to place oral diet order for NPO patient raises error
        with self.assertRaises(NPOPatientMealBlockError):
            self.engine.create_diet_order(
                order_id="ORD-NPO-001",
                patient_id="PAT-SURG-202",
                diet_type=DietType.REGULAR,
                meal_slot=MealSlot.BREAKFAST,
                ordered_by_doctor_id="DOC-SURG-01",
            )

        # 2. Place NPO order explicitly
        npo_order = self.engine.create_diet_order(
            order_id="ORD-NPO-002",
            patient_id="PAT-SURG-202",
            diet_type=DietType.NPO,
            meal_slot=MealSlot.BREAKFAST,
            ordered_by_doctor_id="DOC-SURG-01",
        )
        self.assertEqual(npo_order.diet_type, DietType.NPO)

        # Place valid orders for other patients
        self.engine.create_diet_order(
            order_id="ORD-REG-001",
            patient_id="PAT-GEN-101",
            diet_type=DietType.REGULAR,
            meal_slot=MealSlot.BREAKFAST,
            ordered_by_doctor_id="DOC-GEN-02",
        )
        self.engine.create_diet_order(
            order_id="ORD-DIA-001",
            patient_id="PAT-ENDO-303",
            diet_type=DietType.DIABETIC,
            meal_slot=MealSlot.BREAKFAST,
            ordered_by_doctor_id="DOC-ENDO-03",
        )

        # Production aggregation must exclude NPO patient
        production = self.engine.aggregate_kitchen_production(MealSlot.BREAKFAST)
        self.assertEqual(production["total_meals_to_prepare"], 2)
        self.assertEqual(production["diet_breakdown"].get(DietType.REGULAR.value), 1)
        self.assertEqual(production["diet_breakdown"].get(DietType.DIABETIC.value), 1)
        self.assertEqual(production["excluded_npo_patients"], 1)

        # 3. Mechanical block when attempting to assemble meal tray for NPO order
        with self.assertRaises(NPOPatientMealBlockError) as ctx:
            self.engine.assemble_meal_tray(
                tray_barcode="TRAY-NPO-994202-BK",
                order_id="ORD-NPO-002",
                menu_items=["Porridge", "Boiled Egg", "Apple"],
            )
        self.assertIn("CRITICAL SAFETY BLOCK", str(ctx.exception))
        self.assertIn("Laparoscopic Appendectomy", str(ctx.exception))

        # Check audit log records blocked event
        blocked_log = self.engine.get_blocked_npo_audit_log()
        self.assertTrue(len(blocked_log) >= 1)
        self.assertEqual(blocked_log[0]["patient_id"], "PAT-SURG-202")

    def test_allergy_conflict_prevention(self):
        """Tray assembly must be blocked if food items contain patient allergens."""
        order = self.engine.create_diet_order(
            order_id="ORD-REG-101",
            patient_id="PAT-GEN-101",
            diet_type=DietType.REGULAR,
            meal_slot=MealSlot.LUNCH,
            ordered_by_doctor_id="DOC-GEN-02",
        )

        # Attempt to prepare tray containing peanut sauce (patient allergic to peanuts)
        with self.assertRaises(DietaryAllergenConflictError) as ctx:
            self.engine.assemble_meal_tray(
                tray_barcode="TRAY-882101-LUNCH",
                order_id=order.order_id,
                menu_items=["Rice", "Chicken Satay with Peanut Sauce"],
                allergens_in_meal=["peanuts"],
            )
        self.assertIn("peanuts", str(ctx.exception))

    def test_bedside_dual_scan_delivery_workflow(self):
        """Validates bedside nurse dual-barcode scanning ensuring right tray to right patient."""
        order = self.engine.create_diet_order(
            order_id="ORD-DIA-303",
            patient_id="PAT-ENDO-303",
            diet_type=DietType.DIABETIC,
            meal_slot=MealSlot.LUNCH,
            ordered_by_doctor_id="DOC-ENDO-03",
        )

        # Assemble tray
        tray = self.engine.assemble_meal_tray(
            tray_barcode="TRAY-773303-LUNCH",
            order_id=order.order_id,
            menu_items=["Brown Rice", "Dal", "Steamed Vegetables"],
        )
        self.assertEqual(tray.status, TrayStatus.ASSEMBLED)

        # Dispatch tray
        dispatched = self.engine.dispatch_tray_to_ward(tray.tray_barcode)
        self.assertEqual(dispatched.status, TrayStatus.DISPATCHED)

        # 1. Nurse accidentally scans WRONG patient wristband (MRN mismatch)
        with self.assertRaises(BedsideMealMismatchError):
            self.engine.bedside_nurse_delivery_verification(
                scanned_tray_barcode=tray.tray_barcode,
                scanned_patient_wristband_mrn="MRN-882101",  # Wrong MRN
                nurse_id="NURSE-FLOOR-4",
            )

        # 2. Nurse scans correct patient wristband
        delivery = self.engine.bedside_nurse_delivery_verification(
            scanned_tray_barcode=tray.tray_barcode,
            scanned_patient_wristband_mrn="MRN-773303",  # Correct MRN
            nurse_id="NURSE-FLOOR-4",
        )
        self.assertEqual(delivery["status"], "DELIVERY_VERIFIED")
        self.assertEqual(tray.status, TrayStatus.DELIVERED)
        self.assertEqual(tray.verified_by_nurse_id, "NURSE-FLOOR-4")


if __name__ == "__main__":
    unittest.main()
