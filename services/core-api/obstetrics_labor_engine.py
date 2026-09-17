"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Module: obstetrics_labor_engine.py
Operational Scope:
  - Antenatal Care (ANC) Serial Visit Tracker & High-Risk Pregnancy Stratification
  - Digital WHO Partograph with Alert & Action Line Real-Time Tracking
  - Quality Gate 1: Cervical Dilatation Crossing Action Line Triggers High-Priority Obstetric Alert
  - Category 1 Emergency C-Section Decision-to-Delivery Interval (DDI) Countdown (< 30 min)
  - Postpartum Hemorrhage (PPH) Rapid Escalation (Tone, Tissue, Trauma, Thrombin) (Gap 2)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any


class ObstetricSafetyError(Exception):
    """Base exception for obstetric safety alerts."""
    pass


class PartographActionLineBreachError(ObstetricSafetyError):
    """Raised when labor progression crosses the WHO Partograph Action Line."""
    pass


@dataclass
class PartographEntry:
    entry_id: str
    patient_id: str
    hours_in_active_labor: float
    cervical_dilatation_cm: float  # 4 to 10 cm
    fetal_heart_rate_bpm: float    # Normal: 110-160 bpm
    contractions_per_10min: int
    amniotic_fluid_state: str      # INTACT, CLEAR, MECONIUM_STAINED, BLOOD_STAINED
    recorded_at: str
    alert_line_dilatation_cm: float
    action_line_dilatation_cm: float
    action_line_breached: bool
    alert_line_breached: bool


@dataclass
class EmergencyCSectionDDI:
    case_id: str
    patient_id: str
    category: int                  # 1 = Immediate life threat (DDI < 30 min), 2 = Maternal/fetal compromise, 3 = No compromise
    decision_time: datetime
    target_delivery_time: datetime
    actual_delivery_time: Optional[datetime] = None
    target_ddi_minutes: float = 30.0
    actual_ddi_minutes: Optional[float] = None
    indication: str = ""
    is_breached: bool = False


class ObstetricsLaborEngine:
    """
    Labor ward and obstetrics clinical safety engine managing digital partographs,
    prolonged labor alerts, and emergency C-section DDI countdowns.
    """

    def __init__(self):
        # patient_id -> list of PartographEntry
        self.partographs: Dict[str, List[PartographEntry]] = {}
        self.csection_cases: Dict[str, EmergencyCSectionDDI] = {}

    def log_partograph_progress(
        self,
        patient_id: str,
        hours_in_active_labor: float,
        cervical_dilatation_cm: float,
        fetal_heart_rate_bpm: float,
        contractions_per_10min: int,
        amniotic_fluid_state: str = "CLEAR",
        recorded_at: Optional[datetime] = None
    ) -> PartographEntry:
        """
        Quality Gate 1:
        Partograph triggers high-priority alert when cervical dilatation crosses the action line.
        WHO Partograph Standard:
        - Active labor begins at 4 cm.
        - Alert line slope: 1 cm/hour dilatation starting at 4 cm at hour 0.
          dilatation_expected = 4.0 + (1.0 * hours_in_active_labor)
        - Action line is parallel to the alert line, shifted 4 hours to the right.
          action_line_threshold = 4.0 + 1.0 * (hours_in_active_labor - 4.0) if hours >= 4 else 4.0
        If measured dilatation is to the right of (below) the action line, it represents prolonged / obstructed labor.
        Specifically, for a given duration T, if cervical dilatation < (Alert - 4cm of expected progress), Action line is breached.
        Equivalently: At hour T, Alert Line expected = 4 + T. Action Line expected = 4 + (T - 4).
        If measured dilatation <= Action Line expected dilatation, labor is severely arrested/obstructed.
        """
        if recorded_at is None:
            recorded_at = datetime.now(timezone.utc)

        # Alert line: 1 cm/hour from 4 cm (e.g., at 0h = 4cm, 4h = 8cm, 6h = 10cm)
        alert_line_expected = min(10.0, 4.0 + hours_in_active_labor)
        # Action line: 4 hours lag behind alert line (starts after 4h)
        # At hour 4, action line is 4cm; at hour 6, action line is 6cm; at hour 8, action line is 8cm
        action_line_expected = min(10.0, max(4.0, 4.0 + (hours_in_active_labor - 4.0))) if hours_in_active_labor >= 4.0 else 0.0

        alert_breached = cervical_dilatation_cm < alert_line_expected
        action_breached = (hours_in_active_labor >= 4.0) and (cervical_dilatation_cm <= action_line_expected)

        entry = PartographEntry(
            entry_id=f"PARTO-{patient_id}-{int(hours_in_active_labor*10)}",
            patient_id=patient_id,
            hours_in_active_labor=hours_in_active_labor,
            cervical_dilatation_cm=cervical_dilatation_cm,
            fetal_heart_rate_bpm=fetal_heart_rate_bpm,
            contractions_per_10min=contractions_per_10min,
            amniotic_fluid_state=amniotic_fluid_state,
            recorded_at=recorded_at.isoformat(),
            alert_line_dilatation_cm=alert_line_expected,
            action_line_dilatation_cm=action_line_expected,
            action_line_breached=action_breached,
            alert_line_breached=alert_breached
        )
        self.partographs.setdefault(patient_id, []).append(entry)

        # Quality Gate 1: Action line breach triggers critical high-priority alert
        if action_breached:
            raise PartographActionLineBreachError(
                f"HIGH-PRIORITY OBSTETRIC ALERT: Cervical dilatation ({cervical_dilatation_cm} cm at {hours_in_active_labor}h) "
                f"has CROSSED THE WHO PARTOGRAPH ACTION LINE (Expected minimum {action_line_expected} cm). "
                f"Arrest of labor / Cephalopelvic Disproportion suspected. Immediate senior obstetrician review & intervention required."
            )

        return entry

    def trigger_category_1_emergency_csection(
        self,
        case_id: str,
        patient_id: str,
        indication: str,
        decision_time: Optional[datetime] = None
    ) -> EmergencyCSectionDDI:
        """
        Triggers statutory Category 1 Emergency C-Section countdown timer (DDI < 30 minutes).
        RCOG / NICE / National health guidelines standard.
        """
        if decision_time is None:
            decision_time = datetime.now(timezone.utc)

        target_time = decision_time + timedelta(minutes=30)
        csec = EmergencyCSectionDDI(
            case_id=case_id,
            patient_id=patient_id,
            category=1,
            decision_time=decision_time,
            target_delivery_time=target_time,
            target_ddi_minutes=30.0,
            indication=indication
        )
        self.csection_cases[case_id] = csec
        return csec

    def record_delivery_time(self, case_id: str, actual_delivery_time: datetime) -> EmergencyCSectionDDI:
        """Records infant delivery time and calculates actual Decision-to-Delivery Interval (DDI)."""
        csec = self.csection_cases.get(case_id)
        if not csec:
            raise ObstetricSafetyError(f"C-Section case {case_id} not found.")

        csec.actual_delivery_time = actual_delivery_time
        ddi_min = (actual_delivery_time - csec.decision_time).total_seconds() / 60.0
        csec.actual_ddi_minutes = round(ddi_min, 1)
        csec.is_breached = ddi_min > csec.target_ddi_minutes
        return csec
