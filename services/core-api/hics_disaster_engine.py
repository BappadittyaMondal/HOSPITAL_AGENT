#!/usr/bin/env python3
"""
Hospital Incident Command System (HICS) & Disaster Surge Engine (Gap 33) (Phase 03).
Enforces:
1. 4-Tier Disaster Escalation protocol.
2. One-click elective surgery cancellation cascade to free operating rooms and anesthesiologists.
3. Automated emergency staff recall broadcast (SMS/Phone blast to off-duty doctors and nurses).
4. Liquid Medical Oxygen (LMO) burn-rate telemetry runway estimator.
"""
import uuid
from typing import Dict, List, Tuple
from datetime import datetime, timezone

class HICSAlertLevel:
    LEVEL_1_ROUTINE = 1
    LEVEL_2_INTERNAL_SURGE = 2
    LEVEL_3_EXTERNAL_DISASTER = 3
    LEVEL_4_CATASTROPHIC_LOCKDOWN = 4

class HICSDisasterEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.current_level = HICSAlertLevel.LEVEL_1_ROUTINE
        self.disaster_log: List[Dict] = []
        self._elective_surgeries: List[Dict] = []
        self._off_duty_staff: List[Dict] = []

    def load_operational_state(self, elective_surgeries: List[Dict], off_duty_staff: List[Dict]):
        self._elective_surgeries = elective_surgeries
        self._off_duty_staff = off_duty_staff

    def activate_disaster_surge(
        self,
        target_level: int,
        incident_type: str, # "MASS_CASUALTY_BUS_CRASH", "INDUSTRIAL_GAS_LEAK", "PANDEMIC_WAVE"
        incident_commander: str
    ) -> Dict:
        """
        Activates HICS Emergency Surge.
        Triggers elective OT cancellation cascade and automated staff recall blasts.
        """
        self.current_level = target_level
        action_id = f"HICS-ACTION-{uuid.uuid4().hex[:8].upper()}"

        cancelled_surgeries = []
        staff_recalled = []

        if target_level >= HICSAlertLevel.LEVEL_3_EXTERNAL_DISASTER:
            # 1. Cancel and postpone elective surgeries
            for s in self._elective_surgeries:
                if s.get("type") == "ELECTIVE":
                    s["status"] = "CANCELLED_DUE_TO_HICS_SURGE"
                    cancelled_surgeries.append(s["surgery_id"])

            # 2. Automated Staff Recall Blast
            for staff in self._off_duty_staff:
                staff_recalled.append({
                    "staff_id": staff["staff_id"],
                    "name": staff["name"],
                    "role": staff["role"],
                    "phone": staff["phone"],
                    "recall_message": (
                        f"CRITICAL HOSPITAL EMERGENCY: HICS Level {target_level} ({incident_type}) activated. "
                        f"All clinical staff required to report to Emergency Operations Center immediately."
                    )
                })

        dossier = {
            "action_id": action_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert_level": target_level,
            "incident_type": incident_type,
            "incident_commander": incident_commander,
            "elective_surgeries_cancelled_count": len(cancelled_surgeries),
            "staff_recall_count": len(staff_recalled),
            "cancelled_surgery_ids": cancelled_surgeries,
            "staff_recalled": staff_recalled
        }
        self.disaster_log.append(dossier)
        return dossier

    def calculate_oxygen_runway_hours(
        self,
        current_liquid_oxygen_liters: float,
        active_ventilators_count: int,
        high_flow_nasal_cannula_count: int,
        ward_low_flow_patients_count: int
    ) -> Dict:
        """
        Calculates remaining oxygen runway hours based on current patient consumption burn-rate.
        Average draw:
        - Ventilator: ~20 Liters/minute
        - High-Flow Nasal Cannula (HFNC): ~50 Liters/minute
        - Low-flow ward mask/cannula: ~6 Liters/minute
        """
        # Gas consumption in gas liters per minute
        burn_rate_gas_lpm = (
            (active_ventilators_count * 20.0) +
            (high_flow_nasal_cannula_count * 50.0) +
            (ward_low_flow_patients_count * 6.0)
        )

        if burn_rate_gas_lpm <= 0:
            return {"runway_hours": 999.0, "status": "NO_ACTIVE_OXYGEN_LOAD"}

        # 1 liter of Liquid Medical Oxygen (LMO) expands to ~860 liters of gas
        total_gas_liters_available = current_liquid_oxygen_liters * 860.0
        runway_minutes = total_gas_liters_available / burn_rate_gas_lpm
        runway_hours = round(runway_minutes / 60.0, 1)

        critical_alert = runway_hours < 24.0 # Less than 24 hours supply remaining

        return {
            "liquid_oxygen_liters_remaining": current_liquid_oxygen_liters,
            "gas_burn_rate_liters_per_min": burn_rate_gas_lpm,
            "estimated_runway_hours": runway_hours,
            "critical_low_oxygen_alarm": critical_alert,
            "action_required": "EMERGENCY_TANKER_DISPATCH_REQUIRED" if critical_alert else "NORMAL_MONITORING"
        }
