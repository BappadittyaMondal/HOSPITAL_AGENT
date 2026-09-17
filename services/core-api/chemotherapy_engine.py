#!/usr/bin/env python3
"""
Medical Oncology & Chemotherapy Subsystem (Gap 3) (Phase 04).
Enforces:
1. Body Surface Area (BSA) calculation (Mosteller and DuBois formulas).
2. Pre-chemotherapy hematologic & organ safety gates (ANC < 1000/µL or Platelets < 50,000/µL blocks infusion).
3. Inviolable Independent Dual-Nurse Sign-off verification for high-alert antineoplastic drugs.
"""
import math
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

def calculate_bsa_mosteller(height_cm: float, weight_kg: float) -> float:
    """Calculates Body Surface Area using Mosteller formula: sqrt((H*W)/3600)."""
    return round(math.sqrt((height_cm * weight_kg) / 3600.0), 2)

def calculate_bsa_dubois(height_cm: float, weight_kg: float) -> float:
    """Calculates Body Surface Area using DuBois & DuBois formula."""
    return round(0.007184 * (height_cm ** 0.725) * (weight_kg ** 0.425), 2)

class ChemotherapySafetyEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._chemo_orders: Dict[str, Dict] = {}

    def evaluate_pre_chemo_lab_thresholds(
        self,
        anc_per_ul: float,       # Absolute Neutrophil Count
        platelets_per_ul: float, # Platelet count
        hemoglobin_g_dl: float,
        serum_creatinine_mg_dl: float
    ) -> Tuple[bool, List[str]]:
        """
        Hard Pre-Chemotherapy Lab Safety Thresholds:
        Blocks chemotherapy if ANC < 1000/µL (neutropenic sepsis) or Platelets < 50,000/µL (fatal bleed).
        """
        blocks = []
        if anc_per_ul < 1000.0:
            blocks.append(f"PRE-CHEMO HARD STOP: Severe Neutropenia (ANC {anc_per_ul}/µL < 1000/µL). Infusion blocked due to septic mortality risk.")

        if platelets_per_ul < 50000.0:
            blocks.append(f"PRE-CHEMO HARD STOP: Severe Thrombocytopenia (Platelets {platelets_per_ul}/µL < 50,000/µL). Infusion blocked due to intracranial hemorrhage risk.")

        if serum_creatinine_mg_dl > 2.0:
            blocks.append(f"RENAL WARNING: Serum Creatinine {serum_creatinine_mg_dl} mg/dL elevated. Oncologist review required for platinum dose reduction.")

        is_safe = len(blocks) == 0 or all(not b.startswith("PRE-CHEMO HARD STOP") for b in blocks)
        return is_safe, blocks

    def create_chemotherapy_order(
        self,
        patient_id: str,
        regimen_name: str,
        drug_name: str,
        dose_per_m2: float,
        height_cm: float,
        weight_kg: float,
        prescribing_oncologist_id: str,
        anc_per_ul: Optional[float] = None,
        platelets_per_ul: Optional[float] = None,
        serum_creatinine_mg_dl: Optional[float] = None
    ) -> Dict:
        """Creates a chemotherapy order calculating exact dose based on BSA and validating lab gates."""
        bsa = calculate_bsa_mosteller(height_cm, weight_kg)
        calculated_total_dose = round(dose_per_m2 * bsa, 1)
        order_id = f"CHEMO-ORD-{uuid.uuid4().hex[:8].upper()}"

        dispense_status = "LOCKED_PENDING_DUAL_NURSE_VERIFICATION"
        lab_blocks = []
        if anc_per_ul is not None and platelets_per_ul is not None:
            is_safe, blocks = self.evaluate_pre_chemo_lab_thresholds(
                anc_per_ul=anc_per_ul,
                platelets_per_ul=platelets_per_ul,
                hemoglobin_g_dl=12.0,
                serum_creatinine_mg_dl=serum_creatinine_mg_dl or 1.0
            )
            if not is_safe:
                dispense_status = "BLOCKED_LAB_SAFETY_GATE"
                lab_blocks = blocks

        order = {
            "order_id": order_id,
            "patient_id": patient_id,
            "regimen_name": regimen_name,
            "drug_name": drug_name,
            "dose_per_m2": dose_per_m2,
            "patient_bsa_m2": bsa,
            "calculated_total_dose": calculated_total_dose,
            "prescribing_oncologist_id": prescribing_oncologist_id,
            "nurse_1_signoff": None,
            "nurse_2_signoff": None,
            "dispense_status": dispense_status,
            "lab_blocks": lab_blocks,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._chemo_orders[order_id] = order
        return order

    def signoff_nurse_verification(
        self,
        order_id: str,
        nurse_id: str,
        nurse_role_position: int, # 1 for Prep Nurse, 2 for Independent Checking Nurse
        verified_independent_dose: float
    ) -> Tuple[bool, str]:
        """
        Mandatory Independent Dual-Nurse Verification:
        Both nurses must independently calculate and match the dose.
        """
        order = self._chemo_orders.get(order_id)
        if not order:
            return False, "ORDER_NOT_FOUND"

        if order.get("dispense_status") == "BLOCKED_LAB_SAFETY_GATE":
            return False, "PRE_CHEMO_LAB_DEFICIT: Cannot sign off order blocked by laboratory hematologic safety gate."

        # Check dose match tolerance (within 1%)
        if abs(verified_independent_dose - order["calculated_total_dose"]) > (order["calculated_total_dose"] * 0.01):
            return False, f"VERIFICATION_FAILED: Verified dose {verified_independent_dose}mg does not match calculated dose {order['calculated_total_dose']}mg."

        timestamp = datetime.now(timezone.utc).isoformat()
        if nurse_role_position == 1:
            order["nurse_1_signoff"] = {"nurse_id": nurse_id, "timestamp": timestamp}
            return True, "NURSE_1_VERIFIED: Waiting for independent Nurse 2 second-check."
        elif nurse_role_position == 2:
            if not order["nurse_1_signoff"]:
                return False, "SEQUENCE_ERROR: Nurse 1 preparation check must be completed first."
            if order["nurse_1_signoff"]["nurse_id"] == nurse_id:
                return False, "INDEPENDENT_CHECK_VIOLATION: Nurse 2 must be an INDEPENDENT clinician, not the same nurse!"

            order["nurse_2_signoff"] = {"nurse_id": nurse_id, "timestamp": timestamp}
            order["dispense_status"] = "APPROVED_FOR_BEDSIDE_INFUSION"
            return True, "DUAL_NURSE_VERIFICATION_COMPLETE: Chemotherapy unlocked for infusion."

        return False, "INVALID_NURSE_POSITION"

    def can_infuse(self, order_id: str) -> bool:
        order = self._chemo_orders.get(order_id)
        if not order:
            return False
        return order["dispense_status"] == "APPROVED_FOR_BEDSIDE_INFUSION"
