"""
PROJECT "HOSPITAL" — PHASE 19: PRODUCTION SYSTEMS HARDENING
Test Suite: test_currency_and_logging.py
Validates:
  - Financial Decimal precision eliminating floating-point rounding errors (ROUND_HALF_UP)
  - Dynamic tariff estimation and multi-line invoice reconciliation
  - Enterprise structured JSON logger output format
  - Contextual correlation ID and tenant ID propagation across execution flows
  - Structured exception capturing with stacktrace in JSON format
"""

import io
import os
import sys
import json
import unittest
from decimal import Decimal
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from dynamic_billing_engine import DynamicBillingEngine, TariffItem
from pmjay_nhcx_engine import PMJAYNHCXEngine, PMJAYPackageBreakageError
from logger import (
    get_logger, set_correlation_id, get_correlation_id,
    set_context_tenant, get_context_tenant, JSONFormatter
)


class TestCurrencyAndLogging(unittest.TestCase):

    def setUp(self):
        self.billing = DynamicBillingEngine()
        self.pmjay = PMJAYNHCXEngine()

    def test_decimal_precision_multi_line_reconciliation(self):
        """Dynamic billing engine must compute exact monetary sums without floating point drift."""
        self.billing.register_tariff_item(TariffItem(
            service_code="SRV-STENT",
            service_name="Coronary Stent Consumable",
            sac_code="9993",
            base_price=12543.33,
            gst_rate_pct=12.0  # 12% GST
        ))
        self.billing.register_tariff_item(TariffItem(
            service_code="SRV-MED",
            service_name="Specialized Injection",
            sac_code="9993",
            base_price=412.67,
            gst_rate_pct=5.0   # 5% GST
        ))

        inv = self.billing.create_invoice("INV-PRECISION-01", "PAT-01", "ENC-01", "PRIVATE")
        # Private tier = 2.2x multiplier
        # Stent: 12543.33 * 2.2 = 27595.33; GST 12% = 3311.44; Total = 30906.77
        l1 = self.billing.add_line_item("INV-PRECISION-01", "SRV-STENT", quantity=2)
        l2 = self.billing.add_line_item("INV-PRECISION-01", "SRV-MED", quantity=3)

        self.assertIsInstance(inv.total_gross, float)
        self.assertIsInstance(inv.total_gst, float)
        self.assertIsInstance(inv.total_net, float)

        # Expected manual Decimal calculation:
        # l1: unit_price = round(12543.33 * 2.2, 2) = 27595.33
        #     l1_gross = 27595.33 * 2 = 55190.66
        #     l1_gst = round(55190.66 * 0.12, 2) = 6622.88
        # l2: unit_price = round(412.67 * 2.2, 2) = 907.87
        #     l2_gross = 907.87 * 3 = 2723.61
        #     l2_gst = round(2723.61 * 0.05, 2) = 136.18
        # total_gross = 55190.66 + 2723.61 = 57914.27
        # total_gst = 6622.88 + 136.18 = 6759.06
        # total_net = 57914.27 + 6759.06 = 64673.33
        self.assertEqual(inv.total_gross, 57914.27)
        self.assertEqual(inv.total_gst, 6759.06)
        self.assertEqual(inv.total_net, 64673.33)

    def test_pmjay_decimal_addons_and_anti_breakage(self):
        """PM-JAY engine enforces decimal precision on specialized addons and blocks unbundled consumables."""
        enc = self.pmjay.register_pmjay_encounter(
            encounter_id="ENC-PMJAY-PRECISION",
            patient_id="PAT-PMJAY-1",
            pmjay_card_id="PMJAY-CARD-999",
            package_code="SG001A",
            preauth_number="PREAUTH-888"
        )
        # Attempt unbundled consumable -> must fail
        with self.assertRaises(PMJAYPackageBreakageError):
            self.pmjay.add_billing_item("ENC-PMJAY-PRECISION", "Surgical Gloves", "CONSUMABLES", 350.50)

        # Contracted specialized implant addon -> allowed with exact Decimal arithmetic
        self.pmjay.add_billing_item("ENC-PMJAY-PRECISION", "High-Flex Titanium Joint", "SPECIALIZED_IMPLANT", 15450.75)
        self.pmjay.add_billing_item("ENC-PMJAY-PRECISION", "Bone Cement Kit", "SPECIALIZED_BIOMATERIAL", 4549.25)

        total_addons = self.pmjay.get_total_billed_addons("ENC-PMJAY-PRECISION")
        self.assertEqual(total_addons, 20000.00)

    def test_structured_json_logger_formatting(self):
        """Structured logger must output single-line valid JSON with ISO timestamps and trace headers."""
        set_correlation_id("REQ-TRACE-PHASE19-ABC")
        set_context_tenant("TENANT-AIIMS-DELHI")

        logger = get_logger("hospital.test")
        
        # Test JSONFormatter directly to inspect output
        formatter = JSONFormatter()
        import logging
        record = logging.LogRecord(
            name="hospital.test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=99,
            msg="Clinical threshold alert triggered",
            args=(),
            exc_info=None
        )
        record.extra_fields = {"patient_id": "PAT-999", "spo2": 84.5}

        json_str = formatter.format(record)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["level"], "WARNING")
        self.assertEqual(parsed["logger"], "hospital.test")
        self.assertEqual(parsed["message"], "Clinical threshold alert triggered")
        self.assertEqual(parsed["correlation_id"], "REQ-TRACE-PHASE19-ABC")
        self.assertEqual(parsed["tenant_id"], "TENANT-AIIMS-DELHI")
        self.assertEqual(parsed["patient_id"], "PAT-999")
        self.assertEqual(parsed["spo2"], 84.5)
        self.assertIn("timestamp", parsed)

    def test_structured_logger_exception_capture(self):
        """Structured logger captures exception tracebacks as nested JSON dictionaries."""
        formatter = JSONFormatter()
        import logging
        try:
            raise ValueError("Zero-denominator drug titration failure")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="hospital.error",
                level=logging.ERROR,
                pathname=__file__,
                lineno=130,
                msg="Computation crashed",
                args=(),
                exc_info=exc_info
            )
            json_str = formatter.format(record)
            parsed = json.loads(json_str)

            self.assertIn("exception", parsed)
            self.assertEqual(parsed["exception"]["type"], "ValueError")
            self.assertIn("Zero-denominator drug titration", parsed["exception"]["message"])
            self.assertIsInstance(parsed["exception"]["stacktrace"], list)


if __name__ == "__main__":
    unittest.main()
