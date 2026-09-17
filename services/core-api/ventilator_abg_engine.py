"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Module: ventilator_abg_engine.py
Operational Scope:
  - Mechanical Ventilator Parameter Telemetry Ingestion (Mode, PEEP, FiO2, VT, Ppeak, Pplat)
  - Rapid Shallow Breathing Index (RSBI) Calculation & Weaning Readiness Evaluator
  - Automated Arterial Blood Gas (ABG) Interpretation (Acid-Base, Anion Gap, Winter's Formula, PaO2/FiO2 ARDS)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class VentilatorTelemetry:
    patient_id: str
    mode: str          # AC_VC, SIMV, PSV, BIPAP, APRV
    fio2: float        # 0.21 to 1.0 (or 21 to 100)
    peep: float        # cmH2O
    tidal_volume_ml: float
    respiratory_rate: float
    ppeak: Optional[float] = None
    pplat: Optional[float] = None


@dataclass
class RSBIEvaluation:
    patient_id: str
    rsbi_score: float
    weaning_ready: bool
    interpretation: str


@dataclass
class ABGInterpretation:
    ph: float
    paco2: float
    pao2: float
    hco3: float
    anion_gap: Optional[float]
    pf_ratio: float
    ards_severity: str  # NONE, MILD, MODERATE, SEVERE
    primary_disorder: str
    compensation_status: str
    diagnostic_summary: str


class VentilatorABGEngine:
    """
    Mechanical ventilation tracking and automated ABG clinical decision support engine.
    """

    def calculate_rsbi(self, patient_id: str, respiratory_rate: float, tidal_volume_ml: float) -> RSBIEvaluation:
        """
        Calculates Rapid Shallow Breathing Index (RSBI):
        RSBI = RR (breaths/min) / VT (Liters)
        RSBI < 105 indicates weaning readiness.
        """
        if tidal_volume_ml <= 0:
            raise ValueError("Tidal volume must be positive.")

        vt_liters = tidal_volume_ml / 1000.0
        rsbi = round(respiratory_rate / vt_liters, 1)

        weaning_ready = rsbi < 105.0
        interpretation = (
            f"RSBI = {rsbi} breaths/min/L (< 105): Weaning readiness criteria MET. Consider spontaneous breathing trial (SBT)."
            if weaning_ready else
            f"RSBI = {rsbi} breaths/min/L (>= 105): High probability of weaning failure. Maintain mechanical support."
        )

        return RSBIEvaluation(
            patient_id=patient_id,
            rsbi_score=rsbi,
            weaning_ready=weaning_ready,
            interpretation=interpretation
        )

    def interpret_abg(
        self,
        ph: float,
        paco2: float,
        pao2: float,
        hco3: float,
        fio2: float = 0.21,
        sodium_na: Optional[float] = None,
        chloride_cl: Optional[float] = None
    ) -> ABGInterpretation:
        """
        Automated ABG diagnostic evaluator:
        1. Anion Gap calculation: AG = Na - (Cl + HCO3)
        2. Primary Acid-Base disorder
        3. Winter's Formula for metabolic acidosis compensation
        4. PaO2/FiO2 ratio (Berlin ARDS definition)
        """
        # Normalize FiO2 to decimal 0.21 - 1.0
        norm_fio2 = fio2 / 100.0 if fio2 > 1.0 else fio2
        pf_ratio = round(pao2 / norm_fio2, 1)

        # ARDS severity based on Berlin Definition (with PEEP >= 5)
        if pf_ratio >= 300:
            ards_severity = "NONE"
        elif pf_ratio >= 200:
            ards_severity = "MILD_ARDS"
        elif pf_ratio >= 100:
            ards_severity = "MODERATE_ARDS"
        else:
            ards_severity = "SEVERE_ARDS"

        # Anion Gap
        anion_gap = None
        if sodium_na is not None and chloride_cl is not None:
            anion_gap = round(sodium_na - (chloride_cl + hco3), 1)

        # Primary disorder & Winter's formula
        primary_disorder = "NORMAL"
        compensation = "NONE"

        if ph < 7.35:
            # Acidemia
            if hco3 < 22.0 and paco2 <= 45.0:
                # Metabolic Acidosis
                ag_type = "HIGH ANION GAP" if (anion_gap and anion_gap > 12.0) else "NORMAL ANION GAP"
                primary_disorder = f"{ag_type} METABOLIC ACIDOSIS"
                # Winter's formula: Expected PaCO2 = 1.5 * HCO3 + 8 (+/- 2)
                expected_paco2 = round((1.5 * hco3) + 8.0, 1)
                lower_bound = expected_paco2 - 2.0
                upper_bound = expected_paco2 + 2.0

                if paco2 < lower_bound:
                    compensation = f"CONCOMITANT RESPIRATORY ALKALOSIS (Measured PaCO2 {paco2} < Winter's {lower_bound}-{upper_bound})"
                elif paco2 > upper_bound:
                    compensation = f"CONCOMITANT RESPIRATORY ACIDOSIS (Measured PaCO2 {paco2} > Winter's {lower_bound}-{upper_bound})"
                else:
                    compensation = f"ADEQUATELY COMPENSATED (Winter's PaCO2 range {lower_bound}-{upper_bound})"
            elif paco2 > 45.0:
                primary_disorder = "RESPIRATORY ACIDOSIS"
                compensation = "RENAL COMPENSATION PRESENT" if hco3 > 26.0 else "UNCOMPENSATED ACUTE"
        elif ph > 7.45:
            # Alkalemia
            if hco3 > 26.0:
                primary_disorder = "METABOLIC ALKALOSIS"
                compensation = "COMPENSATING RESPIRATORY RETENTION" if paco2 > 45.0 else "UNCOMPENSATED"
            elif paco2 < 35.0:
                primary_disorder = "RESPIRATORY ALKALOSIS"
                compensation = "RENAL LOSS PRESENT" if hco3 < 22.0 else "UNCOMPENSATED ACUTE"

        diagnostic_summary = (
            f"ABG DIAGNOSIS: {primary_disorder}. Compensation: {compensation}. "
            f"Oxygenation: P/F Ratio = {pf_ratio} ({ards_severity})."
        )
        if anion_gap is not None:
            diagnostic_summary += f" Anion Gap = {anion_gap} mEq/L."

        return ABGInterpretation(
            ph=ph,
            paco2=paco2,
            pao2=pao2,
            hco3=hco3,
            anion_gap=anion_gap,
            pf_ratio=pf_ratio,
            ards_severity=ards_severity,
            primary_disorder=primary_disorder,
            compensation_status=compensation,
            diagnostic_summary=diagnostic_summary
        )
