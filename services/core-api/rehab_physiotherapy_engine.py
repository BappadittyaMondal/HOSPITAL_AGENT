"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Module: rehab_physiotherapy_engine.py
Operational Scope:
  - Rehabilitation Treatment Plan & Physical Therapy Progression Tracker (Gap 5)
  - Functional Outcome Instruments: Barthel Index (0-100) Activities of Daily Living
  - Goniometric Joint Range of Motion (ROM) & Visual Analog Scale (VAS) Pain Tracking
  - Cardiac Rehabilitation Protocol Phasing (Phase I Inpatient to Phase III Maintenance)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


@dataclass
class BarthelIndexAssessment:
    assessment_id: str
    patient_id: str
    feeding: int         # 0, 5, 10
    bathing: int         # 0, 5
    grooming: int        # 0, 5
    dressing: int        # 0, 5, 10
    bowels: int          # 0, 5, 10
    bladder: int         # 0, 5, 10
    toilet_use: int      # 0, 5, 10
    transfers: int       # 0, 5, 10, 15
    mobility: int        # 0, 5, 10, 15
    stairs: int          # 0, 5, 10
    total_score: int
    dependency_level: str  # TOTAL_DEPENDENCY, SEVERE, MODERATE, SLIGHT, INDEPENDENT
    assessed_by: str
    assessed_at: str


@dataclass
class RangeOfMotionRecord:
    patient_id: str
    joint_name: str      # e.g., "Right Knee", "Left Shoulder"
    movement: str        # Flexion, Extension, Abduction, Adduction
    active_rom_degrees: float
    passive_rom_degrees: float
    normal_rom_degrees: float
    vas_pain_score: int  # 0 - 10
    assessed_by: str
    assessed_at: str


class RehabPhysiotherapyEngine:
    """
    Physical medicine & rehabilitation operational engine managing ADL outcome metrics,
    goniometric range of motion tracking, and cardiac rehabilitation progression.
    """

    def __init__(self):
        self.barthel_records: List[BarthelIndexAssessment] = []
        self.rom_records: List[RangeOfMotionRecord] = []
        self.cardiac_rehab_plans: Dict[str, Dict[str, Any]] = {}

    def calculate_barthel_index(
        self,
        patient_id: str,
        feeding: int,
        bathing: int,
        grooming: int,
        dressing: int,
        bowels: int,
        bladder: int,
        toilet_use: int,
        transfers: int,
        mobility: int,
        stairs: int,
        therapist_id: str
    ) -> BarthelIndexAssessment:
        """
        Calculates standard Barthel Index of Activities of Daily Living (ADL) (0 - 100).
        """
        total = (feeding + bathing + grooming + dressing + bowels +
                 bladder + toilet_use + transfers + mobility + stairs)

        if total <= 20:
            level = "TOTAL_DEPENDENCY"
        elif total <= 60:
            level = "SEVERE_DEPENDENCY"
        elif total <= 90:
            level = "MODERATE_DEPENDENCY"
        elif total <= 99:
            level = "SLIGHT_DEPENDENCY"
        else:
            level = "INDEPENDENT"

        assessment = BarthelIndexAssessment(
            assessment_id=f"BARTHEL-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            patient_id=patient_id,
            feeding=feeding,
            bathing=bathing,
            grooming=grooming,
            dressing=dressing,
            bowels=bowels,
            bladder=bladder,
            toilet_use=toilet_use,
            transfers=transfers,
            mobility=mobility,
            stairs=stairs,
            total_score=total,
            dependency_level=level,
            assessed_by=therapist_id,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.barthel_records.append(assessment)
        return assessment

    def record_range_of_motion(
        self,
        patient_id: str,
        joint_name: str,
        movement: str,
        active_deg: float,
        passive_deg: float,
        normal_deg: float,
        vas_pain: int,
        therapist_id: str
    ) -> RangeOfMotionRecord:
        """Logs goniometric range of motion measurement and pain score."""
        if not (0 <= vas_pain <= 10):
            raise ValueError("VAS pain score must be between 0 and 10.")

        rec = RangeOfMotionRecord(
            patient_id=patient_id,
            joint_name=joint_name,
            movement=movement,
            active_rom_degrees=active_deg,
            passive_rom_degrees=passive_deg,
            normal_rom_degrees=normal_deg,
            vas_pain_score=vas_pain,
            assessed_by=therapist_id,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.rom_records.append(rec)
        return rec

    def enroll_cardiac_rehab(
        self,
        patient_id: str,
        phase: int,  # 1 = Inpatient, 2 = Monitored Outpatient, 3 = Maintenance
        ejection_fraction_pct: float,
        met_target: float,
        cardiologist_id: str
    ) -> Dict[str, Any]:
        """Enrolls post-MI or post-CABG patient into structured cardiac rehabilitation."""
        plan = {
            "patient_id": patient_id,
            "phase": phase,
            "phase_name": f"PHASE_{phase}_CARDIAC_REHAB",
            "ejection_fraction_pct": ejection_fraction_pct,
            "met_target": met_target,
            "ecg_telemetry_required": phase in (1, 2),
            "cardiologist_id": cardiologist_id,
            "enrolled_at": datetime.now(timezone.utc).isoformat()
        }
        self.cardiac_rehab_plans[patient_id] = plan
        return plan
