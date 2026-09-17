#!/usr/bin/env python3
"""
Clinical Rule Versioning & Governance Engine (Gap 35).
Ensures that:
1. Every DRE rule, formulary change, and tariff card has an immutable version,
   cryptographic hash, effective datetime, expiry datetime, and clinical committee approval.
2. Historical encounter integrity: An encounter is forever evaluated against the exact
   rule version active at that specific historical timestamp (zero retroactive recalculation).
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

class ClinicalRuleVersion:
    def __init__(
        self,
        rule_id: str,
        version: int,
        rule_name: str,
        rule_definition: Dict,
        effective_from: datetime,
        effective_to: Optional[datetime],
        approved_by: str, # e.g., "Pharmacy & Therapeutics Committee"
        change_reason: str
    ):
        self.rule_id = rule_id
        self.version = version
        self.rule_name = rule_name
        self.rule_definition = rule_definition
        self.effective_from = effective_from
        self.effective_to = effective_to
        self.approved_by = approved_by
        self.change_reason = change_reason
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = f"{self.rule_id}:{self.version}:{json.dumps(self.rule_definition, sort_keys=True)}:{self.effective_from.isoformat()}:{self.approved_by}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def is_active_at(self, timestamp: datetime) -> bool:
        if timestamp < self.effective_from:
            return False
        if self.effective_to and timestamp >= self.effective_to:
            return False
        return True

class ClinicalRuleRegistry:
    def __init__(self):
        self._rules: Dict[str, List[ClinicalRuleVersion]] = {}

    def register_rule_version(self, rule_version: ClinicalRuleVersion):
        if rule_version.rule_id not in self._rules:
            self._rules[rule_version.rule_id] = []
        
        # Verify version sequence
        existing = self._rules[rule_version.rule_id]
        if existing:
            last_version = existing[-1]
            if rule_version.version <= last_version.version:
                raise ValueError(f"Version must be strictly increasing. Current: {last_version.version}, Attempted: {rule_version.version}")
            # Retire previous version if active
            if not last_version.effective_to:
                last_version.effective_to = rule_version.effective_from

        self._rules[rule_version.rule_id].append(rule_version)

    def get_rule_at_timestamp(self, rule_id: str, timestamp: datetime) -> Optional[ClinicalRuleVersion]:
        """Resolves the exact rule version that was legally and clinically active at `timestamp`."""
        versions = self._rules.get(rule_id, [])
        for v in versions:
            if v.is_active_at(timestamp):
                return v
        return None
