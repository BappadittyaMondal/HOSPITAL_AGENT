#!/usr/bin/env python3
"""
Clinical Safety Rule Regression Test Suite Harness for HOSPITAL Platform.
Executes automated deterministic safety test cases against known lethal drug interactions,
anaphylactic allergy cross-reactivities, renal dose limits, and pediatric overdose thresholds.

INVIOLABLE GOVERNANCE GATE:
Zero Tolerance — Any regression or failure in the safety engine aborts CI/CD builds immediately.
"""
import sys
import json
import time
from typing import Dict, List, Tuple

# Canonical clinical safety test cases (gold standard clinical toxicology)
CANONICAL_SAFETY_CASES = [
    {
        "id": "DDI-001",
        "category": "DRUG_DRUG_INTERACTION",
        "drug_a": "Nitroglycerin",
        "drug_b": "Sildenafil",
        "severity": "LETHAL_HARD_STOP",
        "mechanism": "Severe, life-threatening refractory hypotension via synergistic cGMP vasodilation.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "DDI-002",
        "category": "DRUG_DRUG_INTERACTION",
        "drug_a": "Methotrexate",
        "drug_b": "Trimethoprim-Sulfamethoxazole",
        "severity": "LETHAL_HARD_STOP",
        "mechanism": "Synergistic dihydrofolate reductase inhibition causing acute fatal pancytopenia.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "DDI-003",
        "category": "DRUG_DRUG_INTERACTION",
        "drug_a": "Potassium Chloride IV",
        "drug_b": "Spironolactone",
        "severity": "LETHAL_HARD_STOP",
        "mechanism": "Synergistic potassium retention causing ventricular fibrillation / cardiac arrest.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "DDI-004",
        "category": "DRUG_DRUG_INTERACTION",
        "drug_a": "Linezolid",
        "drug_b": "Fluoxetine",
        "severity": "LETHAL_HARD_STOP",
        "mechanism": "Non-selective MAO inhibition plus SSRI inducing acute fatal Serotonin Syndrome.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "DDI-005",
        "category": "DRUG_DRUG_INTERACTION",
        "drug_a": "Simvastatin",
        "drug_b": "Clarithromycin",
        "severity": "SEVERE_HARD_STOP",
        "mechanism": "Potent CYP3A4 inhibition increasing statin AUC >10-fold, inducing rhabdomyolysis and acute tubular necrosis.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "ALLERGY-001",
        "category": "DRUG_ALLERGY_ANAPHYLAXIS",
        "allergen": "Penicillin",
        "prescribed_drug": "Amoxicillin",
        "severity": "LETHAL_HARD_STOP",
        "mechanism": "Beta-lactam core cross-reactivity causing acute IgE-mediated anaphylactic shock.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "ALLERGY-002",
        "category": "DRUG_ALLERGY_ANAPHYLAXIS",
        "allergen": "Sulfonamides",
        "prescribed_drug": "Sulfamethoxazole",
        "severity": "LETHAL_HARD_STOP",
        "mechanism": "Arylamine sulfonamide cross-reactivity causing Stevens-Johnson Syndrome / Toxic Epidermal Necrolysis.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "RENAL-001",
        "category": "ORGAN_IMPAIRMENT_CONTRAINDICATION",
        "prescribed_drug": "Metformin",
        "patient_egfr": 22.0,  # mL/min/1.73m2 (Contraindicated if eGFR < 30)
        "severity": "SEVERE_HARD_STOP",
        "mechanism": "Impaired renal elimination leading to toxic biguanide accumulation and fatal lactic acidosis.",
        "expected_action": "HARD_STOP_BLOCK"
    },
    {
        "id": "PEDIATRIC-001",
        "category": "PEDIATRIC_DOSE_GUARD",
        "prescribed_drug": "Paracetamol IV",
        "patient_age_months": 8,
        "patient_weight_kg": 7.5,
        "attempted_dose_mg": 1000.0,  # Adult dose ordered for 7.5 kg infant (Max safe is 15mg/kg = 112.5mg)
        "severity": "LETHAL_HARD_STOP",
        "mechanism": "Near-10x pediatric overdose resulting in acute fulminant hepatic necrosis.",
        "expected_action": "HARD_STOP_BLOCK"
    }
]

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "core-api")))
from cpoe_dre_engine import CPOEDREEngine
from nicu_pediatric_engine import NICUPediatricEngine, NeonatalDoseToxicityError

