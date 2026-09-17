"""
PROJECT "HOSPITAL" — PHASE 14: RESILIENCE & COMPLIANCE
Module: nabh_epidemic_surveillance.py
Operational Scope:
  - Sub-task 14.5: NABH 5th Edition Accreditation Readiness Engine (10 Core Chapters)
  - Sub-task 14.6: Statutory Integrated Disease Surveillance Programme (IDSP) Reporting & Pincode Cluster Detector (Gap 32)
  - Weekly IDSP Form S (Syndromic), Form P (Presumptive), Form L (Laboratory Confirmed)
  - Sub-task 14.7: Pandemic Surge Escalation Engine (Gap 33) & Elective Surgery Suspension Cascade
  - PPE Consumable Burn-Rate & Autonomy Calculator
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set


class SurveillanceError(Exception):
    """Base exception for surveillance and epidemic operations."""
    pass


class PandemicSurgeTier(str, Enum):
    TIER_0_ROUTINE = "TIER_0_ROUTINE"
    TIER_1_ADVISORY = "TIER_1_ADVISORY"
    TIER_2_MODERATE_SURGE = "TIER_2_MODERATE_SURGE"
    TIER_3_CODE_BLACK = "TIER_3_CODE_BLACK"  # Full epidemic/pandemic emergency


@dataclass
class NABHChapterScore:
    chapter_code: str       # e.g., "AAC", "COP", "MOM", "HIC", "PSQ"
    chapter_name: str
    total_objective_elements: int
    compliant_elements: int
    readiness_pct: float


@dataclass
class DiseaseCaseReport:
    report_id: str
    patient_id: str
    pincode: str
    syndrome_or_disease: str  # e.g., "Dengue", "Cholera", "Malaria", "COVID-19", "Typhoid"
    case_type: str            # SYNDROMIC (S), PRESUMPTIVE (P), LAB_CONFIRMED (L)
    reported_at: datetime


@dataclass
class ElectiveSurgerySchedule:
    surgery_id: str
    patient_id: str
    procedure_name: str
    is_emergency: bool       # True = Emergency (e.g. Perforation/Trauma), False = Elective (e.g. Cosmetic/Knee)
    scheduled_date: datetime
    status: str = "SCHEDULED"  # SCHEDULED, SUSPENDED_FOR_PANDEMIC, COMPLETED


class NABHEpidemicSurveillanceEngine:
    """
    NABH 5th Edition Accreditation Readiness,
    IDSP Weekly Statutory Disease Surveillance, and Pandemic Surge Escalation Engine.
    """

    # IDSP Outbreak Threshold: 5 cases of the same notifiable condition in the same pincode within 7 days
    OUTBREAK_CLUSTER_THRESHOLD = 5

    NABH_CHAPTERS = {
        "AAC": "Access, Assessment and Continuity of Care",
        "COP": "Care of Patients",
        "MOM": "Management of Medication",
        "PRE": "Patient Rights and Education",
        "HIC": "Hospital Infection Control",
        "PSQ": "Patient Safety and Quality Improvement",
        "ROM": "Responsibilities of Management",
        "FMS": "Facility Management and Safety",
        "HRM": "Human Resource Management",
        "IMS": "Information Management System",
    }

    def __init__(self):
        self._surveillance_cases: List[DiseaseCaseReport] = []
        self._surgeries: Dict[str, ElectiveSurgerySchedule] = {}
        self._current_surge_tier: PandemicSurgeTier = PandemicSurgeTier.TIER_0_ROUTINE
        self._nabh_scores: Dict[str, Dict[str, int]] = {
            code: {"total": 10, "compliant": 10} for code in self.NABH_CHAPTERS
        }

    # =========================================================================
    # 14.5 NABH ACCREDITATION READINESS ENGINE
    # =========================================================================

    def update_nabh_chapter_compliance(self, chapter_code: str, total_elements: int, compliant_elements: int) -> None:
        if chapter_code not in self.NABH_CHAPTERS:
            raise SurveillanceError(f"Unknown NABH chapter {chapter_code}")
        self._nabh_scores[chapter_code] = {"total": total_elements, "compliant": compliant_elements}

    def generate_nabh_readiness_audit(self) -> Dict[str, Any]:
        """Calculates hospital-wide NABH 5th Edition accreditation readiness score."""
        chapter_summaries: List[NABHChapterScore] = []
        grand_total = 0
        grand_compliant = 0

        for code, name in self.NABH_CHAPTERS.items():
            tot = self._nabh_scores[code]["total"]
            comp = self._nabh_scores[code]["compliant"]
            pct = round((comp / tot) * 100.0, 1) if tot > 0 else 0.0
            chapter_summaries.append(NABHChapterScore(
                chapter_code=code,
                chapter_name=name,
                total_objective_elements=tot,
                compliant_elements=comp,
                readiness_pct=pct,
            ))
            grand_total += tot
            grand_compliant += comp

        overall_readiness_pct = round((grand_compliant / grand_total) * 100.0, 1) if grand_total > 0 else 0.0

        return {
            "standard": "NABH_5TH_EDITION_HOSPITAL_STANDARDS",
            "overall_readiness_pct": overall_readiness_pct,
            "accreditation_ready": overall_readiness_pct >= 90.0,
            "chapter_breakdown": [c.__dict__ for c in chapter_summaries],
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # =========================================================================
    # 14.6 IDSP STATUTORY DISEASE SURVEILLANCE & PINCODE CLUSTER DETECTOR
    # =========================================================================

    def record_disease_case(
        self,
        report_id: str,
        patient_id: str,
        pincode: str,
        disease_name: str,
        case_type: str,  # "S", "P", or "L"
        reported_at: Optional[datetime] = None,
    ) -> DiseaseCaseReport:
        """Records syndromic, presumptive, or lab-confirmed notifiable disease case."""
        case = DiseaseCaseReport(
            report_id=report_id,
            patient_id=patient_id,
            pincode=pincode,
            syndrome_or_disease=disease_name,
            case_type=case_type.upper(),
            reported_at=reported_at or datetime.now(timezone.utc),
        )
        self._surveillance_cases.append(case)
        return case

    def detect_pincode_disease_clusters(self, lookback_days: int = 7) -> List[Dict[str, Any]]:
        """
        Detects syndromic disease clusters by geographic postal pincode.
        Alerts state epidemiology unit if >= 5 cases detected within 7 days.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=lookback_days)

        # Group by (pincode, disease)
        clusters: Dict[tuple, int] = {}
        for c in self._surveillance_cases:
            if c.reported_at >= cutoff:
                key = (c.pincode, c.syndrome_or_disease)
                clusters[key] = clusters.get(key, 0) + 1

        outbreak_alerts: List[Dict[str, Any]] = []
        for (pincode, disease), count in clusters.items():
            if count >= self.OUTBREAK_CLUSTER_THRESHOLD:
                outbreak_alerts.append({
                    "alert": "STATUTORY_EPIDEMIC_OUTBREAK_CLUSTER_DETECTED",
                    "pincode": pincode,
                    "disease": disease,
                    "cases_in_7_days": count,
                    "threshold": self.OUTBREAK_CLUSTER_THRESHOLD,
                    "statutory_action": "Notify State IDSP Surveillance Unit & Municipal Health Officer",
                })

        return outbreak_alerts

    def generate_weekly_idsp_report(self, reporting_week_num: int, reporting_year: int) -> Dict[str, Any]:
        """
        Automates weekly statutory IDSP Form S (Syndromic), Form P (Presumptive),
        and Form L (Laboratory confirmed) report for MoHFW.
        """
        form_s_counts: Dict[str, int] = {}
        form_p_counts: Dict[str, int] = {}
        form_l_counts: Dict[str, int] = {}

        for c in self._surveillance_cases:
            d = c.syndrome_or_disease
            if c.case_type == "S":
                form_s_counts[d] = form_s_counts.get(d, 0) + 1
            elif c.case_type == "P":
                form_p_counts[d] = form_p_counts.get(d, 0) + 1
            elif c.case_type == "L":
                form_l_counts[d] = form_l_counts.get(d, 0) + 1

        return {
            "reporting_program": "INTEGRATED_DISEASE_SURVEILLANCE_PROGRAMME_IDSP",
            "reporting_week": reporting_week_num,
            "reporting_year": reporting_year,
            "form_s_syndromic": form_s_counts,
            "form_p_presumptive": form_p_counts,
            "form_l_laboratory_confirmed": form_l_counts,
            "total_cases_reported": len(self._surveillance_cases),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # =========================================================================
    # 14.7 PANDEMIC SURGE ESCALATION & PPE BURN-RATE CALCULATOR
    # =========================================================================

    def register_scheduled_surgery(
        self,
        surgery_id: str,
        patient_id: str,
        procedure_name: str,
        is_emergency: bool,
        scheduled_date: datetime,
    ) -> ElectiveSurgerySchedule:
        surgery = ElectiveSurgerySchedule(
            surgery_id=surgery_id,
            patient_id=patient_id,
            procedure_name=procedure_name,
            is_emergency=is_emergency,
            scheduled_date=scheduled_date,
        )
        self._surgeries[surgery_id] = surgery
        return surgery

    def escalate_pandemic_surge_tier(self, target_tier: PandemicSurgeTier) -> Dict[str, Any]:
        """
        Pandemic Surge Escalation Engine.
        If escalating to Tier 3 (Code Black), executes an automated Elective Surgery Cancellation Cascade
        to liberate OT ventilators, anesthesiologists, and recovery beds for acute epidemic patients.
        """
        self._current_surge_tier = target_tier
        suspended_surgeries: List[str] = []

        if target_tier == PandemicSurgeTier.TIER_3_CODE_BLACK:
            for surg in self._surgeries.values():
                # Emergency surgeries (e.g. trauma, intestinal perforation) are NEVER cancelled
                if not surg.is_emergency and surg.status == "SCHEDULED":
                    surg.status = "SUSPENDED_FOR_PANDEMIC"
                    suspended_surgeries.append(surg.surgery_id)

        return {
            "surge_tier": target_tier.value,
            "is_code_black": target_tier == PandemicSurgeTier.TIER_3_CODE_BLACK,
            "elective_surgeries_suspended_count": len(suspended_surgeries),
            "suspended_surgery_ids": suspended_surgeries,
            "emergency_surgeries_preserved": sum(1 for s in self._surgeries.values() if s.is_emergency),
            "escalation_time": datetime.now(timezone.utc).isoformat(),
        }

    def calculate_ppe_burn_rate_and_autonomy(
        self,
        active_isolation_patients: int,
        staff_per_shift: int,
        shifts_per_day: int = 3,
        current_n95_stock: int = 3000,
        current_ppe_coverall_stock: int = 1500,
    ) -> Dict[str, Any]:
        """
        Calculates PPE consumable daily burn rate and inventory autonomy days.
        Formula: Daily N95 = (Staff per shift * Shifts * 2 masks) + (Patients * 1 mask)
        Daily Coveralls = Staff per shift * Shifts * 1.5 suits
        """
        daily_n95_burn = (staff_per_shift * shifts_per_day * 2) + (active_isolation_patients * 1)
        daily_coverall_burn = int(staff_per_shift * shifts_per_day * 1.5)

        n95_days_autonomy = round(current_n95_stock / max(1, daily_n95_burn), 1)
        coverall_days_autonomy = round(current_ppe_coverall_stock / max(1, daily_coverall_burn), 1)

        is_critically_low = min(n95_days_autonomy, coverall_days_autonomy) < 7.0

        return {
            "active_isolation_census": active_isolation_patients,
            "daily_n95_burn_rate": daily_n95_burn,
            "n95_stock_remaining": current_n95_stock,
            "n95_autonomy_days": n95_days_autonomy,
            "daily_coverall_burn_rate": daily_coverall_burn,
            "coverall_stock_remaining": current_ppe_coverall_stock,
            "coverall_autonomy_days": coverall_days_autonomy,
            "is_critically_low_supply": is_critically_low,
        }
