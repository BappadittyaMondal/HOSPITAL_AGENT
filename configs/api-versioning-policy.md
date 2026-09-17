# HOSPITAL PLATFORM — API VERSIONING & EVOLUTION SPECIFICATION

**Standard:** URI Path Versioning (`/api/v1/`, `/api/v2/`)  
**Status:** Mandatory Architectural Invariant  
**Audience:** All Core Services, Mobile Clients, Modality Interfaces, and External Gateways (ABDM, NHCX)  

---

## 1. Versioning Rules
1. **URI Path Semantics:** All public API endpoints MUST start with `/api/v{major}/`.
   - Example: `https://his.hospital.local/api/v1/patients/`
   - Breaking changes require incrementing the major version number (e.g., `/api/v2/`).
2. **Backward-Compatible Non-Breaking Evolution Rules:**
   - **Allowed in v1:** Adding new optional request fields.
   - **Allowed in v1:** Adding new response fields.
   - **Prohibited in v1:** Renaming or deleting existing fields.
   - **Prohibited in v1:** Changing field types or validation constraints (e.g., making an optional field mandatory).
   - **Prohibited in v1:** Modifying HTTP response status codes for identical payloads.

---

## 2. Deprecation & Sunset Lifecycle
When an endpoint or version must be phased out:
1. **Active:** Normal operation. No deprecation warnings.
2. **Deprecated:** Minimum 12-month advance notice.
   - The API MUST include HTTP headers in every response:
     ```http
     Deprecation: @1773734400
     Sunset: Wed, 17 Mar 2027 00:00:00 GMT
     Link: </api/v2/migration-guide>; rel="deprecation"
     ```
3. **Sunset (410 Gone):** After the sunset date passes, the endpoint returns `410 Gone` with a structured payload directing consumers to the active version.

---

## 3. Consumer Contract Testing (Pact / Schema Validation)
- Every API endpoint is accompanied by an OpenAPI 3.1 schema.
- CI/CD executes contract regression tests (`tests/phase01/test_api_contracts.py`) verifying that:
  - Required request and response properties are never omitted.
  - JSON schema definitions match production payloads.
  - HTTP headers comply with security and versioning policies.
