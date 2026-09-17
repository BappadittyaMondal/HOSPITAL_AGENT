"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Module: nurse_staffing_watchdog.py
Operational Scope:
  - Real-Time Nurse-to-Patient Ratio Live Watchdog (Gap 6)
  - Ward Acuity-Based Ratio Benchmarks (ICU 1:1, HDU 1:2, General Ward 1:5)
  - Automated Alert Dispatcher to Chief Nursing Officer (CNO) on Staffing Deficit
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


@dataclass
class WardStaffingSnapshot:
    ward_id: str
    ward_type: str  # ICU, HDU, GENERAL, PEDIATRIC
    active_nurse_count: int
    occupied_bed_count: int
    max_patient_per_nurse_threshold: float
    current_patient_per_nurse_ratio: float
    is_breached: bool
    deficit_nurses: int
    alert_level: str  # NORMAL, WARNING, CRITICAL_DEFICIT


class NurseStaffingWatchdogEngine:
    """
    Live monitoring engine calculating real-time nurse-to-patient staffing ratios,
    detecting understaffing against clinical acuity guidelines, and alerting nursing leadership.
    """

    # Clinical accreditation ratio standards (Maximum patients per 1 nurse)
    ACUITY_RATIO_STANDARDS = {
        "ICU": 1.0,        # 1:1
        "NICU": 1.0,       # 1:1
        "HDU": 2.0,        # 1:2
        "PEDIATRIC": 3.0,  # 1:3
        "GENERAL": 5.0     # 1:5
    }

    def __init__(self):
        self.cno_alerts: List[Dict[str, Any]] = []

    def evaluate_ward_staffing(
        self,
        ward_id: str,
        ward_type: str,
        active_nurse_count: int,
        occupied_bed_count: int
    ) -> WardStaffingSnapshot:
        """
        Evaluates live nurse-to-patient ratio for a ward.
        Dispatches alert if ratio breaches safety thresholds.
        """
        threshold = self.ACUITY_RATIO_STANDARDS.get(ward_type.upper(), 5.0)

        if active_nurse_count <= 0:
            ratio = float(occupied_bed_count) if occupied_bed_count > 0 else 0.0
            is_breached = occupied_bed_count > 0
            deficit = max(1, int(occupied_bed_count / threshold))
            alert_level = "CRITICAL_DEFICIT"
        else:
            ratio = round(occupied_bed_count / active_nurse_count, 2)
            is_breached = ratio > threshold
            # Needed nurses = ceil(occupied_bed_count / threshold) - active_nurse_count
            needed_nurses = int((occupied_bed_count + threshold - 0.001) // threshold)
            deficit = max(0, needed_nurses - active_nurse_count)
            alert_level = "CRITICAL_DEFICIT" if deficit >= 2 else ("WARNING" if is_breached else "NORMAL")

        snapshot = WardStaffingSnapshot(
            ward_id=ward_id,
            ward_type=ward_type,
            active_nurse_count=active_nurse_count,
            occupied_bed_count=occupied_bed_count,
            max_patient_per_nurse_threshold=threshold,
            current_patient_per_nurse_ratio=ratio,
            is_breached=is_breached,
            deficit_nurses=deficit,
            alert_level=alert_level
        )

        if is_breached:
            self._dispatch_cno_alert(snapshot)

        return snapshot

    def _dispatch_cno_alert(self, snapshot: WardStaffingSnapshot):
        now_str = datetime.now(timezone.utc).isoformat()
        alert = {
            "alert_id": f"CNO-RATIO-ALERT-{snapshot.ward_id}-{len(self.cno_alerts)+1}",
            "ward_id": snapshot.ward_id,
            "ward_type": snapshot.ward_type,
            "severity": snapshot.alert_level,
            "message": (
                f"NURSE-PATIENT RATIO BREACH in {snapshot.ward_id} ({snapshot.ward_type}): "
                f"Current ratio is 1:{snapshot.current_patient_per_nurse_ratio} (Standard is 1:{snapshot.max_patient_per_nurse_threshold}). "
                f"Staff deficit: {snapshot.deficit_nurses} nurse(s) urgently required."
            ),
            "timestamp": now_str,
            "recipient": "CHIEF_NURSING_OFFICER"
        }
        self.cno_alerts.append(alert)
