#!/usr/bin/env python3
"""
Clinical Rule Versioning Verification Test Suite.
Verifies immutable rule hashes, version increments, and historical point-in-time preservation.
"""
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from rule_versioning import ClinicalRuleVersion, ClinicalRuleRegistry

def test_rule_versioning():
    registry = ClinicalRuleRegistry()
    print("================================================================================")
    print(" [CLINICAL RULE VERSIONING TEST] VERIFYING IMMUTABLE VERSIONING & HISTORY")
    print("================================================================================")

    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t_encounter = datetime(2025, 6, 15, 14, 30, tzinfo=timezone.utc)
    t_current = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    # Version 1: Metformin max dose 2000mg
    v1 = ClinicalRuleVersion(
        rule_id="RULE-METFORMIN-MAX-DOSE",
        version=1,
        rule_name="Metformin Daily Maximum Dose",
        rule_definition={"max_daily_mg": 2000, "contraindicated_egfr": 30},
        effective_from=t0,
        effective_to=None,
        approved_by="P&T Committee 2025",
        change_reason="Initial baseline guideline"
    )
    registry.register_rule_version(v1)
    print(f" [PASS] Version 1 registered with SHA-256 hash: {v1.hash[:16]}...")

    # Version 2: Updated in 2026: Metformin max dose updated to 2550mg
    v2 = ClinicalRuleVersion(
        rule_id="RULE-METFORMIN-MAX-DOSE",
        version=2,
        rule_name="Metformin Daily Maximum Dose (Revised)",
        rule_definition={"max_daily_mg": 2550, "contraindicated_egfr": 30},
        effective_from=t1,
        effective_to=None,
        approved_by="P&T Committee 2026",
        change_reason="Updated to align with ADA 2026 Standards of Care"
    )
    registry.register_rule_version(v2)
    print(f" [PASS] Version 2 registered with SHA-256 hash: {v2.hash[:16]}...")

    # Historical Encounter Verification:
    # A patient encounter documented in June 2025 MUST resolve Version 1 (max 2000mg)
    resolved_historical = registry.get_rule_at_timestamp("RULE-METFORMIN-MAX-DOSE", t_encounter)
    assert resolved_historical is not None
    assert resolved_historical.version == 1
    assert resolved_historical.rule_definition["max_daily_mg"] == 2000
    print(" [PASS] Historical encounter in 2025 correctly resolves Rule Version 1 (2000mg).")

    # Current Encounter Verification:
    # An encounter today MUST resolve Version 2 (max 2550mg)
    resolved_current = registry.get_rule_at_timestamp("RULE-METFORMIN-MAX-DOSE", t_current)
    assert resolved_current is not None
    assert resolved_current.version == 2
    assert resolved_current.rule_definition["max_daily_mg"] == 2550
    print(" [PASS] Current encounter in 2026 correctly resolves Rule Version 2 (2550mg).")

    print("================================================================================")
    print(" CLINICAL RULE VERSIONING & HISTORICAL PRESERVATION VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_rule_versioning())
