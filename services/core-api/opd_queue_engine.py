#!/usr/bin/env python3
"""
OPD Dynamic Queue & Appointment Orchestration Engine (Phase 03).
Enforces:
1. Real-time token issuance with estimated wait time calculation.
2. Doctor emergency absence / Code Blue queue rebalancing across parallel chambers.
3. Vernacular patient queue anxiety notifications (Bengali, Hindi, English).
"""
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone

class OPDQueueEngine:
    def __init__(self, tenant_id: str, avg_consult_mins: int = 12):
        self.tenant_id = tenant_id
        self.avg_consult_mins = avg_consult_mins
        # Department -> list of doctor_ids
        self._departments: Dict[str, List[str]] = {}
        # doctor_id -> list of tokens
        self._queues: Dict[str, List[Dict]] = {}
        # doctor_id -> metadata
        self._doctors: Dict[str, Dict] = {}

    def register_doctor(self, doctor_id: str, name: str, department: str, chamber_number: str):
        if department not in self._departments:
            self._departments[department] = []
        if doctor_id not in self._departments[department]:
            self._departments[department].append(doctor_id)

        self._doctors[doctor_id] = {
            "doctor_id": doctor_id,
            "name": name,
            "department": department,
            "chamber_number": chamber_number,
            "status": "AVAILABLE" # AVAILABLE, IN_EMERGENCY_SURGERY, OFF_DUTY
        }
        self._queues[doctor_id] = []

    def issue_token(self, doctor_id: str, patient_mrn: str, patient_name: str, language: str = "BENGALI") -> Dict:
        """Issues an OPD token and computes real-time estimated wait time."""
        doctor = self._doctors.get(doctor_id)
        if not doctor:
            raise ValueError(f"Doctor '{doctor_id}' not found")

        queue = self._queues[doctor_id]
        token_number = len(queue) + 1
        patients_ahead = len(queue)
        est_wait_mins = patients_ahead * self.avg_consult_mins

        token = {
            "token_id": str(uuid.uuid4()),
            "token_number": token_number,
            "doctor_id": doctor_id,
            "doctor_name": doctor["name"],
            "chamber_number": doctor["chamber_number"],
            "department": doctor["department"],
            "patient_mrn": patient_mrn,
            "patient_name": patient_name,
            "patients_ahead": patients_ahead,
            "est_wait_mins": est_wait_mins,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "notification_message": self._format_anxiety_message(token_number, patients_ahead, est_wait_mins, language)
        }

        queue.append(token)
        return token

    def _format_anxiety_message(self, token_num: int, ahead: int, wait_mins: int, lang: str) -> str:
        if lang == "BENGALI":
            if ahead == 0:
                return f"টোকেন নং #{token_num}: আপনার পালা এসে গেছে, অনুগ্রহ করে ডাক্তারের চেম্বারে প্রবেশ করুন।"
            return f"টোকেন নং #{token_num}: আপনার আগে {ahead} জন রোগী আছেন। আনুমানিক অপেক্ষা {wait_mins} মিনিট।"
        elif lang == "HINDI":
            if ahead == 0:
                return f"टोकन संख्या #{token_num}: आपकी बारी आ गई है, कृपया डॉक्टर के कक्ष में प्रवेश करें।"
            return f"टोकन संख्या #{token_num}: आपके आगे {ahead} मरीज हैं। अनुमानित प्रतीक्षा {wait_mins} मिनट।"
        else: # English
            if ahead == 0:
                return f"Token #{token_num}: It is your turn. Please enter the doctor's consultation chamber."
            return f"Token #{token_num}: There are {ahead} patients ahead of you. Estimated wait: ~{wait_mins} minutes."

    def rebalance_queue_on_doctor_emergency(self, absent_doctor_id: str) -> List[Dict]:
        """
        Emergency Queue Rebalancing:
        When a doctor is called away to emergency surgery, redistributes waiting patients
        equally across other available doctors in the same department.
        """
        absent_doc = self._doctors.get(absent_doctor_id)
        if not absent_doc:
            return []

        absent_doc["status"] = "IN_EMERGENCY_SURGERY"
        stranded_tokens = self._queues.get(absent_doctor_id, [])
        self._queues[absent_doctor_id] = [] # Clear absent doctor's queue

        dept = absent_doc["department"]
        available_doctors = [
            d_id for d_id in self._departments.get(dept, [])
            if d_id != absent_doctor_id and self._doctors[d_id]["status"] == "AVAILABLE"
        ]

        if not available_doctors:
            return [] # No parallel doctors available

        reassigned_tokens = []
        for idx, token in enumerate(stranded_tokens):
            target_doc_id = available_doctors[idx % len(available_doctors)]
            target_doc = self._doctors[target_doc_id]
            target_queue = self._queues[target_doc_id]

            new_token_num = len(target_queue) + 1
            patients_ahead = len(target_queue)
            est_wait_mins = patients_ahead * self.avg_consult_mins

            reassigned = {
                **token,
                "reassigned_from": absent_doc["name"],
                "doctor_id": target_doc_id,
                "doctor_name": target_doc["name"],
                "chamber_number": target_doc["chamber_number"],
                "token_number": new_token_num,
                "patients_ahead": patients_ahead,
                "est_wait_mins": est_wait_mins,
                "notification_message": (
                    f"জরুরী বিজ্ঞপ্তি: ডা: {absent_doc['name']} জরুরী অপারেশনের জন্য ডাক পেয়েছেন। "
                    f"আপনার টোকেন ডা: {target_doc['name']} (চেম্বার {target_doc['chamber_number']})-এ স্থানান্তরিত হয়েছে। "
                    f"নতুন টোকেন #{new_token_num} (~{est_wait_mins} মিনিট)।"
                )
            }
            target_queue.append(reassigned)
            reassigned_tokens.append(reassigned)

        return reassigned_tokens
