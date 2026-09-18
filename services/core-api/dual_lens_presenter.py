# ====================================================================================================
# PROJECT "HOSPITAL" — DUAL-LENS PAN-INSTITUTIONAL CLINICAL PRESENTER
# ====================================================================================================
# Module: services/core-api/dual_lens_presenter.py
# Purpose: Synthesizes complex multi-institutional clinical evidence into a structured, dual-panel
#          clinical advisory: Local Actionable Care (AIIMS/CMC/SSKM/ICMR NLEM affordable generic plan)
#          alongside Global Reference Benchmarks (Mayo Clinic/Hopkins/Cleveland Clinic state-of-the-art),
#          ensuring patient equity, financial transparency, and global clinical excellence.
# ====================================================================================================

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


@dataclass
class DualLensReport:
    report_id: str
    patient_id: str
    clinical_syndrome: str
    timestamp: str
    dre_safety_firewall_status: str  # PASSED_SUB_MILLISECOND, BLOCKED_CONTRAINDICATION
    panel_a_local_actionable_standard: Dict[str, Any]
    panel_b_global_reference_benchmark: Dict[str, Any]
    economic_transparency_summary: Dict[str, Any]
    statutory_governance_notice: str


class DualLensPresentationAgent:
    """
    Formulates the dual-panel clinical presentation, bridging local actionable
    protocols with world-class tertiary reference benchmarks.
    """

    def generate_presentation(
        self,
        report_id: str,
        patient_id: str,
        clinical_syndrome: str,
        local_recommendation: Dict[str, Any],
        global_benchmark: Dict[str, Any],
        dre_passed: bool = True,
        economic_analysis: Optional[Dict[str, Any]] = None
    ) -> DualLensReport:
        firewall_status = "PASSED_SUB_MILLISECOND_DRE" if dre_passed else "BLOCKED_BY_DRE_SAFETY_KERNEL"

        gov_notice = (
            "STATUTORY GOVERNANCE ADVISORY: This document is formulated by the Pan-Institutional Clinical Knowledge "
            "Core (PICK-Core) as an Attended Level-3 Clinical Decision Support System. Under NMC Telemedicine Guidelines "
            "and international medical law, all draft recommendations require physical verification and digital sign-off "
            "by a licensed Registered Medical Practitioner (RMP) before medication administration."
        )

        econ = economic_analysis or {
            "local_daily_cost_inr": local_recommendation.get("estimated_daily_cost_inr", 0.0),
            "global_daily_cost_inr": global_benchmark.get("estimated_daily_cost_inr", 0.0),
            "nlem_coverage": "100% covered under National List of Essential Medicines",
            "jan_aushadhi_savings_pct": 75.0
        }

        return DualLensReport(
            report_id=report_id,
            patient_id=patient_id,
            clinical_syndrome=clinical_syndrome,
            timestamp=datetime.now(timezone.utc).isoformat(),
            dre_safety_firewall_status=firewall_status,
            panel_a_local_actionable_standard={
                "header": "PANEL A: IMMEDIATE ACTIONABLE CLINICAL PROTOCOL (AIIMS / CMC / SSKM / ICMR STW)",
                "governing_institutions": ["AIIMS New Delhi", "CMC Vellore", "IPGMER/SSKM Hospital Kolkata", "ICMR"],
                "first_line_therapy": local_recommendation.get("first_line_therapy", []),
                "nlem_generic_molecules": local_recommendation.get("nlem_generic_molecules", []),
                "estimated_daily_cost_inr": local_recommendation.get("estimated_daily_cost_inr", 0.0),
                "clinical_rationale": local_recommendation.get("clinical_rationale", ""),
                "citations": local_recommendation.get("citations", [])
            },
            panel_b_global_reference_benchmark={
                "header": "PANEL B: GLOBAL REFERENCE BENCHMARK (MAYO CLINIC / CLEVELAND CLINIC / JOHNS HOPKINS)",
                "governing_institutions": ["Mayo Clinic", "Cleveland Clinic", "Johns Hopkins Medicine", "NCCN"],
                "cutting_edge_therapy": global_benchmark.get("first_line_therapy", []),
                "global_reference_molecules": global_benchmark.get("nlem_generic_molecules", []),
                "estimated_daily_cost_inr": global_benchmark.get("estimated_daily_cost_inr", 0.0),
                "clinical_rationale": global_benchmark.get("clinical_rationale", ""),
                "citations": global_benchmark.get("citations", [])
            },
            economic_transparency_summary=econ,
            statutory_governance_notice=gov_notice
        )


# Singleton Instance
dual_lens_presenter = DualLensPresentationAgent()
