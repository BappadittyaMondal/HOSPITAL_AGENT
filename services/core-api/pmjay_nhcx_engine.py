"""
PROJECT "HOSPITAL" — PHASE 11: REVENUE CYCLE
Module: pmjay_nhcx_engine.py
Operational Scope:
  - Ayushman Bharat PM-JAY Bundled Package Master (HBP 2.2)
  - Quality Gate 2: Inviolable Package Breakage Barrier Blocking Unbundled Consumable & Doctor Charges
  - National Health Claims Exchange (NHCX) FHIR Claim Pre-Auth Generator
  - Automated Claim Denial Risk Pre-Submission Scanner (Missing ICD-10, Missing Lab Evidence)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any


def to_dec(val: Any) -> Decimal:
    return Decimal(str(val))


def quantize_inr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PMJAYError(Exception):
    """Base exception for PM-JAY compliance violations."""
    pass


class PMJAYPackageBreakageError(PMJAYError):
    """Raised when an illegal attempt is made to unbundle charges covered under an all-inclusive PM-JAY package."""
    pass


class NHCXClaimValidationError(Exception):
    """Raised when an NHCX insurance claim lacks mandatory diagnostic or clinical justification."""
    pass


@dataclass
class PMJAYPackage:
    package_code: str       # e.g., "SG001A", "CR004B"
    procedure_name: str     # e.g., "Laparoscopic Cholecystectomy", "Total Knee Arthroplasty"
    specialty: str          # GENERAL_SURGERY, ORTHOPEDICS, CARDIOLOGY
    bundled_rate_inr: float
    includes_consumables: bool = True
    includes_bed_charges: bool = True
    includes_doctor_visits: bool = True
    includes_investigations: bool = True


@dataclass
class PMJAYPatientEncounter:
    encounter_id: str
    patient_id: str
    pmjay_card_id: str
    active_package_code: str
    preauth_number: str
    billed_items: List[Dict[str, Any]] = field(default_factory=list)


class PMJAYNHCXEngine:
    """
    Manages statutory PM-JAY package compliance, package breakage prevention,
    and NHCX claims generation with denial risk pre-screening.
    """

    # Categories strictly bundled inside PM-JAY surgical packages
    PROHIBITED_ADDON_CATEGORIES = {
        "CONSUMABLES", "SYRINGE", "GLOVES", "IV_CANULA", "BED_CHARGES",
        "DOCTOR_VISIT", "NURSING_CHARGES", "STANDARD_LAB"
    }

    def __init__(self):
        self.packages: Dict[str, PMJAYPackage] = {}
        self.encounters: Dict[str, PMJAYPatientEncounter] = {}
        self._seed_default_packages()

    def _seed_default_packages(self):
        default_pkgs = [
            PMJAYPackage(
                package_code="SG001A",
                procedure_name="Laparoscopic Cholecystectomy",
                specialty="GENERAL_SURGERY",
                bundled_rate_inr=28000.0
            ),
            PMJAYPackage(
                package_code="OR005A",
                procedure_name="Total Knee Arthroplasty (Unilateral)",
                specialty="ORTHOPEDICS",
                bundled_rate_inr=95000.0
            ),
            PMJAYPackage(
                package_code="CR002A",
                procedure_name="Coronary Angioplasty with Single Drug-Eluting Stent",
                specialty="CARDIOLOGY",
                bundled_rate_inr=65000.0
            )
        ]
        for p in default_pkgs:
            self.packages[p.package_code] = p

    def register_pmjay_encounter(
        self,
        encounter_id: str,
        patient_id: str,
        pmjay_card_id: str,
        package_code: str,
        preauth_number: str
    ) -> PMJAYPatientEncounter:
        """Registers a cashless PM-JAY patient under an all-inclusive national package."""
        if package_code not in self.packages:
            raise PMJAYError(f"PM-JAY Package code '{package_code}' not found in national master.")

        enc = PMJAYPatientEncounter(
            encounter_id=encounter_id,
            patient_id=patient_id,
            pmjay_card_id=pmjay_card_id,
            active_package_code=package_code,
            preauth_number=preauth_number
        )
        self.encounters[encounter_id] = enc
        return enc

    def add_billing_item(
        self,
        encounter_id: str,
        item_name: str,
        category: str,
        amount_inr: float
    ) -> Dict[str, Any]:
        """
        Quality Gate 2:
        System blocks attempt to add individual syringe or nursing charges to a cashless PM-JAY bundled package.
        Enforces statutory anti-breakage rules.
        """
        enc = self.encounters.get(encounter_id)
        if not enc:
            raise PMJAYError(f"Encounter {encounter_id} is not an active PM-JAY patient.")

        pkg = self.packages[enc.active_package_code]
        norm_cat = category.strip().upper()

        # INVIOLABLE PACKAGE BREAKAGE BARRIER
        if norm_cat in self.PROHIBITED_ADDON_CATEGORIES:
            raise PMJAYPackageBreakageError(
                f"STATUTORY PM-JAY VIOLATION: Illegal attempt to bill unbundled item '{item_name}' (Category: {category}) "
                f"for ₹{amount_inr} to PM-JAY patient {enc.patient_id}. "
                f"Package '{pkg.procedure_name}' ({pkg.package_code}) is ALL-INCLUSIVE (₹{pkg.bundled_rate_inr}). "
                f"Billing separate consumables, nursing, or physician fees is strictly illegal under NHA guidelines."
            )

        # Allow non-bundled specialized exclusions if explicitly contracted (e.g. specialized implants)
        amt_dec = quantize_inr(to_dec(amount_inr))
        entry = {
            "item_name": item_name,
            "category": category,
            "amount_inr": float(amt_dec),
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        enc.billed_items.append(entry)
        return entry

    def get_total_billed_addons(self, encounter_id: str) -> float:
        """Returns the total sum of authorized specialized addons in INR."""
        enc = self.encounters.get(encounter_id)
        if not enc:
            raise PMJAYError(f"Encounter {encounter_id} is not an active PM-JAY patient.")
        total_dec = sum(to_dec(i["amount_inr"]) for i in enc.billed_items)
        return float(quantize_inr(to_dec(total_dec)))

    def scan_nhcx_claim_denial_risk(
        self,
        encounter_id: str,
        primary_icd10_code: Optional[str],
        preauth_approval_id: Optional[str],
        attached_diagnostic_reports: List[str]
    ) -> Dict[str, Any]:
        """
        National Health Claims Exchange (NHCX) pre-submission risk scanner.
        Flags deficiencies that would lead to instant insurer claim rejection.
        """
        rejection_reasons = []

        if not primary_icd10_code or not primary_icd10_code.strip():
            rejection_reasons.append("MISSING_PRIMARY_DIAGNOSIS: Claim lacks statutory ICD-10 code.")

        if not preauth_approval_id or not preauth_approval_id.strip():
            rejection_reasons.append("MISSING_PREAUTH_APPROVAL: Insurer pre-authorization reference absent.")

        if not attached_diagnostic_reports:
            rejection_reasons.append("MISSING_CLINICAL_JUSTIFICATION: No diagnostic lab or radiology report attached to substantiate admission.")

        is_high_risk = len(rejection_reasons) > 0

        return {
            "encounter_id": encounter_id,
            "claim_dispatch_eligible": not is_high_risk,
            "denial_risk_level": "HIGH" if is_high_risk else "LOW",
            "rejection_reasons": rejection_reasons
        }
