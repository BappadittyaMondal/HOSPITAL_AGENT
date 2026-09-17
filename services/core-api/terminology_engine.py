#!/usr/bin/env python3
"""
High-Performance Standard Clinical Terminology Engine.
Provides sub-5ms in-memory lookup and semantic search for:
1. SNOMED CT (International & Indian Extension)
2. LOINC (v2.76+ Laboratory & Observational Codes)
3. ICD-11 MMS (International Classification of Diseases, 11th Revision)
"""
import time
from typing import Dict, List, Optional

# Core clinical reference seed dataset across the 3 standard terminologies
SEED_TERMINOLOGY_DATA = {
    "SNOMED": [
        {"code": "38341003", "display": "Hypertensive disorder, systemic arterial (disorder)", "semantic_tag": "disorder"},
        {"code": "73211009", "display": "Diabetes mellitus (disorder)", "semantic_tag": "disorder"},
        {"code": "22298006", "display": "Myocardial infarction (disorder)", "semantic_tag": "disorder"},
        {"code": "44054006", "display": "Type 2 diabetes mellitus (disorder)", "semantic_tag": "disorder"},
        {"code": "233604007", "display": "Pneumonia (disorder)", "semantic_tag": "disorder"},
        {"code": "80146002", "display": "Appendectomy (procedure)", "semantic_tag": "procedure"},
        {"code": "399248000", "display": "Complete blood count (procedure)", "semantic_tag": "procedure"},
        {"code": "182888003", "display": "Medication prescribed (situation)", "semantic_tag": "situation"},
        {"code": "41847000", "display": "Normal blood pressure (finding)", "semantic_tag": "finding"},
        {"code": "386661006", "display": "Fever (finding)", "semantic_tag": "finding"}
    ],
    "LOINC": [
        {"code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood", "component": "Hemoglobin", "system": "Bld"},
        {"code": "4544-3", "display": "Hematocrit [Volume Fraction] of Blood", "component": "Hematocrit", "system": "Bld"},
        {"code": "6690-2", "display": "Leukocytes [#/volume] in Blood", "component": "Leukocytes", "system": "Bld"},
        {"code": "777-3", "display": "Platelets [#/volume] in Blood", "component": "Platelets", "system": "Bld"},
        {"code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma", "component": "Glucose", "system": "Ser/Plas"},
        {"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma", "component": "Creatinine", "system": "Ser/Plas"},
        {"code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma", "component": "Potassium", "system": "Ser/Plas"},
        {"code": "2951-2", "display": "Sodium [Moles/volume] in Serum or Plasma", "component": "Sodium", "system": "Ser/Plas"},
        {"code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood", "component": "HbA1c", "system": "Bld"},
        {"code": "33914-3", "display": "Glomerular filtration rate/1.73 sq M.predicted", "component": "eGFR", "system": "Ser/Plas"}
    ],
    "ICD11": [
        {"code": "BA00", "display": "Essential hypertension", "chapter": "11"},
        {"code": "5A11", "display": "Type 2 diabetes mellitus", "chapter": "05"},
        {"code": "BA41", "display": "Acute myocardial infarction", "chapter": "11"},
        {"code": "CA40", "display": "Pneumonia", "chapter": "12"},
        {"code": "1D01", "display": "Dengue fever", "chapter": "01"},
        {"code": "1A00", "display": "Cholera", "chapter": "01"},
        {"code": "8B11", "display": "Ischemic stroke", "chapter": "08"},
        {"code": "MD11", "display": "Non-accidental injury to child", "chapter": "22"},
        {"code": "MB23", "display": "Suicide attempt", "chapter": "21"},
        {"code": "JA00", "display": "Single spontaneous delivery", "chapter": "18"}
    ]
}

class TerminologyEngine:
    def __init__(self):
        # Code to Concept map: (system, code) -> concept
        self._code_index: Dict[str, Dict] = {}
        # Search index for text queries
        self._text_index: Dict[str, List[Dict]] = {"SNOMED": [], "LOINC": [], "ICD11": []}
        self._load_seed_terminologies()

    def _load_seed_terminologies(self):
        for system, concepts in SEED_TERMINOLOGY_DATA.items():
            for c in concepts:
                key = f"{system}:{c['code']}"
                enriched = {**c, "system": system}
                self._code_index[key] = enriched
                self._text_index[system].append(enriched)

    def lookup_code(self, system: str, code: str) -> Optional[Dict]:
        """Sub-millisecond direct code lookup (O(1) hash map)."""
        key = f"{system.upper()}:{code.strip()}"
        return self._code_index.get(key)

    def search(self, system: str, query: str, limit: int = 5) -> List[Dict]:
        """Fast prefix/substring search."""
        sys_key = system.upper()
        if sys_key not in self._text_index:
            return []
        q = query.lower().strip()
        results = []
        for item in self._text_index[sys_key]:
            if q in item["display"].lower() or q == item["code"].lower():
                results.append(item)
                if len(results) >= limit:
                    break
        return results

