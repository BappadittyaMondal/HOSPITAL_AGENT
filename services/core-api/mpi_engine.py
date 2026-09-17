#!/usr/bin/env python3
"""
Master Patient Index (MPI) Probabilistic Linkage Engine (Phase 02).
Implements the Fellegi-Sunter record linkage methodology with specialized phonetic
and typographical normalizers for Indian names (Bengali/Hindi/Sanskrit variants),
ABDM ABHA linkage, manual duplicate review console, and reversible unmerge audit engine.
"""
import re
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

# Indian surname phonetic clusters (Bengali/Sanskrit formal vs colloquial variants)
INDIAN_PHONETIC_CLUSTERS = [
    {"banerjee", "bandopadhyay", "bannerjee", "banerji"},
    {"chatterjee", "chattopadhyay", "chatterji"},
    {"mukherjee", "mukhopadhyay", "mukherji"},
    {"ganguly", "gangopadhyay", "ganguli"},
    {"bhattacharya", "bhattacharyya", "bhattacharjee"},
    {"chakraborty", "chakraborti", "chakravarty", "chakravarti"},
    {"sengupta", "sen", "gupta"},
    {"debnath", "deb"},
    {"majumdar", "mazumdar"},
    {"dutta", "datta", "dutt"},
    {"bose", "basu"},
    {"das", "dass"},
    {"chowdhury", "choudhury", "choudhary"}
]

