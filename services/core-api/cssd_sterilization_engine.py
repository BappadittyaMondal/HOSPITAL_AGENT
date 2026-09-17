"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Module: cssd_sterilization_engine.py
Operational Scope:
  - Central Sterile Services Department (CSSD) Barcoded Instrument Tray Lifecycle
  - Autoclave Validation Parameters (134°C, 30 psi, Bowie-Dick Test)
  - Quality Gate 3: Biological Spore Test Failure Triggers Automated Tray Batch Recall & Lock
  - Mechanical Block Preventing Issuance of Unverified or Compromised Trays to OT
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class CSSDError(Exception):
    """Base exception for CSSD sterilization violations."""
    pass


class SterilizationFailureError(CSSDError):
    """Raised when an autoclave biological indicator fails, locking all batch trays."""
    pass


class TrayUnsterileIssueError(CSSDError):
    """Raised when an unsterile, unverified, or recalled tray is attempted to be issued to an OT."""
    pass


@dataclass
class InstrumentTray:
    tray_barcode: str
    tray_name: str           # e.g., "Major Laparotomy Set A", "Orthopedic Hip Replacement Set"
    instrument_count: int
    current_status: str      # DECONTAMINATION, PACKAGING, AUTOCLAVING, STERILE_STORAGE, ISSUED_TO_OT, RECALLED_LOCKED
    autoclave_batch_id: Optional[str] = None
    sterilized_at: Optional[str] = None
    expiry_date: Optional[str] = None
    destination_ot: Optional[str] = None


@dataclass
class AutoclaveCycleRun:
    batch_id: str
    autoclave_id: str
    temperature_c: float     # e.g., 134.0
    pressure_psi: float      # e.g., 30.5
    exposure_time_min: float # e.g., 4.0
    bowie_dick_passed: bool
    biological_spore_result: str  # PENDING, NEGATIVE (Pass), POSITIVE (Fail)
    operator_id: str
    started_at: str
    completed_at: str
    trays_in_run: List[str] = field(default_factory=list)
    is_recalled: bool = False


class CSSDSterilizationEngine:
    """
    CSSD operations engine managing tray barcodes, autoclave validation,
    and automatic recall locks upon biological indicator failure.
    """

    def __init__(self):
        self.trays: Dict[str, InstrumentTray] = {}
        self.autoclave_runs: Dict[str, AutoclaveCycleRun] = {}
        self.recall_alerts: List[Dict[str, Any]] = []

    def register_tray(self, tray_barcode: str, tray_name: str, count: int) -> InstrumentTray:
        tray = InstrumentTray(
            tray_barcode=tray_barcode,
            tray_name=tray_name,
            instrument_count=count,
            current_status="PACKAGING"
        )
        self.trays[tray_barcode] = tray
        return tray

    def record_autoclave_run(
        self,
        batch_id: str,
        autoclave_id: str,
        temperature_c: float,
        pressure_psi: float,
        exposure_time_min: float,
        bowie_dick_passed: bool,
        operator_id: str,
        tray_barcodes: List[str]
    ) -> AutoclaveCycleRun:
        """
        Records the completion of an autoclave sterilization cycle.
        Sets trays to AUTOCLAVING status awaiting Biological Indicator (BI) release.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        run = AutoclaveCycleRun(
            batch_id=batch_id,
            autoclave_id=autoclave_id,
            temperature_c=temperature_c,
            pressure_psi=pressure_psi,
            exposure_time_min=exposure_time_min,
            bowie_dick_passed=bowie_dick_passed,
            biological_spore_result="PENDING",
            operator_id=operator_id,
            started_at=now_str,
            completed_at=now_str,
            trays_in_run=tray_barcodes
        )
        self.autoclave_runs[batch_id] = run

        for code in tray_barcodes:
            if code in self.trays:
                self.trays[code].autoclave_batch_id = batch_id
                self.trays[code].current_status = "AUTOCLAVING"

        return run

    def record_biological_indicator_result(
        self,
        batch_id: str,
        spore_growth_detected: bool,
        microbiologist_id: str
    ) -> Dict[str, Any]:
        """
        Quality Gate 3:
        Failed autoclave spore test automatically locks all surgical trays processed in that sterilization run.
        """
        run = self.autoclave_runs.get(batch_id)
        if not run:
            raise CSSDError(f"Autoclave run {batch_id} not found.")

        now_str = datetime.now(timezone.utc).isoformat()

        if spore_growth_detected:
            # STERILIZATION FAILURE (Geobacillus stearothermophilus spore survived)
            run.biological_spore_result = "POSITIVE"
            run.is_recalled = True

            # AUTOMATIC TRAY LOCK & RECALL
            locked_trays = []
            for code in run.trays_in_run:
                if code in self.trays:
                    self.trays[code].current_status = "RECALLED_LOCKED"
                    locked_trays.append(code)

            recall_alert = {
                "alert_id": f"CSSD-RECALL-{batch_id}",
                "batch_id": batch_id,
                "autoclave_id": run.autoclave_id,
                "reason": "BIOLOGICAL SPORE TEST FAILURE (Spore growth positive): Sterilization cycle compromised.",
                "microbiologist_id": microbiologist_id,
                "locked_trays": locked_trays,
                "timestamp": now_str
            }
            self.recall_alerts.append(recall_alert)

            raise SterilizationFailureError(
                f"CRITICAL CSSD INFECTION HAZARD: Autoclave batch {batch_id} failed biological spore indicator! "
                f"All {len(locked_trays)} trays mechanically locked and recalled: {locked_trays}."
            )

        # Sterilization Successful
        run.biological_spore_result = "NEGATIVE"
        run.is_recalled = False

        # Release trays to STERILE_STORAGE
        for code in run.trays_in_run:
            if code in self.trays:
                self.trays[code].current_status = "STERILE_STORAGE"
                self.trays[code].sterilized_at = now_str

        return {
            "batch_id": batch_id,
            "biological_spore_result": "NEGATIVE",
            "status": "APPROVED_STERILE",
            "released_trays_count": len(run.trays_in_run),
            "validated_by": microbiologist_id
        }

    def issue_tray_to_operating_room(self, tray_barcode: str, ot_room_id: str, technician_id: str) -> Dict[str, Any]:
        """
        Issues tray to operating theater.
        Mechanically blocks if tray is in RECALLED_LOCKED, AUTOCLAVING, or unsterile state.
        """
        tray = self.trays.get(tray_barcode)
        if not tray:
            raise CSSDError(f"Tray {tray_barcode} not found.")

        if tray.current_status == "RECALLED_LOCKED":
            raise TrayUnsterileIssueError(
                f"SAFETY HARD STOP: Tray {tray_barcode} is in RECALLED_LOCKED state due to autoclave spore failure. Issuance strictly barred."
            )

        if tray.current_status != "STERILE_STORAGE":
            raise TrayUnsterileIssueError(
                f"Tray {tray_barcode} is not in STERILE_STORAGE (Current status: '{tray.current_status}'). Issuance denied."
            )

        tray.current_status = "ISSUED_TO_OT"
        tray.destination_ot = ot_room_id

        return {
            "tray_barcode": tray_barcode,
            "tray_name": tray.tray_name,
            "destination_ot": ot_room_id,
            "status": "ISSUED_TO_OT",
            "issued_by": technician_id
        }
