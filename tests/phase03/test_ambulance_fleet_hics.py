#!/usr/bin/env python3
"""
Ambulance Fleet, Visitor Management & HICS Disaster Verification Test Suite (Phase 03).
Tests sub-10ms nearest ambulance dispatch, pre-hospital vitals telemetry,
visitor quotas, epidemic lockdown mode, and HICS disaster oxygen runway calculation.
"""
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from ambulance_fleet_engine import AmbulanceFleetEngine, AmbulanceCapability
from visitor_management import VisitorManagementEngine
from hics_disaster_engine import HICSDisasterEngine, HICSAlertLevel

def test_ambulance_fleet_hics():
    print("================================================================================")
    print(" [AMBULANCE, VISITOR & HICS TEST SUITE] VERIFYING FLEET, EPIDEMIC & DISASTER")
    print("================================================================================")

    TENANT_ID = "11111111-1111-1111-1111-111111111111"

    # 1. Test Ambulance Fleet Nearest Dispatch
    fleet = AmbulanceFleetEngine()
    # Register BLS ambulance close to incident
    fleet.register_ambulance("AMB-BLS-01", "WB-01-A-1001", AmbulanceCapability.BLS, 22.5700, 88.3600)
    # Register ALS ambulance slightly further
    fleet.register_ambulance("AMB-ALS-01", "WB-01-A-9999", AmbulanceCapability.ALS, 22.5800, 88.3700)

    # Incident: Severe myocardial infarction requiring ALS
    incident_lat, incident_lon = 22.5710, 88.3620

    t0 = time.perf_counter()
    dispatched, dist_km = fleet.dispatch_nearest_ambulance(
        incident_lat, incident_lon, required_capability=AmbulanceCapability.ALS
    )
    dispatch_latency_ms = (time.perf_counter() - t0) * 1000

    assert dispatched is not None
    assert dispatched["vehicle_id"] == "AMB-ALS-01" # Chose ALS despite BLS being closer
    assert dispatched["capability"] == AmbulanceCapability.ALS
    print(f" [PASS] Nearest ALS ambulance dispatched in {dispatch_latency_ms:.2f} ms ({dispatched['reg_number']} - {dist_km:.2f} km).")
    assert dispatch_latency_ms < 10.0, "Dispatch algorithm exceeded 10ms threshold!"

    # 2. Test Pre-Hospital Telemetry Streaming
    telemetry = fleet.stream_pre_hospital_telemetry(
        vehicle_id="AMB-ALS-01",
        heart_rate=118,
        systolic_bp=85,
        diastolic_bp=55,
        spo2=88.5, # Critical hypoxia
        ecg_lead2_status="ST_ELEVATION_SUSPECTED_ANTERIOR",
        estimated_arrival_mins=8
    )
    assert telemetry["hospital_resuscitation_bay_alert"] is True
    print(f" [PASS] Pre-hospital telemetry alert sent to Resuscitation Bay (SpO2 {telemetry['spo2']}%, ETA {telemetry['eta_minutes']} mins).")

    # 3. Test Visitor Management Quotas & Epidemic Lockdown
    vm = VisitorManagementEngine(tenant_id=TENANT_ID)
    # Bed 1 in ICU (Quota: 1 visitor)
    ok1, _, pass1 = vm.issue_visitor_pass("Arup Mukherjee", "MRN-100", "ICU-BED-04", "INTENSIVE_CARE_UNIT")
    assert ok1 is True
    # Second visitor for same ICU bed -> BLOCKED BY QUOTA
    ok2, quota_msg, _ = vm.issue_visitor_pass("Priya Mukherjee", "MRN-100", "ICU-BED-04", "INTENSIVE_CARE_UNIT")
    assert ok2 is False
    assert "QUOTA_EXCEEDED" in quota_msg
    print(" [PASS] ICU visitor quota strictly enforced (1 visitor per bed).")

    # Activate Epidemic Lockdown Mode
    lockdown = vm.activate_epidemic_lockdown("Dr. Medical Superintendent", "Novel Respiratory Pathogen Cluster")
    assert lockdown["status"] == "EPIDEMIC_LOCKDOWN_ACTIVE"
    assert lockdown["revoked_passes_count"] == 1
    # New visitor attempt during lockdown -> BLOCKED
    ok3, lock_msg, _ = vm.issue_visitor_pass("Visitor X", "MRN-200", "GEN-BED-12", "GENERAL_WARD")
    assert ok3 is False
    assert "EPIDEMIC_LOCKDOWN" in lock_msg
    print(" [PASS] One-click Epidemic Lockdown mode revoked active passes and blocked new entries.")

    # 4. Test HICS Disaster Engine
    hics = HICSDisasterEngine(tenant_id=TENANT_ID)
    elective_surgeries = [
        {"surgery_id": "SURG-EL-01", "type": "ELECTIVE", "procedure": "Knee Arthroscopy"},
        {"surgery_id": "SURG-EM-02", "type": "EMERGENCY", "procedure": "Ruptured Ectopic Pregnancy"}
    ]
    off_duty_staff = [
        {"staff_id": "ST-01", "name": "Dr. Pradip Roy", "role": "ANESTHESIOLOGIST", "phone": "9830000001"},
        {"staff_id": "ST-02", "name": "Nurse Maya Sen", "role": "ICU_NURSE", "phone": "9830000002"}
    ]
    hics.load_operational_state(elective_surgeries, off_duty_staff)

    # Activate Level 3 External Disaster (Train derailment / Mass casualty)
    disaster_dossier = hics.activate_disaster_surge(
        target_level=HICSAlertLevel.LEVEL_3_EXTERNAL_DISASTER,
        incident_type="MASS_CASUALTY_TRAIN_DERAILMENT",
        incident_commander="Dr. Superintendent"
    )
    assert disaster_dossier["elective_surgeries_cancelled_count"] == 1
    assert disaster_dossier["staff_recall_count"] == 2
    assert elective_surgeries[0]["status"] == "CANCELLED_DUE_TO_HICS_SURGE"
    assert elective_surgeries[1].get("status") != "CANCELLED_DUE_TO_HICS_SURGE" # Emergency surgery NOT cancelled!
    print(" [PASS] HICS Level 3 Disaster Surge: Elective surgeries cancelled; Emergency surgeries protected; Staff recalled.")

    # 5. Liquid Medical Oxygen (LMO) Runway Calculator
    o2_runway = hics.calculate_oxygen_runway_hours(
        current_liquid_oxygen_liters=5000.0, # 5,000 L of liquid O2
        active_ventilators_count=40,        # 40 * 20 = 800 LPM
        high_flow_nasal_cannula_count=20,   # 20 * 50 = 1000 LPM
        ward_low_flow_patients_count=50     # 50 * 6 = 300 LPM -> Total: 2100 LPM
    )
    # Total gas: 5000 * 860 = 4,300,000 liters. / 2100 LPM = 2047.6 mins = ~34.1 hours
    assert o2_runway["estimated_runway_hours"] > 30.0
    assert o2_runway["critical_low_oxygen_alarm"] is False
    print(f" [PASS] Oxygen Telemetry Runway: {o2_runway['estimated_runway_hours']} hours remaining under peak disaster draw.")

    print("================================================================================")
    print(" AMBULANCE FLEET, VISITOR MANAGEMENT & HICS ENGINES FULLY VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_ambulance_fleet_hics())
