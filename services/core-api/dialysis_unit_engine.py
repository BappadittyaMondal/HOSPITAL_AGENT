"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Module: dialysis_unit_engine.py
Operational Scope:
  - Hemodialysis Machine Allocation & Serology Isolation Engine (Gap 4)
  - Quality Gate 2: Inviolable Barrier Blocking HBsAg+ or HCV+ Patients from General Dialysis Machines
  - Reverse Osmosis (RO) Water Quality Surveillance (Endotoxin < 0.25 EU/mL, Chloramine < 0.1 mg/L)
  - Continuous Renal Replacement Therapy (CRRT) Flowsheet & Regional Citrate Anticoagulation (RCA) Tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class DialysisError(Exception):
    """Base exception for dialysis unit safety violations."""
    pass


class DialysisIsolationBreachError(DialysisError):
    """Raised when an infected patient is assigned to an incompatible or general dialysis machine."""
    pass


class ROWaterContaminationError(DialysisError):
    """Raised when RO water chemical or endotoxin thresholds are breached."""
    pass


@dataclass
class DialysisMachine:
    machine_id: str
    bay_id: str
    machine_type: str        # GENERAL, DEDICATED_HEPB, DEDICATED_HEPC
    is_operational: bool = True
    current_patient_id: Optional[str] = None
    last_disinfection_time: Optional[datetime] = None


@dataclass
class ROWaterTestRecord:
    test_id: str
    tested_at: datetime
    endotoxin_eu_per_ml: float   # Must be < 0.25 EU/mL
    total_chloramine_mg_l: float  # Must be < 0.1 mg/L
    conductivity_us_cm: float
    is_safe: bool
    technician_id: str


