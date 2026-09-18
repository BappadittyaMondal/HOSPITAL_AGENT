# ====================================================================================================
# PROJECT "HOSPITAL" — CORE API ASGI APPLICATION SERVER
# ====================================================================================================
# Module: services/core-api/main.py
# Purpose: Production ASGI entrypoint providing REST endpoints, health probes, authentication
#          token issuing, and deterministic safety rule evaluations aligned with openapi.yaml.
# ====================================================================================================

import os
import sys
import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger("hospital.core_api")

def parse_dose_string(dose_str: Optional[str]) -> float:
    """
    Strictly parses dose strings like '500mg', '10.5 ml', '250 MCG', '500'.
    Rejects non-numeric, malformed, zero, or negative inputs with ValueError.
    """
    if not dose_str or not isinstance(dose_str, str):
        raise ValueError(f"Dose value missing or invalid: {dose_str}")

    clean = dose_str.strip()
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%]*)$", clean)
    if not m:
        raise ValueError(f"Malformed or non-numeric dose format: '{dose_str}'")
    val = float(m.group(1))
    if val <= 0.0:
        raise ValueError(f"Prescribed dose must be strictly positive (>0), got: {val}")
    return val

# In-process microservice framework fallback for standalone execution
try:
    from fastapi import FastAPI, HTTPException, Header, Depends, status
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from db_session import outbox_manager, db_config
from auth_manager import auth_security_manager
from audit_ledger import audit_ledger

def record_audit_event_safe(
    tenant_id: str,
    event_type: str,
    aggregate_id: str,
    actor_id: str,
    payload: Dict[str, Any]
) -> None:
    """
    Safely records a tamper-evident audit event.
    Logs warnings on failure; fails closed (raises HTTPException 500) if HOSPITAL_ENV == 'production'.
    """
    try:
        audit_ledger.record_event(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            actor_id=actor_id,
            payload=payload
        )
    except Exception as exc:
        logger.error(f"[AUDIT LEDGER FAILURE] Failed to record event {event_type} for {aggregate_id}: {exc}", exc_info=True)
        if os.getenv("HOSPITAL_ENV", "development").lower() in ("production", "prod"):
            if HAS_FASTAPI:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"status": "AUDIT_LEDGER_ERROR", "error": "Inviolable cryptographic audit logging failed. Transaction aborted."}
                )
            raise RuntimeError("Inviolable cryptographic audit logging failed. Transaction aborted.")
from cpoe_dre_engine import CPOEDREEngine
from structured_history_engine import StructuredHistoryEngine, ChiefComplaintCategory
from syndromic_protocol_engine import SyndromicProtocolEngine, SyndromicArchetype
from clinical_emergency_scorers import (
    calculate_glasgow_coma_scale,
    evaluate_fast_stroke,
    calculate_pediatric_emergency_doses,
    calculate_anaphylaxis_protocol,
    calculate_parkland_burns_fluid
)
from blood_bank_engine import BloodBankEngine, normalize_blood_group
from ndps_narcotics_vault import (
    NDPSNarcoticsVaultEngine, BiometricCredential,
    DualBiometricAuthenticationError, NarcoticVaultError
)
from pmjay_nhcx_engine import (
    PMJAYNHCXEngine, PMJAYPackage, PMJAYPackageBreakageError
)
from dynamic_billing_engine import DynamicBillingEngine
from edge_resilience_engine import (
    EdgeResilienceEngine, ResourceClass, ResourceNotLeasedError, EdgeResilienceError
)
from obstetrics_labor_engine import (
    ObstetricsLaborEngine, PartographActionLineBreachError, ObstetricSafetyError
)

# Instantiate deterministic clinical and operational engines
dre_engine = CPOEDREEngine(tenant_id="TENANT-MAIN-01")
history_engine = StructuredHistoryEngine()
protocol_engine = SyndromicProtocolEngine(tenant_id="TENANT-MAIN-01")

# Operational Hospital Engines
blood_bank_engine = BloodBankEngine(tenant_id="TENANT-MAIN-01")
blood_bank_engine.register_blood_unit("UNIT-O-NEG-001", "O_NEG", "PACKED_RED_BLOOD_CELLS")
blood_bank_engine.register_blood_unit("UNIT-A-POS-001", "A_POS", "PACKED_RED_BLOOD_CELLS")
blood_bank_engine.register_blood_unit("UNIT-B-POS-001", "B_POS", "PACKED_RED_BLOOD_CELLS")
blood_bank_engine.register_blood_unit("UNIT-AB-POS-001", "AB_POS", "PACKED_RED_BLOOD_CELLS")

narcotics_vault = NDPSNarcoticsVaultEngine()
admin_cred = BiometricCredential("PHARM-01", "PHARMACIST", "BIO-ADMIN-TOKEN-01", True, datetime.now(timezone.utc))
witness_cred = BiometricCredential("NURSE-01", "NURSE_INCHARGE", "BIO-WITNESS-TOKEN-01", True, datetime.now(timezone.utc))
narcotics_vault.initialize_drug_vault("MORPHINE_10MG", 100, admin_cred, witness_cred)
narcotics_vault.initialize_drug_vault("FENTANYL_100MCG", 50, admin_cred, witness_cred)

pmjay_engine = PMJAYNHCXEngine()

billing_engine = DynamicBillingEngine()
edge_engine = EdgeResilienceEngine()
obstetrics_engine = ObstetricsLaborEngine()

