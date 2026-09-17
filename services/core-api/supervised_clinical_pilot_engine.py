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

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional


class PilotSurveillanceException(Exception):
    """Base exception for clinical pilot progression violations."""
    pass


class PilotGateThresholdDeficitError(PilotSurveillanceException):
    """Raised when a pilot stage fails to meet mandatory safety thresholds for graduation."""
    pass


def _validate_non_negative_int(val: int, name: str) -> int:
    if not isinstance(val, int) or isinstance(val, bool):
        raise PilotSurveillanceException(f"Invalid {name}: must be an integer, got {type(val).__name__}")
    if val < 0:
        raise PilotSurveillanceException(f"Invalid {name}: value {val} cannot be negative")
    return val


def _validate_non_negative_float(val: float, name: str) -> float:
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        raise PilotSurveillanceException(f"Invalid {name}: must be numeric, got {type(val).__name__}")
    if math.isnan(val) or math.isinf(val):
        raise PilotSurveillanceException(f"Invalid {name}: value cannot be NaN or Infinite")
    if val < 0.0:
        raise PilotSurveillanceException(f"Invalid {name}: value {val} cannot be negative")
    return float(val)


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
        total_shadow_encounters = _validate_non_negative_int(total_shadow_encounters, "total_shadow_encounters")
        discrepant_encounters = _validate_non_negative_int(discrepant_encounters, "discrepant_encounters")
        smart_paper_qr_scans_successful = _validate_non_negative_int(smart_paper_qr_scans_successful, "smart_paper_qr_scans_successful")

        if discrepant_encounters > total_shadow_encounters:
            raise PilotSurveillanceException(
                f"INVARIANT BREACH: Discrepant encounters ({discrepant_encounters}) cannot exceed total encounters ({total_shadow_encounters})."
            )
        if smart_paper_qr_scans_successful > total_shadow_encounters:
            raise PilotSurveillanceException(
                f"INVARIANT BREACH: Successful QR scans ({smart_paper_qr_scans_successful}) cannot exceed total encounters ({total_shadow_encounters})."
            )

        if total_shadow_encounters == 0:
            evidence_status = "INSUFFICIENT_EVIDENCE"
            discrepancy_rate = 100.0
        else:
            evidence_status = "ADEQUATE_EVIDENCE"
            discrepancy_rate = (discrepant_encounters / total_shadow_encounters) * 100.0

        metrics = {
            "total_encounters": total_shadow_encounters,
            "discrepant_encounters": discrepant_encounters,
            "discrepancy_rate_percent": round(discrepancy_rate, 2),
            "qr_scans_successful": smart_paper_qr_scans_successful,
            "evidence_status": evidence_status,
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
        total_trauma_arrivals = _validate_non_negative_int(total_trauma_arrivals, "total_trauma_arrivals")
        bypassed_cashier_promptly = _validate_non_negative_int(bypassed_cashier_promptly, "bypassed_cashier_promptly")
        temp_id_generation_p99_ms = _validate_non_negative_float(temp_id_generation_p99_ms, "temp_id_generation_p99_ms")

        if bypassed_cashier_promptly > total_trauma_arrivals:
            raise PilotSurveillanceException(
                f"INVARIANT BREACH: Bypassed cashier arrivals ({bypassed_cashier_promptly}) cannot exceed total arrivals ({total_trauma_arrivals})."
            )

        if total_trauma_arrivals == 0:
            evidence_status = "INSUFFICIENT_EVIDENCE"
            compliance_pct = 0.0
        else:
            evidence_status = "ADEQUATE_EVIDENCE"
            compliance_pct = (bypassed_cashier_promptly / total_trauma_arrivals) * 100.0

        metrics = {
            "total_trauma_arrivals": total_trauma_arrivals,
            "bypassed_cashier": bypassed_cashier_promptly,
            "financial_decoupling_compliance_percent": round(compliance_pct, 2),
            "temp_id_p99_ms": temp_id_generation_p99_ms,
            "evidence_status": evidence_status,
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
        total_emar_administrations = _validate_non_negative_int(total_emar_administrations, "total_emar_administrations")
        dual_wristband_scanned = _validate_non_negative_int(dual_wristband_scanned, "dual_wristband_scanned")
        npo_meal_attempts_blocked = _validate_non_negative_int(npo_meal_attempts_blocked, "npo_meal_attempts_blocked")
        npo_meals_dispatched_to_patient = _validate_non_negative_int(npo_meals_dispatched_to_patient, "npo_meals_dispatched_to_patient")

        if dual_wristband_scanned > total_emar_administrations:
            raise PilotSurveillanceException(
                f"INVARIANT BREACH: Dual wristband scanned doses ({dual_wristband_scanned}) cannot exceed total eMAR administrations ({total_emar_administrations})."
            )

        if total_emar_administrations == 0:
            evidence_status = "INSUFFICIENT_EVIDENCE"
            scan_rate = 0.0
        else:
            evidence_status = "ADEQUATE_EVIDENCE"
            scan_rate = (dual_wristband_scanned / total_emar_administrations) * 100.0

        metrics = {
            "total_emar_doses": total_emar_administrations,
            "dual_wristband_scanned": dual_wristband_scanned,
            "emar_barcode_scan_percent": round(scan_rate, 2),
            "npo_blocked_attempts": npo_meal_attempts_blocked,
            "npo_leak_count": npo_meals_dispatched_to_patient,
            "evidence_status": evidence_status,
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
        total_sepsis_events = _validate_non_negative_int(total_sepsis_events, "total_sepsis_events")
        sepsis_alarms_under_5s = _validate_non_negative_int(sepsis_alarms_under_5s, "sepsis_alarms_under_5s")
        surgical_cases_completed = _validate_non_negative_int(surgical_cases_completed, "surgical_cases_completed")
        retained_sponge_discrepancies_at_closure = _validate_non_negative_int(
            retained_sponge_discrepancies_at_closure, "retained_sponge_discrepancies_at_closure"
        )

        if sepsis_alarms_under_5s > total_sepsis_events:
            raise PilotSurveillanceException(
                f"INVARIANT BREACH: Sub-5s alarms ({sepsis_alarms_under_5s}) cannot exceed total sepsis events ({total_sepsis_events})."
            )

        if total_sepsis_events == 0:
            evidence_status = "INSUFFICIENT_EVIDENCE"
            alarm_sla_rate = 0.0
        else:
            evidence_status = "ADEQUATE_EVIDENCE"
            alarm_sla_rate = (sepsis_alarms_under_5s / total_sepsis_events) * 100.0

        metrics = {
            "total_sepsis_events": total_sepsis_events,
            "alarms_under_5s": sepsis_alarms_under_5s,
            "alarm_sla_compliance_percent": round(alarm_sla_rate, 2),
            "surgical_cases": surgical_cases_completed,
            "retained_foreign_objects": retained_sponge_discrepancies_at_closure,
            "evidence_status": evidence_status,
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
        if from_stage != self._current_stage:
            raise PilotSurveillanceException(
                f"GOVERNANCE HARD-STOP: Out-of-order stage transition. Current active stage is {self._current_stage}, cannot advance from stage {from_stage}."
            )

        if not csb_auth_token or not isinstance(csb_auth_token, str) or not csb_auth_token.startswith(f"CSB-AUTH-STAGE-{from_stage}") or len(csb_auth_token.strip()) < 18:
            raise PilotSurveillanceException(
                f"GOVERNANCE HARD-STOP: Advancing from Stage {from_stage} requires valid CSB authorization token."
            )

        metrics = self._stage_metrics[from_stage].get("metrics", {})
        if not metrics:
            raise PilotSurveillanceException(
                f"GOVERNANCE HARD-STOP: No metrics recorded for Stage {from_stage}. Cannot advance unmonitored stage."
            )

        if metrics.get("evidence_status") == "INSUFFICIENT_EVIDENCE":
            raise PilotGateThresholdDeficitError(
                f"STAGE {from_stage} GATE FAILED: Zero observations recorded (INSUFFICIENT_EVIDENCE). Minimum observation quota required."
            )

        # Stage 1 Gate: Discrepancy rate <= 1.0%
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

        nurse_ergonomics_score_out_of_5 = _validate_non_negative_float(
            nurse_ergonomics_score_out_of_5, "nurse_ergonomics_score_out_of_5"
        )
        if nurse_ergonomics_score_out_of_5 > 5.0:
            raise PilotSurveillanceException(
                f"INVALID METRIC: Nurse ergonomics score {nurse_ergonomics_score_out_of_5} cannot exceed 5.0."
            )

        p99_latency_ms = _validate_non_negative_float(p99_latency_ms, "p99_latency_ms")

        if not medical_superintendent_signature_token or not isinstance(medical_superintendent_signature_token, str):
            raise PilotSurveillanceException("Medical Superintendent signature token must be a non-empty string.")

        token_str = medical_superintendent_signature_token.strip()
        if token_str == "UNVERIFIED-SIGNATURE" or not (token_str.startswith("MS-SIG-") or len(token_str) >= 32):
            raise PilotSurveillanceException(
                "SECURITY HARD-STOP: Medical Superintendent signature token is unverified or invalid format."
            )

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
            "medical_superintendent_token": token_str,
            "nurse_ergonomics_score": nurse_ergonomics_score_out_of_5,
            "p99_latency_ms": p99_latency_ms,
            "pilot_duration_days": 30
        }
        return self._final_go_live_certificate

    @property
    def current_stage(self) -> int:
        return self._current_stage
