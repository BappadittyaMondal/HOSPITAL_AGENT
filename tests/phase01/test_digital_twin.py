#!/usr/bin/env python3
"""
Digital Twin Simulator Verification Test Suite.
Verifies synthetic patient flow generation, triage distribution realism,
and generation performance under high load.
"""
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from digital_twin_simulator import DigitalTwinSimulator

def test_digital_twin():
    print("================================================================================")
    print(" [DIGITAL TWIN SIMULATOR TEST] VERIFYING SYNTHETIC SURGE GENERATION")
    print("================================================================================")

    sim = DigitalTwinSimulator(tenant_id="11111111-1111-1111-1111-111111111111")

    # 1. Mass Casualty Surge Simulation
    t0 = time.perf_counter()
    trauma_batch = sim.simulate_surge_batch(100, surge_mode="MASS_CASUALTY_TRAUMA")
    gen_time_ms = (time.perf_counter() - t0) * 1000

    high_acuity_count = sum(1 for p in trauma_batch if p["encounter"]["acuity_level"] in [1, 2])
    assert high_acuity_count >= 60, f"Mass casualty should be predominantly ESI 1-2, got {high_acuity_count}/100"
    print(f" [PASS] Mass casualty trauma surge simulated: {high_acuity_count}% ESI 1-2 critical triage.")

    # 2. Routine OPD Surge Simulation
    opd_batch = sim.simulate_surge_batch(500, surge_mode="ROUTINE_OPD")
    low_acuity_count = sum(1 for p in opd_batch if p["encounter"]["acuity_level"] in [4, 5])
    assert low_acuity_count >= 150
    print(f" [PASS] Routine OPD surge simulated: 500 patient encounters generated.")

    # 3. High-throughput generation benchmark (1,000 patients)
    t_start = time.perf_counter()
    large_batch = sim.simulate_surge_batch(1000, surge_mode="ROUTINE_OPD")
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    assert len(large_batch) == 1000
    print(f" [BENCHMARK] 1,000 complete synthetic patient journeys generated in {elapsed_ms:.2f} ms")
    assert elapsed_ms < 500.0, f"Performance issue: took {elapsed_ms}ms"
    print(" [PASS] High-throughput synthetic patient generation verified (< 0.5 ms per patient).")

    print("================================================================================")
    print(" DIGITAL TWIN SIMULATION FRAMEWORK FULLY OPERATIONAL.")
    return 0

if __name__ == "__main__":
    sys.exit(test_digital_twin())
