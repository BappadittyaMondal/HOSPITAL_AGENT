"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Module: oncology_daycare_engine.py
Operational Scope:
  - Quality Gate 3: Inviolable Pre-Chemotherapy Lab Gate (ANC < 1,000/µL or Platelets < 50,000/µL Halts Release)
  - Chemotherapy Protocol Double-Verification Engine (Dual Clinical Sign-Off)
  - Extravasation Emergency Protocol (Vesicant Specific Antidotes: Dexrazoxane vs Hyaluronidase)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class OncologySafetyError(Exception):
    """Base exception for oncology safety violations."""
    pass


class ChemotherapyLabGateViolationError(OncologySafetyError):
    """Raised when hematologic lab parameters breach pre-chemotherapy safety thresholds."""
    pass


@dataclass
class PreChemoLabValues:
    patient_id: str
    anc_cells_per_ul: float         # Absolute Neutrophil Count (Normal > 1500; Min safe threshold 1000)
    platelet_count_per_ul: float   # Platelets (Normal 150k-450k; Min safe threshold 50,000)
    hemoglobin_g_dl: float
    serum_creatinine_mg_dl: float
    total_bilirubin_mg_dl: float
    tested_at: datetime


@dataclass
class ChemoOrderVerification:
    order_id: str
    patient_id: str
    regimen_name: str
    drug_name: str
    dose_prescribed_mg: float
    bsa_m2: float
    primary_pharmacist_id: str
    secondary_pharmacist_id: str
    is_verified: bool
    status: str  # PENDING, APPROVED_FOR_DISPENSING, HALTED_LAB_CONTRAINDICATION


class OncologyDayCareEngine:
    """
    Oncology day-care administration engine enforcing hematologic safety gates,
    dual pharmacist protocol verification, and vesicant extravasation protocols.
    """

    MIN_SAFE_ANC = 1000.0          # cells/µL
    MIN_SAFE_PLATELETS = 50000.0   # cells/µL

    def __init__(self):
        self.patient_labs: Dict[str, PreChemoLabValues] = {}
        self.verified_orders: List[ChemoOrderVerification] = []

    def record_pre_chemo_labs(
        self,
        patient_id: str,
        anc_cells_per_ul: float,
        platelet_count_per_ul: float,
        hemoglobin_g_dl: float,
        creatinine_mg_dl: float,
        bilirubin_mg_dl: float,
        tested_at: Optional[datetime] = None
    ) -> PreChemoLabValues:
        """Records active pre-chemotherapy laboratory blood panel."""
        if tested_at is None:
            tested_at = datetime.now(timezone.utc)

        labs = PreChemoLabValues(
            patient_id=patient_id,
            anc_cells_per_ul=anc_cells_per_ul,
            platelet_count_per_ul=platelet_count_per_ul,
            hemoglobin_g_dl=hemoglobin_g_dl,
            serum_creatinine_mg_dl=creatinine_mg_dl,
            total_bilirubin_mg_dl=bilirubin_mg_dl,
            tested_at=tested_at
        )
        self.patient_labs[patient_id] = labs
        return labs

    def verify_and_authorize_chemo_release(
        self,
        order_id: str,
        patient_id: str,
        regimen_name: str,
        drug_name: str,
        dose_prescribed_mg: float,
        bsa_m2: float,
        primary_pharmacist_id: str,
        secondary_pharmacist_id: str
    ) -> ChemoOrderVerification:
        """
        Quality Gate 3:
        System halts chemotherapy release if active lab results show Absolute Neutrophil Count < 1,000 cells/µL
        or Platelet count < 50,000 cells/µL.
        Requires independent dual-pharmacist review.
        """
        if primary_pharmacist_id == secondary_pharmacist_id:
            raise OncologySafetyError("DUAL VERIFICATION VIOLATION: Primary and secondary verifying pharmacists must be distinct.")

        labs = self.patient_labs.get(patient_id)
        if not labs:
            raise OncologySafetyError(f"No active pre-chemotherapy laboratory panel recorded for patient {patient_id}.")

        # 1. INVIOLABLE LAB GATE: ANC Check
        if labs.anc_cells_per_ul < self.MIN_SAFE_ANC:
            raise ChemotherapyLabGateViolationError(
                f"FATAL MYELOSUPPRESSION SAFETY GATE BREACH: Active ANC is {labs.anc_cells_per_ul} cells/µL "
                f"(Absolute minimum threshold is {self.MIN_SAFE_ANC} cells/µL). "
                f"Chemotherapy release of {drug_name} is strictly halted to prevent fatal neutropenic sepsis."
            )

        # 2. INVIOLABLE LAB GATE: Platelet Check
        if labs.platelet_count_per_ul < self.MIN_SAFE_PLATELETS:
            raise ChemotherapyLabGateViolationError(
                f"FATAL THROMBOCYTOPENIA SAFETY GATE BREACH: Active Platelets are {labs.platelet_count_per_ul} cells/µL "
                f"(Absolute minimum threshold is {self.MIN_SAFE_PLATELETS} cells/µL). "
                f"Chemotherapy release of {drug_name} is strictly halted to prevent catastrophic hemorrhage."
            )

        verification = ChemoOrderVerification(
            order_id=order_id,
            patient_id=patient_id,
            regimen_name=regimen_name,
            drug_name=drug_name,
            dose_prescribed_mg=dose_prescribed_mg,
            bsa_m2=bsa_m2,
            primary_pharmacist_id=primary_pharmacist_id,
            secondary_pharmacist_id=secondary_pharmacist_id,
            is_verified=True,
            status="APPROVED_FOR_DISPENSING"
        )
        self.verified_orders.append(verification)
        return verification

    def get_extravasation_antidote_protocol(self, drug_name: str) -> Dict[str, Any]:
        """Returns vesicant extravasation emergency guidance based on drug class."""
        norm = drug_name.upper()
        if any(d in norm for d in ["DOXORUBICIN", "DAUNORUBICIN", "EPIRUBICIN"]):
            return {
                "vesicant_class": "ANTHRACYCLINE",
                "thermal_application": "COLD_DRY_COMPRESS (15-20 min QID for 48h)",
                "antidote": "Dexrazoxane (Totect) IV within 6 hours (Day 1: 1000mg/m², Day 2: 1000mg/m², Day 3: 500mg/m²)",
                "contraindicated": "DO NOT APPLY HEAT (enhances cytotoxicity)"
            }
        elif any(v in norm for v in ["VINCRISTINE", "VINBLASTINE", "VINORELBINE"]):
            return {
                "vesicant_class": "VINCA_ALKALOID",
                "thermal_application": "WARM_DRY_COMPRESS (enhances local systemic absorption)",
                "antidote": "Hyaluronidase 150-1500 units SC clockwise around extravasation site",
                "contraindicated": "DO NOT APPLY COLD (exacerbates local tissue ulceration)"
            }
        else:
            return {
                "vesicant_class": "GENERAL_IRRITANT",
                "thermal_application": "COLD_COMPRESS",
                "antidote": "Symptomatic wound care and aspiration",
                "contraindicated": "None"
            }
