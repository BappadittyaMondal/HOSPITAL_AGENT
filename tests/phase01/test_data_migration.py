#!/usr/bin/env python3
"""
Legacy Data Migration & FHIR R4 ETL Verification Test Suite.
Verifies phone cleansing, name normalization, and FHIR R4 Patient resource creation.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from data_migration_etl import LegacyPatientETL, cleanse_indian_phone, normalize_name

def test_data_migration():
    print("================================================================================")
    print(" [LEGACY DATA MIGRATION TEST] VERIFYING CLEANSER & FHIR R4 ETL PIPELINE")
    print("================================================================================")

    # 1. Phone number cleansing tests
    assert cleanse_indian_phone("9830012345") == "+919830012345"
    assert cleanse_indian_phone("+91 98300 12345") == "+919830012345"
    assert cleanse_indian_phone("09830012345") == "+919830012345"
    print(" [PASS] Indian mobile number variations normalized to E.164 (+91XXXXXXXXXX).")

    # 2. Name normalization tests
    assert normalize_name("dr. subhash mukherjee") == "Subhash Mukherjee"
    assert normalize_name("  SMT.   pritilata   waddedar ") == "Pritilata Waddedar"
    print(" [PASS] Demographic name casing and honorifics normalized.")

    # 3. Full ETL transformation to FHIR R4
    etl = LegacyPatientETL(tenant_id="11111111-1111-1111-1111-111111111111")
    legacy_row = {
        "OldMRN": "OLD-HOSP-2015-9921",
        "PatientName": "Shri Debesh Roy",
        "Gender": "Male",
        "DOB": "14/08/1982",
        "ContactPhone": "9831198311"
    }

    fhir_patient = etl.transform_legacy_record_to_fhir(legacy_row)
    assert fhir_patient["resourceType"] == "Patient"
    assert fhir_patient["birthDate"] == "1982-08-14"
    assert fhir_patient["gender"] == "male"
    assert fhir_patient["name"][0]["text"] == "Debesh Roy"
    assert fhir_patient["identifier"][0]["value"] == "OLD-HOSP-2015-9921"
    assert fhir_patient["telecom"][0]["value"] == "+919831198311"
    print(" [PASS] Legacy tabular record successfully transformed into compliant HL7 FHIR R4 Patient.")

    print("================================================================================")
    print(" LEGACY MIGRATION ETL ENGINE VERIFIED.")
    return 0

if __name__ == "__main__":
    sys.exit(test_data_migration())
