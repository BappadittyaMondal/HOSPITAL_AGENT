"""
PROJECT "HOSPITAL" — PHASE 12: HOSPITAL OPERATIONS
Module: biomedical_waste_engine.py
Operational Scope:
  - Sub-task 12.3: Biomedical Waste Management Engine (BMW Rules 2016) (Gap 11)
  - Color-Coded Segregation at Source (Yellow, Red, White Puncture-Proof, Blue)
  - Barcoded Bag Weight Tracking & Handover Chain of Custody
  - Common Bio-Medical Waste Treatment Facility (CBWTF) Manifest Generation
  - Quality Gate 2: State Pollution Control Board (SPCB) Annual Form IV Statutory Report Generator
  - Discrepancy & Pilferage Alarm for Weight Variances (> 5%)
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any


class BMWError(Exception):
    """Base exception for biomedical waste management violations."""
    pass


class BMWCategory(str, Enum):
    YELLOW = "YELLOW"       # Anatomical, soiled, discarded medicines, cytotoxic, chemical
    RED = "RED"             # Contaminated recyclables (tubing, catheters, IV bottles, syringes without needles)
    WHITE_SHARPS = "WHITE"  # Puncture-proof sharps (needles, scalpels, blades)
    BLUE = "BLUE"           # Contaminated glassware, medicine vials, metallic implants


class BagStatus(str, Enum):
    GENERATED_AT_SOURCE = "GENERATED_AT_SOURCE"
    COLLECTED_CENTRAL_STORE = "COLLECTED_CENTRAL_STORE"
    HANDED_OVER_CBWTF = "HANDED_OVER_CBWTF"
    DISPOSED = "DISPOSED"


@dataclass
class BMWBag:
    bag_barcode: str
    category: BMWCategory
    department_id: str
    weight_kg: float
    generated_at: datetime
    generator_staff_id: str
    status: BagStatus = BagStatus.GENERATED_AT_SOURCE
    central_received_at: Optional[datetime] = None
    cbwtf_manifest_id: Optional[str] = None


@dataclass
class CBWTFManifest:
    manifest_id: str
    cbwtf_agency_name: str
    vehicle_number: str
    driver_name: str
    driver_license: str
    dispatched_at: datetime
    bag_barcodes: List[str]
    category_weights_kg: Dict[str, float]
    total_manifest_weight_kg: float
    actual_truck_scale_weight_kg: float
    weight_discrepancy_kg: float
    weight_discrepancy_pct: float
    is_discrepancy_alert: bool
    manifest_sha256: str


class BiomedicalWasteEngine:
    """
    Biomedical Waste Management Engine compliant with India's Bio-Medical Waste Management Rules, 2016.
    Tracks barcoded bags from ward generation to CBWTF incineration/autoclaving with SPCB reporting.
    """

    # Statutory Discrepancy Threshold (CPCB Guideline): Weight variance between source and CBWTF > 5%
    MAX_PERMISSIBLE_WEIGHT_VARIANCE_PCT = 5.0

    def __init__(self, hospital_name: str = "AIIMS Tertiary Health Network", spcb_reg_no: str = "SPCB/BMW/2026/8941"):
        self.hospital_name = hospital_name
        self.spcb_reg_no = spcb_reg_no
        self._bags: Dict[str, BMWBag] = {}
        self._manifests: Dict[str, CBWTFManifest] = {}

    def record_waste_generation(
        self,
        bag_barcode: str,
        category: BMWCategory,
        department_id: str,
        weight_kg: float,
        generator_staff_id: str,
    ) -> BMWBag:
        """Records color-coded biomedical waste generation at ward/OT/ICU source."""
        if weight_kg <= 0.0:
            raise BMWError("Waste bag weight must be greater than zero kg.")
        if bag_barcode in self._bags:
            raise BMWError(f"Duplicate BMW bag barcode: {bag_barcode}")

        bag = BMWBag(
            bag_barcode=bag_barcode,
            category=category,
            department_id=department_id,
            weight_kg=round(weight_kg, 3),
            generated_at=datetime.now(timezone.utc),
            generator_staff_id=generator_staff_id,
            status=BagStatus.GENERATED_AT_SOURCE,
        )
        self._bags[bag_barcode] = bag
        return bag

    def receive_at_central_waste_storage(self, bag_barcode: str, receiver_staff_id: str) -> BMWBag:
        """Hospital sanitation handler collects bag and checks it into central 48-hour storage."""
        if bag_barcode not in self._bags:
            raise BMWError(f"Bag barcode {bag_barcode} not found.")

        bag = self._bags[bag_barcode]
        bag.status = BagStatus.COLLECTED_CENTRAL_STORE
        bag.central_received_at = datetime.now(timezone.utc)
        return bag

    def generate_cbwtf_dispatch_manifest(
        self,
        manifest_id: str,
        bag_barcodes: List[str],
        cbwtf_agency_name: str,
        vehicle_number: str,
        driver_name: str,
        driver_license: str,
        actual_truck_scale_weight_kg: float,
    ) -> CBWTFManifest:
        """
        Dispatches accumulated biomedical waste bags to the authorized CBWTF vehicle.
        Reconciles source registered weights with truck scale weight.
        Raises discrepancy alert if variance exceeds 5%.
        """
        if not bag_barcodes:
            raise BMWError("Cannot generate manifest with zero bags.")
        if manifest_id in self._manifests:
            raise BMWError(f"Duplicate manifest ID: {manifest_id}")

        category_weights: Dict[str, float] = {
            BMWCategory.YELLOW.value: 0.0,
            BMWCategory.RED.value: 0.0,
            BMWCategory.WHITE_SHARPS.value: 0.0,
            BMWCategory.BLUE.value: 0.0,
        }

        total_registered_weight = 0.0

        for barcode in bag_barcodes:
            if barcode not in self._bags:
                raise BMWError(f"Bag {barcode} not recognized in hospital inventory.")
            bag = self._bags[barcode]
            if bag.status == BagStatus.HANDED_OVER_CBWTF:
                raise BMWError(f"Bag {barcode} already handed over in previous manifest {bag.cbwtf_manifest_id}.")

            category_weights[bag.category.value] += bag.weight_kg
            total_registered_weight += bag.weight_kg
            bag.status = BagStatus.HANDED_OVER_CBWTF
            bag.cbwtf_manifest_id = manifest_id

        # Round category weights
        for cat in category_weights:
            category_weights[cat] = round(category_weights[cat], 3)
        total_registered_weight = round(total_registered_weight, 3)

        # Reconcile weight variance
        weight_discrepancy = round(abs(actual_truck_scale_weight_kg - total_registered_weight), 3)
        discrepancy_pct = (
            round((weight_discrepancy / total_registered_weight) * 100.0, 2)
            if total_registered_weight > 0
            else 0.0
        )
        is_alert = discrepancy_pct > self.MAX_PERMISSIBLE_WEIGHT_VARIANCE_PCT

        # Cryptographic tamper-proof seal
        manifest_payload = {
            "manifest_id": manifest_id,
            "cbwtf_agency": cbwtf_agency_name,
            "vehicle": vehicle_number,
            "driver": driver_name,
            "bags": bag_barcodes,
            "category_weights": category_weights,
            "total_weight_kg": total_registered_weight,
            "scale_weight_kg": actual_truck_scale_weight_kg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        manifest_sha256 = hashlib.sha256(json.dumps(manifest_payload, sort_keys=True).encode("utf-8")).hexdigest()

        manifest = CBWTFManifest(
            manifest_id=manifest_id,
            cbwtf_agency_name=cbwtf_agency_name,
            vehicle_number=vehicle_number,
            driver_name=driver_name,
            driver_license=driver_license,
            dispatched_at=datetime.now(timezone.utc),
            bag_barcodes=bag_barcodes,
            category_weights_kg=category_weights,
            total_manifest_weight_kg=total_registered_weight,
            actual_truck_scale_weight_kg=round(actual_truck_scale_weight_kg, 3),
            weight_discrepancy_kg=weight_discrepancy,
            weight_discrepancy_pct=discrepancy_pct,
            is_discrepancy_alert=is_alert,
            manifest_sha256=manifest_sha256,
        )
        self._manifests[manifest_id] = manifest
        return manifest

    def generate_spcb_annual_form_iv_report(self, reporting_year: int) -> Dict[str, Any]:
        """
        Quality Gate 2: Generates statutory Annual Report Form IV under Bio-Medical Waste Management Rules 2016
        for submission to the State Pollution Control Board (SPCB).
        Reconciles total generated vs total treated/dispatched waste.
        """
        category_totals = {
            BMWCategory.YELLOW.value: 0.0,
            BMWCategory.RED.value: 0.0,
            BMWCategory.WHITE_SHARPS.value: 0.0,
            BMWCategory.BLUE.value: 0.0,
        }

        department_totals: Dict[str, float] = {}
        total_bags_count = 0
        total_kg_generated = 0.0
        total_kg_dispatched = 0.0

        for bag in self._bags.values():
            if bag.generated_at.year == reporting_year:
                category_totals[bag.category.value] += bag.weight_kg
                total_kg_generated += bag.weight_kg
                dept = bag.department_id
                department_totals[dept] = department_totals.get(dept, 0.0) + bag.weight_kg
                total_bags_count += 1
                if bag.status == BagStatus.HANDED_OVER_CBWTF:
                    total_kg_dispatched += bag.weight_kg

        # Round values
        for cat in category_totals:
            category_totals[cat] = round(category_totals[cat], 3)
        for dept in department_totals:
            department_totals[dept] = round(department_totals[dept], 3)
        total_kg_generated = round(total_kg_generated, 3)
        total_kg_dispatched = round(total_kg_dispatched, 3)

        report_content = {
            "form_name": "FORM_IV_ANNUAL_REPORT_BMWM_RULES_2016",
            "reporting_year": reporting_year,
            "hospital_name": self.hospital_name,
            "spcb_authorization_no": self.spcb_reg_no,
            "total_bags_logged": total_bags_count,
            "total_waste_generated_kg": total_kg_generated,
            "total_waste_dispatched_to_cbwtf_kg": total_kg_dispatched,
            "category_summary_kg": category_totals,
            "departmental_breakdown_kg": department_totals,
            "number_of_cbwtf_manifests": len(self._manifests),
            "treatment_methods": {
                BMWCategory.YELLOW.value: "Incineration / Plasma Pyrolysis / Deep Burial",
                BMWCategory.RED.value: "Autoclaving / Microwaving followed by Shredding & Recycling",
                BMWCategory.WHITE_SHARPS.value: "Autoclaving / Dry Heat Sterilization followed by Shredding / Mutilation",
                BMWCategory.BLUE.value: "Disinfection (Sodium Hypochlorite) / Autoclaving followed by Recycling",
            },
            "spcb_compliance_certified": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Regulatory hash
        report_sha256 = hashlib.sha256(json.dumps(report_content, sort_keys=True).encode("utf-8")).hexdigest()
        report_content["statutory_seal_sha256"] = report_sha256

        return report_content

    def get_manifest(self, manifest_id: str) -> Optional[CBWTFManifest]:
        return self._manifests.get(manifest_id)