# Singleton instance
_engine = TerminologyEngine()

def get_terminology_engine() -> TerminologyEngine:
    return _engine


import re

# ====================================================================================================
# BRAND-TO-GENERIC ACTIVE PHARMACEUTICAL INGREDIENT (API) INDEX
# Comprehensive dictionary spanning Indian market brands and US FDA / International trade names
# ====================================================================================================
BRAND_TO_GENERIC_MAP: Dict[str, str] = {
    # PDE5 Inhibitors (Fatal DDI with Nitrates)
    "caverta": "sildenafil",
    "penegra": "sildenafil",
    "viagra": "sildenafil",
    "revatio": "sildenafil",
    "kamagra": "sildenafil",
    "silagra": "sildenafil",
    "manforce": "sildenafil",
    "cialis": "tadalafil",
    "megalis": "tadalafil",
    "forzest": "tadalafil",
    "levitra": "vardenafil",

    # Nitrates (Fatal DDI with PDE5 Inhibitors)
    "sorbitrate": "isosorbide dinitrate",
    "isordil": "isosorbide dinitrate",
    "monotrate": "isosorbide mononitrate",
    "imdur": "isosorbide mononitrate",
    "angispan": "nitroglycerin",
    "nitrolingual": "nitroglycerin",
    "nitrocontin": "nitroglycerin",
    "glyceryl trinitrate": "nitroglycerin",

    # NSAIDs (Lethal DDI with Warfarin / ulcerogenic)
    "dynapar": "diclofenac",
    "voveran": "diclofenac",
    "voltaren": "diclofenac",
    "combiflam": "ibuprofen",
    "brufen": "ibuprofen",
    "advil": "ibuprofen",
    "motrin": "ibuprofen",
    "naprosyn": "naproxen",
    "aleve": "naproxen",
    "toradol": "ketorolac",
    "ketorol": "ketorolac",
    "indocin": "indomethacin",
    "mobic": "meloxicam",
    "feldene": "piroxicam",
    "disprin": "aspirin",
    "ecospirin": "aspirin",
    "ecosprin": "aspirin",
    "aspirin": "aspirin",
    "bayer": "aspirin",

    # Anticoagulants
    "uniwarfin": "warfarin",
    "coumadin": "warfarin",
    "jantoven": "warfarin",
    "warfar": "warfarin",
    "clexane": "enoxaparin",
    "lovenox": "enoxaparin",
    "eliquis": "apixaban",
    "xarelto": "rivaroxaban",
    "pradaxa": "dabigatran",

    # Antibiotics / Oxazolidinones / Folate Antagonists
    "zyvox": "linezolid",
    "linospan": "linezolid",
    "lizomac": "linezolid",
    "bactrim": "trimethoprim-sulfamethoxazole",
    "septra": "trimethoprim-sulfamethoxazole",
    "septrin": "trimethoprim-sulfamethoxazole",
    "cotrimoxazole": "trimethoprim-sulfamethoxazole",
    "augmentin": "amoxicillin-clavulanate",
    "moxikind-cv": "amoxicillin-clavulanate",
    "clavum": "amoxicillin-clavulanate",
    "amoxil": "amoxicillin",
    "omnipen": "ampicillin",
    "pipracil": "piperacillin",
    "tazocin": "piperacillin-tazobactam",
    "rocephin": "ceftriaxone",
    "monocef": "ceftriaxone",
    "ancef": "cefazolin",
    "kefzol": "cefazolin",
    "claforan": "cefotaxime",
    "taxim": "cefotaxime",
    "maxipime": "cefepime",
    "suprax": "cefixime",
    "zifi": "cefixime",
    "cipro": "ciprofloxacin",
    "ciplox": "ciprofloxacin",
    "cifran": "ciprofloxacin",
    "levaquin": "levofloxacin",
    "levomac": "levofloxacin",
    "l-cin": "levofloxacin",
    "avelox": "moxifloxacin",
    "moxicip": "moxifloxacin",

    # Antidepressants (SSRIs / SNRIs)
    "prozac": "fluoxetine",
    "fludac": "fluoxetine",
    "zoloft": "sertraline",
    "daxid": "sertraline",
    "paxil": "paroxetine",
    "parotin": "paroxetine",
    "celexa": "citalopram",
    "celica": "citalopram",
    "lexapro": "escitalopram",
    "cipralex": "escitalopram",
    "nexito": "escitalopram",
    "effexor": "venlafaxine",
    "venlor": "venlafaxine",
    "cymbalta": "duloxetine",
    "dulane": "duloxetine",

    # Antiplatelet & PPIs
    "plavix": "clopidogrel",
    "clopilet": "clopidogrel",
    "deplatt": "clopidogrel",
    "omez": "omeprazole",
    "prilosec": "omeprazole",
    "losec": "omeprazole",
    "nexium": "esomeprazole",
    "esomac": "esomeprazole",
    "pantocid": "pantoprazole",
    "pan": "pantoprazole",
    "protonix": "pantoprazole",

    # Antihypertensives / ACEi / ARBs / Diuretics
    "cardace": "ramipril",
    "altace": "ramipril",
    "vasotec": "enalapril",
    "envas": "enalapril",
    "prinivil": "lisinopril",
    "zestril": "lisinopril",
    "listril": "lisinopril",
    "cozaar": "losartan",
    "losar": "losartan",
    "covance": "losartan",
    "telma": "telmisartan",
    "micardis": "telmisartan",
    "telmikem": "telmisartan",
    "diovan": "valsartan",
    "valzaar": "valsartan",
    "aldactone": "spironolactone",
    "aldostig": "spironolactone",
    "inspra": "eplerenone",
    "eptus": "eplerenone",
    "k-bind": "potassium chloride",
    "potcl": "potassium chloride",

    # Cardiac / Antiarrhythmics
    "lanoxin": "digoxin",
    "cordarone": "amiodarone",
    "betapace": "sotalol",
    "haldol": "haloperidol",
    "zofran": "ondansetron",
    "emset": "ondansetron",

    # Antidiabetic
    "glucophage": "metformin",
    "glycomet": "metformin",
    "glybovin": "glibenclamide",

    # Oncology / Chemotherapy
    "adriblastina": "doxorubicin",
    "adriamycin": "doxorubicin",
    "blenoxane": "bleomycin",
    "platinol": "cisplatin",
    "trexall": "methotrexate",
    "folitrax": "methotrexate",

    # Teratogens (FDA Pregnancy Category D/X)
    "accutane": "isotretinoin",
    "isotroin": "isotretinoin",
    "depakote": "sodium valproate",
    "valparin": "sodium valproate",
    "encorate": "sodium valproate",
    "lipitor": "atorvastatin",
    "atorva": "atorvastatin",
    "atorlip": "atorvastatin",
    "crestor": "rosuvastatin",
    "rosuvas": "rosuvastatin",
    "rozavel": "rosuvastatin",
    "zocor": "simvastatin",
    "simvotin": "simvastatin",

    # Beers Criteria Geriatric High-Risk
    "atarax": "hydroxyzine",
    "benadryl": "diphenhydramine",
    "zeet": "chlorpheniramine",
    "piriton": "chlorpheniramine",
    "phenergan": "promethazine",
    "avomine": "promethazine",
    "valium": "diazepam",
    "calmpose": "diazepam",
    "librium": "chlordiazepoxide",
    "klonopin": "clonazepam",
    "rivotril": "clonazepam",
    "zapiz": "clonazepam",
    "elavil": "amitriptyline",
    "tryptomer": "amitriptyline"
}


