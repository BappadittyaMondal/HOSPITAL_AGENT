"""
PROJECT "HOSPITAL" — PHASE 12: HOSPITAL OPERATIONS
Module: linen_laundry_engine.py
Operational Scope:
  - Sub-task 12.2: Linen & Contaminated Laundry Management (Gap 31)
  - Departmental Linen Inventory & Indent Lifecycle Tracking
  - Biohazard & Infectious Linen Segregation (CDC / NABH Guidelines)
  - Washer Thermal & Chemical Disinfection Telemetry Validation (> 71°C for 25 min)
  - Mechanical Quarantine Gate Preventing Release of Unsterilized Linen
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any


class LinenError(Exception):
    """Base exception for linen and laundry operations."""
    pass


class DisinfectionFailureError(LinenError):
    """Raised when an unsterilized or failed laundry batch is attempted to be released to ward inventory."""
    pass


class LinenType(str, Enum):
    BEDSHEET = "BEDSHEET"
    PILLOW_COVER = "PILLOW_COVER"
    PATIENT_GOWN = "PATIENT_GOWN"
    SURGEON_SCRUB = "SURGEON_SCRUB"
    OT_DRAPE = "OT_DRAPE"
    BLANKET = "BLANKET"


class LinenBiohazardGrade(str, Enum):
    ROUTINE_SOILED = "ROUTINE_SOILED"
    CONTAMINATED_INFECTIOUS = "CONTAMINATED_INFECTIOUS"  # Yellow biohazard bag (Blood/Body fluids/C.diff)
    CYTOTOXIC = "CYTOTOXIC"  # Purple bag (Chemotherapy soiled)


class WashCycleStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    DISINFECTED_PASSED = "DISINFECTED_PASSED"
    DISINFECTION_FAILED = "DISINFECTION_FAILED"
    QUARANTINED_RE_WASH = "QUARANTINED_RE_WASH"
    RELEASED_TO_STORE = "RELEASED_TO_STORE"


@dataclass
class LaundryWashCycle:
    cycle_id: str
    machine_id: str
    batch_barcode: str
    biohazard_grade: LinenBiohazardGrade
    item_counts: Dict[str, int]
    wash_start_time: datetime
    max_temperature_c: float = 0.0
    duration_at_or_above_target_mins: float = 0.0
    chemical_disinfectant_ppm: float = 0.0  # Chlorine / Peracetic acid
    status: WashCycleStatus = WashCycleStatus.IN_PROGRESS
    completed_at: Optional[datetime] = None
    operator_id: Optional[str] = None
    validation_notes: str = ""


@dataclass
class WardLinenIndent:
    indent_id: str
    ward_id: str
    requested_items: Dict[str, int]
    requested_by: str
    status: str = "PENDING"  # PENDING, FULFILLED, PARTIAL
    fulfilled_at: Optional[datetime] = None


class LinenLaundryEngine:
    """
    Central Hospital Linen & Laundry Management Engine.
    Enforces statutory disinfection cycles per CDC & NABH standards to prevent nosocomial transmission.
    """

    # CDC / NABH Disinfection Criteria:
    # 1. High-temp Thermal cycle: >= 71.0 °C for >= 25.0 continuous minutes
    # 2. Low-temp Chemical cycle: >= 65.0 °C for >= 10.0 minutes with >= 100 ppm active chlorine
    MIN_THERMAL_TEMP_C = 71.0
    MIN_THERMAL_DURATION_MINS = 25.0

    MIN_CHEMICAL_TEMP_C = 65.0
    MIN_CHEMICAL_DURATION_MINS = 10.0
    MIN_CHEMICAL_PPM = 100.0

    def __init__(self):
        self._ward_stock: Dict[str, Dict[str, int]] = {}  # ward_id -> {item: count}
        self._central_clean_store: Dict[str, int] = {
            LinenType.BEDSHEET.value: 1000,
            LinenType.PILLOW_COVER.value: 1000,
            LinenType.PATIENT_GOWN.value: 600,
            LinenType.SURGEON_SCRUB.value: 400,
            LinenType.OT_DRAPE.value: 500,
            LinenType.BLANKET.value: 300,
        }
        self._wash_cycles: Dict[str, LaundryWashCycle] = {}
        self._indents: Dict[str, WardLinenIndent] = {}

    def initiate_wash_cycle(
        self,
        cycle_id: str,
        machine_id: str,
        batch_barcode: str,
        biohazard_grade: LinenBiohazardGrade,
        item_counts: Dict[str, int],
        operator_id: str,
    ) -> LaundryWashCycle:
        """Starts a washer-extractor cycle with biohazard categorization."""
        cycle = LaundryWashCycle(
            cycle_id=cycle_id,
            machine_id=machine_id,
            batch_barcode=batch_barcode,
            biohazard_grade=biohazard_grade,
            item_counts=item_counts,
            wash_start_time=datetime.now(timezone.utc),
            operator_id=operator_id,
        )
        self._wash_cycles[cycle_id] = cycle
        return cycle

    def record_wash_cycle_telemetry(
        self,
        cycle_id: str,
        max_temperature_c: float,
        duration_at_or_above_target_mins: float,
        chemical_disinfectant_ppm: float = 0.0,
    ) -> LaundryWashCycle:
        """
        Ingests digital telemetry from industrial laundry machine controller.
        Validates whether disinfection criteria were met.
        """
        if cycle_id not in self._wash_cycles:
            raise LinenError(f"Wash cycle {cycle_id} not found.")

        cycle = self._wash_cycles[cycle_id]
        cycle.max_temperature_c = max_temperature_c
        cycle.duration_at_or_above_target_mins = duration_at_or_above_target_mins
        cycle.chemical_disinfectant_ppm = chemical_disinfectant_ppm
        cycle.completed_at = datetime.now(timezone.utc)

        # Disinfection Validation Logic
        is_thermal_valid = (
            max_temperature_c >= self.MIN_THERMAL_TEMP_C
            and duration_at_or_above_target_mins >= self.MIN_THERMAL_DURATION_MINS
        )
        is_chemical_valid = (
            max_temperature_c >= self.MIN_CHEMICAL_TEMP_C
            and duration_at_or_above_target_mins >= self.MIN_CHEMICAL_DURATION_MINS
            and chemical_disinfectant_ppm >= self.MIN_CHEMICAL_PPM
        )

        if is_thermal_valid:
            cycle.status = WashCycleStatus.DISINFECTED_PASSED
            cycle.validation_notes = (
                f"Thermal disinfection satisfied: {max_temperature_c}°C for {duration_at_or_above_target_mins} mins "
                f"(NABH standard >= 71°C for 25 mins)."
            )
        elif is_chemical_valid:
            cycle.status = WashCycleStatus.DISINFECTED_PASSED
            cycle.validation_notes = (
                f"Chemical disinfection satisfied: {max_temperature_c}°C for {duration_at_or_above_target_mins} mins "
                f"with {chemical_disinfectant_ppm} ppm chlorine."
            )
        else:
            cycle.status = WashCycleStatus.DISINFECTION_FAILED
            cycle.validation_notes = (
                f"[DISINFECTION DEFICIENCY] Cycle reached only {max_temperature_c}°C for "
                f"{duration_at_or_above_target_mins} mins (Bleach: {chemical_disinfectant_ppm} ppm). "
                f"Failed CDC/NABH safety threshold! Quarantined."
            )

        return cycle

    def release_batch_to_clean_inventory(self, cycle_id: str, supervisor_id: str) -> Dict[str, Any]:
        """
        Releases clean laundry to central inventory.
        ENFORCES HARD SAFETY GATE: If status is not DISINFECTED_PASSED, release is strictly blocked.
        """
        if cycle_id not in self._wash_cycles:
            raise LinenError(f"Wash cycle {cycle_id} not found.")

        cycle = self._wash_cycles[cycle_id]

        if cycle.status != WashCycleStatus.DISINFECTED_PASSED:
            cycle.status = WashCycleStatus.QUARANTINED_RE_WASH
            raise DisinfectionFailureError(
                f"[INFECTION CONTROL VIOLATION] Batch {cycle.batch_barcode} (Cycle {cycle_id}) "
                f"cannot be released to clean storage! Status: {cycle.status.value}. "
                f"Reason: {cycle.validation_notes}"
            )

        # Add items to central clean store
        for item, count in cycle.item_counts.items():
            self._central_clean_store[item] = self._central_clean_store.get(item, 0) + count

        cycle.status = WashCycleStatus.RELEASED_TO_STORE

        return {
            "status": "BATCH_RELEASED",
            "cycle_id": cycle_id,
            "batch_barcode": cycle.batch_barcode,
            "items_added": cycle.item_counts,
            "released_by": supervisor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def create_ward_indent(
        self,
        indent_id: str,
        ward_id: str,
        requested_items: Dict[str, int],
        requested_by: str,
    ) -> WardLinenIndent:
        """Ward nurse in-charge indents fresh linen."""
        indent = WardLinenIndent(
            indent_id=indent_id,
            ward_id=ward_id,
            requested_items=requested_items,
            requested_by=requested_by,
        )
        self._indents[indent_id] = indent
        return indent

    def fulfill_ward_indent(self, indent_id: str, issuer_id: str) -> Dict[str, Any]:
        """Issues clean linen from central laundry store to ward."""
        if indent_id not in self._indents:
            raise LinenError(f"Indent {indent_id} not found.")

        indent = self._indents[indent_id]
        if indent.status == "FULFILLED":
            raise LinenError(f"Indent {indent_id} already fulfilled.")

        # Check stock availability
        for item, qty in indent.requested_items.items():
            available = self._central_clean_store.get(item, 0)
            if available < qty:
                raise LinenError(
                    f"Insufficient clean stock for {item}. Requested: {qty}, Available: {available}"
                )

        # Deduct from central store and add to ward stock
        if indent.ward_id not in self._ward_stock:
            self._ward_stock[indent.ward_id] = {}

        for item, qty in indent.requested_items.items():
            self._central_clean_store[item] -= qty
            self._ward_stock[indent.ward_id][item] = self._ward_stock[indent.ward_id].get(item, 0) + qty

        indent.status = "FULFILLED"
        indent.fulfilled_at = datetime.now(timezone.utc)

        return {
            "status": "INDENT_FULFILLED",
            "indent_id": indent_id,
            "ward_id": indent.ward_id,
            "items_issued": indent.requested_items,
            "issued_by": issuer_id,
            "timestamp": indent.fulfilled_at.isoformat(),
        }

    def get_central_stock(self) -> Dict[str, int]:
        return dict(self._central_clean_store)

    def get_ward_stock(self, ward_id: str) -> Dict[str, int]:
        return dict(self._ward_stock.get(ward_id, {}))
