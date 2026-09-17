"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Module: anesthesia_pacu_engine.py
Operational Scope:
  - Pre-Anesthetic Checkup (PAC) Airway Assessment (Mallampati Class I-IV, ASA Status I-VI)
  - Post-Anesthesia Care Unit (PACU) Modified Aldrete Recovery Scoring
  - Hard Gate: PACU Discharge Blocked Until Aldrete Score >= 9
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class PACUDischargeBlockError(Exception):
    """Raised when a patient is attempted to be discharged from PACU with an Aldrete score < 9."""
    pass


@dataclass
class PACAssessment:
    pac_id: str
    patient_id: str
    asa_class: str          # ASA_I, ASA_II, ASA_III, ASA_IV, ASA_V, ASA_VI
    is_emergency: bool
    mallampati_class: int   # 1, 2, 3, 4
    mouth_opening_cm: float
    thyromental_distance_cm: float
    difficult_airway_predicted: bool
    assessed_by_anesthetist: str
    assessed_at: str


@dataclass
class AldreteScoreRecord:
    assessment_id: str
    patient_id: str
    pacu_bay_id: str
    activity: int          # 0-2
    respiration: int       # 0-2
    circulation: int       # 0-2
    consciousness: int     # 0-2
    o2_saturation: int     # 0-2
    total_score: int
    is_eligible_for_discharge: bool
    assessed_by_nurse_id: str
    assessed_at: str


class AnesthesiaPACUEngine:
    """
    Manages pre-operative anesthesia evaluation and PACU post-op recovery scoring.
    """

    def __init__(self):
        self.pac_records: Dict[str, PACAssessment] = {}
        self.aldrete_records: Dict[str, List[AldreteScoreRecord]] = {}

    def conduct_pac_assessment(
        self,
        patient_id: str,
        asa_class: str,
        is_emergency: bool,
        mallampati_class: int,
        mouth_opening_cm: float,
        thyromental_distance_cm: float,
        anesthetist_id: str
    ) -> PACAssessment:
        """
        Conducts pre-anesthetic checkup.
        Flags difficult airway if Mallampati Class 3 or 4, or thyromental distance < 6.0 cm,
        or mouth opening < 3.0 cm.
        """
        difficult_airway = (
            (mallampati_class >= 3) or
            (thyromental_distance_cm < 6.0) or
            (mouth_opening_cm < 3.0)
        )

        record = PACAssessment(
            pac_id=f"PAC-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            patient_id=patient_id,
            asa_class=asa_class,
            is_emergency=is_emergency,
            mallampati_class=mallampati_class,
            mouth_opening_cm=mouth_opening_cm,
            thyromental_distance_cm=thyromental_distance_cm,
            difficult_airway_predicted=difficult_airway,
            assessed_by_anesthetist=anesthetist_id,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.pac_records[patient_id] = record
        return record

    def evaluate_aldrete_score(
        self,
        patient_id: str,
        pacu_bay_id: str,
        activity: int,
        respiration: int,
        circulation: int,
        consciousness: int,
        o2_saturation: int,
        nurse_id: str
    ) -> AldreteScoreRecord:
        """
        Modified Aldrete Scoring System for post-anesthesia recovery:
        Requires total score >= 9 for ward transfer.
        """
        for param, val in [("Activity", activity), ("Respiration", respiration),
                           ("Circulation", circulation), ("Consciousness", consciousness),
                           ("O2 Saturation", o2_saturation)]:
            if val not in (0, 1, 2):
                raise ValueError(f"Aldrete parameter '{param}' must be 0, 1, or 2.")

        total = activity + respiration + circulation + consciousness + o2_saturation
        eligible = total >= 9

        record = AldreteScoreRecord(
            assessment_id=f"ALDRETE-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            patient_id=patient_id,
            pacu_bay_id=pacu_bay_id,
            activity=activity,
            respiration=respiration,
            circulation=circulation,
            consciousness=consciousness,
            o2_saturation=o2_saturation,
            total_score=total,
            is_eligible_for_discharge=eligible,
            assessed_by_nurse_id=nurse_id,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.aldrete_records.setdefault(patient_id, []).append(record)
        return record

    def authorize_pacu_discharge_to_ward(self, patient_id: str, authorizing_anesthetist_id: str) -> Dict[str, Any]:
        """
        Hard rule: Authorizing discharge to surgical ward requires latest Aldrete Score >= 9.
        """
        records = self.aldrete_records.get(patient_id, [])
        if not records:
            raise PACUDischargeBlockError(f"No Aldrete recovery score recorded for patient {patient_id}.")

        latest = records[-1]
        if not latest.is_eligible_for_discharge:
            raise PACUDischargeBlockError(
                f"DISCHARGE TO WARD BLOCKED: Patient {patient_id} has an Aldrete Score of {latest.total_score}/10 "
                f"(Minimum 9 required). Patient still exhibits post-anesthetic depression."
            )

        return {
            "patient_id": patient_id,
            "aldrete_score": latest.total_score,
            "discharged_to_ward": True,
            "authorizing_anesthetist_id": authorizing_anesthetist_id,
            "authorized_at": datetime.now(timezone.utc).isoformat()
        }
