"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Module: hai_device_surveillance.py
Operational Scope:
  - Invasive Medical Device Tracking (Central Venous Catheter, Urinary Catheter, Ventilator)
  - Quality Gate 3: Automated Active Device-Day Counting & Removal Duration Logging
  - NHSN / CDC / NABH Standard HAI Rate Calculations (CLABSI, CAUTI, VAP per 1,000 Device-Days)
  - Contact Precaution & Isolation Flagging (MRSA, VRE, C. diff, MDR) (Gap 18)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any


@dataclass
class InvasiveDeviceRecord:
    device_id: str
    patient_id: str
    device_type: str  # CENTRAL_LINE, URINARY_CATHETER, VENTILATOR
    insertion_site: str
    inserted_by: str
    inserted_at: datetime
    is_active: bool = True
    removed_by: Optional[str] = None
    removed_at: Optional[datetime] = None
    total_device_hours: float = 0.0
    total_device_days: int = 0
    removal_reason: Optional[str] = None


@dataclass
class HAIBenchmarkMetric:
    metric_name: str
    infection_count: int
    device_days: int
    rate_per_1000_device_days: float
    benchmark_threshold: float
    is_exceeded: bool


class HAIDeviceSurveillanceEngine:
    """
    Automated device-day counting, removal duration logging,
    and NHSN/NABH benchmark infection rate calculation engine.
    """

    # Benchmarks per 1,000 device-days
    BENCHMARKS = {
        "CLABSI": 1.5,
        "CAUTI": 2.0,
        "VAP": 2.5
    }

    def __init__(self):
        # device_id -> InvasiveDeviceRecord
        self.devices: Dict[str, InvasiveDeviceRecord] = {}
        # patient_id -> list of active device_ids
        self.patient_active_devices: Dict[str, List[str]] = {}
        # HAI Incident logs: [{'incident_id': ..., 'patient_id': ..., 'infection_type': 'CLABSI'}]
        self.hai_incidents: List[Dict[str, Any]] = []

    def record_device_insertion(
        self,
        device_id: str,
        patient_id: str,
        device_type: str,
        insertion_site: str,
        inserted_by: str,
        inserted_at: Optional[datetime] = None
    ) -> InvasiveDeviceRecord:
        """Records the insertion of an invasive medical device and registers it in active monitoring."""
        if inserted_at is None:
            inserted_at = datetime.now(timezone.utc)

        if device_type not in ("CENTRAL_LINE", "URINARY_CATHETER", "VENTILATOR"):
            raise ValueError(f"Unsupported invasive device type: {device_type}")

        rec = InvasiveDeviceRecord(
            device_id=device_id,
            patient_id=patient_id,
            device_type=device_type,
            insertion_site=insertion_site,
            inserted_by=inserted_by,
            inserted_at=inserted_at,
            is_active=True
        )
        self.devices[device_id] = rec
        self.patient_active_devices.setdefault(patient_id, []).append(device_id)
        return rec

    def record_device_removal(
        self,
        device_id: str,
        removed_by: str,
        removal_reason: str,
        removed_at: Optional[datetime] = None
    ) -> InvasiveDeviceRecord:
        """
        Quality Gate 3:
        Device removal automatically decrements active device counter and logs total duration.
        """
        if removed_at is None:
            removed_at = datetime.now(timezone.utc)

        rec = self.devices.get(device_id)
        if not rec:
            raise ValueError(f"Device {device_id} not found in surveillance registry.")

        if not rec.is_active:
            raise ValueError(f"Device {device_id} is already deactivated/removed.")

        rec.is_active = False
        rec.removed_by = removed_by
        rec.removed_at = removed_at
        rec.removal_reason = removal_reason

        # Calculate exact duration
        duration = removed_at - rec.inserted_at
        hours = max(0.0, duration.total_seconds() / 3600.0)
        # Device days defined as count of calendar days or 24-hour chunks (ceil at minimum 1 day)
        days = max(1, int((hours + 23) // 24))

        rec.total_device_hours = round(hours, 2)
        rec.total_device_days = days

        # Decrement active device tracking for patient
        if rec.patient_id in self.patient_active_devices:
            if device_id in self.patient_active_devices[rec.patient_id]:
                self.patient_active_devices[rec.patient_id].remove(device_id)

        return rec

    def get_active_device_count(self, device_type: Optional[str] = None) -> int:
        """Returns currently active devices in the hospital."""
        active = [d for d in self.devices.values() if d.is_active]
        if device_type:
            active = [d for d in active if d.device_type == device_type]
        return len(active)

    def log_hai_infection(
        self,
        patient_id: str,
        infection_type: str,  # CLABSI, CAUTI, VAP, SSI
        pathogen_isolated: str,
        diagnosed_by: str,
        is_mdr: bool = False
    ) -> Dict[str, Any]:
        """Logs a confirmed hospital-acquired infection with pathogen profiling."""
        incident = {
            "incident_id": f"HAI-{infection_type}-{len(self.hai_incidents)+1}",
            "patient_id": patient_id,
            "infection_type": infection_type,
            "pathogen_isolated": pathogen_isolated,
            "is_mdr": is_mdr,
            "diagnosed_by": diagnosed_by,
            "reported_at": datetime.now(timezone.utc).isoformat()
        }
        self.hai_incidents.append(incident)
        return incident

    def calculate_hai_rates(
        self,
        total_central_line_days: int,
        total_catheter_days: int,
        total_ventilator_days: int
    ) -> Dict[str, HAIBenchmarkMetric]:
        """
        Calculates institutional HAI rates per 1,000 device-days against international benchmarks.
        """
        clabsi_count = sum(1 for i in self.hai_incidents if i["infection_type"] == "CLABSI")
        cauti_count = sum(1 for i in self.hai_incidents if i["infection_type"] == "CAUTI")
        vap_count = sum(1 for i in self.hai_incidents if i["infection_type"] == "VAP")

        clabsi_rate = (clabsi_count / total_central_line_days * 1000.0) if total_central_line_days > 0 else 0.0
        cauti_rate = (cauti_count / total_catheter_days * 1000.0) if total_catheter_days > 0 else 0.0
        vap_rate = (vap_count / total_ventilator_days * 1000.0) if total_ventilator_days > 0 else 0.0

        results = {
            "CLABSI": HAIBenchmarkMetric(
                metric_name="CLABSI per 1000 Central Line Days",
                infection_count=clabsi_count,
                device_days=total_central_line_days,
                rate_per_1000_device_days=round(clabsi_rate, 2),
                benchmark_threshold=self.BENCHMARKS["CLABSI"],
                is_exceeded=clabsi_rate > self.BENCHMARKS["CLABSI"]
            ),
            "CAUTI": HAIBenchmarkMetric(
                metric_name="CAUTI per 1000 Catheter Days",
                infection_count=cauti_count,
                device_days=total_catheter_days,
                rate_per_1000_device_days=round(cauti_rate, 2),
                benchmark_threshold=self.BENCHMARKS["CAUTI"],
                is_exceeded=cauti_rate > self.BENCHMARKS["CAUTI"]
            ),
            "VAP": HAIBenchmarkMetric(
                metric_name="VAP per 1000 Ventilator Days",
                infection_count=vap_count,
                device_days=total_ventilator_days,
                rate_per_1000_device_days=round(vap_rate, 2),
                benchmark_threshold=self.BENCHMARKS["VAP"],
                is_exceeded=vap_rate > self.BENCHMARKS["VAP"]
            )
        }
        return results
