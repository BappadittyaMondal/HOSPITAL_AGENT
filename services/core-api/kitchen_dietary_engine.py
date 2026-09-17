"""
PROJECT "HOSPITAL" — PHASE 12: HOSPITAL OPERATIONS
Module: kitchen_dietary_engine.py
Operational Scope:
  - Sub-task 12.1: Central Kitchen & Dietary Distribution Subsystem (Gap 7)
  - Clinical Diet Order Aggregation & Meal Production Planning
  - Inviolable Clinical Gate: Hard Block on Meal Tray Assembly & Dispatch for NPO Patients
  - Barcoded Meal Tray Generation & Bedside Dual-Scan Nursing Verification
  - Clinical Allergen & Dietary Restriction Safety Verification
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any


class DietaryError(Exception):
    """Base exception for kitchen and dietary violations."""
    pass


class NPOPatientMealBlockError(DietaryError):
    """Raised when an illegal attempt is made to prepare, assemble, or dispatch a meal tray for an NPO patient."""
    pass


class DietaryAllergenConflictError(DietaryError):
    """Raised when a meal contains an allergen recorded in the patient's clinical allergy profile."""
    pass


class BedsideMealMismatchError(DietaryError):
    """Raised when the bedside wristband barcode does not match the meal tray barcode."""
    pass


class DietType(str, Enum):
    REGULAR = "REGULAR"
    DIABETIC = "DIABETIC"
    RENAL = "RENAL"
    LOW_SODIUM = "LOW_SODIUM"
    SOFT_BLAND = "SOFT_BLAND"
    FULL_FLUID = "FULL_FLUID"
    CLEAR_FLUID = "CLEAR_FLUID"
    NPO = "NPO"  # Nil Per Os (Nothing by mouth)
    ENTERAL = "ENTERAL"
    PARENTERAL = "PARENTERAL"


