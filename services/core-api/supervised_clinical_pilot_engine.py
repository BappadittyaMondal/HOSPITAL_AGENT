"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 17.3: 5-STAGE SUPERVISED CLINICAL PILOT SURVEILLANCE ENGINE
====================================================================================================
Module: services/core-api/supervised_clinical_pilot_engine.py
Purpose: Orchestrates and audits the 30-Day Supervised Clinical Pilot across all 5 progressive
         stages (OPD Shadow -> ED -> Inpatient/Pharmacy -> ICU/OT -> Enterprise Go-Live). Enforces
         strict clinical gate thresholds (< 1.0% shadow discrepancy, 0 NPO leaks, 99.5% eMAR scan).
====================================================================================================
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional


class PilotSurveillanceException(Exception):
    """Base exception for clinical pilot progression violations."""
    pass


class PilotGateThresholdDeficitError(PilotSurveillanceException):
    """Raised when a pilot stage fails to meet mandatory safety thresholds for graduation."""
    pass


class SupervisedClinicalPilotEngine:
    """Manages progression, metrics collection, and gate certifications for the 30-Day Supervised Pilot."""

    def __init__(self):
        self._current_stage: int = 1
        self._stage_metrics: Dict[int, Dict] = {
            1: {"name": "OPD_SHADOW_PILOT", "target_days": "1-7", "status": "ACTIVE", "metrics": {}},
            2: {"name": "EMERGENCY_DEPARTMENT", "target_days": "8-14", "status": "LOCKED", "metrics": {}},
            3: {"name": "INPATIENT_AND_PHARMACY", "target_days": "15-21", "status": "LOCKED", "metrics": {}},
            4: {"name": "ICU_AND_OPERATING_THEATRE", "target_days": "22-27", "status": "LOCKED", "metrics": {}},
            5: {"name": "ENTERPRISE_FINAL_REVIEW", "target_days": "28-30", "status": "LOCKED", "metrics": {}}
        }
        self._final_go_live_certificate: Optional[Dict] = None

    def record_stage_1_opd_metrics(
        self,
        total_shadow_encounters: int,
        discrepant_encounters: int,
        smart_paper_qr_scans_successful: int
    ) -> Dict:
        """Records Stage 1 shadow mode metrics comparing physical paper charts to digital entries."""
        if total_shadow_encounters == 0:
            discrepancy_rate = 0.0
        else:
            discrepancy_rate = (discrepant_encounters / total_shadow_encounters) * 100.0

        metrics = {
            "total_encounters": total_shadow_encounters,
            "discrepant_encounters": discrepant_encounters,
            "discrepancy_rate_percent": round(discrepancy_rate, 2),
            "qr_scans_successful": smart_paper_qr_scans_successful,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        self._stage_metrics[1]["metrics"] = metrics
        return metrics

    def record_stage_2_emergency_metrics(
        self,
        total_trauma_arrivals: int,
        bypassed_cashier_promptly: int,
        temp_id_generation_p99_ms: float
    ) -> Dict:
        """Records Stage 2 Emergency Department triage and financial decoupling metrics."""
        compliance_pct = 100.0 if total_trauma_arrivals == 0 else (bypassed_cashier_promptly / total_trauma_arrivals) * 100.0
        metrics = {
            "total_trauma_arrivals": total_trauma_arrivals,
            "bypassed_cashier": bypassed_cashier_promptly,
            "financial_decoupling_compliance_percent": round(compliance_pct, 2),
            "temp_id_p99_ms": temp_id_generation_p99_ms,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        self._stage_metrics[2]["metrics"] = metrics
        return metrics

    def record_stage_3_inpatient_metrics(
        self,
        total_emar_administrations: int,
        dual_wristband_scanned: int,
        npo_meal_attempts_blocked: int,
        npo_meals_dispatched_to_patient: int
    ) -> Dict:
        """Records Stage 3 bedside eMAR and kitchen NPO safety metrics."""
        scan_rate = 100.0 if total_emar_administrations == 0 else (dual_wristband_scanned / total_emar_administrations) * 100.0
        metrics = {
            "total_emar_doses": total_emar_administrations,
            "dual_wristband_scanned": dual_wristband_scanned,
            "emar_barcode_scan_percent": round(scan_rate, 2),
            "npo_blocked_attempts": npo_meal_attempts_blocked,
            "npo_leak_count": npo_meals_dispatched_to_patient,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        self._stage_metrics[3]["metrics"] = metrics
        return metrics

    def record_stage_4_icu_ot_metrics(
        self,
        total_sepsis_events: int,
        sepsis_alarms_under_5s: int,
        surgical_cases_completed: int,
        retained_sponge_discrepancies_at_closure: int
    ) -> Dict:
        """Records Stage 4 ICU telemetry and OT WHO checklist surgical count metrics."""
        alarm_sla_rate = 100.0 if total_sepsis_events == 0 else (sepsis_alarms_under_5s / total_sepsis_events) * 100.0
        metrics = {
            "total_sepsis_events": total_sepsis_events,
            "alarms_under_5s": sepsis_alarms_under_5s,
            "alarm_sla_compliance_percent": round(alarm_sla_rate, 2),
            "surgical_cases": surgical_cases_completed,
            "retained_foreign_objects": retained_sponge_discrepancies_at_closure,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        self._stage_metrics[4]["metrics"] = metrics
        return metrics

    def advance_stage(
        self,
        from_stage: int,
        csb_auth_token: str
    ) -> Dict:
        """Advances the pilot to the next stage, strictly enforcing clinical gate thresholds."""
        if not csb_auth_token or not csb_auth_token.startswith(f"CSB-AUTH-STAGE-{from_stage}"):
            raise PilotSurveillanceException(
                f"GOVERNANCE HARD-STOP: Advancing from Stage {from_stage} requires valid CSB authorization token."
            )

        metrics = self._stage_metrics[from_stage].get("metrics", {})

        # Stage 1 Gate: Discrepancy rate < 1.0%
        if from_stage == 1:
            disc_rate = metrics.get("discrepancy_rate_percent", 100.0)
            if disc_rate > 1.0:
                raise PilotGateThresholdDeficitError(
                    f"STAGE 1 GATE FAILED: Shadow discrepancy rate {disc_rate}% exceeds 1.0% maximum allowable SLA."
                )

        # Stage 2 Gate: Financial Decoupling 100%
        elif from_stage == 2:
            decoupling_rate = metrics.get("financial_decoupling_compliance_percent", 0.0)
            if decoupling_rate < 100.0:
                raise PilotGateThresholdDeficitError(
                    f"STAGE 2 GATE FAILED: Emergency financial decoupling must be 100.0%. Achieved: {decoupling_rate}%"
                )

        # Stage 3 Gate: eMAR scan >= 99.5% and 0 NPO leaks
        elif from_stage == 3:
            scan_rate = metrics.get("emar_barcode_scan_percent", 0.0)
            npo_leaks = metrics.get("npo_leak_count", 999)
            if scan_rate < 99.5 or npo_leaks > 0:
                raise PilotGateThresholdDeficitError(
                    f"STAGE 3 GATE FAILED: eMAR scan rate {scan_rate}% (< 99.5%) or NPO leaks {npo_leaks} (> 0)."
                )

        # Stage 4 Gate: 100% sub-5s alarms and 0 retained sponges
        elif from_stage == 4:
            sla_rate = metrics.get("alarm_sla_compliance_percent", 0.0)
            retained = metrics.get("retained_foreign_objects", 999)
            if sla_rate < 100.0 or retained > 0:
                raise PilotGateThresholdDeficitError(
                    f"STAGE 4 GATE FAILED: ICU alarm SLA {sla_rate}% or retained foreign objects {retained}."
                )

        self._stage_metrics[from_stage]["status"] = "PASSED"
        next_stage = from_stage + 1
        if next_stage <= 5:
            self._stage_metrics[next_stage]["status"] = "ACTIVE"
            self._current_stage = next_stage

        return {
            "graduated_stage": from_stage,
            "next_stage": next_stage,
            "status": "ADVANCED",
            "csb_token_verified": csb_auth_token
        }

    def certify_enterprise_go_live(
        self,
        nurse_ergonomics_score_out_of_5: float,
        p99_latency_ms: float,
        medical_superintendent_signature_token: str
    ) -> Dict:
        """Generates the statutory Enterprise Production Go-Live Certificate upon Stage 5 completion."""
        if self._stage_metrics[4]["status"] != "PASSED":
            raise PilotSurveillanceException("Cannot certify enterprise go-live before Stages 1-4 are PASSED.")

        if nurse_ergonomics_score_out_of_5 < 4.0:
            raise PilotGateThresholdDeficitError(
                f"ERGONOMICS DEFICIT: Nurse feedback score {nurse_ergonomics_score_out_of_5}/5.0 < 4.0 threshold."
            )

        if p99_latency_ms > 200.0:
            raise PilotGateThresholdDeficitError(
                f"LATENCY BREACH: P99 latency {p99_latency_ms}ms exceeds 200ms enterprise SLA."
            )

        self._stage_metrics[5]["status"] = "CERTIFIED"
        self._final_go_live_certificate = {
            "certificate_id": f"CERT-ENTERPRISE-GOLIVE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "certified_at": datetime.now(timezone.utc).isoformat(),
            "status": "PERMANENT_PRODUCTION_APPROVED",
            "medical_superintendent_token": medical_superintendent_signature_token,
            "nurse_ergonomics_score": nurse_ergonomics_score_out_of_5,
            "p99_latency_ms": p99_latency_ms,
            "pilot_duration_days": 30
        }
        return self._final_go_live_certificate

    @property
    def current_stage(self) -> int:
        return self._current_stage
