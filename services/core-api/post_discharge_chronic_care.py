"""
PROJECT "HOSPITAL" — PHASE 13: PATIENT EXPERIENCE
Module: post_discharge_chronic_care.py
Operational Scope:
  - Sub-task 13.3: Automated Post-Discharge Follow-Up & WhatsApp Symptom Bot
  - Quality Gate 3: Red-Flag Symptom ("Worse Fever", "Severe Pain") Triggering Immediate Nurse Callback Task
  - Sub-task 13.4: Longitudinal Chronic Disease Self-Management Pathways (Diabetes, HTN, Heart Failure, COPD)
  - Periodic Lab (HbA1c, Lipids) & Clinical Follow-up Automated Reminder Engine
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set


class FollowUpError(Exception):
    """Base exception for post-discharge follow-up operations."""
    pass


class TriageSeverity(str, Enum):
    RED_FLAG_EMERGENCY = "RED_FLAG_EMERGENCY"  # Immediate nurse/physician callback
    MODERATE_WARNING = "MODERATE_WARNING"      # Routine review within 24h
    NORMAL_RECOVERY = "NORMAL_RECOVERY"        # No acute action required


class ChronicPathwayType(str, Enum):
    DIABETES_T2 = "DIABETES_T2"
    HYPERTENSION = "HYPERTENSION"
    HEART_FAILURE = "HEART_FAILURE"
    COPD = "COPD"


@dataclass
class PostDischargeEncounter:
    encounter_id: str
    patient_id: str
    patient_name: str
    phone_number: str
    discharging_ward: str
    discharge_date: datetime
    primary_diagnosis: str
    checkin_day2_due: datetime
    checkin_day5_due: datetime
    day2_completed: bool = False
    day5_completed: bool = False


@dataclass
class NurseCallbackTask:
    task_id: str
    patient_id: str
    patient_name: str
    phone_number: str
    ward_id: str
    reported_symptom: str
    severity: TriageSeverity
    triggered_at: datetime
    sla_response_minutes: int
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    nurse_notes: str = ""


@dataclass
class ChronicCareEnrollment:
    enrollment_id: str
    patient_id: str
    pathway: ChronicPathwayType
    enrolled_at: datetime
    last_hba1c_date: Optional[datetime] = None
    next_hba1c_due: Optional[datetime] = None
    last_lipid_date: Optional[datetime] = None
    next_lipid_due: Optional[datetime] = None
    baseline_weight_kg: float = 70.0
    active_alerts: List[str] = field(default_factory=list)


class PostDischargeChronicCareEngine:
    """
    Automates interactive WhatsApp follow-up check-ins at Day 2 and Day 5,
    evaluates red-flag triggers to schedule immediate nurse callbacks,
    and manages longitudinal chronic disease pathways.
    """

    # Clinical Red-Flag Trigger Keywords
    RED_FLAG_KEYWORDS = {
        "worse fever", "high fever", "burning fever", "তীব্র জ্বর", "জ্বর বেড়েছে", "तेज बुखार",
        "chest pain", "বুকে ব্যথা", "सीने में दर्द",
        "shortness of breath", "breathing trouble", "শ্বাসকষ্ট", "सांस फूलना",
        "bleeding", "wound oozing", "পুঁজ", "রক্তপাত", "खून बहना",
        "persistent vomiting", "ক্রমাগত বমি", "लगातार उल्टी",
    }

    def __init__(self):
        self._encounters: Dict[str, PostDischargeEncounter] = {}
        self._callback_tasks: Dict[str, NurseCallbackTask] = {}
        self._chronic_enrollments: Dict[str, ChronicCareEnrollment] = {}

    def register_discharge_encounter(
        self,
        encounter_id: str,
        patient_id: str,
        patient_name: str,
        phone_number: str,
        discharging_ward: str,
        primary_diagnosis: str,
        discharge_date: Optional[datetime] = None,
    ) -> PostDischargeEncounter:
        """Registers patient discharge and schedules Day 2 and Day 5 check-ins."""
        d_date = discharge_date or datetime.now(timezone.utc)
        encounter = PostDischargeEncounter(
            encounter_id=encounter_id,
            patient_id=patient_id,
            patient_name=patient_name,
            phone_number=phone_number,
            discharging_ward=discharging_ward,
            discharge_date=d_date,
            primary_diagnosis=primary_diagnosis,
            checkin_day2_due=d_date + timedelta(days=2),
            checkin_day5_due=d_date + timedelta(days=5),
        )
        self._encounters[encounter_id] = encounter
        return encounter

    def process_whatsapp_checkin_response(
        self,
        encounter_id: str,
        checkin_day: int,  # 2 or 5
        patient_response_text: str,
        reported_pain_score_1_to_10: int = 0,
        has_fever: bool = False,
    ) -> Dict[str, Any]:
        """
        Processes inbound WhatsApp interactive check-in bot response.
        Quality Gate 3: If patient indicates "worse fever" or any critical red flag,
        generates an immediate STAT Nurse Callback Task on the discharging ward dashboard.
        """
        if encounter_id not in self._encounters:
            raise FollowUpError(f"Discharge encounter {encounter_id} not found.")

        enc = self._encounters[encounter_id]
        if checkin_day == 2:
            enc.day2_completed = True
        elif checkin_day == 5:
            enc.day5_completed = True

        lower_text = patient_response_text.lower()

        # Check Red Flags
        detected_red_flags = [kw for kw in self.RED_FLAG_KEYWORDS if kw in lower_text]
        if has_fever and ("worse" in lower_text or "increased" in lower_text or "high" in lower_text):
            detected_red_flags.append("worse fever")

        if detected_red_flags or reported_pain_score_1_to_10 >= 8:
            severity = TriageSeverity.RED_FLAG_EMERGENCY
            symptom_summary = ", ".join(detected_red_flags) if detected_red_flags else f"Severe Pain ({reported_pain_score_1_to_10}/10)"

            task_id = f"CALLBACK-{enc.patient_id}-D{checkin_day}-{int(datetime.now(timezone.utc).timestamp())}"
            task = NurseCallbackTask(
                task_id=task_id,
                patient_id=enc.patient_id,
                patient_name=enc.patient_name,
                phone_number=enc.phone_number,
                ward_id=enc.discharging_ward,
                reported_symptom=symptom_summary,
                severity=severity,
                triggered_at=datetime.now(timezone.utc),
                sla_response_minutes=15,  # STAT 15-minute SLA
            )
            self._callback_tasks[task_id] = task

            return {
                "status": "RED_FLAG_TRIGGERED",
                "severity": severity.value,
                "nurse_callback_task_id": task_id,
                "dispatched_to_ward": enc.discharging_ward,
                "sla_minutes": 15,
                "bot_reply": (
                    "We have detected a critical warning symptom. A senior triage nurse from your ward "
                    "has been alerted and will call you immediately within 15 minutes."
                ),
            }

        elif reported_pain_score_1_to_10 >= 4:
            return {
                "status": "MODERATE_SYMPTOM",
                "severity": TriageSeverity.MODERATE_WARNING.value,
                "bot_reply": (
                    "Thank you for your update. Your pain is being monitored. Please take your prescribed "
                    "analgesics as scheduled. If it worsens, notify us immediately."
                ),
            }
        else:
            return {
                "status": "RECOVERING_WELL",
                "severity": TriageSeverity.NORMAL_RECOVERY.value,
                "bot_reply": "Glad to hear you are recovering well! Remember to stay hydrated and complete your medications.",
            }

    def enroll_in_chronic_pathway(
        self,
        enrollment_id: str,
        patient_id: str,
        pathway: ChronicPathwayType,
        baseline_weight_kg: float = 70.0,
    ) -> ChronicCareEnrollment:
        """Enrolls chronic care patient in structured longitudinal pathway."""
        now = datetime.now(timezone.utc)
        enrollment = ChronicCareEnrollment(
            enrollment_id=enrollment_id,
            patient_id=patient_id,
            pathway=pathway,
            enrolled_at=now,
            baseline_weight_kg=baseline_weight_kg,
            next_hba1c_due=now + timedelta(days=90) if pathway == ChronicPathwayType.DIABETES_T2 else None,
            next_lipid_due=now + timedelta(days=180) if pathway in (ChronicPathwayType.DIABETES_T2, ChronicPathwayType.HYPERTENSION) else None,
        )
        self._chronic_enrollments[enrollment_id] = enrollment
        return enrollment

    def log_chronic_telemetry(
        self,
        enrollment_id: str,
        blood_glucose_mg_dl: Optional[float] = None,
        systolic_bp: Optional[int] = None,
        diastolic_bp: Optional[int] = None,
        weight_kg: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Ingests at-home patient telemetry and flags clinical decompensation."""
        if enrollment_id not in self._chronic_enrollments:
            raise FollowUpError(f"Enrollment {enrollment_id} not found.")

        enr = self._chronic_enrollments[enrollment_id]
        alerts: List[str] = []

        # Diabetes checks
        if blood_glucose_mg_dl is not None:
            if blood_glucose_mg_dl < 70.0:
                alerts.append(f"HYPOGLYCEMIA ALERT: Blood glucose {blood_glucose_mg_dl} mg/dL is dangerously low! Take fast-acting carbs.")
            elif blood_glucose_mg_dl > 300.0:
                alerts.append(f"HYPERGLYCEMIA ALERT: Blood glucose {blood_glucose_mg_dl} mg/dL exceeds safety threshold.")

        # Hypertension checks
        if systolic_bp is not None and diastolic_bp is not None:
            if systolic_bp >= 180 or diastolic_bp >= 120:
                alerts.append(f"HYPERTENSIVE CRISIS ALERT: BP {systolic_bp}/{diastolic_bp} mmHg requires emergency medical review.")
            elif systolic_bp >= 140 or diastolic_bp >= 90:
                alerts.append(f"Elevated BP: {systolic_bp}/{diastolic_bp} mmHg.")

        # Heart failure rapid fluid retention check (> 2.0 kg gain above baseline)
        if weight_kg is not None and enr.pathway == ChronicPathwayType.HEART_FAILURE:
            weight_gain = weight_kg - enr.baseline_weight_kg
            if weight_gain >= 2.0:
                alerts.append(f"HEART FAILURE DECOMPENSATION ALERT: Sudden weight gain of {weight_gain:.1f} kg indicates fluid overload!")

        enr.active_alerts = alerts

        return {
            "enrollment_id": enrollment_id,
            "pathway": enr.pathway.value,
            "alerts_triggered": alerts,
            "requires_clinical_intervention": len(alerts) > 0,
        }

    def get_pending_nurse_callbacks(self, ward_id: Optional[str] = None) -> List[NurseCallbackTask]:
        """Returns active nurse callback tasks on the ward dashboard."""
        tasks = [t for t in self._callback_tasks.values() if not t.is_completed]
        if ward_id:
            tasks = [t for t in tasks if t.ward_id == ward_id]
        return tasks
