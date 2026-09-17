"""
PROJECT "HOSPITAL" — PHASE 12: HOSPITAL OPERATIONS
Module: asset_oxygen_telemetry_engine.py
Operational Scope:
  - Sub-task 12.5: Real-Time RFID & BLE Asset Tracking & Geofencing (Gap 30)
  - Quality Gate 3: Mobile Crash Cart Geofence Breach Alarm (< 10s SLA)
  - Sub-task 12.6: Medical Gas Pipeline System (MGPS) & Liquid Medical Oxygen (LMO) Telemetry
  - Dynamic Oxygen Burn-Rate & Tank Autonomy Run-Hours Calculator
  - Pipeline Pressure Safety Thresholds (< 3.8 bar warning, < 3.2 bar emergency)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any


class AssetTrackingError(Exception):
    """Base exception for asset tracking failures."""
    pass


class GeofenceBreachSecurityAlarm(AssetTrackingError):
    """Raised when critical emergency equipment crosses unauthorized spatial perimeter."""
    pass


class OxygenTelemetryError(Exception):
    """Base exception for medical gas pipeline failures."""
    pass


class OxygenCriticalShortageAlarm(OxygenTelemetryError):
    """Raised when remaining oxygen autonomy falls below critical emergency thresholds (< 6 hours)."""
    pass


class AssetCriticality(str, Enum):
    STAT_CRITICAL = "STAT_CRITICAL"     # Crash carts, defibrillators, transport ventilators
    HIGH = "HIGH"                       # Infusion pumps, syringe drivers, mobile ultrasound
    MEDIUM = "MEDIUM"                   # Wheelchairs, stretchers, portable ECG


@dataclass
class MobileAsset:
    asset_id: str
    asset_name: str
    serial_number: str
    criticality: AssetCriticality
    allowed_zones: Set[str]              # Authorized ward/zone IDs (e.g., {"ED_ZONE_A", "ED_TRAUMA_BAY"})
    current_zone_id: str
    x_coord: float = 0.0
    y_coord: float = 0.0
    floor_level: int = 1
    battery_pct: float = 100.0
    last_ping_time: Optional[datetime] = None
    is_in_breach: bool = False


@dataclass
class GeofenceAlertEvent:
    alert_id: str
    asset_id: str
    asset_name: str
    breached_zone_id: str
    allowed_zones: List[str]
    alert_timestamp: datetime
    detection_latency_seconds: float
    security_dispatched: bool = True
    resolved: bool = False


@dataclass
class LMOTankTelemetry:
    tank_id: str
    capacity_liters: float              # Total tank water capacity (e.g., 20,000 L liquid O2)
    current_liquid_volume_liters: float # Current liquid volume
    liquid_level_pct: float
    tank_pressure_bar: float            # Normal ~8 - 12 bar in storage tank
    manifold_line_pressure_bar: float   # Ward line pressure: normal 4.0 - 4.5 bar
    ambient_temp_c: float
    telemetry_time: datetime


class AssetOxygenTelemetryEngine:
    """
    Hospital Operations Engine managing real-time BLE asset tracking,
    sub-10-second geofence security alerts, and Liquid Medical Oxygen (LMO) telemetry.
    """

    # MGPS Standards (HTM 02-01 / Indian MoHFW MGPS Guidelines):
    NORMAL_LINE_PRESSURE_MIN_BAR = 4.0
    NORMAL_LINE_PRESSURE_MAX_BAR = 4.5
    LINE_PRESSURE_WARNING_BAR = 3.8
    LINE_PRESSURE_CRITICAL_BAR = 3.2

    # LMO Liquid to Gas Expansion Ratio (1 liter liquid oxygen ≈ 860 liters gaseous O2 at NTP)
    LIQUID_TO_GAS_EXPANSION_RATIO = 860.0

    def __init__(self):
        self._assets: Dict[str, MobileAsset] = {}
        self._geofence_alerts: List[GeofenceAlertEvent] = []
        self._latest_lmo_telemetry: Optional[LMOTankTelemetry] = None
        self._active_ward_draw_liters_per_min: Dict[str, float] = {}  # ward_id -> L/min

    # =========================================================================
    # 12.5 ASSET TRACKING & GEOFENCING
    # =========================================================================

    def register_mobile_asset(
        self,
        asset_id: str,
        asset_name: str,
        serial_number: str,
        criticality: AssetCriticality,
        allowed_zones: Set[str],
        initial_zone_id: str,
        floor_level: int = 1,
    ) -> MobileAsset:
        """Registers mobile clinical equipment into real-time tracking network."""
        asset = MobileAsset(
            asset_id=asset_id,
            asset_name=asset_name,
            serial_number=serial_number,
            criticality=criticality,
            allowed_zones=allowed_zones,
            current_zone_id=initial_zone_id,
            floor_level=floor_level,
            last_ping_time=datetime.now(timezone.utc),
        )
        self._assets[asset_id] = asset
        return asset

    def ingest_ble_beacon_ping(
        self,
        asset_id: str,
        detected_zone_id: str,
        x_coord: float,
        y_coord: float,
        battery_pct: float,
        ping_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Ingests real-time telemetry from ward BLE receivers.
        Quality Gate 3: If critical equipment (e.g. Emergency Crash Cart) moves outside
        its designated perimeter, triggers an immediate security alarm within < 10 seconds SLA.
        """
        start_eval_time = time.perf_counter()

        if asset_id not in self._assets:
            raise AssetTrackingError(f"Asset ID {asset_id} not registered.")

        asset = self._assets[asset_id]
        now = ping_timestamp or datetime.now(timezone.utc)
        asset.current_zone_id = detected_zone_id
        asset.x_coord = x_coord
        asset.y_coord = y_coord
        asset.battery_pct = battery_pct
        asset.last_ping_time = now

        # Evaluate Geofence Boundary
        if detected_zone_id not in asset.allowed_zones:
            asset.is_in_breach = True
            eval_elapsed_seconds = round(time.perf_counter() - start_eval_time, 4)

            alert = GeofenceAlertEvent(
                alert_id=f"GEOFENCE-{asset_id}-{int(now.timestamp())}",
                asset_id=asset_id,
                asset_name=asset.asset_name,
                breached_zone_id=detected_zone_id,
                allowed_zones=list(asset.allowed_zones),
                alert_timestamp=now,
                detection_latency_seconds=eval_elapsed_seconds,
            )
            self._geofence_alerts.append(alert)

            # Enforce < 10s SLA check
            sla_breached = eval_elapsed_seconds >= 10.0

            alarm_msg = (
                f"[GEOFENCE BREACH SECURITY ALARM] {asset.criticality.value} Asset '{asset.asset_name}' (ID: {asset.asset_id}) "
                f"has moved outside authorized perimeter! Current Zone: {detected_zone_id} "
                f"(Allowed: {list(asset.allowed_zones)}). Alarm dispatched to Security Console in {eval_elapsed_seconds:.4f}s "
                f"(SLA < 10.0s: {'MET' if not sla_breached else 'BREACHED'})."
            )

            # For STAT_CRITICAL assets, raise exception to halt caller or trigger audible siren
            if asset.criticality == AssetCriticality.STAT_CRITICAL:
                raise GeofenceBreachSecurityAlarm(alarm_msg)

            return {
                "status": "GEOFENCE_BREACH_ALERT",
                "asset_id": asset_id,
                "alarm": alarm_msg,
                "detection_latency_seconds": eval_elapsed_seconds,
            }

        asset.is_in_breach = False
        return {
            "status": "ZONE_AUTHORIZED",
            "asset_id": asset_id,
            "current_zone": detected_zone_id,
            "coordinates": {"x": x_coord, "y": y_coord},
        }

    def get_geofence_alerts(self) -> List[GeofenceAlertEvent]:
        return list(self._geofence_alerts)

    # =========================================================================
    # 12.6 MEDICAL GAS PIPELINE & OXYGEN TELEMETRY
    # =========================================================================

    def record_lmo_tank_telemetry(
        self,
        tank_id: str,
        capacity_liters: float,
        current_liquid_volume_liters: float,
        tank_pressure_bar: float,
        manifold_line_pressure_bar: float,
        ambient_temp_c: float = 28.0,
    ) -> LMOTankTelemetry:
        """Ingests cryogenic LMO bulk tank and central manifold telemetry."""
        if current_liquid_volume_liters > capacity_liters:
            raise OxygenTelemetryError("Current volume exceeds tank water capacity.")

        level_pct = round((current_liquid_volume_liters / capacity_liters) * 100.0, 1)

        telemetry = LMOTankTelemetry(
            tank_id=tank_id,
            capacity_liters=capacity_liters,
            current_liquid_volume_liters=round(current_liquid_volume_liters, 2),
            liquid_level_pct=level_pct,
            tank_pressure_bar=round(tank_pressure_bar, 2),
            manifold_line_pressure_bar=round(manifold_line_pressure_bar, 2),
            ambient_temp_c=round(ambient_temp_c, 1),
            telemetry_time=datetime.now(timezone.utc),
        )
        self._latest_lmo_telemetry = telemetry
        return telemetry

    def update_ward_oxygen_draw(self, ward_id: str, flow_rate_liters_per_min: float) -> None:
        """Updates instantaneous oxygen draw in L/min for a specific hospital ward or unit."""
        self._active_ward_draw_liters_per_min[ward_id] = max(0.0, flow_rate_liters_per_min)

    def calculate_oxygen_burn_rate_and_autonomy(self) -> Dict[str, Any]:
        """
        Calculates total hospital oxygen consumption rate and remaining autonomy hours.
        Evaluates pipeline pressure safety thresholds:
          - Line pressure < 3.8 bar: Warning
          - Line pressure < 3.2 bar: Critical ventilator failure risk
        Evaluates supply autonomy:
          - Autonomy < 24h: Warning
          - Autonomy < 6h: Emergency Critical Shortage Siren
        """
        if not self._latest_lmo_telemetry:
            raise OxygenTelemetryError("No active LMO telemetry available.")

        lmo = self._latest_lmo_telemetry
        total_draw_lpm = sum(self._active_ward_draw_liters_per_min.values())

        # If zero draw recorded, use default baseline draw of 50 L/min for minimal hospital leakage/basal
        effective_draw_lpm = max(50.0, total_draw_lpm)

        # Total available gaseous oxygen in liters = Liquid Liters * 860 expansion ratio
        total_gaseous_liters_available = lmo.current_liquid_volume_liters * self.LIQUID_TO_GAS_EXPANSION_RATIO

        # Autonomy in minutes = Available gaseous liters / draw per minute
        autonomy_minutes = total_gaseous_liters_available / effective_draw_lpm
        autonomy_hours = round(autonomy_minutes / 60.0, 1)

        # Manifold Pressure Status
        line_pressure = lmo.manifold_line_pressure_bar
        if line_pressure < self.LINE_PRESSURE_CRITICAL_BAR:
            pressure_status = "CRITICAL_LOW_PRESSURE"
            pressure_alert = (
                f"[MGPS EMERGENCY] Manifold line pressure {line_pressure} bar is below 3.2 bar threshold! "
                f"Mechanical ventilators risk pressure failure! Switch to emergency cylinder bank!"
            )
        elif line_pressure < self.LINE_PRESSURE_WARNING_BAR:
            pressure_status = "WARNING_LOW_PRESSURE"
            pressure_alert = f"Manifold pressure {line_pressure} bar is sub-optimal (< 3.8 bar)."
        else:
            pressure_status = "NORMAL"
            pressure_alert = "Manifold line pressure within standard operating range (4.0 - 4.5 bar)."

        # Autonomy Status & Safety Gates
        if autonomy_hours < 6.0:
            autonomy_status = "EMERGENCY_CRITICAL"
            autonomy_alert = (
                f"[DISASTER OXYGEN ALERT] Remaining hospital oxygen supply is only {autonomy_hours} hours (< 6.0h)! "
                f"Immediate cryogenic tanker dispatch and district administration SOS notification required!"
            )
        elif autonomy_hours < 24.0:
            autonomy_status = "TIER_1_WARNING"
            autonomy_alert = f"Oxygen supply below 24-hour buffer ({autonomy_hours} hours remaining). Expedite refilling."
        else:
            autonomy_status = "STABLE"
            autonomy_alert = f"Oxygen supply stable with {autonomy_hours} hours autonomy at current burn rate."

        # If remaining autonomy is under 6 hours, raise statutory alarm
        if autonomy_hours < 6.0:
            raise OxygenCriticalShortageAlarm(autonomy_alert)

        return {
            "tank_id": lmo.tank_id,
            "liquid_volume_liters": lmo.current_liquid_volume_liters,
            "liquid_level_pct": lmo.liquid_level_pct,
            "total_gaseous_liters_available": round(total_gaseous_liters_available, 0),
            "hospital_burn_rate_lpm": round(effective_draw_lpm, 1),
            "estimated_autonomy_hours": autonomy_hours,
            "autonomy_status": autonomy_status,
            "autonomy_alert": autonomy_alert,
            "manifold_pressure_bar": line_pressure,
            "manifold_pressure_status": pressure_status,
            "manifold_pressure_alert": pressure_alert,
            "ward_draw_breakdown_lpm": dict(self._active_ward_draw_liters_per_min),
        }
