#!/usr/bin/env python3
"""
Digital Twin Synthetic Hospital Event Simulator (Gap 24).
Generates realistic clinical patient arrival distributions:
1. Monday Morning OPD Surges (High volume, low acuity)
2. Mass Casualty Trauma Influx (Low volume, extreme ESI-1 acuity)
3. Monsoon Epidemic Spike (Inpatient bed saturation)
Used to stress-test queuing engines, bed allocation deadlocks, and latency without risking live patients.
"""
import random
import uuid
from typing import Dict, List
from datetime import datetime, timezone

class DigitalTwinSimulator:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def generate_synthetic_patient(self, index: int, surge_mode: str = "ROUTINE_OPD") -> Dict:
        first_names = ["Anirban", "Debarati", "Sourav", "Priyanka", "Saptarshi", "Mousumi", "Amitabh", "Barnali"]
        last_names = ["Banerjee", "Chatterjee", "Mukherjee", "Bhattacharya", "Sengupta", "Dey", "Ghosh", "Roy"]
        
        if surge_mode == "MASS_CASUALTY_TRAUMA":
            acuity = random.choice([1, 1, 2, 2, 3]) # Extreme ESI acuity
            enc_type = "EMERGENCY"
            chief_complaint = random.choice([
                "Blast trauma with multiple penetrating lacerations",
                "Crush injury lower extremities from collapsed scaffolding",
                "Severe blunt chest trauma with dyspnea",
                "Head injury with loss of consciousness and GCS 8"
            ])
        elif surge_mode == "MONSOON_DENGUE_SPIKE":
            acuity = random.choice([2, 3, 3, 4])
            enc_type = random.choice(["OPD", "EMERGENCY"])
            chief_complaint = "High grade fever for 5 days with severe retro-orbital pain and thrombocytopenia"
        else: # ROUTINE_OPD
            acuity = random.choice([3, 4, 4, 5, 5])
            enc_type = "OPD"
            chief_complaint = random.choice([
                "Routine diabetes check-up and fasting blood sugar review",
                "Mild chronic cough for 2 weeks",
                "Knee joint pain during walking",
                "Hypertension routine follow-up"
            ])

        fn = random.choice(first_names)
        ln = random.choice(last_names)
        patient_id = str(uuid.uuid4())
        
        return {
            "patient_id": patient_id,
            "tenant_id": self.tenant_id,
            "mrn": f"SYN-{random.randint(100000, 999999)}",
            "name": f"{fn} {ln}",
            "gender": random.choice(["male", "female"]),
            "age": random.randint(18, 85),
            "encounter": {
                "encounter_id": str(uuid.uuid4()),
                "encounter_type": enc_type,
                "acuity_level": acuity,
                "chief_complaint": chief_complaint,
                "arrived_at": datetime.now(timezone.utc).isoformat()
            }
        }

    def simulate_surge_batch(self, count: int, surge_mode: str = "ROUTINE_OPD") -> List[Dict]:
        """Generates a batch of synthetic patients arriving at the hospital."""
        return [self.generate_synthetic_patient(i, surge_mode) for i in range(count)]
