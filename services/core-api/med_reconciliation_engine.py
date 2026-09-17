"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Module: med_reconciliation_engine.py
Operational Scope:
  - Care Transition Medication Reconciliation (Admission, Ward Transfer, ICU, Discharge)
  - Discrepancy Detection: Unintended Omissions, Duplications, and Dose Alterations
  - Structured Clinician Decisioning (Continue, Discontinue, Substitute, Modify)
  - Institutional Antibiogram Generation & Defined Daily Dose (DDD) per 1,000 Patient Days (Gap 17)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set


@dataclass
class MedicationItem:
    drug_id: str
    drug_name: str
    dosage: str
    route: str
    frequency: str  # OD, BD, TDS, QID, PRN, STAT
    therapeutic_class: str  # e.g., "BETA_BLOCKER", "STATIN", "PPI", "ACE_INHIBITOR"
    start_date: Optional[str] = None
    indication: Optional[str] = None


@dataclass
class DiscrepancyAlert:
    discrepancy_type: str  # UNINTENDED_OMISSION, THERAPEUTIC_DUPLICATION, DOSE_MISMATCH, FREQUENCY_MISMATCH
    drug_id: str
    drug_name: str
    details: str
    severity: str  # HIGH, MODERATE, LOW


@dataclass
class ReconciliationDecision:
    drug_id: str
    action: str  # CONTINUE, DISCONTINUE, SUBSTITUTE, MODIFY, HOLD
    clinical_rationale: str
    modified_dosage: Optional[str] = None
    clinician_id: str = "DOC-DEFAULT"
    timestamp: str = ""


