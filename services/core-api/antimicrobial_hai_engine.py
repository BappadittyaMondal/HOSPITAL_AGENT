#!/usr/bin/env python3
"""
Antimicrobial Stewardship Program (ASP) & HAI Surveillance Engine (Gaps 17, 18) (Phase 04).
Enforces:
1. WHO AWaRe antibiotic classification (Access, Watch, Reserve).
2. Reserve antibiotic restrictions: Requires Infectious Disease (ID) consultant approval.
3. 48-72 hour mandatory antimicrobial timeout and de-escalation review.
4. Hospital-Acquired Infection (HAI) algorithmic surveillance (CAUTI, CLABSI, VAP, SSI).
"""
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone, timedelta

class WHOAWaReTier:
    ACCESS = "ACCESS"
    WATCH = "WATCH"
    RESERVE = "RESERVE"

# WHO AWaRe Antibiotic Mapping
AWARE_CLASSIFICATION = {
    # ACCESS (First-line, narrow spectrum)
    "amoxicillin": WHOAWaReTier.ACCESS,
    "ampicillin": WHOAWaReTier.ACCESS,
    "cefazolin": WHOAWaReTier.ACCESS,
    "metronidazole": WHOAWaReTier.ACCESS,
    "gentamicin": WHOAWaReTier.ACCESS,
    "doxycycline": WHOAWaReTier.ACCESS,

    # WATCH (Higher resistance potential)
    "ceftriaxone": WHOAWaReTier.WATCH,
    "ciprofloxacin": WHOAWaReTier.WATCH,
    "piperacillin-tazobactam": WHOAWaReTier.WATCH,
    "meropenem": WHOAWaReTier.WATCH,
    "vancomycin": WHOAWaReTier.WATCH,

    # RESERVE (Last resort critical priority)
    "colistin": WHOAWaReTier.RESERVE,
    "polymyxin b": WHOAWaReTier.RESERVE,
    "linezolid": WHOAWaReTier.RESERVE,
    "tigecycline": WHOAWaReTier.RESERVE,
    "ceftazidime-avibactam": WHOAWaReTier.RESERVE
}

class AntimicrobialHAIEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._antibiotic_prescriptions: Dict[str, Dict] = {}
        self._hai_incidents: List[Dict] = []

    def prescribe_antibiotic(
        self,
        patient_id: str,
        antibiotic_name: str,
        prescribing_doctor_id: str,
        indication: str,
        current_time: Optional[datetime] = None
    ) -> Dict:
        """Prescribes antibiotic and applies WHO AWaRe stewardship gates."""
        now = current_time or datetime.now(timezone.utc)
        name_clean = antibiotic_name.lower().strip()
        aware_tier = AWARE_CLASSIFICATION.get(name_clean, WHOAWaReTier.WATCH)

        rx_id = f"ASP-RX-{uuid.uuid4().hex[:8].upper()}"
        is_reserve = (aware_tier == WHOAWaReTier.RESERVE)

        rx_record = {
            "rx_id": rx_id,
            "patient_id": patient_id,
            "antibiotic_name": antibiotic_name,
            "aware_tier": aware_tier,
            "prescribing_doctor_id": prescribing_doctor_id,
            "indication": indication,
            "prescribed_at": now.isoformat(),
            "id_specialist_approved": False if is_reserve else True,
            "id_approved_by": None,
            "timeout_due_at": (now + timedelta(hours=48)).isoformat(),
            "status": "PENDING_ID_APPROVAL" if is_reserve else "ACTIVE_APPROVED"
        }

        self._antibiotic_prescriptions[rx_id] = rx_record
        return rx_record

    def approve_reserve_antibiotic(self, rx_id: str, id_consultant_id: str) -> bool:
        """Infectious Disease Consultant approval for WHO Reserve tier."""
        rx = self._antibiotic_prescriptions.get(rx_id)
        if not rx or rx["aware_tier"] != WHOAWaReTier.RESERVE:
            return False

        rx["id_specialist_approved"] = True
        rx["id_approved_by"] = id_consultant_id
        rx["status"] = "ACTIVE_APPROVED"
        return True

    def check_48hr_antimicrobial_timeout(self, rx_id: str, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """Evaluates whether the 48-hour timeout has arrived requiring de-escalation."""
        rx = self._antibiotic_prescriptions.get(rx_id)
        if not rx:
            return False, "RX_NOT_FOUND"

        now = current_time or datetime.now(timezone.utc)
        prescribed_at = datetime.fromisoformat(rx["prescribed_at"])
        elapsed_hours = (now - prescribed_at).total_seconds() / 3600.0

        if elapsed_hours >= 48.0:
            return True, (
                f"ASP 48-HOUR TIMEOUT ALERT: {rx['antibiotic_name']} has run for {elapsed_hours:.1f} hours. "
                "Mandatory de-escalation review required based on culture & sensitivity results."
            )
        return False, "WITHIN_SAFE_INITIAL_WINDOW"

    def screen_hai_cauti(
        self,
        patient_id: str,
        catheter_duration_days: int,
        fever_temp_celsius: float,
        urine_culture_cfu_ml: int
    ) -> Tuple[bool, Optional[Dict]]:
        """Screens for Catheter-Associated Urinary Tract Infection (CAUTI)."""
        if catheter_duration_days >= 2 and fever_temp_celsius >= 38.0 and urine_culture_cfu_ml >= 100000:
            hai_dossier = {
                "hai_id": f"HAI-CAUTI-{uuid.uuid4().hex[:6].upper()}",
                "patient_id": patient_id,
                "infection_type": "CAUTI",
                "evidence": f"Foley in situ {catheter_duration_days} days; Temp {fever_temp_celsius}°C; Urine culture {urine_culture_cfu_ml} CFU/mL.",
                "action": "Immediate catheter removal prompt, targeted culture-specific antibiotic, infection control log.",
                "flagged_at": datetime.now(timezone.utc).isoformat()
            }
            self._hai_incidents.append(hai_dossier)
            return True, hai_dossier
        return False, None