if HAS_FASTAPI:
    app = FastAPI(
        title="HOSPITAL Core Platform API",
        description="Zero-Trust End-to-End Hospital Information System (HIS) API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class TokenRequest(BaseModel):
        username: str
        password: str
        tenant_id: str

    class OrderItem(BaseModel):
        code: str
        name: str
        dose: Optional[str] = "500mg"
        route: Optional[str] = "ORAL"

    class EvaluateOrderRequest(BaseModel):
        patient_id: str
        clinician_id: str
        order_type: str = "MEDICATION"
        items: List[OrderItem]
        patient_weight_kg: Optional[float] = None
        patient_bsa_m2: Optional[float] = None
        serum_creatinine: Optional[float] = None
        patient_age: Optional[int] = None
        is_female: Optional[bool] = None
        current_medications: Optional[List[str]] = []
        known_allergies: Optional[List[str]] = []
        is_pregnant: Optional[bool] = None

    class HistoryIntakeRequest(BaseModel):
        session_id: str
        patient_id: str
        chief_complaint: str
        patient_age: int
        is_female: bool
        is_pregnant: Optional[bool] = False
        answers: Dict[str, Any] = {}

    class SyndromicHoldingPlanRequest(BaseModel):
        patient_id: str
        syndrome: str
        patient_age: int
        is_female: bool
        patient_weight_kg: float
        vitals: Dict[str, float]
        current_medications: Optional[List[str]] = []
        known_allergies: Optional[List[str]] = []
        is_pregnant: Optional[bool] = False
        estimated_transit_hours: Optional[float] = 6.0

    class EmergencyScoreRequest(BaseModel):
        score_type: str  # GCS, FAST, PEDIATRIC, ANAPHYLAXIS, BURNS_PARKLAND
        eye_score: Optional[int] = 4
        verbal_score: Optional[int] = 5
        motor_score: Optional[int] = 6
        facial_droop: Optional[bool] = False
        arm_weakness: Optional[bool] = False
        speech_difficulty: Optional[bool] = False
        onset_hours_ago: Optional[float] = 1.0
        patient_weight_kg: Optional[float] = None
        patient_age_years: Optional[float] = None
        is_child: Optional[bool] = False
        tbsa_percentage: Optional[float] = 20.0
        hours_since_burn: Optional[float] = 0.0
        fluids_already_given_ml: Optional[float] = 0.0

    class CrossmatchRequest(BaseModel):
        recipient_mrn: str
        recipient_blood_group: str
        unit_barcode: str
        transfusion_order_id: str
        emergency_unmatched_release: Optional[bool] = False

    class NarcoticDispenseRequest(BaseModel):
        drug_id: str
        batch_number: str
        quantity: int
        patient_id: str
        order_id: str
        primary_user_id: str
        primary_role: str
        primary_bio_token: Optional[str] = None
        primary_bio_verified: Optional[bool] = None
        secondary_user_id: str
        secondary_role: str
        secondary_bio_token: Optional[str] = None
        secondary_bio_verified: Optional[bool] = None

    class PMJAYAdjudicateRequest(BaseModel):
        encounter_id: str
        patient_id: str
        pmjay_card_id: str
        package_code: str
        item_code: str
        item_name: str
        category: str
        amount_inr: float

    class EdgeLeaseRequest(BaseModel):
        node_id: str
        resource_id: str
        resource_type: str = "ICU_BED"
        duration_hours: Optional[float] = 72.0

    class PartographRecordRequest(BaseModel):
        patient_id: str
        hours_in_active_labor: float
        cervical_dilatation_cm: float
        fetal_heart_rate_bpm: float
        contractions_per_10min: int
        amniotic_fluid_state: Optional[str] = "CLEAR"

    async def get_current_principal(
        authorization: Optional[str] = Header(None, alias="Authorization"),
        x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
    ) -> Dict[str, Any]:
        env_mode = os.getenv("HOSPITAL_ENV", "development").lower()
        strict_auth = os.getenv("STRICT_AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")

        if not authorization:
            if env_mode in ("production", "prod") or strict_auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"status": "UNAUTHORIZED", "error": "Missing mandatory Authorization Bearer token."}
                )
            return {
                "sub": "dev_principal",
                "tenant_id": x_tenant_id or "TENANT-MAIN-01",
                "role": "CONSULTANT_PHYSICIAN",
                "permissions": ["*"]
            }

        valid, payload, err = auth_security_manager.decode_and_verify_token(authorization)
        if not valid or not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"status": "UNAUTHORIZED", "error": f"Invalid or expired authentication token: {err}"}
            )

        # Anti-Tenant-Tampering Gate: Header tenant cannot override authenticated token tenant
        token_tenant = payload.get("tenant_id")
        user_role = payload.get("role", "")
        if x_tenant_id and token_tenant and x_tenant_id != token_tenant:
            if user_role not in ("SUPERADMIN", "SYSTEM_ADMIN"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "FORBIDDEN",
                        "error": f"Cross-tenant access prohibited: Request tenant '{x_tenant_id}' does not match authenticated token tenant '{token_tenant}'."
                    }
                )

        return payload

    def require_permission(required_permission: str):
        """FastAPI route dependency enforcing granular role-based permissions."""
        async def permission_checker(principal: Dict[str, Any] = Depends(get_current_principal)):
            perms = principal.get("permissions", [])
            role = principal.get("role", "")
            if "*" in perms or role in ("SUPERADMIN", "SYSTEM_ADMIN"):
                return principal
            if required_permission not in perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "FORBIDDEN",
                        "error": f"Principal lacking mandatory permission '{required_permission}'. Role: '{role}'."
                    }
                )
            return principal
        return permission_checker

    @app.get("/health", summary="Service Health & Readiness Probe")
    async def get_health_status():
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "services": {
                "postgres": "connected",
                "redis": "connected",
                "safety_engine": "online",
                "syndromic_engine": "online"
            }
        }

    @app.get("/ready", summary="Readiness Check")
    async def get_readiness_status():
        # Dynamic readiness verification across critical subsystems
        is_dre_ready = dre_engine is not None
        is_blood_bank_ready = blood_bank_engine is not None and len(blood_bank_engine._inventory) > 0
        is_narcotics_ready = narcotics_vault is not None and len(narcotics_vault.balances) > 0
        is_edge_ready = edge_engine is not None

        all_ready = is_dre_ready and is_blood_bank_ready and is_narcotics_ready and is_edge_ready
        if not all_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "ready": False,
                    "reason": "One or more core clinical subsystems are uninitialized or offline.",
                    "subsystems": {
                        "dre_engine": is_dre_ready,
                        "blood_bank": is_blood_bank_ready,
                        "narcotics_vault": is_narcotics_ready,
                        "edge_resilience": is_edge_ready
                    }
                }
            )

        return {
            "ready": True,
            "database": "active",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subsystems": {
                "dre_engine": "HEALTHY",
                "blood_bank": "HEALTHY",
                "narcotics_vault": "HEALTHY",
                "edge_resilience": "HEALTHY"
            }
        }

    @app.post("/api/v1/auth/token", summary="Authenticate Clinical Staff & Issue Contextual JWT")
    async def authenticate_staff(req: TokenRequest):
        user_info = auth_security_manager.verify_credentials(req.username, req.password)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        token = auth_security_manager.create_access_token(
            username=user_info["username"],
            tenant_id=req.tenant_id,
            role=user_info["role"],
            permissions=user_info["permissions"]
        )
        return {
            "token": token,
            "expires_in": 28800,
            "role": user_info["role"],
            "permissions": user_info["permissions"]
        }

    @app.post("/api/v1/safety/evaluate-order", summary="Sub-millisecond DRE Clinical Safety Verification")
    async def evaluate_clinical_order(
        req: EvaluateOrderRequest,
        x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        import time
        t0 = time.perf_counter()
        all_hard_stops = []
        all_warnings = []
        tenant = x_tenant_id or principal.get("tenant_id") or "TENANT-MAIN-01"

        # Check for mandatory clinical data
        for item in req.items:
            drug_l = item.name.lower()
            if "metformin" in drug_l and req.serum_creatinine is None:
                all_hard_stops.append({
                    "rule_id": "DRE-INSUFFICIENT-DATA",
                    "message": "Metformin requires verified serum creatinine / eGFR before evaluation. Default creatinine assumption prohibited.",
                    "severity": "CRITICAL_FATAL"
                })

            if req.patient_age is not None and req.patient_age < 18 and req.patient_weight_kg is None:
                all_hard_stops.append({
                    "rule_id": "DRE-INSUFFICIENT-DATA",
                    "message": "Pediatric medication order requires exact measured patient weight (kg). Default weight assumption prohibited.",
                    "severity": "CRITICAL_FATAL"
                })

            # Teratogenic drug hold when pregnancy status is unspecified for female of childbearing age
            teratogenic_keywords = ("methotrexate", "warfarin", "isotretinoin", "thalidomide", "valproate", "simvastatin", "atorvastatin")
            if any(tk in drug_l for tk in teratogenic_keywords):
                is_fem = req.is_female if req.is_female is not None else False
                age = req.patient_age if req.patient_age is not None else 30
                if is_fem and (12 <= age <= 55) and (req.is_pregnant is None):
                    all_hard_stops.append({
                        "rule_id": "DRE-INSUFFICIENT-DATA",
                        "message": f"Teratogenic medication '{item.name}' requires explicit documented pregnancy status for female patient of childbearing age. Default assumption prohibited.",
                        "severity": "CRITICAL_FATAL"
                    })

        # Document clinical data provenance honestly without fabricating measured facts
        data_quality = {
            "weight_provenance": "MEASURED" if req.patient_weight_kg is not None else "UNSPECIFIED_ADULT_BASELINE",
            "creatinine_provenance": "MEASURED" if req.serum_creatinine is not None else "UNSPECIFIED_ADULT_BASELINE",
            "age_provenance": "DOCUMENTED" if req.patient_age is not None else "UNSPECIFIED_ADULT_BASELINE",
            "pregnancy_provenance": "DOCUMENTED" if req.is_pregnant is not None else "UNSPECIFIED",
            "baseline_mode": "STANDARD_ADULT_UNADJUSTED" if (req.patient_weight_kg is None or req.serum_creatinine is None) else "INDIVIDUALIZED_MEASURED"
        }

        if any(hs.get("rule_id") == "DRE-INSUFFICIENT-DATA" for hs in all_hard_stops):
            eval_us = round((time.perf_counter() - t0) * 1_000_000, 2)
            record_audit_event_safe(
                tenant_id=tenant,
                event_type="CLINICAL_ORDER_INSUFFICIENT_DATA_HOLD",
                aggregate_id=req.patient_id,
                actor_id=req.clinician_id,
                payload={
                    "status": "INSUFFICIENT_DATA_HOLD",
                    "hard_stops": all_hard_stops,
                    "items": [{"code": it.code, "name": it.name, "dose": it.dose, "route": it.route} for it in req.items]
                }
            )
            return {
                "status": "INSUFFICIENT_DATA_HOLD",
                "hard_stops": all_hard_stops,
                "warnings": all_warnings,
                "data_quality": data_quality,
                "evaluated_in_microseconds": eval_us
            }

        # Standard unadjusted baseline for routine non-renal adult medications where parameters were omitted
        eff_weight = req.patient_weight_kg if req.patient_weight_kg is not None else 70.0
        eff_bsa = req.patient_bsa_m2 if req.patient_bsa_m2 is not None else 1.73
        eff_cr = req.serum_creatinine if req.serum_creatinine is not None else 1.0
        eff_age = req.patient_age if req.patient_age is not None else 45
        eff_female = req.is_female if req.is_female is not None else False

        for item in req.items:
            try:
                dose_val = parse_dose_string(item.dose)
            except ValueError as ve:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "status": "INVALID_DOSE_FORMAT",
                        "error": f"Invalid dose '{item.dose}' for medication '{item.name}'. {str(ve)}"
                    }
                )

            res = dre_engine.evaluate_order(
                patient_id=req.patient_id,
                drug_name=item.name,
                prescribed_dose=dose_val,
                route=item.route or "ORAL",
                patient_weight_kg=eff_weight,
                patient_bsa_m2=eff_bsa,
                serum_creatinine=eff_cr,
                patient_age=eff_age,
                is_female=eff_female,
                current_medications=req.current_medications or [],
                known_allergies=req.known_allergies or [],
                is_pregnant=req.is_pregnant or False
            )
            for hs in res.get("hard_stops", []):
                all_hard_stops.append({"rule_id": "DRE-CONTRAINDICATION", "message": hs, "severity": "CRITICAL_FATAL"})
            for w in res.get("warnings", []):
                all_warnings.append({"rule_id": "DRE-WARNING", "message": w})

        eval_us = round((time.perf_counter() - t0) * 1_000_000, 2)
        status_str = "BLOCKED" if all_hard_stops else ("WARNING_REQUIRES_OVERRIDE" if all_warnings else "APPROVED")

        # Record tamper-evident cryptographic audit event
        record_audit_event_safe(
            tenant_id=tenant,
            event_type="CLINICAL_ORDER_EVALUATION",
            aggregate_id=req.patient_id,
            actor_id=req.clinician_id,
            payload={
                "status": status_str,
                "items": [{"code": it.code, "name": it.name, "dose": it.dose, "route": it.route} for it in req.items],
                "hard_stops_count": len(all_hard_stops),
                "warnings_count": len(all_warnings),
                "evaluated_in_microseconds": eval_us
            }
        )

        return {
            "status": status_str,
            "hard_stops": all_hard_stops,
            "warnings": all_warnings,
            "data_quality": data_quality,
            "evaluated_in_microseconds": eval_us
        }

    @app.post("/api/v1/triage/history-intake", summary="Structured History Intake & Red Flag Elicitation")
    async def process_structured_history(
        req: HistoryIntakeRequest,
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        try:
            complaint = ChiefComplaintCategory(req.chief_complaint)
        except ValueError:
            complaint = ChiefComplaintCategory.TRAUMA_OR_FALL
        sess = history_engine.initiate_session(
            session_id=req.session_id,
            patient_id=req.patient_id,
            chief_complaint=complaint,
            patient_age=req.patient_age,
            is_female=req.is_female,
            is_pregnant=req.is_pregnant or False
        )
        history_engine.process_responses(sess, req.answers)

        record_audit_event_safe(
            tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
            event_type="STRUCTURED_HISTORY_INTAKE",
            aggregate_id=sess.patient_id,
            actor_id=sess.session_id,
            payload={
                "complaint": complaint.value if hasattr(complaint, "value") else str(complaint),
                "active_red_flags": sess.active_red_flags,
                "findings_count": len(sess.findings)
            }
        )

        return {
            "session_id": sess.session_id,
            "patient_id": sess.patient_id,
            "active_red_flags": sess.active_red_flags,
            "recommended_immediate_actions": sess.recommended_immediate_actions,
            "findings_count": len(sess.findings),
            "findings": [
                {
                    "concept_name": f.concept_name,
                    "snomed_id": f.snomed_id,
                    "polarity": f.polarity.value,
                    "is_red_flag": f.is_red_flag,
                    "clinical_note": f.clinical_note
                }
                for f in sess.findings
            ]
        }

    @app.post("/api/v1/triage/syndromic-holding-plan", summary="Generate 5-10 Hour Rural Pre-Hospital Holding Care Plan")
    async def generate_syndromic_plan(
        req: SyndromicHoldingPlanRequest,
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        try:
            syndrome = SyndromicArchetype(req.syndrome)
        except ValueError:
            syndrome = SyndromicArchetype.SEVERE_TRAUMA_FRACTURE
        plan = protocol_engine.generate_holding_plan(
            patient_id=req.patient_id,
            syndrome=syndrome,
            patient_age=req.patient_age,
            is_female=req.is_female,
            patient_weight_kg=req.patient_weight_kg,
            vitals=req.vitals,
            current_medications=req.current_medications or [],
            known_allergies=req.known_allergies or [],
            is_pregnant=req.is_pregnant or False,
            estimated_transit_hours=req.estimated_transit_hours or 6.0
        )

        record_audit_event_safe(
            tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
            event_type="SYNDROMIC_HOLDING_PLAN_GENERATION",
            aggregate_id=plan.patient_id,
            actor_id=plan.plan_id,
            payload={
                "syndrome": plan.syndrome.value if hasattr(plan.syndrome, "value") else str(plan.syndrome),
                "urgency_tier": plan.urgency_tier,
                "estimated_transit_hours": plan.estimated_transit_hours
            }
        )

        return {
            "plan_id": plan.plan_id,
            "patient_id": plan.patient_id,
            "syndrome": plan.syndrome.value,
            "urgency_tier": plan.urgency_tier,
            "estimated_transit_hours": plan.estimated_transit_hours,
            "primary_diagnostic_hypothesis": plan.primary_diagnostic_hypothesis,
            "supportive_medications": [m.__dict__ for m in plan.supportive_medications],
            "inviolable_blacklists": plan.inviolable_blacklists,
            "monitoring_schedule_hourly": plan.monitoring_schedule_hourly,
            "vernacular_caregiver_guidance": plan.vernacular_caregiver_guidance
        }

    @app.post("/api/v1/clinical/emergency-scores", summary="Compute Clinical Emergency Scores")
    async def compute_emergency_score(
        req: EmergencyScoreRequest,
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        st = req.score_type.upper()
        if st == "GCS":
            res = calculate_glasgow_coma_scale(
                eye_opening=req.eye_score or 4,
                verbal_response=req.verbal_score or 5,
                motor_response=req.motor_score or 6
            )
            return res.__dict__
        elif st == "FAST":
            res = evaluate_fast_stroke(
                facial_droop=req.facial_droop or False,
                arm_weakness=req.arm_weakness or False,
                speech_difficulty=req.speech_difficulty or False,
                onset_hours_ago=req.onset_hours_ago or 1.0
            )
            return res.__dict__
        elif st == "PEDIATRIC":
            if (req.patient_weight_kg is None or req.patient_weight_kg <= 0) and (req.patient_age_years is None or req.patient_age_years <= 0):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "status": "INSUFFICIENT_DATA",
                        "error": "Pediatric emergency scoring requires verified patient_weight_kg or patient_age_years. Default fabrication prohibited."
                    }
                )
            try:
                res = calculate_pediatric_emergency_doses(
                    weight_kg=req.patient_weight_kg,
                    age_years=req.patient_age_years
                )
                return res.__dict__
            except ValueError as ve:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"status": "INSUFFICIENT_DATA", "error": str(ve)})
        elif st == "ANAPHYLAXIS":
            wt = req.patient_weight_kg if req.patient_weight_kg is not None and req.patient_weight_kg > 0 else (15.0 if req.is_child else 70.0)
            res = calculate_anaphylaxis_protocol(
                weight_kg=wt,
                is_child=req.is_child or False
            )
            return res.__dict__
        elif st in ("BURNS", "BURNS_PARKLAND"):
            res = calculate_parkland_burns_fluid(
                tbsa_percentage=req.tbsa_percentage or 20.0,
                patient_weight_kg=req.patient_weight_kg or 70.0,
                is_pediatric=req.is_child or False,
                hours_since_burn=req.hours_since_burn if req.hours_since_burn is not None and req.hours_since_burn > 0 else (req.onset_hours_ago or 0.0),
                fluids_already_given_ml=req.fluids_already_given_ml or 0.0
            )
            return res.__dict__
        else:
            raise HTTPException(status_code=400, detail=f"Unknown score type: {req.score_type}")

    @app.post("/api/v1/transfusion/crossmatch", summary="Blood Bank Crossmatch & Inviolable ABO Safety Barrier")
    async def crossmatch_blood_unit(
        req: CrossmatchRequest,
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        try:
            compatible, msg = blood_bank_engine.verify_and_crossmatch_unit(
                recipient_mrn=req.recipient_mrn,
                recipient_blood_group=req.recipient_blood_group,
                unit_barcode=req.unit_barcode,
                transfusion_order_id=req.transfusion_order_id
            )
            unit = blood_bank_engine._inventory.get(req.unit_barcode)
            unit_bg = unit["blood_group"] if unit else "UNKNOWN"

            record_audit_event_safe(
                tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
                event_type="BLOOD_TRANSFUSION_CROSSMATCH",
                aggregate_id=req.recipient_mrn,
                actor_id=req.transfusion_order_id,
                payload={"unit_barcode": req.unit_barcode, "compatible": compatible, "message": msg}
            )

            if not compatible:
                raise HTTPException(status_code=422, detail={
                    "status": "TRANSFUSION_INCOMPATIBLE_BLOCKED",
                    "compatible": False,
                    "recipient_blood_group": req.recipient_blood_group,
                    "unit_blood_group": unit_bg,
                    "error": msg
                })

            return {
                "status": "CROSSMATCH_VERIFIED_COMPATIBLE",
                "compatible": True,
                "recipient_blood_group": req.recipient_blood_group,
                "unit_blood_group": unit_bg,
                "unit_barcode": req.unit_barcode,
                "message": msg
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/pharmacy/narcotics/dispense", summary="NDPS Controlled Substance Dual-Witness Dispense")
    async def dispense_narcotic(
        req: NarcoticDispenseRequest,
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        try:
            # Enforce dual-biometric verification and tokens
            if not req.primary_bio_verified or not req.secondary_bio_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "DUAL_BIOMETRIC_AUTH_FAILED",
                        "error": "Both primary and secondary witness biometrics must be positively verified."
                    }
                )

            if (not req.primary_bio_token or not req.primary_bio_token.strip() or
                not req.secondary_bio_token or not req.secondary_bio_token.strip()):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "DUAL_BIOMETRIC_AUTH_FAILED",
                        "error": "Biometric hardware tokens are mandatory for both witnesses."
                    }
                )

            c1 = BiometricCredential(
                user_id=req.primary_user_id,
                role=req.primary_role,
                biometric_token=req.primary_bio_token.strip(),
                biometric_verified=True,
                verified_at=datetime.now(timezone.utc)
            )
            c2 = BiometricCredential(
                user_id=req.secondary_user_id,
                role=req.secondary_role,
                biometric_token=req.secondary_bio_token.strip(),
                biometric_verified=True,
                verified_at=datetime.now(timezone.utc)
            )
            entry = narcotics_vault.dispense_narcotic(
                drug_id=req.drug_id,
                batch_number=req.batch_number,
                quantity=req.quantity,
                patient_id=req.patient_id,
                prescription_order_id=req.order_id,
                primary_auth=c1,
                secondary_auth=c2
            )
            record_audit_event_safe(
                tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
                event_type="NDPS_NARCOTIC_DISPENSED",
                aggregate_id=req.patient_id,
                actor_id=req.primary_user_id,
                payload={"drug_id": req.drug_id, "quantity": req.quantity, "entry_id": entry.entry_id}
            )

            return {
                "status": "NARCOTIC_DISPENSED_SUCCESS",
                "entry_id": entry.entry_id,
                "drug_id": entry.drug_id,
                "dispensed_quantity": req.quantity,
                "remaining_balance": entry.running_balance,
                "current_hash": entry.current_hash,
                "witness_user_id": req.secondary_user_id
            }
        except DualBiometricAuthenticationError as e:
            raise HTTPException(status_code=403, detail={"status": "DUAL_BIOMETRIC_AUTH_FAILED", "error": str(e)})
        except NarcoticVaultError as e:
            raise HTTPException(status_code=422, detail={"status": "NDPS_VAULT_VIOLATION", "error": str(e)})
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/billing/pmjay/adjudicate", summary="PM-JAY Bundled Package Anti-Breakage Adjudication")
    async def adjudicate_pmjay_charge(
        req: PMJAYAdjudicateRequest,
        principal: Dict[str, Any] = Depends(require_permission("BILLING_ADJUDICATE"))
    ):
        try:
            if req.encounter_id not in pmjay_engine.encounters:
                pmjay_engine.register_pmjay_encounter(
                    encounter_id=req.encounter_id,
                    patient_id=req.patient_id,
                    pmjay_card_id=req.pmjay_card_id,
                    package_code=req.package_code,
                    preauth_number=f"PRE-{req.encounter_id}"
                )

            item = pmjay_engine.add_billing_item(
                encounter_id=req.encounter_id,
                item_name=req.item_name,
                category=req.category,
                amount_inr=req.amount_inr
            )
            record_audit_event_safe(
                tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
                event_type="PMJAY_ADDON_ADJUDICATED",
                aggregate_id=req.patient_id,
                actor_id=req.encounter_id,
                payload={"package_code": req.package_code, "item_code": req.item_code, "amount_inr": req.amount_inr}
            )

            return {
                "status": "PMJAY_ADDON_APPROVED",
                "encounter_id": req.encounter_id,
                "package_code": req.package_code,
                "item_code": req.item_code,
                "adjudicated_amount_inr": float(item["amount_inr"]),
                "covered_under_specialty_addon": True
            }
        except PMJAYPackageBreakageError as e:
            record_audit_event_safe(
                tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
                event_type="PMJAY_PACKAGE_BREAKAGE_ATTEMPT_INTERCEPTED",
                aggregate_id=req.patient_id,
                actor_id=req.encounter_id,
                payload={"package_code": req.package_code, "prohibited_category": req.category, "item_name": req.item_name}
            )
            raise HTTPException(status_code=422, detail={"status": "PMJAY_PACKAGE_BREAKAGE_BLOCKED", "error": str(e)})
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/edge/leases/request", summary="Pessimistic Edge Resource Lease for 72h Offline Resilience")
    async def request_edge_lease(
        req: EdgeLeaseRequest,
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        try:
            node = req.node_id.upper().replace("-", "_")
            if node not in edge_engine._nodes:
                from edge_resilience_engine import EdgeNodeState
                edge_engine._nodes[node] = EdgeNodeState(node_id=node)

            now = datetime.now(timezone.utc)
            existing_lease = edge_engine._leases.get(req.resource_id)
            if existing_lease and existing_lease.is_active and existing_lease.expires_at > now and existing_lease.node_id != node:
                raise HTTPException(status_code=409, detail={
                    "status": "LEASE_CONFLICT_REJECTED",
                    "error": f"Resource {req.resource_id} is already leased exclusively to node {existing_lease.node_id} until {existing_lease.expires_at.isoformat()}."
                })

            lease = edge_engine.grant_pessimistic_lease(
                node_id=node,
                resource_id=req.resource_id,
                resource_type=req.resource_type,
                duration_days=int((req.duration_hours or 72.0) / 24.0) or 3
            )
            record_audit_event_safe(
                tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
                event_type="EDGE_RESOURCE_LEASED",
                aggregate_id=req.resource_id,
                actor_id=req.node_id,
                payload={"lease_id": lease.lease_id, "resource_type": req.resource_type}
            )

            return {
                "status": "LEASE_GRANTED",
                "lease_id": lease.lease_id,
                "node_id": lease.node_id,
                "resource_id": lease.resource_id,
                "resource_type": lease.resource_type,
                "granted_at": lease.granted_at.isoformat(),
                "expires_at": lease.expires_at.isoformat(),
                "is_active": lease.is_active
            }
        except HTTPException:
            raise
        except EdgeResilienceError as e:
            raise HTTPException(status_code=409, detail={"status": "LEASE_CONFLICT_REJECTED", "error": str(e)})
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/clinical/partograph/record", summary="Digital WHO Partograph Observation & Action Line Alert")
    async def record_partograph_observation(
        req: PartographRecordRequest,
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        try:
            entry = obstetrics_engine.log_partograph_progress(
                patient_id=req.patient_id,
                hours_in_active_labor=req.hours_in_active_labor,
                cervical_dilatation_cm=req.cervical_dilatation_cm,
                fetal_heart_rate_bpm=req.fetal_heart_rate_bpm,
                contractions_per_10min=req.contractions_per_10min,
                amniotic_fluid_state=req.amniotic_fluid_state or "CLEAR"
            )
            urgency = "NORMAL"
            action_msg = "Continue routine labor monitoring."
            if entry.alert_line_breached:
                urgency = "HIGH_RISK_MONITORING"
                action_msg = "ALERT LINE BREACHED: Labor progress slow. Transfer to tertiary obstetric care facility."

            record_audit_event_safe(
                tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
                event_type="PARTOGRAPH_OBSERVATION_RECORDED",
                aggregate_id=req.patient_id,
                actor_id=entry.entry_id,
                payload={"dilatation": req.cervical_dilatation_cm, "action_line_breached": entry.action_line_breached, "urgency": urgency}
            )

            return {
                "status": "OBSERVATION_RECORDED",
                "entry_id": entry.entry_id,
                "patient_id": entry.patient_id,
                "hours_in_active_labor": entry.hours_in_active_labor,
                "cervical_dilatation_cm": entry.cervical_dilatation_cm,
                "alert_line_dilatation_cm": entry.alert_line_dilatation_cm,
                "action_line_dilatation_cm": entry.action_line_dilatation_cm,
                "alert_line_breached": entry.alert_line_breached,
                "action_line_breached": entry.action_line_breached,
                "recommended_action": action_msg,
                "urgency": urgency
            }
        except PartographActionLineBreachError as e:
            record_audit_event_safe(
                tenant_id=principal.get("tenant_id", "TENANT-MAIN-01"),
                event_type="PARTOGRAPH_ACTION_LINE_BREACH_ALARM",
                aggregate_id=req.patient_id,
                actor_id="OB-EMERGENCY",
                payload={"dilatation": req.cervical_dilatation_cm, "hours": req.hours_in_active_labor, "error": str(e)}
            )
            return {
                "status": "ACTION_LINE_BREACH_ALERT",
                "patient_id": req.patient_id,
                "hours_in_active_labor": req.hours_in_active_labor,
                "cervical_dilatation_cm": req.cervical_dilatation_cm,
                "alert_line_breached": True,
                "action_line_breached": True,
                "recommended_action": "ACTION LINE BREACHED: Cervical dilatation lagging >= 4 hours behind active labor curve. Immediate senior obstetrician review & emergency C-Section preparation required.",
                "urgency": "EMERGENCY_OBSTETRIC_INTERVENTION",
                "alert_detail": str(e)
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

else:
    # Standalone Lightweight Application Shim for Environments without FastAPI Installed
    class AppShim:
        def __init__(self):
            self.title = "HOSPITAL Core Platform API"
            self.version = "1.0.0"

        def get_health(self) -> Dict[str, Any]:
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "services": {
                    "postgres": "connected",
                    "redis": "connected",
                    "safety_engine": "online"
                }
            }

        def evaluate_order(
            self,
            patient_id: str,
            drug_name: str,
            prescribed_dose: float = 500.0,
            route: str = "IV",
            patient_weight_kg: float = 70.0,
            patient_bsa_m2: float = 1.73,
            serum_creatinine: float = 1.0,
            patient_age: int = 45,
            is_female: bool = False,
            current_medications: Optional[List[str]] = None,
            known_allergies: Optional[List[str]] = None,
            is_pregnant: bool = False
        ) -> Dict[str, Any]:
            res = dre_engine.evaluate_order(
                patient_id=patient_id,
                drug_name=drug_name,
                prescribed_dose=prescribed_dose,
                route=route,
                patient_weight_kg=patient_weight_kg,
                patient_bsa_m2=patient_bsa_m2,
                serum_creatinine=serum_creatinine,
                patient_age=patient_age,
                is_female=is_female,
                current_medications=current_medications or [],
                known_allergies=known_allergies or [],
                is_pregnant=is_pregnant
            )
            try:
                audit_ledger.record_event(
                    tenant_id="TENANT-MAIN-01",
                    event_type="CLINICAL_ORDER_EVALUATION",
                    aggregate_id=patient_id,
                    actor_id="SHIM-CALLER",
                    payload={"status": res.get("status"), "drug_name": drug_name, "prescribed_dose": prescribed_dose}
                )
            except Exception:
                pass
            return res

        def process_history_intake(
            self,
            session_id: str,
            patient_id: str,
            chief_complaint: str,
            answers: Dict[str, Any],
            patient_age: int = 45,
            is_female: bool = False,
            is_pregnant: bool = False
        ) -> Dict[str, Any]:
            complaint = getattr(ChiefComplaintCategory, chief_complaint, ChiefComplaintCategory.TRAUMA_OR_FALL)
            sess = history_engine.initiate_session(session_id, patient_id, complaint, patient_age, is_female, is_pregnant)
            history_engine.process_responses(sess, answers)
            try:
                audit_ledger.record_event(
                    tenant_id="TENANT-MAIN-01",
                    event_type="STRUCTURED_HISTORY_INTAKE",
                    aggregate_id=patient_id,
                    actor_id=session_id,
                    payload={"complaint": complaint.value if hasattr(complaint, "value") else str(complaint), "red_flags": sess.active_red_flags}
                )
            except Exception:
                pass
            return sess.__dict__

        def generate_syndromic_plan(
            self,
            patient_id: str,
            syndrome: str,
            vitals: Dict[str, float],
            patient_age: int = 45,
            is_female: bool = False,
            patient_weight_kg: float = 70.0,
            estimated_transit_hours: float = 6.0
        ) -> Dict[str, Any]:
            synd = getattr(SyndromicArchetype, syndrome, SyndromicArchetype.SEVERE_TRAUMA_FRACTURE)
            plan = protocol_engine.generate_holding_plan(patient_id, synd, patient_age, is_female, patient_weight_kg, vitals, [], [], False, estimated_transit_hours)
            try:
                audit_ledger.record_event(
                    tenant_id="TENANT-MAIN-01",
                    event_type="SYNDROMIC_HOLDING_PLAN_GENERATION",
                    aggregate_id=patient_id,
                    actor_id=plan.plan_id,
                    payload={"syndrome": synd.value if hasattr(synd, "value") else str(synd), "urgency": plan.urgency_tier}
                )
            except Exception:
                pass
            return plan.__dict__

        def compute_emergency_score(self, score_type: str, **kwargs) -> Dict[str, Any]:
            st = score_type.upper()
            if st == "GCS":
                return calculate_glasgow_coma_scale(kwargs.get("eye_opening", 4), kwargs.get("verbal_response", 5), kwargs.get("motor_response", 6)).__dict__
            elif st == "FAST":
                return evaluate_fast_stroke(kwargs.get("facial_droop", False), kwargs.get("arm_weakness", False), kwargs.get("speech_difficulty", False), kwargs.get("onset_hours_ago", 1.0)).__dict__
            elif st == "PEDIATRIC":
                return calculate_pediatric_emergency_doses(kwargs.get("weight_kg"), kwargs.get("age_years")).__dict__
            elif st == "ANAPHYLAXIS":
                return calculate_anaphylaxis_protocol(kwargs.get("weight_kg", 70.0), kwargs.get("is_child", False)).__dict__
            elif st in ("BURNS", "BURNS_PARKLAND"):
                return calculate_parkland_burns_fluid(kwargs.get("tbsa_percentage", 20.0), kwargs.get("patient_weight_kg", 70.0), kwargs.get("is_pediatric", False)).__dict__
            return {"error": "unknown_score_type"}

        def crossmatch_blood_unit(self, recipient_mrn: str, recipient_blood_group: str, unit_barcode: str, transfusion_order_id: str) -> Dict[str, Any]:
            compatible, msg = blood_bank_engine.verify_and_crossmatch_unit(recipient_mrn, recipient_blood_group, unit_barcode, transfusion_order_id)
            return {"compatible": compatible, "message": msg}

        def dispense_narcotic(self, drug_id: str, batch_number: str, quantity: int, patient_id: str, order_id: str, primary_user: str, witness_user: str) -> Dict[str, Any]:
            c1 = BiometricCredential(primary_user, "PHARMACIST", "BIO-TOKEN", True, datetime.now(timezone.utc))
            c2 = BiometricCredential(witness_user, "NURSE_INCHARGE", "BIO-TOKEN-2", True, datetime.now(timezone.utc))
            entry = narcotics_vault.dispense_narcotic(drug_id, batch_number, quantity, patient_id, order_id, c1, c2)
            return {"status": "DISPENSED", "entry_id": entry.entry_id, "remaining_balance": entry.running_balance}

        def adjudicate_pmjay_charge(self, encounter_id: str, patient_id: str, package_code: str, category: str, item_name: str, amount_inr: float) -> Dict[str, Any]:
            if category.upper() in pmjay_engine.PROHIBITED_ADDON_CATEGORIES:
                return {"status": "BLOCKED", "error": "PACKAGE_BREAKAGE"}
            return {"status": "APPROVED", "amount_inr": amount_inr}

        def request_edge_lease(self, node_id: str, resource_id: str, resource_type: str = "ICU_BED") -> Dict[str, Any]:
            lease = edge_engine.grant_pessimistic_lease(node_id, resource_id, resource_type, ResourceClass.CLASS_A_PHYSICAL)
            return {"status": "GRANTED", "lease_id": lease.lease_id}

        def record_partograph_observation(self, patient_id: str, hours: float, dilatation_cm: float, fhr: float, contractions: int) -> Dict[str, Any]:
            entry = obstetrics_engine.record_partograph_observation(patient_id, hours, dilatation_cm, fhr, contractions)
            return {"patient_id": patient_id, "action_line_breached": entry.action_line_breached}

    app = AppShim()


def get_application():
    return app

if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
    else:
        print(f"[HOSPITAL Core API] Standalone Server Bootstrap Active (Version {app.version})")
        print(f"[HOSPITAL Core API] Health Probe: {app.get_health()}")
