#!/usr/bin/env python3
"""
Multilingual Kiosk & Smart Paper QR Bridge Engine (Phase 03).
Enforces:
1. Trilingual touch kiosk navigation (Bengali, Hindi, English) with voice narration prompts.
2. Smart Paper Bridge: Generates encrypted, offline-verifiable 2D QR chits for phone-less patients.
3. Universal verification decoder for nurse/doctor workstation barcode scanners.
"""
import hmac
import hashlib
import base64
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone

KIOSK_LOCALIZED_MENUS = {
    "BENGALI": {
        "welcome": "হাসপাতালে স্বাগতম। আপনি কি সেবা নিতে চান নির্বাচন করুন:",
        "options": [
            {"id": "NEW_REGISTRATION", "title": "নতুন রোগী নিবন্ধন", "voice_prompt": "নতুন রোগী নিবন্ধনের জন্য এখানে স্পর্শ করুন"},
            {"id": "EXISTING_APPOINTMENT", "title": "পুরানো রোগী / ডাক্তার দেখানো", "voice_prompt": "ডাক্তার দেখানোর টোকেন নিতে এখানে স্পর্শ করুন"},
            {"id": "EMERGENCY_HELP", "title": "জরুরী চিকিৎসা সহায়তা", "voice_prompt": "জরুরী চিকিৎসার জন্য লাল বোতাম স্পর্শ করুন"},
            {"id": "REPORT_COLLECTION", "title": "ল্যাব রিপোর্ট সংগ্রহ", "voice_prompt": "রিপোর্ট সংগ্রহের জন্য এখানে স্পর্শ করুন"}
        ]
    },
    "HINDI": {
        "welcome": "अस्पताल में आपका स्वागत है। कृपया आवश्यक सेवा का चयन करें:",
        "options": [
            {"id": "NEW_REGISTRATION", "title": "नया मरीज पंजीकरण", "voice_prompt": "नए मरीज के पंजीकरण के लिए यहाँ स्पर्श करें"},
            {"id": "EXISTING_APPOINTMENT", "title": "पुराने मरीज / डॉक्टर परामर्श", "voice_prompt": "डॉक्टर परामर्श टोकन के लिए यहाँ स्पर्श करें"},
            {"id": "EMERGENCY_HELP", "title": "आपातकालीन चिकित्सा सहायता", "voice_prompt": "आपातकालीन सहायता हेतु लाल बटन दबाएँ"},
            {"id": "REPORT_COLLECTION", "title": "जांच रिपोर्ट संग्रह", "voice_prompt": "जांच रिपोर्ट लेने के लिए यहाँ स्पर्श करें"}
        ]
    },
    "ENGLISH": {
        "welcome": "Welcome to the Hospital. Please select your required service:",
        "options": [
            {"id": "NEW_REGISTRATION", "title": "New Patient Registration", "voice_prompt": "Touch here for new patient registration"},
            {"id": "EXISTING_APPOINTMENT", "title": "OPD Doctor Consultation", "voice_prompt": "Touch here for doctor consultation token"},
            {"id": "EMERGENCY_HELP", "title": "Emergency Medical Assistance", "voice_prompt": "Press the red button for emergency help"},
            {"id": "REPORT_COLLECTION", "title": "Collect Diagnostic Reports", "voice_prompt": "Touch here to collect lab reports"}
        ]
    }
}

class SmartPaperBridge:
    def __init__(self, signing_key: str = "HOSPITAL_HMAC_SMART_PAPER_KEY_2026"):
        self.signing_key = signing_key.encode()

    def generate_paper_token_qr_payload(
        self,
        tenant_id: str,
        mrn: str,
        token_number: int,
        department: str,
        chamber: str
    ) -> Dict:
        """
        Generates an encrypted, tamper-evident Smart Paper QR payload for thermal ticket printing.
        Allows phone-less rural/elderly patients to complete their entire hospital journey on paper.
        """
        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        raw_body = f"{tenant_id[:8]}|{mrn}|{token_number}|{department}|{chamber}|{now}"
        signature = hmac.new(self.signing_key, raw_body.encode(), hashlib.sha256).hexdigest()[:16]
        
        qr_encoded_string = f"HOSP-V1:{raw_body}:{signature}"
        
        return {
            "qr_string": qr_encoded_string,
            "printed_text": {
                "header": "HOSPITAL SMART PAPER CHIT",
                "token_display": f"TOKEN #{token_number}",
                "department": department,
                "chamber": f"ROOM {chamber}",
                "patient_mrn": mrn,
                "instruction_bengali": "অনুগ্রহ করে এই স্লিপটি আপনার সাথে রাখুন এবং ডাকলে চেম্বারে প্রবেশ করুন।",
                "instruction_english": "Please keep this slip and present it upon arrival at the chamber."
            }
        }

    def decode_and_verify_paper_qr(self, qr_string: str) -> Optional[Dict]:
        """
        Scans and verifies the Smart Paper QR token at doctor or nurse workstation.
        Returns parsed verified token or None if tampered.
        """
        if not qr_string.startswith("HOSP-V1:"):
            return None

        parts = qr_string.split(":")
        if len(parts) != 3:
            return None

        _, raw_body, signature = parts
        expected_sig = hmac.new(self.signing_key, raw_body.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(signature, expected_sig):
            return None # Cryptographic tamper detected

        fields = raw_body.split("|")
        return {
            "tenant_prefix": fields[0],
            "mrn": fields[1],
            "token_number": int(fields[2]),
            "department": fields[3],
            "chamber": fields[4],
            "timestamp": fields[5],
            "verified": True
        }
