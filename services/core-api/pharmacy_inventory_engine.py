"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Module: pharmacy_inventory_engine.py
Operational Scope:
  - Hospital Drug Master & Formulary (ATC, Schedule H/H1/X, Brand-to-Generic)
  - Look-Alike Sound-Alike (LASA) Tall Man Flagging & Intercept Engine
  - First-Expiry-First-Out (FEFO) Batch Allocation Engine
  - Vaccine Cold-Chain Temperature Surveillance (2°C-8°C) & AEFI Incident Logging
  - Automated Reorder Point (ROP) & Purchase Velocity Calculation (Gap 9, 19)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import math


@dataclass
class DrugMasterItem:
    drug_id: str
    generic_name: str
    brand_names: List[str]
    dosage_form: str  # TABLET, INJECTION, SYRUP, INFUSION, INHALER
    strength: str     # e.g., "500 mg", "40 mg/mL"
    route: str        # ORAL, IV, IM, SC, INHALATION, TOPICAL
    schedule: str     # GENERAL, SCHEDULE_H, SCHEDULE_H1, SCHEDULE_X (Narcotic)
    atc_code: str     # Anatomical Therapeutic Chemical
    is_high_alert: bool = False
    tall_man_name: Optional[str] = None
    storage_temp_range: Tuple[float, float] = (15.0, 25.0)  # Standard ambient Celsius


@dataclass
class InventoryBatch:
    batch_number: str
    drug_id: str
    quantity_on_hand: int
    expiry_date: datetime
    received_date: datetime
    cost_per_unit: float
    status: str = "ACTIVE"  # ACTIVE, QUARANTINED_EXCURSION, EXPIRED, RECALLED
    temp_logs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LASAPair:
    drug_id_a: str
    drug_id_b: str
    tall_man_a: str
    tall_man_b: str
    clinical_warning: str