class MedicationReconciliationEngine:
    """
    Care transition reconciliation engine comparing home medications against
    active hospital orders, detecting discrepancies, and enforcing clinical sign-off.
    """

    def __init__(self):
        self.reconciliation_records: List[Dict[str, Any]] = []
        # WHO Standard Defined Daily Doses (grams)
        self.who_standard_ddd: Dict[str, float] = {
            "MEROPENEM": 3.0,
            "COLISTIN": 9.0,       # 9 million IU ~ approx metric
            "PIPERACILLIN_TAZOBACTAM": 14.0,
            "VANCOMYCIN": 2.0,
            "CEFTRIAXONE": 2.0,
            "CIPROFLOXACIN": 1.0,
            "AMIKACIN": 1.0
        }

    def detect_discrepancies(
        self,
        baseline_meds: List[MedicationItem],
        target_meds: List[MedicationItem],
        transition_type: str  # ADMISSION, WARD_TRANSFER, DISCHARGE
    ) -> List[DiscrepancyAlert]:
        """
        Compares baseline (e.g. Home meds) against target (e.g. Inpatient orders).
        Detects omissions, duplications, and dose discrepancies.
        """
        alerts: List[DiscrepancyAlert] = []

        target_by_id = {m.drug_id: m for m in target_meds}
        target_classes: Dict[str, List[MedicationItem]] = {}
        for m in target_meds:
            target_classes.setdefault(m.therapeutic_class, []).append(m)

        # 1. Detect Unintended Omissions (present in baseline but completely absent in target)
        for base in baseline_meds:
            if base.drug_id not in target_by_id:
                # Check if entire class was dropped or substituted
                same_class_in_target = target_classes.get(base.therapeutic_class, [])
                if not same_class_in_target:
                    alerts.append(DiscrepancyAlert(
                        discrepancy_type="UNINTENDED_OMISSION",
                        drug_id=base.drug_id,
                        drug_name=base.drug_name,
                        details=f"Prior chronic medication {base.drug_name} ({base.dosage} {base.frequency}) was omitted during {transition_type}.",
                        severity="HIGH" if base.therapeutic_class in ("ANTICOAGULANT", "INSULIN", "ANTIEPILEPTIC", "ANTIHYPERTENSIVE") else "MODERATE"
                    ))
            else:
                # Present in both - check dose and frequency
                target = target_by_id[base.drug_id]
                if base.dosage.strip().upper() != target.dosage.strip().upper():
                    alerts.append(DiscrepancyAlert(
                        discrepancy_type="DOSE_MISMATCH",
                        drug_id=base.drug_id,
                        drug_name=base.drug_name,
                        details=f"Dose altered from {base.dosage} (Baseline) to {target.dosage} (Target) during {transition_type}.",
                        severity="MODERATE"
                    ))
                if base.frequency.strip().upper() != target.frequency.strip().upper():
                    alerts.append(DiscrepancyAlert(
                        discrepancy_type="FREQUENCY_MISMATCH",
                        drug_id=base.drug_id,
                        drug_name=base.drug_name,
                        details=f"Frequency altered from {base.frequency} (Baseline) to {target.frequency} (Target) during {transition_type}.",
                        severity="LOW"
                    ))

        # 2. Detect Therapeutic Duplications in Target Orders
        for th_class, items in target_classes.items():
            if len(items) > 1 and th_class not in ("ANESTHETIC_ADJUNCT", "MULTIVITAMIN", "SUPPLEMENT"):
                drug_names = ", ".join([m.drug_name for m in items])
                alerts.append(DiscrepancyAlert(
                    discrepancy_type="THERAPEUTIC_DUPLICATION",
                    drug_id=items[0].drug_id,
                    drug_name=drug_names,
                    details=f"Potential duplicate therapy within class '{th_class}': {drug_names} ordered concurrently.",
                    severity="HIGH"
                ))

        return alerts

    def complete_reconciliation(
        self,
        patient_id: str,
        transition_type: str,
        clinician_id: str,
        decisions: List[ReconciliationDecision],
        unresolved_alerts: List[DiscrepancyAlert]
    ) -> Dict[str, Any]:
        """
        Clinician completes and signs the medication reconciliation document.
        Requires justification for omissions or modifications.
        """
        now_str = datetime.now(timezone.utc).isoformat()

        # Enforce that all decisions modifying or discontinuing baseline meds include rationale
        for d in decisions:
            if d.action in ("DISCONTINUE", "MODIFY", "HOLD") and not d.clinical_rationale.strip():
                raise ValueError(f"Mandatory clinical rationale required for action '{d.action}' on drug {d.drug_id}.")
            d.timestamp = now_str
            d.clinician_id = clinician_id

        record = {
            "reconciliation_id": f"MEDREC-{patient_id}-{transition_type}-{int(datetime.now(timezone.utc).timestamp())}",
            "patient_id": patient_id,
            "transition_type": transition_type,
            "clinician_id": clinician_id,
            "signed_at": now_str,
            "decisions": [d.__dict__ for d in decisions],
            "unresolved_alerts_count": len(unresolved_alerts),
            "status": "COMPLETED"
        }
        self.reconciliation_records.append(record)
        return record

    def calculate_defined_daily_dose_rate(
        self,
        antibiotic_name: str,
        total_grams_consumed: float,
        total_patient_bed_days: int
    ) -> Dict[str, Any]:
        """
        Calculates WHO Defined Daily Dose (DDD) per 1,000 patient-days (Gap 17).
        Metric: (Total Grams / WHO DDD standard) / Patient Bed Days * 1,000
        """
        std_ddd = self.who_standard_ddd.get(antibiotic_name.upper())
        if not std_ddd:
            raise ValueError(f"WHO Standard DDD not configured for antibiotic: {antibiotic_name}")

        if total_patient_bed_days <= 0:
            raise ValueError("Total patient bed days must be greater than zero.")

        ddd_units_consumed = total_grams_consumed / std_ddd
        ddd_per_1000_pd = (ddd_units_consumed / total_patient_bed_days) * 1000.0

        return {
            "antibiotic": antibiotic_name,
            "total_grams_consumed": total_grams_consumed,
            "who_standard_ddd_grams": std_ddd,
            "ddd_units_consumed": round(ddd_units_consumed, 2),
            "total_patient_bed_days": total_patient_bed_days,
            "ddd_per_1000_patient_days": round(ddd_per_1000_pd, 2)
        }

    def generate_antibiogram(
        self,
        isolate_test_results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Aggregates microbiology susceptibility data into an institutional antibiogram.
        Input format: [{'organism': 'KLEBSIELLA_PNEUMONIAE', 'antibiotic': 'MEROPENEM', 'susceptibility': 'S'}, ...]
        Returns { organism: { antibiotic: susceptibility_percentage } }
        """
        counts: Dict[str, Dict[str, Dict[str, int]]] = {}

        for test in isolate_test_results:
            org = test["organism"]
            abx = test["antibiotic"]
            res = test["susceptibility"]  # 'S' = Susceptible, 'I' = Intermediate, 'R' = Resistant

            counts.setdefault(org, {}).setdefault(abx, {"total": 0, "susceptible": 0})
            counts[org][abx]["total"] += 1
            if res.upper() == "S":
                counts[org][abx]["susceptible"] += 1

        antibiogram: Dict[str, Dict[str, float]] = {}
        for org, abx_dict in counts.items():
            antibiogram[org] = {}
            for abx, data in abx_dict.items():
                pct = (data["susceptible"] / data["total"]) * 100.0 if data["total"] > 0 else 0.0
                antibiogram[org][abx] = round(pct, 1)

        return antibiogram