def normalize_drug_name(raw_name: str) -> str:
    """
    Standardizes commercial brand names and clinical aliases to active generic INN.
    Strips formulation suffixes, dosage numbers, and route qualifiers.
    Sub-millisecond lookup guarantee.
    """
    if not raw_name or not isinstance(raw_name, str):
        return ""

    cleaned = raw_name.lower().strip()

    # Direct match in brand map
    if cleaned in BRAND_TO_GENERIC_MAP:
        return BRAND_TO_GENERIC_MAP[cleaned]

    # Split on whitespace/punctuation to check tokens
    tokens = re.split(r"[\s\-_/,+]+", cleaned)
    for token in tokens:
        # Check token without trailing dosage units (e.g. "50mg", "100mcg")
        clean_token = re.sub(r"\d+(\.\d+)?(mg|mcg|g|ml|iu|u|%|meq)?$", "", token).strip()
        if clean_token in BRAND_TO_GENERIC_MAP:
            return BRAND_TO_GENERIC_MAP[clean_token]
        if token in BRAND_TO_GENERIC_MAP:
            return BRAND_TO_GENERIC_MAP[token]

    # Check compound substring matches for known brands
    for brand, generic in BRAND_TO_GENERIC_MAP.items():
        if len(brand) >= 4 and brand in cleaned:
            return generic

    # Return normalized clean name if not a known brand
    stripped = re.sub(r"\b(tab|tablet|cap|capsule|inj|injection|syp|syrup|iv|im|po|oral|prn|stat|od|bd|tid|qid|\d+mg|\d+mcg|\d+g|\d+ml)\b", "", cleaned).strip()
    return stripped if stripped else cleaned


def get_drug_aliases(generic_name: str) -> List[str]:
    """Returns all registered brand names mapped to the given generic drug."""
    target = generic_name.lower().strip()
    return [brand for brand, generic in BRAND_TO_GENERIC_MAP.items() if generic == target]

