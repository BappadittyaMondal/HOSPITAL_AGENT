#!/usr/bin/env python3
"""
PROJECT 'HOSPITAL' — PHASE 28: CORE INFRASTRUCTURE & SECURITY REMEDIATION TEST SUITE
Module: tests/phase28/test_core_remediation.py
"""

import os
import sys
import unittest
from decimal import Decimal
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../services/core-api')))
import main
from sbccl_experience_engine import (
    create_csb_authorization_token,
    verify_csb_authorization_token
)
from dynamic_billing_engine import DynamicBillingEngine, TariffItem

class TestCoreRemediation(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)

    def test_csb_token_security_and_strict_validation(self):
        """Verify static bypass token is rejected under strict/production mode, and authentic HMAC token passes."""
        os.environ['STRICT_AUTH_REQUIRED'] = 'true'
        try:
            is_valid_bypass = verify_csb_authorization_token(
                token_str='CSB-AUTH-TOKEN-2026-BOARD-CERTIFIED',
                target_version='v1.3.0-PROD-CANDIDATE'
            )
            self.assertFalse(is_valid_bypass)

            valid_token = create_csb_authorization_token(
                board_member_id='AIIMS_DEAN_CLINICAL_GOVERNANCE',
                target_version='v1.3.0-PROD-CANDIDATE'
            )
            self.assertTrue(verify_csb_authorization_token(
                token_str=valid_token,
                target_version='v1.3.0-PROD-CANDIDATE'
            ))

            self.assertFalse(verify_csb_authorization_token(
                token_str=valid_token,
                target_version='v1.4.0-TAMPERED'
            ))
        finally:
            os.environ.pop('STRICT_AUTH_REQUIRED', None)

    def test_dynamic_health_probe_reports_honest_runtime_status(self):
        """Health probe reports accurate runtime persistence mode and service health."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('mode', data)
        self.assertIn('services', data)
        self.assertEqual(data['services']['safety_engine'], 'online')
        self.assertEqual(data['services']['syndromic_engine'], 'online')
        self.assertIn('edge_sqlite_wal_active', data['services']['postgres'])
        self.assertIn('in_memory_lru_active', data['services']['redis'])

    def test_billing_decimal_quantization_exactness(self):
        """Financial quantization avoids floating point fractional cent leakage."""
        billing = DynamicBillingEngine()
        billing.register_tariff_item(TariffItem(
            service_code='SRV-TEST-01',
            service_name='Test Blood Work',
            sac_code='9993',
            base_price=333.33,
            gst_rate_pct=18.0
        ))
        inv = billing.create_invoice('INV-REM-01', 'PAT-REM-01', 'ENC-REM-01', 'GENERAL')
        line = billing.add_line_item('INV-REM-01', 'SRV-TEST-01', quantity=3)
        self.assertEqual(line.gst_amount, 180.00)
        self.assertEqual(line.total_amount, 1179.99)
        self.assertEqual(inv.total_net, 1179.99)

if __name__ == '__main__':
    unittest.main()