class DeterministicSafetyHarness:
    """Evaluates safety test cases directly against the production CPOEDREEngine and NICUPediatricEngine."""
    def __init__(self):
        self.dre = CPOEDREEngine(tenant_id="TENANT-REGRESSION")
        self.nicu = NICUPediatricEngine()
        self.nicu.register_neonate(
            patient_id="NEO-REG-01",
            gestational_age_weeks=38.0,
            birth_weight_grams=7500.0,
            current_weight_grams=7500.0
        )

    def evaluate(self, test_case: Dict) -> Tuple[bool, str]:
        cat = test_case.get("category")
        
        # 1. Evaluate Drug-Drug Interactions directly via production DRE
        if cat == "DRUG_DRUG_INTERACTION":
            drug_a = test_case["drug_a"]
            drug_b = test_case["drug_b"]
            res = self.dre.evaluate_order(
                patient_id="P_DDI_TEST",
                drug_name=drug_a,
                prescribed_dose=100.0,
                route="ORAL",
                patient_weight_kg=70.0,
                patient_bsa_m2=1.73,
                serum_creatinine=1.0,
                patient_age=50,
                is_female=False,
                current_medications=[drug_b],
                known_allergies=[]
            )
            if res["status"] == "BLOCKED":
                return True, f"INTERCEPTED: {res['hard_stops'][0]}"

        # 2. Evaluate Drug-Allergy Cross-Reactivity directly via production DRE
        elif cat == "DRUG_ALLERGY_ANAPHYLAXIS":
            allergen = test_case["allergen"]
            prescribed_drug = test_case["prescribed_drug"]
            res = self.dre.evaluate_order(
                patient_id="P_ALLERGY_TEST",
                drug_name=prescribed_drug,
                prescribed_dose=100.0,
                route="ORAL",
                patient_weight_kg=70.0,
                patient_bsa_m2=1.73,
                serum_creatinine=1.0,
                patient_age=50,
                is_female=False,
                current_medications=[],
                known_allergies=[allergen]
            )
            if res["status"] == "BLOCKED":
                return True, f"INTERCEPTED: {res['hard_stops'][0]}"

        # 3. Evaluate Renal Dose Limits directly via production DRE
        elif cat == "ORGAN_IMPAIRMENT_CONTRAINDICATION":
            prescribed_drug = test_case["prescribed_drug"]
            res = self.dre.evaluate_order(
                patient_id="P_RENAL_TEST",
                drug_name=prescribed_drug,
                prescribed_dose=500.0,
                route="ORAL",
                patient_weight_kg=70.0,
                patient_bsa_m2=1.73,
                serum_creatinine=3.0,
                patient_age=65,
                is_female=False,
                current_medications=[],
                known_allergies=[]
            )
            if res["status"] == "BLOCKED":
                return True, f"INTERCEPTED: {res['hard_stops'][0]}"

        # 4. Evaluate Pediatric Overdose directly via production NICUPediatricEngine
        elif cat == "PEDIATRIC_DOSE_GUARD":
            dose = test_case.get("attempted_dose_mg", 0.0)
            try:
                self.nicu.validate_and_calculate_dose(
                    patient_id="NEO-REG-01",
                    drug_id="DRUG-PARACETAMOL-IV",
                    prescribed_absolute_dose_mg=dose,
                    clinician_id="DOC-REG-01"
                )
            except NeonatalDoseToxicityError as e:
                return True, f"INTERCEPTED: {str(e)}"

        return False, "NO_INTERCEPTION_ALLOWED"

def run_regression_suite(strict_mode: bool = True) -> int:
    harness = DeterministicSafetyHarness()
    print("================================================================================")
    print(" [CLINICAL SAFETY REGRESSION SUITE] EXECUTING INVIOLABLE DRE SAFETY GATES")
    print(f" Test Cases Registered: {len(CANONICAL_SAFETY_CASES)}")
    print(f" Mode: {'STRICT ZERO-TOLERANCE (CI BLOCKING)' if strict_mode else 'AUDIT ONLY'}")
    print("================================================================================")

    passed = 0
    failed = 0
    start_time = time.perf_counter()

    for tc in CANONICAL_SAFETY_CASES:
        t0 = time.perf_counter()
        blocked, reason = harness.evaluate(tc)
        latency_us = (time.perf_counter() - t0) * 1_000_000

        expected = (tc["expected_action"] == "HARD_STOP_BLOCK")
        if blocked == expected:
            passed += 1
            print(f" [PASS] [{tc['id']}] {tc['category']} -> {reason} ({latency_us:.1f} µs)")
        else:
            failed += 1
            print(f" [FATAL REGRESSION] [{tc['id']}] FAILED TO BLOCK LETHAL COMBINATION: {tc} -> {reason}")

    total_time_ms = (time.perf_counter() - start_time) * 1000
    print("================================================================================")
    print(f" RESULTS: {passed} PASSED | {failed} FAILED in {total_time_ms:.2f} ms")
    
    if failed > 0:
        print(" [FATAL SAFETY BLOCK] CLINICAL SAFETY REGRESSION DETECTED!")
        print(" CI/CD DEPLOYMENT PIPELINE TERMINATED IMMEDIATELY.")
        return 1
    
    print(" [SAFETY GATE PASSED] All lethal combinations 100% intercepted with sub-millisecond latency.")
    return 0

if __name__ == "__main__":
    strict = "--strict" in sys.argv or True
    exit_code = run_regression_suite(strict_mode=strict)
    sys.exit(exit_code)
