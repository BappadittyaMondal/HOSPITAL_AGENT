# ====================================================================================================
# PROJECT "HOSPITAL" — FULL-GRAPH LOCAL ONTOLOGICAL INDEX (SNOMED-CT & ICD-11)
# ====================================================================================================
# Module: services/core-api/snomed_icd_ontology_index.py
# Purpose: High-throughput (< 1 ms), deterministic in-memory ontology hierarchy, semantic token matcher,
#          and clinical subsumption engine mapping SNOMED CT Concept IDs to ICD-11 MMS codes.
# ====================================================================================================

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any


@dataclass
class OntologicalConcept:
    concept_id: str               # SNOMED CT Concept ID
    fully_specified_name: str     # e.g., "Acute myocardial infarction (disorder)"
    preferred_term: str          # e.g., "Acute MI"
    icd11_code: str               # e.g., "BA41.0"
    semantic_tag: str             # "disorder", "finding", "procedure", "substance"
    parent_concept_ids: Set[str] = field(default_factory=set)
    colloquial_aliases: Set[str] = field(default_factory=set)


class LocalOntologyGraphIndex:
    """
    In-memory directed acyclic graph (DAG) index representing clinical
    hierarchies with sub-millisecond parent-child relationship traversal.
    """

    def __init__(self):
        self._concepts: Dict[str, OntologicalConcept] = {}
        self._alias_lookup: Dict[str, str] = {}
        self._init_core_ontology()

    def _init_core_ontology(self):
        """Initializes canonical tertiary clinical ontology subgraphs."""
        # Top-Level Root Nodes
        self.register_concept(OntologicalConcept(
            concept_id="64572001",
            fully_specified_name="Disease (disorder)",
            preferred_term="Disease",
            icd11_code="00",
            semantic_tag="disorder"
        ))

        # Cardiovascular Branch
        self.register_concept(OntologicalConcept(
            concept_id="49601007",
            fully_specified_name="Cardiovascular disease (disorder)",
            preferred_term="Cardiovascular disease",
            icd11_code="BA00",
            semantic_tag="disorder",
            parent_concept_ids={"64572001"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="414545008",
            fully_specified_name="Ischemic heart disease (disorder)",
            preferred_term="Ischemic heart disease",
            icd11_code="BA40",
            semantic_tag="disorder",
            parent_concept_ids={"49601007"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="57054005",
            fully_specified_name="Acute coronary syndrome (disorder)",
            preferred_term="Acute coronary syndrome",
            icd11_code="BA41",
            semantic_tag="disorder",
            parent_concept_ids={"414545008"},
            colloquial_aliases={"heart attack", "coronary attack", "acs", "buke byatha"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="70422006",
            fully_specified_name="Acute myocardial infarction (disorder)",
            preferred_term="Acute MI",
            icd11_code="BA41.0",
            semantic_tag="disorder",
            parent_concept_ids={"57054005"},
            colloquial_aliases={"ami", "myocardial infarction", "stemi", "nstemi"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="54329005",
            fully_specified_name="Acute anterior myocardial infarction (disorder)",
            preferred_term="Anterior STEMI",
            icd11_code="BA41.00",
            semantic_tag="disorder",
            parent_concept_ids={"70422006"},
            colloquial_aliases={"anterior wall mi", "anterior stemi", "lad stemi"}
        ))

        # Neurological Branch
        self.register_concept(OntologicalConcept(
            concept_id="118940003",
            fully_specified_name="Disorder of nervous system (disorder)",
            preferred_term="Neurological disorder",
            icd11_code="8A00",
            semantic_tag="disorder",
            parent_concept_ids={"64572001"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="230690007",
            fully_specified_name="Cerebrovascular accident (disorder)",
            preferred_term="Stroke",
            icd11_code="8B00",
            semantic_tag="disorder",
            parent_concept_ids={"118940003"},
            colloquial_aliases={"stroke", "brain stroke", "paralysis attack", "pockha-ghat"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="423441009",
            fully_specified_name="Acute ischemic stroke (disorder)",
            preferred_term="Ischemic stroke",
            icd11_code="8B11",
            semantic_tag="disorder",
            parent_concept_ids={"230690007"},
            colloquial_aliases={"ais", "ischemic stroke", "cerebral infarction"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="274100004",
            fully_specified_name="Subarachnoid hemorrhage (disorder)",
            preferred_term="Subarachnoid hemorrhage",
            icd11_code="8B00.0",
            semantic_tag="disorder",
            parent_concept_ids={"230690007"},
            colloquial_aliases={"sah", "thunderclap headache", "aneurysmal bleed"}
        ))

        # Infectious & Tropical Branch
        self.register_concept(OntologicalConcept(
            concept_id="404684003",
            fully_specified_name="Clinical finding (finding)",
            preferred_term="Clinical finding",
            icd11_code="MG00",
            semantic_tag="finding"
        ))
        self.register_concept(OntologicalConcept(
            concept_id="386661006",
            fully_specified_name="Fever (finding)",
            preferred_term="Fever",
            icd11_code="MG22",
            semantic_tag="finding",
            parent_concept_ids={"404684003"},
            colloquial_aliases={"pyrexia", "fever", "jwor", "bukhar"}
        ))
        self.register_concept(OntologicalConcept(
            concept_id="38362002",
            fully_specified_name="Dengue fever (disorder)",
            preferred_term="Dengue",
            icd11_code="1D20",
            semantic_tag="disorder",
            parent_concept_ids={"64572001"},
            colloquial_aliases={"dengue", "breakbone fever", "dengu jwor"}
        ))

    def register_concept(self, concept: OntologicalConcept):
        self._concepts[concept.concept_id] = concept
        clean_pt = concept.preferred_term.lower().strip()
        self._alias_lookup[clean_pt] = concept.concept_id
        for alias in concept.colloquial_aliases:
            self._alias_lookup[alias.lower().strip()] = concept.concept_id

    def get_concept(self, concept_id: str) -> Optional[OntologicalConcept]:
        return self._concepts.get(concept_id)

    def resolve_term_to_concept_id(self, query: str) -> Optional[str]:
        """Resolves raw query or alias to canonical SNOMED Concept ID."""
        clean = query.lower().strip()
        if clean in self._alias_lookup:
            return self._alias_lookup[clean]
        for c_id, c in self._concepts.items():
            if clean in c.fully_specified_name.lower():
                return c_id
        return None

    def is_a_descendant_of(self, child_concept_id: str, ancestor_concept_id: str) -> bool:
        """
        Traverses parent relationships upwards in the DAG to verify subsumption.
        Returns True if child_concept_id is an instance or sub-class of ancestor_concept_id.
        """
        if child_concept_id == ancestor_concept_id:
            return True

        visited = set()
        queue = [child_concept_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            concept = self._concepts.get(current)
            if not concept:
                continue

            if ancestor_concept_id in concept.parent_concept_ids:
                return True

            for p_id in concept.parent_concept_ids:
                if p_id not in visited:
                    queue.append(p_id)

        return False


local_ontology_index = LocalOntologyGraphIndex()