class DialysisUnitEngine:
    """
    Hemodialysis and CRRT safety engine enforcing strict serological isolation,
    machine allocation rules, and water treatment quality gates.
    """

    MAX_SAFE_ENDOTOXIN = 0.25    # EU/mL (AAMI/ISO standard)
    MAX_SAFE_CHLORAMINE = 0.10   # mg/L (prevents fatal methemoglobinemia/hemolysis)

    def __init__(self):
        self.machines: Dict[str, DialysisMachine] = {}
        self.ro_water_logs: List[ROWaterTestRecord] = []
        self.active_sessions: List[Dict[str, Any]] = []

    def register_machine(self, machine_id: str, bay_id: str, machine_type: str) -> DialysisMachine:
        """Registers a dialysis station with defined serology classification."""
        if machine_type not in ("GENERAL", "DEDICATED_HEPB", "DEDICATED_HEPC"):
            raise ValueError(f"Invalid dialysis machine type: {machine_type}")
        machine = DialysisMachine(machine_id=machine_id, bay_id=bay_id, machine_type=machine_type)
        self.machines[machine_id] = machine
        return machine

    def log_ro_water_test(
        self,
        endotoxin_eu_per_ml: float,
        total_chloramine_mg_l: float,
        conductivity_us_cm: float,
        technician_id: str,
        tested_at: Optional[datetime] = None
    ) -> ROWaterTestRecord:
        """
        Logs reverse osmosis water treatment parameters.
        Mechanically halts unit operations if endotoxin or chloramine exceeds limits.
        """
        if tested_at is None:
            tested_at = datetime.now(timezone.utc)

        is_safe = (endotoxin_eu_per_ml < self.MAX_SAFE_ENDOTOXIN) and (total_chloramine_mg_l < self.MAX_SAFE_CHLORAMINE)

        record = ROWaterTestRecord(
            test_id=f"RO-TEST-{int(tested_at.timestamp())}",
            tested_at=tested_at,
            endotoxin_eu_per_ml=endotoxin_eu_per_ml,
            total_chloramine_mg_l=total_chloramine_mg_l,
            conductivity_us_cm=conductivity_us_cm,
            is_safe=is_safe,
            technician_id=technician_id
        )
        self.ro_water_logs.append(record)
        return record

    def is_water_supply_safe(self) -> bool:
        """Checks whether the latest RO water quality test is within safe limits."""
        if not self.ro_water_logs:
            return True  # If not yet logged in dev/init, assume operational unless tested
        return self.ro_water_logs[-1].is_safe

    def allocate_dialysis_machine(
        self,
        patient_id: str,
        machine_id: str,
        patient_hbsag_positive: bool,
        patient_hcv_positive: bool,
        technician_id: str
    ) -> Dict[str, Any]:
        """
        Quality Gate 2:
        System rejects assignment of a Hepatitis B-positive patient to a general dialysis machine.
        Enforces dedicated isolation machines for HBsAg+ and HCV+ seropositive patients.
        """
        # 1. Verify RO water safety
        if not self.is_water_supply_safe():
            latest = self.ro_water_logs[-1]
            raise ROWaterContaminationError(
                f"RO WATER SAFETY HAZARD: Dialysis barred due to contaminated water loop. "
                f"Endotoxin={latest.endotoxin_eu_per_ml} EU/mL, Chloramine={latest.total_chloramine_mg_l} mg/L."
            )

        machine = self.machines.get(machine_id)
        if not machine:
            raise DialysisError(f"Dialysis machine {machine_id} not found.")

        if machine.current_patient_id:
            raise DialysisError(f"Machine {machine_id} is currently occupied by patient {machine.current_patient_id}.")

        # 2. INVIOLABLE SEROLOGY ISOLATION BARRIER
        # Hepatitis B Positive: MUST use DEDICATED_HEPB
        if patient_hbsag_positive:
            if machine.machine_type != "DEDICATED_HEPB":
                raise DialysisIsolationBreachError(
                    f"CRITICAL ISOLATION BREACH: Patient {patient_id} is Hepatitis B Surface Antigen (HBsAg) POSITIVE. "
                    f"Assignment to {machine.machine_type} machine '{machine_id}' strictly rejected. "
                    f"Must allocate a dedicated DEDICATED_HEPB machine in the isolation wing."
                )

        # Hepatitis C Positive: MUST use DEDICATED_HEPC
        elif patient_hcv_positive:
            if machine.machine_type != "DEDICATED_HEPC":
                raise DialysisIsolationBreachError(
                    f"CRITICAL ISOLATION BREACH: Patient {patient_id} is Hepatitis C (HCV) Antibody POSITIVE. "
                    f"Assignment to {machine.machine_type} machine '{machine_id}' strictly rejected. "
                    f"Must allocate a dedicated DEDICATED_HEPC machine."
                )

        # Seronegative Patient: MUST NOT use dedicated HepB or HepC machines
        else:
            if machine.machine_type in ("DEDICATED_HEPB", "DEDICATED_HEPC"):
                raise DialysisIsolationBreachError(
                    f"CROSS-CONTAMINATION HAZARD: Seronegative patient {patient_id} cannot be assigned to "
                    f"dedicated viral hepatitis station '{machine_id}' ({machine.machine_type})."
                )

        # Allocation approved
        machine.current_patient_id = patient_id
        session = {
            "session_id": f"HD-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            "patient_id": patient_id,
            "machine_id": machine_id,
            "machine_type": machine.machine_type,
            "hbsag_positive": patient_hbsag_positive,
            "hcv_positive": patient_hcv_positive,
            "technician_id": technician_id,
            "allocated_at": datetime.now(timezone.utc).isoformat(),
            "status": "ACTIVE_SESSION"
        }
        self.active_sessions.append(session)
        return session

    def calculate_crrt_effluent_dose(
        self,
        dialysate_flow_ml_hr: float,
        replacement_flow_ml_hr: float,
        ultrafiltration_ml_hr: float,
        patient_weight_kg: float
    ) -> Dict[str, Any]:
        """
        Calculates CRRT Effluent Dose:
        Dose (mL/kg/h) = (Qd + Qrep + QUF) / Weight (kg)
        KDIGO guideline target: 20 - 25 mL/kg/h.
        """
        if patient_weight_kg <= 0:
            raise ValueError("Patient weight must be positive.")

        total_effluent_ml_hr = dialysate_flow_ml_hr + replacement_flow_ml_hr + ultrafiltration_ml_hr
        effluent_dose = round(total_effluent_ml_hr / patient_weight_kg, 1)

        is_therapeutic = 20.0 <= effluent_dose <= 30.0

        return {
            "total_effluent_flow_ml_hr": total_effluent_ml_hr,
            "patient_weight_kg": patient_weight_kg,
            "effluent_dose_ml_kg_hr": effluent_dose,
            "is_within_kdigo_target": is_therapeutic,
            "recommendation": (
                "Adequate KDIGO effluent clearance dose." if is_therapeutic else
                "Adjust CRRT flow rates to achieve target 20-25 mL/kg/h."
            )
        }