class MealSlot(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    EVENING_SNACK = "EVENING_SNACK"
    DINNER = "DINNER"


class TrayStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    ASSEMBLED = "ASSEMBLED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    BLOCKED_NPO = "BLOCKED_NPO"
    REJECTED = "REJECTED"


@dataclass
class PatientDietProfile:
    patient_id: str
    mrn: str
    bed_id: str
    ward: str
    allergies: Set[str] = field(default_factory=set)
    is_npo: bool = False
    npo_reason: Optional[str] = None
    npo_ordered_at: Optional[datetime] = None


@dataclass
class DietOrder:
    order_id: str
    patient_id: str
    diet_type: DietType
    meal_slot: MealSlot
    ordered_by_doctor_id: str
    ordered_at: datetime
    caloric_target_kcal: int = 1800
    special_instructions: str = ""
    is_active: bool = True


@dataclass
class MealTray:
    tray_barcode: str
    patient_id: str
    bed_id: str
    ward: str
    meal_slot: MealSlot
    diet_type: DietType
    items: List[str]
    status: TrayStatus = TrayStatus.SCHEDULED
    assembled_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    verified_by_nurse_id: Optional[str] = None


class KitchenDietaryEngine:
    """
    Hospital Central Kitchen and Clinical Dietary Management Engine.
    Enforces strict NPO gates to prevent aspiration in surgical/procedural patients,
    aggregates production batches, and verifies bedside delivery.
    """

    def __init__(self):
        self._patient_profiles: Dict[str, PatientDietProfile] = {}
        self._active_diet_orders: Dict[str, DietOrder] = {}  # order_id -> DietOrder
        self._trays: Dict[str, MealTray] = {}  # tray_barcode -> MealTray
        self._blocked_npo_events: List[Dict[str, Any]] = []

    def register_patient_profile(
        self,
        patient_id: str,
        mrn: str,
        bed_id: str,
        ward: str,
        allergies: Optional[Set[str]] = None,
        is_npo: bool = False,
        npo_reason: Optional[str] = None,
    ) -> PatientDietProfile:
        profile = PatientDietProfile(
            patient_id=patient_id,
            mrn=mrn,
            bed_id=bed_id,
            ward=ward,
            allergies={a.lower() for a in (allergies or set())},
            is_npo=is_npo,
            npo_reason=npo_reason,
            npo_ordered_at=datetime.now(timezone.utc) if is_npo else None,
        )
        self._patient_profiles[patient_id] = profile
        return profile

    def set_npo_status(self, patient_id: str, is_npo: bool, reason: str) -> None:
        """Sets or removes the NPO (Nil Per Os) status for a patient."""
        if patient_id not in self._patient_profiles:
            raise DietaryError(f"Patient profile {patient_id} not found.")
        profile = self._patient_profiles[patient_id]
        profile.is_npo = is_npo
        profile.npo_reason = reason if is_npo else None
        profile.npo_ordered_at = datetime.now(timezone.utc) if is_npo else None

        # If NPO is set, immediately cancel any active scheduled trays
        if is_npo:
            for tray in self._trays.values():
                if tray.patient_id == patient_id and tray.status in (TrayStatus.SCHEDULED, TrayStatus.ASSEMBLED):
                    tray.status = TrayStatus.BLOCKED_NPO
                    self._blocked_npo_events.append({
                        "patient_id": patient_id,
                        "tray_barcode": tray.tray_barcode,
                        "reason": reason,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

    def create_diet_order(
        self,
        order_id: str,
        patient_id: str,
        diet_type: DietType,
        meal_slot: MealSlot,
        ordered_by_doctor_id: str,
        caloric_target_kcal: int = 1800,
        special_instructions: str = "",
    ) -> DietOrder:
        """Places a clinical diet order from ward/physician."""
        if patient_id not in self._patient_profiles:
            raise DietaryError(f"Patient {patient_id} has no registered dietary profile.")
        
        profile = self._patient_profiles[patient_id]
        if profile.is_npo and diet_type != DietType.NPO:
            raise NPOPatientMealBlockError(
                f"Cannot order active oral diet '{diet_type.value}' for patient {patient_id}. "
                f"Patient is currently under strict NPO order: {profile.npo_reason}"
            )

        order = DietOrder(
            order_id=order_id,
            patient_id=patient_id,
            diet_type=diet_type,
            meal_slot=meal_slot,
            ordered_by_doctor_id=ordered_by_doctor_id,
            ordered_at=datetime.now(timezone.utc),
            caloric_target_kcal=caloric_target_kcal,
            special_instructions=special_instructions,
        )
        self._active_diet_orders[order_id] = order
        return order

    def aggregate_kitchen_production(self, meal_slot: MealSlot) -> Dict[str, Any]:
        """
        Aggregates meal counts by diet type for the kitchen production run.
        CRITICAL GATE: Patients marked NPO are completely excluded from production counts.
        """
        counts: Dict[str, int] = {}
        total_eligible_patients = 0
        excluded_npo_count = 0

        for order in self._active_diet_orders.values():
            if not order.is_active or order.meal_slot != meal_slot:
                continue

            profile = self._patient_profiles.get(order.patient_id)
            if not profile or profile.is_npo or order.diet_type == DietType.NPO:
                excluded_npo_count += 1
                continue

            counts[order.diet_type.value] = counts.get(order.diet_type.value, 0) + 1
            total_eligible_patients += 1

        return {
            "meal_slot": meal_slot.value,
            "total_meals_to_prepare": total_eligible_patients,
            "diet_breakdown": counts,
            "excluded_npo_patients": excluded_npo_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def assemble_meal_tray(
        self,
        tray_barcode: str,
        order_id: str,
        menu_items: List[str],
        allergens_in_meal: Optional[List[str]] = None,
    ) -> MealTray:
        """
        Kitchen terminal assembles and barcodes a meal tray.
        ENFORCES HARD NPO BLOCK: Raises NPOPatientMealBlockError if patient is NPO.
        ENFORCES ALLERGY GATE: Raises DietaryAllergenConflictError if patient allergy matches item.
        """
        if order_id not in self._active_diet_orders:
            raise DietaryError(f"Diet order {order_id} not found.")
        
        order = self._active_diet_orders[order_id]
        profile = self._patient_profiles.get(order.patient_id)
        if not profile:
            raise DietaryError(f"Patient profile {order.patient_id} missing.")

        # Inviolable Quality Gate 1: Check NPO Status
        if profile.is_npo or order.diet_type == DietType.NPO:
            event = {
                "patient_id": profile.patient_id,
                "tray_barcode": tray_barcode,
                "reason": profile.npo_reason or "Patient marked NPO",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._blocked_npo_events.append(event)
            raise NPOPatientMealBlockError(
                f"[CRITICAL SAFETY BLOCK] Meal tray assembly strictly blocked for patient {profile.patient_id} (MRN: {profile.mrn}). "
                f"Patient is marked NPO ({profile.npo_reason}). No oral meal can be prepared!"
            )

        # Allergen verification
        meal_allergens = {a.lower() for a in (allergens_in_meal or [])}
        conflicts = profile.allergies.intersection(meal_allergens)
        if conflicts:
            raise DietaryAllergenConflictError(
                f"[ALLERGY ALERT] Cannot assemble tray: Patient {profile.patient_id} has known allergy to: {', '.join(conflicts)}"
            )

        tray = MealTray(
            tray_barcode=tray_barcode,
            patient_id=profile.patient_id,
            bed_id=profile.bed_id,
            ward=profile.ward,
            meal_slot=order.meal_slot,
            diet_type=order.diet_type,
            items=menu_items,
            status=TrayStatus.ASSEMBLED,
            assembled_at=datetime.now(timezone.utc),
        )
        self._trays[tray_barcode] = tray
        return tray

    def dispatch_tray_to_ward(self, tray_barcode: str) -> MealTray:
        """Kitchen dispatches the assembled tray to the ward trolley."""
        if tray_barcode not in self._trays:
            raise DietaryError(f"Tray {tray_barcode} does not exist.")
        
        tray = self._trays[tray_barcode]
        profile = self._patient_profiles[tray.patient_id]

        # Re-verify NPO at point of dispatch in case NPO was ordered while tray was being assembled
        if profile.is_npo:
            tray.status = TrayStatus.BLOCKED_NPO
            self._blocked_npo_events.append({
                "patient_id": profile.patient_id,
                "tray_barcode": tray_barcode,
                "reason": profile.npo_reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            raise NPOPatientMealBlockError(
                f"[DISPATCH GATE BLOCK] Patient {profile.patient_id} was switched to NPO after assembly! "
                f"Tray {tray_barcode} confiscated and blocked from ward trolley."
            )

        tray.status = TrayStatus.DISPATCHED
        tray.dispatched_at = datetime.now(timezone.utc)
        return tray

    def bedside_nurse_delivery_verification(
        self,
        scanned_tray_barcode: str,
        scanned_patient_wristband_mrn: str,
        nurse_id: str,
    ) -> Dict[str, Any]:
        """
        Bedside Nurse dual-barcode scan:
        1. Scan patient wristband (MRN)
        2. Scan meal tray barcode
        Ensures 100% correct meal delivery to right patient and prevents misallocation.
        """
        if scanned_tray_barcode not in self._trays:
            raise DietaryError(f"Scanned tray {scanned_tray_barcode} unrecognized.")

        tray = self._trays[scanned_tray_barcode]
        profile = self._patient_profiles[tray.patient_id]

        # Inviolable bedside NPO re-check
        if profile.is_npo:
            tray.status = TrayStatus.BLOCKED_NPO
            raise NPOPatientMealBlockError(
                f"[BEDSIDE SAFETY ALERT] Patient {profile.patient_id} is NPO ({profile.npo_reason}). "
                f"DO NOT FEED THE PATIENT. Tray withheld."
            )

        if profile.mrn != scanned_patient_wristband_mrn:
            tray.status = TrayStatus.REJECTED
            raise BedsideMealMismatchError(
                f"[BEDSIDE MISMATCH] Tray intended for MRN {profile.mrn} (Bed {profile.bed_id}) "
                f"was scanned at bed with MRN {scanned_patient_wristband_mrn}!"
            )

        tray.status = TrayStatus.DELIVERED
        tray.delivered_at = datetime.now(timezone.utc)
        tray.verified_by_nurse_id = nurse_id

        return {
            "status": "DELIVERY_VERIFIED",
            "tray_barcode": tray.tray_barcode,
            "patient_mrn": profile.mrn,
            "bed_id": profile.bed_id,
            "diet_type": tray.diet_type.value,
            "verified_by_nurse": nurse_id,
            "delivered_at": tray.delivered_at.isoformat(),
        }

    def get_blocked_npo_audit_log(self) -> List[Dict[str, Any]]:
        return list(self._blocked_npo_events)
