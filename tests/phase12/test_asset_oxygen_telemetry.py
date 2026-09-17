"""
Test Suite: test_asset_oxygen_telemetry.py
Phase 12: Hospital Operations — Real-Time RFID/BLE Asset Tracking & Oxygen Telemetry (Gaps 30 & 10)
Mandate / Quality Gate 3:
  - Inviolable Quality Gate 3: Mobile crash cart moved outside Emergency Department
    perimeter triggers security console alarm within < 10 seconds SLA (GeofenceBreachSecurityAlarm).
  - Telemetry from Liquid Medical Oxygen (LMO) tank and piped manifold pressure sensors.
  - Manifold line pressure safety thresholds (< 3.8 bar warning, < 3.2 bar ventilator failure hazard).
  - Dynamic oxygen burn-rate calculator estimating remaining supply autonomy hours.
  - Emergency alarm triggered when remaining autonomy drops below 6 hours.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from asset_oxygen_telemetry_engine import (
    AssetOxygenTelemetryEngine,
    AssetCriticality,
    GeofenceBreachSecurityAlarm,
    OxygenCriticalShortageAlarm,
    AssetTrackingError,
    OxygenTelemetryError,
)


class TestAssetOxygenTelemetryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AssetOxygenTelemetryEngine()

        # Register Emergency Crash Cart with authorized zones
        self.crash_cart = self.engine.register_mobile_asset(
            asset_id="ASSET-CART-ED-01",
            asset_name="Emergency Resuscitation Crash Cart #1",
            serial_number="CART-SN-9941",
            criticality=AssetCriticality.STAT_CRITICAL,
            allowed_zones={"ED_RESUS_BAY_1", "ED_RESUS_BAY_2", "ED_TRIAGE_ZONE"},
            initial_zone_id="ED_RESUS_BAY_1",
            floor_level=0,
        )

    def test_quality_gate_3_crash_cart_geofence_breach_sub_10s_sla(self):
        """
        Quality Gate 3:
        Mobile crash cart moved outside Emergency Department perimeter triggers
        security console alarm in < 10 seconds SLA.
        """
        # 1. Normal movement inside authorized zone
        ping_res = self.engine.ingest_ble_beacon_ping(
            asset_id="ASSET-CART-ED-01",
            detected_zone_id="ED_TRIAGE_ZONE",
            x_coord=14.2,
            y_coord=8.5,
            battery_pct=98.0,
        )
        self.assertEqual(ping_res["status"], "ZONE_AUTHORIZED")
        self.assertFalse(self.crash_cart.is_in_breach)

        # 2. Cart unauthorized movement into OPD corridor (Outside ED perimeter)
        with self.assertRaises(GeofenceBreachSecurityAlarm) as ctx:
            self.engine.ingest_ble_beacon_ping(
                asset_id="ASSET-CART-ED-01",
                detected_zone_id="OPD_CORRIDOR_NORTH",  # Unauthorized zone
                x_coord=88.5,
                y_coord=42.1,
                battery_pct=97.5,
            )

        self.assertIn("GEOFENCE BREACH SECURITY ALARM", str(ctx.exception))
        self.assertIn("Emergency Resuscitation Crash Cart #1", str(ctx.exception))
        self.assertIn("OPD_CORRIDOR_NORTH", str(ctx.exception))

        # 3. Verify alarm event logged and SLA latency < 10.0 seconds
        alerts = self.engine.get_geofence_alerts()
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert.asset_id, "ASSET-CART-ED-01")
        self.assertEqual(alert.breached_zone_id, "OPD_CORRIDOR_NORTH")
        self.assertLess(alert.detection_latency_seconds, 10.0, "Detection latency must be well under 10.0s SLA")
        self.assertTrue(alert.security_dispatched)

    def test_oxygen_pipeline_pressure_monitoring(self):
        """Tests LMO tank telemetry and manifold line pressure threshold evaluation."""
        # Standard healthy operation: 4.2 bar manifold pressure
        self.engine.record_lmo_tank_telemetry(
            tank_id="LMO-TANK-PRIMARY",
            capacity_liters=20000.0,
            current_liquid_volume_liters=14000.0,
            tank_pressure_bar=10.5,
            manifold_line_pressure_bar=4.2,
            ambient_temp_c=27.5,
        )

        self.engine.update_ward_oxygen_draw("ICU_COVID_1", flow_rate_liters_per_min=150.0)
        self.engine.update_ward_oxygen_draw("OT_COMPLEX", flow_rate_liters_per_min=80.0)

        calc = self.engine.calculate_oxygen_burn_rate_and_autonomy()
        self.assertEqual(calc["manifold_pressure_status"], "NORMAL")
        self.assertGreater(calc["estimated_autonomy_hours"], 500.0)

        # Ingest low manifold pressure (3.1 bar < 3.2 bar critical threshold)
        self.engine.record_lmo_tank_telemetry(
            tank_id="LMO-TANK-PRIMARY",
            capacity_liters=20000.0,
            current_liquid_volume_liters=12000.0,
            tank_pressure_bar=4.0,
            manifold_line_pressure_bar=3.1,  # Critical drop!
            ambient_temp_c=27.5,
        )

        calc_crit = self.engine.calculate_oxygen_burn_rate_and_autonomy()
        self.assertEqual(calc_crit["manifold_pressure_status"], "CRITICAL_LOW_PRESSURE")
        self.assertIn("MGPS EMERGENCY", calc_crit["manifold_pressure_alert"])

    def test_dynamic_oxygen_burn_rate_and_critical_shortage_alarm(self):
        """Tests dynamic burn rate calculation and emergency shortage alarm when autonomy < 6h."""
        # Massive hospital draw of 800 L/min (e.g. mass casualty / pandemic surge)
        # Liquid volume remaining: only 150 liters of liquid O2
        # Gaseous equivalent: 150 * 860 = 129,000 L
        # Autonomy: 129,000 / 800 L/min = 161.25 min = ~2.7 hours (< 6.0 hours emergency threshold!)
        self.engine.record_lmo_tank_telemetry(
            tank_id="LMO-TANK-PRIMARY",
            capacity_liters=20000.0,
            current_liquid_volume_liters=150.0,
            tank_pressure_bar=8.0,
            manifold_line_pressure_bar=4.1,
        )

        self.engine.update_ward_oxygen_draw("ALL_WARDS", flow_rate_liters_per_min=800.0)

        with self.assertRaises(OxygenCriticalShortageAlarm) as ctx:
            self.engine.calculate_oxygen_burn_rate_and_autonomy()

        self.assertIn("DISASTER OXYGEN ALERT", str(ctx.exception))
        self.assertIn("cryogenic tanker dispatch", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
