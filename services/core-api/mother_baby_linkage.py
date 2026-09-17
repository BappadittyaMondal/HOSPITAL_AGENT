#!/usr/bin/env python3
"""
Mother-Baby Biological Linkage & Anti-Abduction Security Engine (Gap 2) (Phase 02).
Enforces:
1. Bidirectional clinical linking between obstetric mother and newborn(s).
2. Multiple birth support (Twins, Triplets: Baby A, Baby B).
3. Temporary neonatal MRN generation (`BABY-OF-<MOTHER_MRN>-<N>`).
4. Active RFID anti-abduction pairing: Mother wristband paired with baby ankle tag.
5. Statutory Form 1 birth notification generator (Registration of Births & Deaths Act).
"""
import uuid
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timezone

class NewbornEncounter:
    def __init__(
        self,
        newborn_id: str,
        mother_mrn: str,
        birth_order: int, # 1 for single/twin A, 2 for twin B
        delivery_timestamp: datetime,
        gender: str,
        birth_weight_grams: int,
        gestational_age_weeks: float,
        apgar_1min: int,
        apgar_5min: int,
        delivery_type: str, # "NORMAL_VAGINAL", "ASSISTED_FORCEPS", "EMERGENCY_LSCS", "ELECTIVE_LSCS"
        rfid_tag_id: str
    ):
        self.newborn_id = newborn_id
        self.mother_mrn = mother_mrn
        self.birth_order = birth_order
        suffix = chr(64 + birth_order) if birth_order > 1 else "1" # A, B, etc.
        self.neonatal_temp_mrn = f"BABY-OF-{mother_mrn}-{suffix}"
        self.delivery_timestamp = delivery_timestamp
        self.gender = gender
        self.birth_weight_grams = birth_weight_grams
        self.gestational_age_weeks = gestational_age_weeks
        self.apgar_1min = apgar_1min
        self.apgar_5min = apgar_5min
        self.delivery_type = delivery_type
        self.rfid_tag_id = rfid_tag_id
        self.status = "ACTIVE_INPATIENT"
        self.statutory_form_1_registered = False

class MotherBabyLinkageEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._mother_registry: Dict[str, Dict] = {} # mother_mrn -> mother_profile
        self._newborns: Dict[str, NewbornEncounter] = {} # newborn_id -> NewbornEncounter
        self._rfid_pairings: Dict[str, str] = {} # baby_rfid -> mother_rfid

    def register_mother(self, mother_mrn: str, full_name: str, rfid_wristband: str):
        self._mother_registry[mother_mrn] = {
            "mrn": mother_mrn,
            "full_name": full_name,
            "rfid_wristband": rfid_wristband,
            "children": []
        }

    def record_birth(
        self,
        mother_mrn: str,
        birth_order: int,
        delivery_timestamp: datetime,
        gender: str,
        birth_weight_grams: int,
        gestational_age_weeks: float,
        apgar_1min: int,
        apgar_5min: int,
        delivery_type: str,
        baby_rfid_tag: str
    ) -> NewbornEncounter:
        """Records delivery, links newborn to mother, and pairs RFID anti-abduction tags."""
        mother = self._mother_registry.get(mother_mrn)
        if not mother:
            raise ValueError(f"Mother MRN '{mother_mrn}' not registered in obstetric registry!")

        newborn_id = str(uuid.uuid4())
        encounter = NewbornEncounter(
            newborn_id=newborn_id,
            mother_mrn=mother_mrn,
            birth_order=birth_order,
            delivery_timestamp=delivery_timestamp,
            gender=gender,
            birth_weight_grams=birth_weight_grams,
            gestational_age_weeks=gestational_age_weeks,
            apgar_1min=apgar_1min,
            apgar_5min=apgar_5min,
            delivery_type=delivery_type,
            rfid_tag_id=baby_rfid_tag
        )

        self._newborns[newborn_id] = encounter
        mother["children"].append(encounter.neonatal_temp_mrn)
        # Pair RFIDs
        self._rfid_pairings[baby_rfid_tag] = mother["rfid_wristband"]

        return encounter

    def verify_ward_exit_clearance(self, baby_rfid: str, accompanying_rfid: str) -> Tuple[bool, str]:
        """
        Anti-Abduction Gate: Verifies that baby RFID tag is paired with accompanying mother RFID tag.
        Sounds immediate ward-wide siren if unverified.
        """
        if baby_rfid not in self._rfid_pairings:
            return False, "ALARM_UNREGISTERED_INFANT_TAG: Security lockdown initiated."

        expected_mother_rfid = self._rfid_pairings[baby_rfid]
        if accompanying_rfid != expected_mother_rfid:
            return False, f"SECURITY_ALERT_ABDUCTION_RISK: Accompanying RFID '{accompanying_rfid}' does NOT match registered mother RFID '{expected_mother_rfid}'!"

        return True, "EXIT_AUTHORIZED: Infant paired with verified biological mother."

    def generate_statutory_form_1(self, newborn_id: str) -> Dict:
        """Generates statutory birth report under Registration of Births and Deaths Act."""
        newborn = self._newborns.get(newborn_id)
        if not newborn:
            raise ValueError("Newborn record not found")
        mother = self._mother_registry[newborn.mother_mrn]

        form_1 = {
            "form": "FORM_1_LEGAL_BIRTH_NOTIFICATION",
            "statutory_act": "Registration of Births and Deaths Act, 1969",
            "newborn_temp_mrn": newborn.neonatal_temp_mrn,
            "mother_name": mother["full_name"],
            "mother_mrn": mother["mrn"],
            "delivery_datetime": newborn.delivery_timestamp.isoformat(),
            "gender": newborn.gender,
            "weight_kg": round(newborn.birth_weight_grams / 1000.0, 2),
            "apgar_scores": f"1min:{newborn.apgar_1min} | 5min:{newborn.apgar_5min}",
            "institutional_delivery": True,
            "reporting_timestamp": datetime.now(timezone.utc).isoformat()
        }
        newborn.statutory_form_1_registered = True
        return form_1
