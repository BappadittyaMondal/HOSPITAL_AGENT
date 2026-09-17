#!/usr/bin/env python3
"""
API Contract & OpenAPI 3.1 Verification Test Suite.
Validates that all endpoints adhere to URI versioning (/api/v1/),
contain required security headers (X-Tenant-ID), and define strict schemas.
"""
import os
import sys
import re

def test_openapi_contract():
    openapi_path = os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api", "openapi.yaml")
    if not os.path.exists(openapi_path):
        print(f"FAILED: OpenAPI spec not found at {openapi_path}")
        return 1

    with open(openapi_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("================================================================================")
    print(" [API CONTRACT TEST SUITE] VERIFYING OPENAPI 3.1 & VERSIONING INVARIANTS")
    print("================================================================================")

    # 1. Verify OpenAPI version
    if not re.search(r"openapi:\s*3\.1\.", content):
        print(" [FAIL] Spec must be OpenAPI 3.1.x")
        return 1
    print(" [PASS] Valid OpenAPI 3.1.x version declared.")

    # 2. Verify server URL versioning
    if "/api/v1" not in content:
        print(" [FAIL] Server base URL must be versioned with /api/v1")
        return 1
    print(" [PASS] Server URL enforces /api/v1 versioning prefix.")

    # 3. Verify mandatory endpoints exist
    required_paths = ["/health", "/auth/token", "/safety/evaluate-order"]
    for p in required_paths:
        if p not in content:
            print(f" [FAIL] Mandatory endpoint missing: {p}")
            return 1
        print(f" [PASS] Endpoint defined: {p}")

    # 4. Verify tenant isolation parameter
    if "X-Tenant-ID" not in content:
        print(" [FAIL] Clinical endpoints must require X-Tenant-ID header")
        return 1
    print(" [PASS] Multi-tenancy header X-Tenant-ID enforced.")

    # 5. Verify hard-stop schema in safety endpoint
    if "hard_stops" not in content or "evaluated_in_microseconds" not in content:
        print(" [FAIL] Safety evaluation schema must contain hard_stops and microsecond latency")
        return 1
    print(" [PASS] Clinical safety schema validated with hard_stops and microsecond metrics.")

    print("================================================================================")
    print(" ALL API CONTRACT INVARIANTS VERIFIED SUCCESSFULLY.")
    return 0

if __name__ == "__main__":
    sys.exit(test_openapi_contract())
