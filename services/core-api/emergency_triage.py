#!/usr/bin/env python3
"""
Emergency Triage & Financial Decoupling Engine (Phase 03).
Enforces:
1. 5-Level Emergency Severity Index (ESI) triage algorithm.
2. Instant sub-second temporary emergency registration (TEMP-EMR-XXXX).
3. INVIOLABLE FINANCIAL DECOUPLING: Emergency resuscitation, medication, and diagnostics
   proceed immediately with ZERO billing dependency, zero cashier holds, and zero deposit blocks.
"""
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

class ESILevel:
    LEVEL_1_RESUSCITATION = 1  # Immediate life-saving intervention required (cardiac arrest, apnea, severe shock)
    LEVEL_2_EMERGENT = 2       # High risk, confused/lethargic, severe pain/distress, danger vitals
    LEVEL_3_URGENT = 3         # Stable vitals, requires multiple resources (labs + imaging + IV)
    LEVEL_4_LESS_URGENT = 4    # Stable vitals, requires one resource (simple X-ray or stitches)
    LEVEL_5_NON_URGENT = 5     # Requires zero resources (prescription refill, wound dressing check)

class EmergencyTriageEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._emergency_encounters: Dict[str, Dict] = {}

    def calculate_esi(
        self,
        requires_immediate_lifesaving: bool,
        is_high_risk_or_confused_or_severe_pain: bool,
        predicted_resources_count: int,
        danger_zone_vitals: bool = False
    ) -> int:
        """
        Standard 5-level Emergency Severity Index (ESI) triage algorithm.
        """
        # Step A: Immediate life-saving intervention needed?
        if requires_immediate_lifesaving:
            return ESILevel.LEVEL_1_RESUSCITATION

        # Step B: High risk situation, confused/lethargic/disoriented, or severe pain/distress?
        if is_high_risk_or_confused_or_severe_pain:
            return ESILevel.LEVEL_2_EMERGENT

        # Step C: How many different resources are needed?
        if predicted_resources_count == 0:
            return ESILevel.LEVEL_5_NON_URGENT
        elif predicted_resources_count == 1:
            return ESILevel.LEVEL_4_LESS_URGENT
        else: # 2 or more resources
            # Step D: Check danger zone vital signs (HR, RR, SpO2)
            if danger_zone_vitals:
                return ESILevel.LEVEL_2_EMERGENT
            return ESILevel.LEVEL_3_URGENT

    def fast_register_emergency_patient(
        self,
        esi_level: int,
        chief_complaint: str,
        provisional_name: Optional[str] = None,
        estimated_age: Optional[int] = None,
        gender: Optional[str] = "UNKNOWN"
    ) -> Dict:
        """
        One-click instant emergency registration (< 1 second).
        Creates temporary MRN and immediately routes to resuscitation / acute bay.
        """
        now = datetime.now(timezone.utc)
        temp_mrn = f"TEMP-EMR-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        encounter_id = str(uuid.uuid4())

        destination_bay = "RESUSCITATION_BAY_1" if esi_level == 1 else ("ACUTE_CARE_BAY" if esi_level == 2 else "URGENT_CARE_CHAMBER")

        encounter = {
            "encounter_id": encounter_id,
            "tenant_id": self.tenant_id,
            "temp_mrn": temp_mrn,
            "patient_name": provisional_name or "UNIDENTIFIED_TRAUMA_PATIENT",
            "estimated_age": estimated_age or 35,
            "gender": gender,
            "encounter_type": "EMERGENCY",
            "acuity_level": esi_level,
            "chief_complaint": chief_complaint,
            "assigned_bay": destination_bay,
            "financial_status": "UNBILLED_EMERGENCY_OVERRIDE",
            "clinical_orders": [],
            "arrived_at": now.isoformat()
        }

        self._emergency_encounters[encounter_id] = encounter
        return encounter

    def execute_clinical_order_with_financial_decoupling(
        self,
        encounter_id: str,
        order_item: Dict,
        clinician_id: str
    ) -> Tuple[bool, str, Dict]:
        """
        INVIOLABLE SAFETY GATE:
        Mechanically decouples emergency clinical care from billing/cashier requirements.
        Orders are 100% executed immediately regardless of payment or insurance status.
        """
        encounter = self._emergency_encounters.get(encounter_id)
        if not encounter:
            return False, "ENCOUNTER_NOT_FOUND", {}

        order_id = str(uuid.uuid4())
        executed_order = {
            "order_id": order_id,
            "encounter_id": encounter_id,
            "item_name": order_item.get("name"),
            "order_type": order_item.get("type"), # e.g. "RESUSCITATION_MED", "BLOOD_PRODUCT", "STAT_LAB"
            "ordered_by_clinician_id": clinician_id,
            "clinical_execution_status": "EXECUTED_IMMEDIATELY",
            "billing_decoupled": True,
            "billing_comment": "Emergency clinical priority: Invoiced asynchronously post-stabilization.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        encounter["clinical_orders"].append(executed_order)
        return True, "ORDER_EXECUTED_NO_FINANCIAL_BLOCK", executed_order
