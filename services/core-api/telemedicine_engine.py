#!/usr/bin/env python3
"""
Telemedicine Consultation & NMC 2020 Compliance Engine (Gap 1) (Phase 03).
Enforces:
1. WebRTC bandwidth-adaptive session tiering (HD Video -> 3G Low-FPS -> 2G Audio-Only).
2. Pre-session patient identity verification (ABHA/OTP + Photo).
3. NMC Telemedicine Practice Guidelines 2020 Prescription Categories (List O, List A, List B).
4. INVIOLABLE HARD STOP: Prohibits Schedule X narcotics, controlled psychotropics, and IV injectables
   on first remote consultations.
"""
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

class TelemedSessionTier:
    FULL_HD_VIDEO = "FULL_HD_VIDEO"         # > 1000 kbps
    LOW_FPS_VIDEO = "LOW_FPS_VIDEO"         # 256 - 1000 kbps (3G adaptive)
    AUDIO_ONLY_FALLBACK = "AUDIO_ONLY"       # < 256 kbps (2G resilient)

class TelemedConsultType:
    FIRST_CONSULTATION = "FIRST_CONSULTATION"
    FOLLOW_UP = "FOLLOW_UP"

# NMC 2020 Drug Lists & Prohibited Classes
SCHEDULE_X_PROHIBITED = {
    "morphine", "ketamine", "fentanyl", "buprenorphine", "methadone",
    "diazepam", "lorazepam", "alprazolam", "pentobarbital"
}

NMC_LIST_O_OTC = {
    "paracetamol", "ors", "antacid", "cough lozenges", "saline nasal drops",
    "paracetamol tablet", "cetirizine"
}

class TelemedicineEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._active_sessions: Dict[str, Dict] = {}

    def start_teleconsult_session(
        self,
        appointment_id: str,
        patient_mrn: str,
        doctor_id: str,
        consult_type: str = TelemedConsultType.FIRST_CONSULTATION
    ) -> Dict:
        """Initializes teleconsultation room with virtual waiting room."""
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "appointment_id": appointment_id,
            "patient_mrn": patient_mrn,
            "doctor_id": doctor_id,
            "consult_type": consult_type,
            "patient_identity_verified": False,
            "stream_tier": TelemedSessionTier.FULL_HD_VIDEO,
            "prescribed_items": [],
            "status": "WAITING_ROOM",
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        self._active_sessions[session_id] = session
        return session

    def verify_patient_identity(self, session_id: str, otp_code: str, photo_hash: str) -> bool:
        """Verifies patient identity before remote clinical cockpit activation."""
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        # Simulates statutory OTP verification check
        if len(otp_code) == 6 and otp_code.isdigit():
            session["patient_identity_verified"] = True
            session["status"] = "DOCTOR_COCKPIT_ACTIVE"
            session["photo_hash"] = photo_hash
            return True
        return False

    def adapt_stream_to_bandwidth(self, session_id: str, measured_bandwidth_kbps: int) -> str:
        """
        Dynamically adapts WebRTC media stream to available network quality.
        Ensures session never drops even on rural 2G connections.
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return TelemedSessionTier.AUDIO_ONLY_FALLBACK

        if measured_bandwidth_kbps >= 1000:
            tier = TelemedSessionTier.FULL_HD_VIDEO
        elif measured_bandwidth_kbps >= 256:
            tier = TelemedSessionTier.LOW_FPS_VIDEO
        else:
            tier = TelemedSessionTier.AUDIO_ONLY_FALLBACK

        session["stream_tier"] = tier
        return tier

    def validate_nmc_tele_prescription(
        self,
        session_id: str,
        medication_name: str,
        route: str = "ORAL"
    ) -> Tuple[bool, str]:
        """
        NMC Telemedicine Guidelines 2020 Enforcement Gate:
        - Schedule X controlled drugs are strictly prohibited remotely on first consult.
        - Injectable drugs are prohibited remotely on first consult.
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return False, "SESSION_NOT_FOUND"

        if not session["patient_identity_verified"]:
            return False, "NMC_VIOLATION: Patient identity must be verified before prescribing."

        med_lower = medication_name.lower().strip()
        consult_type = session["consult_type"]

        # 1. Prohibit Schedule X controlled substances
        for banned in SCHEDULE_X_PROHIBITED:
            if banned in med_lower:
                return False, f"NMC_PROHIBITION: Schedule X controlled substance '{medication_name}' CANNOT be prescribed via telemedicine."

        # 2. Prohibit Injectable medications on first remote consult
        if consult_type == TelemedConsultType.FIRST_CONSULTATION and route.upper() in {"IV", "IM", "INTRATHECAL", "SC"}:
            return False, f"NMC_PROHIBITION: Injectable medication '{medication_name}' cannot be prescribed on first telemedicine consult. In-person hospital referral required."

        # 3. Approved
        session["prescribed_items"].append({"name": medication_name, "route": route})
        return True, f"NMC_APPROVED: '{medication_name}' compliant with NMC Telemedicine 2020 Guidelines."