def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Calculates Jaro-Winkler string similarity between two strings."""
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    max_dist = max(len1, len2) // 2 - 1
    if max_dist < 0:
        max_dist = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - max_dist)
        end = min(i + max_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3.0

    # Winkler modification: prefix scale
    prefix = 0
    for i in range(min(4, len1, len2)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + (prefix * 0.1 * (1.0 - jaro))

def indian_phonetic_match(name1: str, name2: str) -> float:
    """Evaluates phonetic equivalence across Indian name clusters."""
    n1, n2 = name1.lower().strip(), name2.lower().strip()
    if n1 == n2:
        return 1.0
    for cluster in INDIAN_PHONETIC_CLUSTERS:
        if n1 in cluster and n2 in cluster:
            return 0.95
    return jaro_winkler_similarity(n1, n2)

class MasterPatientIndex:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._patients: Dict[str, Dict] = {} # mrn -> patient_record
        self._abha_index: Dict[str, str] = {} # abha_id -> mrn
        self._phone_index: Dict[str, List[str]] = {} # phone -> list of mrns
        self._merge_history: List[Dict] = [] # audit trail of merges and unmerges

    def register_patient(self, patient: Dict) -> Tuple[str, Optional[str]]:
        """
        Registers a new patient or identifies potential duplicates using Fellegi-Sunter scoring.
        Returns: (mrn, match_status_message)
        """
        mrn = patient.get("mrn") or f"MRN-{uuid.uuid4().hex[:8].upper()}"
        patient["mrn"] = mrn
        patient["tenant_id"] = self.tenant_id
        patient["status"] = "ACTIVE"
        patient["merged_into"] = None

        # Check exact ABHA collision first
        abha_id = patient.get("abha_id")
        if abha_id and abha_id in self._abha_index:
            existing_mrn = self._abha_index[abha_id]
            return existing_mrn, f"EXACT_ABHA_MATCH: Patient already registered under {existing_mrn}"

        # Fellegi-Sunter Probabilistic Scan against existing active records
        best_candidate = None
        best_score = 0.0

        for existing_mrn, existing_p in self._patients.items():
            if existing_p["status"] != "ACTIVE":
                continue
            score = self.compute_linkage_score(patient, existing_p)
            if score > best_score:
                best_score = score
                best_candidate = existing_p

        # Decision Thresholds
        if best_candidate and best_score >= 0.88:
            return best_candidate["mrn"], f"HIGH_CONFIDENCE_DUPLICATE (Score: {best_score:.3f}) with {best_candidate['mrn']}"
        elif best_candidate and best_score >= 0.65:
            # Route to Medical Records Manual Resolution Queue
            self._store_patient(mrn, patient)
            return mrn, f"POTENTIAL_DUPLICATE_FLAGGED (Score: {best_score:.3f}) with {best_candidate['mrn']}"

        # Clean, unique patient registration
        self._store_patient(mrn, patient)
        return mrn, "UNIQUE_PATIENT_REGISTERED"

    def compute_linkage_score(self, p1: Dict, p2: Dict) -> float:
        """
        Computes composite Fellegi-Sunter probabilistic linkage weight.
        Weights:
        - First Name similarity: 25%
        - Last Name (Indian phonetic cluster): 30%
        - Date of Birth match: 20%
        - Gender match: 5%
        - Primary Phone match: 20%
        """
        # First name
        fn1 = p1.get("first_name", "")
        fn2 = p2.get("first_name", "")
        fn_score = jaro_winkler_similarity(fn1, fn2)

        # Last name with Indian phonetic cluster support
        ln1 = p1.get("last_name", "")
        ln2 = p2.get("last_name", "")
        ln_score = indian_phonetic_match(ln1, ln2)

        # DOB match
        dob1 = p1.get("dob", "")
        dob2 = p2.get("dob", "")
        if dob1 and dob2 and dob1 == dob2:
            dob_score = 1.0
        elif dob1 and dob2 and dob1[:4] == dob2[:4]: # Same birth year
            dob_score = 0.5
        else:
            dob_score = 0.0

        # Gender match
        g1 = p1.get("gender", "").lower()
        g2 = p2.get("gender", "").lower()
        gender_score = 1.0 if g1 and g2 and g1 == g2 else 0.0

        # Phone match
        ph1 = re.sub(r"\D", "", p1.get("primary_phone", ""))[-10:]
        ph2 = re.sub(r"\D", "", p2.get("primary_phone", ""))[-10:]
        phone_score = 1.0 if ph1 and ph2 and ph1 == ph2 else 0.0

        # Composite score calculation
        total_score = (
            (fn_score * 0.25) +
            (ln_score * 0.30) +
            (dob_score * 0.20) +
            (gender_score * 0.05) +
            (phone_score * 0.20)
        )
        return total_score

    def _store_patient(self, mrn: str, patient: Dict):
        self._patients[mrn] = patient
        if patient.get("abha_id"):
            self._abha_index[patient["abha_id"]] = mrn
        phone = re.sub(r"\D", "", patient.get("primary_phone", ""))[-10:]
        if phone:
            if phone not in self._phone_index:
                self._phone_index[phone] = []
            self._phone_index[phone].append(mrn)

    def merge_patient_records(self, primary_mrn: str, secondary_mrn: str, authorized_by: str, reason: str) -> bool:
        """
        Merges duplicate secondary patient into primary patient.
        Preserves complete rollback state in audit history.
        """
        if primary_mrn not in self._patients or secondary_mrn not in self._patients:
            return False
        if primary_mrn == secondary_mrn:
            return False

        sec = self._patients[secondary_mrn]
        sec["status"] = "MERGED"
        sec["merged_into"] = primary_mrn

        merge_event = {
            "event_id": str(uuid.uuid4()),
            "action": "MERGE",
            "primary_mrn": primary_mrn,
            "secondary_mrn": secondary_mrn,
            "authorized_by": authorized_by,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._merge_history.append(merge_event)
        return True

    def unmerge_patient_records(self, secondary_mrn: str, authorized_by: str, reason: str) -> bool:
        """
        Deterministic Unmerge: Safely unlinks a previously joined patient chart.
        """
        if secondary_mrn not in self._patients:
            return False
        sec = self._patients[secondary_mrn]
        if sec["status"] != "MERGED":
            return False

        primary_mrn = sec["merged_into"]
        sec["status"] = "ACTIVE"
        sec["merged_into"] = None

        unmerge_event = {
            "event_id": str(uuid.uuid4()),
            "action": "UNMERGE",
            "primary_mrn": primary_mrn,
            "secondary_mrn": secondary_mrn,
            "authorized_by": authorized_by,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._merge_history.append(unmerge_event)
        return True

    def validate_and_link_abha(self, mrn: str, abha_id: str, abha_address: str) -> bool:
        """
        Validates 14-digit Indian ABHA ID (e.g. 12-3456-7890-1234) and links to MRN.
        """
        cleaned_id = re.sub(r"\D", "", abha_id)
        if len(cleaned_id) != 14:
            return False
        if "@" not in abha_address:
            return False

        if mrn in self._patients:
            self._patients[mrn]["abha_id"] = abha_id
            self._patients[mrn]["abha_address"] = abha_address
            self._abha_index[abha_id] = mrn
            return True
        return False