class PharmacyInventoryEngine:
    """
    Core hospital formulary, batch inventory, and safety engine enforcing
    strict LASA warnings, FEFO batch selection, cold-chain checks, and reordering.
    """

    def __init__(self):
        self.drug_catalog: Dict[str, DrugMasterItem] = {}
        self.batches: Dict[str, List[InventoryBatch]] = {}  # drug_id -> list of batches
        self.lasa_registry: List[LASAPair] = []
        self.aefi_reports: List[Dict[str, Any]] = []

        self._seed_default_lasa_rules()

    def _seed_default_lasa_rules(self):
        """Seed high-risk ISMP Look-Alike Sound-Alike pairs."""
        default_lasa = [
            LASAPair(
                drug_id_a="DRUG-DOPAMINE",
                drug_id_b="DRUG-DOBUTAMINE",
                tall_man_a="DOPamine",
                tall_man_b="DOBUTamine",
                clinical_warning="CRITICAL LASA: Inadvertent substitution between Inotrope/Vasopressor and selective beta-1 inotrope can cause fatal hemodynamic instability."
            ),
            LASAPair(
                drug_id_a="DRUG-VINCRISTINE",
                drug_id_b="DRUG-VINBLASTINE",
                tall_man_a="VinCRIStine",
                tall_man_b="VinBLAStine",
                clinical_warning="FATAL CHEMOTHERAPY LASA: Vincristine is neurotoxic (IV ONLY - NEVER INTRATHECAL). Vinblastine is myelosuppressive. Dosing is 10-fold different."
            ),
            LASAPair(
                drug_id_a="DRUG-HYDRALAZINE",
                drug_id_b="DRUG-HYDROXYZINE",
                tall_man_a="HydrALAzine",
                tall_man_b="HydrOXYzine",
                clinical_warning="CRITICAL LASA: Antihypertensive vs 1st generation antihistamine. Confusion causes severe hypotension or sedation."
            ),
            LASAPair(
                drug_id_a="DRUG-CEFAZOLIN",
                drug_id_b="DRUG-CEFTRIAXONE",
                tall_man_a="CeFAZolin",
                tall_man_b="CefTRIAXone",
                clinical_warning="SURGICAL LASA: 1st gen vs 3rd gen cephalosporin. Inadvertent swap alters surgical prophylaxis spectrum and CSF penetration."
            ),
            LASAPair(
                drug_id_a="DRUG-EPINEPHRINE",
                drug_id_b="DRUG-EPHEDRINE",
                tall_man_a="EpiNEPHrine",
                tall_man_b="EPHEDrine",
                clinical_warning="ACUTE CARE LASA: 1:1000 adrenaline vs indirect sympathomimetic. Ten-fold potency disparity causes catastrophic hypertensive emergency."
            )
        ]
        for pair in default_lasa:
            self.lasa_registry.append(pair)

    def register_drug(self, item: DrugMasterItem) -> DrugMasterItem:
        """Register a medication into the hospital master formulary."""
        self.drug_catalog[item.drug_id] = item
        if item.drug_id not in self.batches:
            self.batches[item.drug_id] = []
        return item

    def check_lasa_conflict(self, drug_id: str, proposed_context_drug_ids: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        Check if a given drug has LASA risks against another drug in the same prescription
        or simply check if it is part of the high-risk LASA registry.
        """
        alerts = []
        for pair in self.lasa_registry:
            if drug_id in (pair.drug_id_a, pair.drug_id_b):
                partner_id = pair.drug_id_b if drug_id == pair.drug_id_a else pair.drug_id_a
                is_co_prescribed = proposed_context_drug_ids and (partner_id in proposed_context_drug_ids)
                alerts.append({
                    "primary_drug_id": drug_id,
                    "confusable_drug_id": partner_id,
                    "tall_man_a": pair.tall_man_a,
                    "tall_man_b": pair.tall_man_b,
                    "co_prescribed": bool(is_co_prescribed),
                    "warning": pair.clinical_warning,
                    "severity": "CRITICAL" if is_co_prescribed else "WARNING"
                })
        return alerts

    def add_batch(self, batch: InventoryBatch) -> InventoryBatch:
        """Receive and add a new inventory batch into stock."""
        if batch.drug_id not in self.batches:
            self.batches[batch.drug_id] = []
        self.batches[batch.drug_id].append(batch)
        return batch

    def allocate_fefo_stock(self, drug_id: str, requested_qty: int, as_of_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        First-Expiry-First-Out (FEFO) Stock Allocation Algorithm.
        Picks available batches in ascending order of expiration date.
        Mechanically excludes expired or quarantined batches.
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        if drug_id not in self.batches or not self.batches[drug_id]:
            return {
                "success": False,
                "error": "OUT_OF_STOCK",
                "allocated_qty": 0,
                "shortfall": requested_qty,
                "allocations": []
            }

        # Filter active and unexpired batches
        eligible_batches = [
            b for b in self.batches[drug_id]
            if b.status == "ACTIVE" and b.expiry_date > as_of_time and b.quantity_on_hand > 0
        ]

        # Sort strictly by expiry_date ascending (FEFO)
        eligible_batches.sort(key=lambda x: x.expiry_date)

        allocations = []
        remaining_needed = requested_qty

        for b in eligible_batches:
            if remaining_needed <= 0:
                break

            qty_to_take = min(b.quantity_on_hand, remaining_needed)
            b.quantity_on_hand -= qty_to_take
            remaining_needed -= qty_to_take

            allocations.append({
                "batch_number": b.batch_number,
                "allocated_qty": qty_to_take,
                "expiry_date": b.expiry_date.isoformat(),
                "remaining_in_batch": b.quantity_on_hand
            })

        return {
            "success": remaining_needed == 0,
            "drug_id": drug_id,
            "requested_qty": requested_qty,
            "allocated_qty": requested_qty - remaining_needed,
            "shortfall": remaining_needed,
            "allocations": allocations
        }

    def record_cold_chain_temperature(
        self,
        drug_id: str,
        batch_number: str,
        temperature_c: float,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Surveils vaccine & biologic cold chain.
        Standard cold chain: 2.0°C to 8.0°C.
        If excursion detected, automatically quarantines the batch to prevent harmful dispensing.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        drug = self.drug_catalog.get(drug_id)
        temp_min, temp_max = drug.storage_temp_range if drug else (2.0, 8.0)

        batch = None
        for b in self.batches.get(drug_id, []):
            if b.batch_number == batch_number:
                batch = b
                break

        if not batch:
            return {"success": False, "error": f"Batch {batch_number} not found for drug {drug_id}"}

        is_excursion = (temperature_c < temp_min) or (temperature_c > temp_max)
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "temperature_c": temperature_c,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "is_excursion": is_excursion
        }
        batch.temp_logs.append(log_entry)

        if is_excursion:
            batch.status = "QUARANTINED_EXCURSION"
            return {
                "success": True,
                "batch_number": batch_number,
                "status": "QUARANTINED_EXCURSION",
                "alert": f"CRITICAL COLD-CHAIN EXCURSION: {temperature_c}°C outside [{temp_min}°C - {temp_max}°C]. Batch locked from dispensing.",
                "log": log_entry
            }

        return {
            "success": True,
            "batch_number": batch_number,
            "status": batch.status,
            "alert": None,
            "log": log_entry
        }

    def log_aefi_report(
        self,
        patient_id: str,
        vaccine_drug_id: str,
        batch_number: str,
        symptom_category: str,  # MINOR, SEVERE, SERIOUS_HOSPITALIZATION, DEATH, CLUSTER
        description: str,
        reporter_id: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Statutory Adverse Event Following Immunization (AEFI) logging.
        Integrates with MoHFW / WHO guidelines for pharmacovigilance.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        report = {
            "report_id": f"AEFI-{int(timestamp.timestamp())}-{len(self.aefi_reports)+1}",
            "patient_id": patient_id,
            "vaccine_drug_id": vaccine_drug_id,
            "batch_number": batch_number,
            "symptom_category": symptom_category,
            "description": description,
            "reporter_id": reporter_id,
            "timestamp": timestamp.isoformat(),
            "regulatory_escalation": symptom_category in ("SERIOUS_HOSPITALIZATION", "DEATH", "CLUSTER")
        }
        self.aefi_reports.append(report)
        return report

    def calculate_reorder_point(
        self,
        daily_consumption_velocity: float,
        lead_time_days: int,
        daily_velocity_std_dev: float = 0.0,
        service_level_z: float = 1.645  # 95% service level
    ) -> Dict[str, Any]:
        """
        Automated Reorder Point (ROP) & Safety Stock calculation (Gap 9).
        ROP = (Daily Velocity * Lead Time) + Safety Stock
        Safety Stock = Z * std_dev * sqrt(Lead Time)
        """
        safety_stock = math.ceil(service_level_z * daily_velocity_std_dev * math.sqrt(lead_time_days))
        lead_time_demand = daily_consumption_velocity * lead_time_days
        rop = math.ceil(lead_time_demand + safety_stock)

        return {
            "daily_consumption_velocity": daily_consumption_velocity,
            "lead_time_days": lead_time_days,
            "safety_stock": safety_stock,
            "reorder_point": rop,
            "formula": f"ROP = ({daily_consumption_velocity} * {lead_time_days}) + {safety_stock}"
        }
