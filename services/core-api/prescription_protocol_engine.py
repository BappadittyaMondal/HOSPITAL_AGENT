# ====================================================================================================
# PROJECT "HOSPITAL" — STANDARD TREATMENT GUIDELINES (STG) PRESCRIPTION GENERATION ENGINE
# ====================================================================================================
# Module: services/core-api/prescription_protocol_engine.py
# Purpose: Generates evidence-based clinical prescription orders and emergency holding regimens
#          aligned strictly with WHO Model Formulary, AIIMS New Delhi Emergency Protocols, and
#          National List of Essential Medicines (NLEM 2022).
# Features:
#   - 48 Complete Clinical Conditions with Primary and Alternative Regimens
#   - Pediatric weight-based dosing computation (mg/kg)
#   - Mandatory baseline laboratory and diagnostic orders
#   - Therapeutic monitoring and non-pharmacological emergency directives
#   - Integrated pre-screening via NLEM Formulary Engine (Zero DDI, zero teratogen leakage)
# ====================================================================================================

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

try:
    from nlem_formulary_engine import global_nlem_formulary_engine
except ImportError:
    from services.core_api.nlem_formulary_engine import global_nlem_formulary_engine


class RegimenType(str, Enum):
    FIRST_LINE = "FIRST_LINE"
    ALTERNATIVE_ALLERGY = "ALTERNATIVE_ALLERGY"
    ALTERNATIVE_PREGNANCY = "ALTERNATIVE_PREGNANCY"
    ALTERNATIVE_RENAL = "ALTERNATIVE_RENAL"


@dataclass
class PrescriptionItem:
    drug_name: str
    dose_adult: str
    pediatric_dose_mg_per_kg: Optional[float] = None
    max_pediatric_dose: Optional[str] = None
    route: str = "ORAL"  # ORAL, IV, IM, SUBLINGUAL, INHALATION, SC
    frequency: str = "OD"  # STAT, OD, BD, TDS, QID, PRN, CONTINUOUS_INFUSION
    duration_days: int = 5
    instructions: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drug_name": self.drug_name,
            "dose_adult": self.dose_adult,
            "pediatric_dose_mg_per_kg": self.pediatric_dose_mg_per_kg,
            "max_pediatric_dose": self.max_pediatric_dose,
            "route": self.route,
            "frequency": self.frequency,
            "duration_days": self.duration_days,
            "instructions": self.instructions
        }


@dataclass
class ClinicalSTGProtocol:
    disease_key: str
    disease_name: str
    category: str
    first_line_regimen: List[PrescriptionItem]
    alternative_regimen: List[PrescriptionItem]
    mandatory_baseline_labs: List[str]
    therapeutic_monitoring: List[str]
    urgent_interventions: List[str]
    clinical_pearls: str = ""


# ====================================================================================================
# COMPREHENSIVE 48-DISEASE STANDARD TREATMENT GUIDELINE REGISTRY (WHO / AIIMS)
# ====================================================================================================

STG_PROTOCOL_CATALOG: Dict[str, ClinicalSTGProtocol] = {
    "ACUTE_MYOCARDIAL_INFARCTION": ClinicalSTGProtocol(
        disease_key="ACUTE_MYOCARDIAL_INFARCTION",
        disease_name="Acute Myocardial Infarction (STEMI / NSTEMI)",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Aspirin", "300mg", None, None, "ORAL", "STAT", 1, "Chewed immediately"),
            PrescriptionItem("Clopidogrel", "300mg", None, None, "ORAL", "STAT", 1, "Loading dose (600mg if primary PCI planned)"),
            PrescriptionItem("Atorvastatin", "80mg", None, None, "ORAL", "STAT", 30, "High-intensity statin therapy at bedtime"),
            PrescriptionItem("Heparin", "5000 units", None, None, "IV", "STAT", 1, "IV bolus followed by weight-adjusted infusion"),
            PrescriptionItem("Nitroglycerin", "0.5mg", None, None, "SUBLINGUAL", "PRN", 1, "Repeat every 5 min up to 3 doses; withhold if SBP < 90 or RV infarction")
        ],
        alternative_regimen=[
            PrescriptionItem("Clopidogrel", "300mg", None, None, "ORAL", "STAT", 1, "Single antiplatelet if documented true aspirin hypersensitivity"),
            PrescriptionItem("Atorvastatin", "80mg", None, None, "ORAL", "STAT", 30, "High-intensity statin"),
            PrescriptionItem("Enoxaparin", "30mg", None, None, "IV", "STAT", 1, "IV bolus followed by 1mg/kg SC BD")
        ],
        mandatory_baseline_labs=["12-Lead ECG within 10 min", "Cardiac Troponin I / T", "Serum Creatinine", "Serum Electrolytes", "CBC", "PT/INR"],
        therapeutic_monitoring=["Continuous cardiac telemetry for lethal arrhythmias", "Blood pressure every 15 min during nitrate therapy", "Watch for bleeding signs"],
        urgent_interventions=["Immediate activation of Cardiac Catheterization Lab (Door-to-Balloon < 90 min)", "Supplemental oxygen only if SpO2 < 90%", "Two wide-bore IV lines"],
        clinical_pearls="Strictly avoid Nitrates and Morphine if inferior STEMI with RV involvement (V4R ST elevation) or SBP < 90 mmHg."
    ),

    "ACUTE_APPENDICITIS": ClinicalSTGProtocol(
        disease_key="ACUTE_APPENDICITIS",
        disease_name="Acute Appendicitis",
        category="GASTROINTESTINAL",
        first_line_regimen=[
            PrescriptionItem("Ceftriaxone", "1g", 50.0, "2g/day", "IV", "BD", 3, "Broad spectrum pre-operative coverage"),
            PrescriptionItem("Metronidazole", "500mg", 7.5, "1500mg/day", "IV", "TDS", 3, "Anaerobic bacteroides coverage"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 3, "Multimodal post-op analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Ciprofloxacin", "400mg", 10.0, "800mg/day", "IV", "BD", 3, "If severe beta-lactam anaphylaxis"),
            PrescriptionItem("Metronidazole", "500mg", 7.5, "1500mg/day", "IV", "TDS", 3, "Anaerobic coverage"),
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "TDS", 2, "Alternative non-NSAID analgesia")
        ],
        mandatory_baseline_labs=["CBC with differential (Leukocytosis > 10,000/uL)", "Serum Creatinine", "Urine Pregnancy Test (hCG) in all reproductive-age females", "USG Abdomen / CT Abdomen"],
        therapeutic_monitoring=["Hourly abdominal exam for generalized guarding", "Temperature and pulse monitoring for sepsis"],
        urgent_interventions=["Keep strictly Nil Per Oral (NPO)", "Urgent Emergency General Surgery Consult for Laparoscopic Appendectomy", "IV Crystalloid resuscitation (Ringer Lactate)"],
        clinical_pearls="Never administer enemas or strong laxatives which increase intraluminal pressure and perforation risk."
    ),

    "BACTERIAL_MENINGITIS": ClinicalSTGProtocol(
        disease_key="BACTERIAL_MENINGITIS",
        disease_name="Acute Bacterial Meningitis",
        category="NEUROLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Ceftriaxone", "2g", 50.0, "4g/day", "IV", "BD", 10, "High meningeal dose; cross blood-brain barrier"),
            PrescriptionItem("Vancomycin", "1000mg", 15.0, "2000mg/day", "IV", "BD", 10, "Empirical MRSA and resistant S. pneumoniae coverage"),
            PrescriptionItem("Dexamethasone", "10mg", 0.15, "40mg/day", "IV", "QID", 4, "Give 15-20 min before or with first antibiotic dose to reduce hearing loss")
        ],
        alternative_regimen=[
            PrescriptionItem("Vancomycin", "1000mg", 15.0, "2000mg/day", "IV", "BD", 10, "In severe beta-lactam anaphylaxis"),
            PrescriptionItem("Chloramphenicol", "1000mg", 25.0, "4000mg/day", "IV", "QID", 10, "High CNS penetration alternative"),
            PrescriptionItem("Dexamethasone", "10mg", 0.15, "40mg/day", "IV", "QID", 4, "Anti-inflammatory meningeal stabilization")
        ],
        mandatory_baseline_labs=["Blood cultures x 2 before antibiotics if possible", "Lumbar Puncture (CSF analysis: opening pressure, Gram stain, protein, glucose, culture)", "Non-contrast Head CT before LP if altered sensorium, focal neuro deficit, or papilledema"],
        therapeutic_monitoring=["GCS and pupillary reflexes every 1 hour", "Serum Sodium (watch for SIADH or cerebral salt wasting)", "Trough Vancomycin levels"],
        urgent_interventions=["Droplet precautions for first 24 hours of effective therapy", "Immediate antibiotic initiation — do NOT delay antibiotics for neuroimaging", "Elevate head of bed 30 degrees"],
        clinical_pearls="If patient is > 50 years or immunocompromised, empirically add Ampicillin 2g IV q4h for Listeria monocytogenes."
    ),

    "SEPTIC_SHOCK": ClinicalSTGProtocol(
        disease_key="SEPTIC_SHOCK",
        disease_name="Septic Shock (Surviving Sepsis Campaign)",
        category="INFECTIOUS",
        first_line_regimen=[
            PrescriptionItem("Piperacillin-Tazobactam", "4.5g", 100.0, "18g/day", "IV", "TDS", 7, "Broad spectrum pseudomonal and intra-abdominal coverage"),
            PrescriptionItem("Vancomycin", "1000mg", 15.0, "2000mg/day", "IV", "BD", 7, "Empirical MRSA coverage"),
            PrescriptionItem("Norepinephrine", "4mg", 0.05, None, "IV", "CONTINUOUS_INFUSION", 3, "Titrate 0.05-2.0 mcg/kg/min to target MAP >= 65 mmHg"),
            PrescriptionItem("Hydrocortisone", "50mg", 1.0, "200mg/day", "IV", "QID", 5, "Refractory vasopressor shock rescue")
        ],
        alternative_regimen=[
            PrescriptionItem("Meropenem", "1g", 20.0, "3g/day", "IV", "TDS", 7, "If prior ESBL or severe penicillin anaphylaxis alternative"),
            PrescriptionItem("Vancomycin", "1000mg", 15.0, "2000mg/day", "IV", "BD", 7, "MRSA coverage"),
            PrescriptionItem("Norepinephrine", "4mg", 0.05, None, "IV", "CONTINUOUS_INFUSION", 3, "First-line vasopressor")
        ],
        mandatory_baseline_labs=["Serum Lactate (recheck at 2-4 hours)", "Blood cultures x 2 sites prior to antimicrobial infusion", "CBC with differential", "Serum Creatinine and LFTs", "Coagulation profile"],
        therapeutic_monitoring=["Invasive arterial blood pressure monitoring", "Continuous pulse oximetry and urine output (>0.5 mL/kg/h)", "Serial lactate clearance"],
        urgent_interventions=["30 mL/kg IV crystalloid (Balanced solution / Plasmalyte) within first 3 hours", "Initiate Norepinephrine early if profound hypotension", "Urgent surgical/interventional source control within 6-12 hours"],
        clinical_pearls="Every 1 hour delay in antibiotic administration produces a 7.6% increase in septic shock mortality."
    ),

    "ACUTE_SEVERE_ASTHMA": ClinicalSTGProtocol(
        disease_key="ACUTE_SEVERE_ASTHMA",
        disease_name="Acute Severe Asthma (Status Asthmaticus)",
        category="PULMONARY",
        first_line_regimen=[
            PrescriptionItem("Salbutamol", "5mg", 0.15, "5mg/neb", "INHALATION", "STAT", 1, "Driven by high-flow oxygen; repeat every 20 min x 3"),
            PrescriptionItem("Ipratropium", "0.5mg", 0.25, "0.5mg/neb", "INHALATION", "STAT", 1, "Combined with Salbutamol for first hour"),
            PrescriptionItem("Hydrocortisone", "100mg", 4.0, "400mg/day", "IV", "QID", 5, "Or Methylprednisolone 1mg/kg IV"),
            PrescriptionItem("Magnesium Sulfate", "2g", 50.0, "2000mg", "IV", "STAT", 1, "Over 20 min in severe/refractory bronchospasm")
        ],
        alternative_regimen=[
            PrescriptionItem("Salbutamol", "5mg", 0.15, "5mg/neb", "INHALATION", "STAT", 1, "Continuous nebulization"),
            PrescriptionItem("Prednisolone", "40mg", 1.0, "50mg/day", "ORAL", "OD", 5, "Oral systemic corticosteroid if able to swallow"),
            PrescriptionItem("Magnesium Sulfate", "2g", 50.0, "2000mg", "IV", "STAT", 1, "Bronchodilator smooth muscle relaxant")
        ],
        mandatory_baseline_labs=["Arterial Blood Gas (ABG) — watch for normal or elevated PaCO2 indicating impending respiratory arrest", "Chest X-Ray to rule out pneumothorax", "Serum Potassium (beta-agonists drive hypokalemia)", "Peak Expiratory Flow (PEFR)"],
        therapeutic_monitoring=["Continuous SpO2 (target 93-95% in adults, 94-98% in children)", "Work of breathing, accessory muscle use, pulsus paradoxus", "Watch for silent chest on auscultation"],
        urgent_interventions=["Immediate high-flow humidified oxygen", "Non-invasive positive pressure ventilation (BiPAP) if tiring", "Prepare for emergency rapid sequence intubation with Ketamine if exhausted"],
        clinical_pearls="A 'normal' PaCO2 (40 mmHg) in a breathless, tachypneic asthmatic is NOT normal — it is a red flag for impending respiratory failure and muscle fatigue."
    ),

    "ORGANOPHOSPHATE_POISONING": ClinicalSTGProtocol(
        disease_key="ORGANOPHOSPHATE_POISONING",
        disease_name="Acute Organophosphate Poisoning",
        category="TOXICOLOGY",
        first_line_regimen=[
            PrescriptionItem("Atropine", "2mg", 0.05, None, "IV", "STAT", 1, "Double dose every 5 min (2, 4, 8, 16mg) until bronchosecretions dry and lungs clear"),
            PrescriptionItem("Pralidoxime", "2g", 30.0, "2000mg", "IV", "STAT", 1, "Loading dose over 30 min, followed by 500mg/h infusion for 24-48h"),
            PrescriptionItem("Diazepam", "10mg", 0.2, "10mg", "IV", "STAT", 1, "Slow IV push for fasciculations, seizures, or extreme agitation")
        ],
        alternative_regimen=[
            PrescriptionItem("Atropine", "2mg", 0.05, None, "IV", "STAT", 1, "Standard atropinization protocol"),
            PrescriptionItem("Midazolam", "5mg", 0.1, "5mg", "IV", "STAT", 1, "Alternative benzodiazepine for seizure control")
        ],
        mandatory_baseline_labs=["Serum Pseudocholinesterase / RBC Acetylcholinesterase activity", "ABG with Lactate", "Serum Electrolytes and Creatinine", "Chest X-Ray (pulmonary edema / aspiration)", "12-Lead ECG (QT prolongation, heart block)"],
        therapeutic_monitoring=["End-points of atropinization: clear chest on auscultation, HR > 80, systolic BP > 80, dry axillae, dilated pupils (tachycardia alone is NOT a contraindication)"],
        urgent_interventions=["Immediate dermal decontamination (remove all contaminated clothing, wash skin thoroughly with soap and water)", "Staff must wear personal protective equipment (PPE / nitrile gloves)", "Endotracheal intubation for copious bronchial secretions"],
        clinical_pearls="Atropine reverses muscarinic effects (SLUDGE: salivation, lacrimation, urination, defecation, GI upset, emesis), but does NOT reverse nicotinic muscle paralysis. Pralidoxime is mandatory for nicotinic receptor reactivation."
    ),

    "ECLAMPSIA": ClinicalSTGProtocol(
        disease_key="ECLAMPSIA",
        disease_name="Eclampsia / Severe Pre-eclampsia with Imminent Eclampsia",
        category="OBSTETRIC_GYNECOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Magnesium Sulfate", "4g", None, None, "IV", "STAT", 1, "Pritchard/Zuspan loading: 4g IV over 10-15 min + 10g deep IM (5g each buttock)"),
            PrescriptionItem("Magnesium Sulfate", "1g", None, None, "IV", "CONTINUOUS_INFUSION", 2, "Maintenance: 1g/h IV or 5g IM q4h for 24 hours post-delivery or post-last seizure"),
            PrescriptionItem("Labetalol", "20mg", None, None, "IV", "STAT", 1, "Slow IV bolus over 2 min; repeat 40-80mg q10m to target SBP 140-150, DBP 90-100"),
            PrescriptionItem("Calcium Gluconate", "1000mg", None, None, "IV", "PRN", 1, "Antidote immediately at bedside for magnesium toxicity (10mL 10% solution over 10 min)")
        ],
        alternative_regimen=[
            PrescriptionItem("Hydralazine", "5mg", None, None, "IV", "STAT", 1, "Alternative vasodilator if labetalol contraindicated (asthma/bradycardia)"),
            PrescriptionItem("Nifedipine", "10mg", None, None, "ORAL", "STAT", 1, "Immediate release orally swallowed if IV access delayed")
        ],
        mandatory_baseline_labs=["Complete Blood Count with Platelet count (<100,000 indicates HELLP syndrome)", "AST, ALT, Bilirubin, LDH (HELLP screening)", "Serum Creatinine and Uric Acid", "Urine Albumin / Protein-to-Creatinine ratio", "Coagulation profile"],
        therapeutic_monitoring=["Hourly knee jerk / patellar reflexes (loss of reflex is earliest sign of Mg toxicity)", "Respiratory rate (>16/min mandatory; <12/min = toxicity)", "Urine output (>30 mL/h mandatory since Mg is 100% renally excreted)"],
        urgent_interventions=["Left lateral tilt to avoid aortocaval compression", "Padded bed rails and bite block/airway protection", "Definitive cure is delivery: stabilize mother first, plan urgent delivery regardless of gestational age"],
        clinical_pearls="Never use ACE inhibitors (Enalapril, Ramipril) or ARBs in pregnancy due to severe fetal renal agenesis and death."
    ),

    "SNAKE_ENVENOMATION_VASCULOTOXIC": ClinicalSTGProtocol(
        disease_key="SNAKE_ENVENOMATION_VASCULOTOXIC",
        disease_name="Vasculotoxic Snake Envenomation (Russell's / Saw-scaled Viper)",
        category="TOXICOLOGY",
        first_line_regimen=[
            PrescriptionItem("Snake Antivenom", "100ml", 10.0, "100ml", "IV", "STAT", 1, "Polyvalent ASV reconstituted in 200mL Normal Saline over 1 hour"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 3, "Safe analgesia; STRICTLY AVOID NSAIDs/Aspirin due to hemorrhage risk"),
            PrescriptionItem("Tetanus Toxoid", "0.5ml", 0.5, "0.5ml", "IM", "STAT", 1, "Wound prophylaxis")
        ],
        alternative_regimen=[
            PrescriptionItem("Snake Antivenom", "100ml", 10.0, "100ml", "IV", "STAT", 1, "Repeat full 10-vial ASV dose if 20WBCT remains non-clotting at 6 hours"),
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "TDS", 2, "Analgesia for severe local swelling")
        ],
        mandatory_baseline_labs=["20-Minute Whole Blood Clotting Test (20WBCT) performed at bedside every 1 hour", "PT/INR and aPTT", "CBC and Platelet count", "Serum Creatinine and Blood Urea Nitrogen (watch for Acute Kidney Injury)", "Urine examination for hematuria / myoglobinuria"],
        therapeutic_monitoring=["Serial limb circumference markings every 1-2 hours", "Blood pressure and pulse every 15 min", "Watch for anaphylaxis to equine ASV (have Epinephrine loaded)"],
        urgent_interventions=["Strict limb immobilization with a splint at heart level", "Strictly PROHIBIT tourniquets, incisions, suctioning, or herbal pastes"],
        clinical_pearls="The 20-Minute Whole Blood Clotting Test is 100% specific: if clean dry glass tube blood does not form a solid clot in 20 min, systemic envenomation is confirmed."
    ),

    "SNAKE_ENVENOMATION_NEUROTOXIC": ClinicalSTGProtocol(
        disease_key="SNAKE_ENVENOMATION_NEUROTOXIC",
        disease_name="Neurotoxic Snake Envenomation (Common Krait / Cobra)",
        category="TOXICOLOGY",
        first_line_regimen=[
            PrescriptionItem("Snake Antivenom", "100ml", 10.0, "100ml", "IV", "STAT", 1, "10 vials polyvalent ASV in 200mL NS over 1 hour"),
            PrescriptionItem("Atropine", "0.6mg", 0.02, "0.6mg", "IV", "STAT", 1, "Prior to Neostigmine to block muscarinic bradycardia"),
            PrescriptionItem("Neostigmine", "1.5mg", 0.04, "1.5mg", "IV", "STAT", 1, "Acetylcholinesterase inhibitor (Neostigmine test for post-synaptic cobra venom)"),
            PrescriptionItem("Tetanus Toxoid", "0.5ml", 0.5, "0.5ml", "IM", "STAT", 1, "Wound prophylaxis")
        ],
        alternative_regimen=[
            PrescriptionItem("Snake Antivenom", "100ml", 10.0, "100ml", "IV", "STAT", 1, "Repeat ASV at 1-2 hours if neuro-paralysis worsens"),
            PrescriptionItem("Neostigmine", "0.5mg", 0.02, "0.5mg", "IV", "PRN", 2, "Repeat every 30 min with Atropine if objective improvement in ptosis/single breath count")
        ],
        mandatory_baseline_labs=["Single Breath Count (SBC) bedside monitoring", "Peak Expiratory Flow Rate", "ABG with PaCO2 monitoring for hypoventilation", "Serum Electrolytes"],
        therapeutic_monitoring=["Hourly cranial nerve exam: ptosis, diplopia, dysarthria, pooling of saliva", "Respiratory rate and chest expansion"],
        urgent_interventions=["Immediate bag-valve-mask ventilatory support or endotracheal intubation upon earliest signs of respiratory fatigue", "Krait bites have NO local swelling and painless fang marks; nocturnal awakening with abdominal pain is high index of suspicion", "Limb splinting without tourniquet"],
        clinical_pearls="Common Krait produces pre-synaptic neurotoxicity with irreversible vesicle depletion; Neostigmine will not work for Krait, only prolonged mechanical ventilation until new motor endplates regenerate."
    ),

    "ANAPHYLAXIS": ClinicalSTGProtocol(
        disease_key="ANAPHYLAXIS",
        disease_name="Acute Anaphylaxis / Severe Systemic Hypersensitivity",
        category="TOXICOLOGY",
        first_line_regimen=[
            PrescriptionItem("Epinephrine", "0.5mg", 0.01, "0.5mg", "IM", "STAT", 1, "1:1000 solution IM in anterolateral mid-thigh; repeat q5-15m x 3 if needed"),
            PrescriptionItem("Hydrocortisone", "200mg", 4.0, "200mg", "IV", "STAT", 1, "To prevent biphasic late-phase anaphylactic recurrence"),
            PrescriptionItem("Diphenhydramine", "50mg", 1.0, "50mg", "IV", "STAT", 1, "H1 antihistamine for cutaneous symptoms"),
            PrescriptionItem("Salbutamol", "5mg", 0.15, "5mg", "INHALATION", "STAT", 1, "Nebulization for refractory bronchospasm")
        ],
        alternative_regimen=[
            PrescriptionItem("Epinephrine", "0.5mg", 0.01, "0.5mg", "IM", "STAT", 1, "First-line lifesaving drug; NO absolute contraindications in anaphylaxis"),
            PrescriptionItem("Dexamethasone", "8mg", 0.2, "8mg", "IV", "STAT", 1, "Alternative corticosteroid"),
            PrescriptionItem("Cetirizine", "10mg", 0.25, "10mg", "ORAL", "OD", 3, "Step-down oral antihistamine")
        ],
        mandatory_baseline_labs=["Serum Tryptase (drawn within 1-2 hours of symptom onset)", "ABG in severe bronchospasm", "Serum Electrolytes and ECG in patients on beta-blockers"],
        therapeutic_monitoring=["Continuous pulse oximetry, cardiac rhythm, and automated BP every 5 min", "Observe patient in hospital for minimum 6-12 hours due to biphasic anaphylaxis risk"],
        urgent_interventions=["Remove inciting allergen immediately", "Supine position with legs elevated (unless airway compromised / vomiting)", "High-flow oxygen 100% via non-rebreather mask", "Aggressive IV fluid bolus (1-2 Liters Normal Saline) for shock"],
        clinical_pearls="Never administer IV Epinephrine as an undiluted 1:1000 push — it causes fatal ventricular arrhythmias and myocardial infarction. Epinephrine for anaphylaxis must ALWAYS be given IM in the anterolateral thigh."
    ),

    "SEVERE_HYPERKALEMIA": ClinicalSTGProtocol(
        disease_key="SEVERE_HYPERKALEMIA",
        disease_name="Severe Hyperkalemia (Serum K+ > 6.5 mEq/L or ECG changes)",
        category="ENDOCRINE_METABOLIC",
        first_line_regimen=[
            PrescriptionItem("Calcium Gluconate", "1000mg", 0.5, "1000mg", "IV", "STAT", 1, "10mL 10% IV over 2-5 min; stabilizes cardiac membrane; repeat in 5-10m if ECG persists"),
            PrescriptionItem("Insulin Regular", "10 units", 0.1, "10 units", "IV", "STAT", 1, "With 100mL 25% or 50mL 50% Dextrose over 15-30 min; shifts K+ into cells"),
            PrescriptionItem("Dextrose 50%", "50ml", 2.0, "50ml", "IV", "STAT", 1, "Administer concomitantly with insulin to prevent hypoglycemia"),
            PrescriptionItem("Salbutamol", "10mg", 0.15, "10mg", "INHALATION", "STAT", 1, "Nebulized over 10 min; beta-2 intracellular potassium shift"),
            PrescriptionItem("Furosemide", "40mg", 1.0, "80mg", "IV", "STAT", 1, "Loop diuretic kaliuresis if urine output preserved")
        ],
        alternative_regimen=[
            PrescriptionItem("Calcium Gluconate", "1000mg", 0.5, "1000mg", "IV", "STAT", 1, "Membrane stabilization"),
            PrescriptionItem("Insulin Regular", "10 units", 0.1, "10 units", "IV", "STAT", 1, "With 100mL 20% Dextrose"),
            PrescriptionItem("Sodium Bicarbonate", "50 mEq", 1.0, "50 mEq", "IV", "STAT", 1, "Alternative intracellular shift if metabolic acidosis present")
        ],
        mandatory_baseline_labs=["STAT Serum Potassium and repeat at 1, 2, and 4 hours", "12-Lead ECG (peaked T waves, PR prolongation, widened QRS, sine wave)", "Serum Creatinine and BUN", "ABG for pH and bicarbonate", "Blood glucose monitoring every 30 min x 3"],
        therapeutic_monitoring=["Continuous cardiac telemetry until QRS narrows and T waves normalize", "Hourly point-of-care glucose to detect delayed insulin-induced hypoglycemia"],
        urgent_interventions=["Urgent nephrology consult for emergency hemodialysis if refractory, anuric, or end-stage renal disease", "Stop all exogenous potassium sources, ACE inhibitors, ARBs, and Spironolactone"],
        clinical_pearls="Calcium Gluconate protects the heart within 3 minutes but does NOT lower serum potassium; Insulin + Dextrose lowers potassium by driving it intracellularly."
    ),

    "SEVERE_HYPOGLYCEMIA": ClinicalSTGProtocol(
        disease_key="SEVERE_HYPOGLYCEMIA",
        disease_name="Severe Hypoglycemia with Neuroglycopenia (Blood Glucose < 54 mg/dL)",
        category="ENDOCRINE_METABOLIC",
        first_line_regimen=[
            PrescriptionItem("Dextrose 50%", "50ml", 2.0, "50ml", "IV", "STAT", 1, "25g elemental dextrose bolus over 2-3 min via patent wide-bore vein"),
            PrescriptionItem("Dextrose 10%", "500ml", 5.0, "500ml", "IV", "CONTINUOUS_INFUSION", 1, "Maintenance infusion at 100 mL/h to maintain blood sugar > 100 mg/dL")
        ],
        alternative_regimen=[
            PrescriptionItem("Glucagon", "1mg", 0.5, "1mg", "IM", "STAT", 1, "If IV access impossible; mobilizes hepatic glycogen stores")
        ],
        mandatory_baseline_labs=["Point-of-care blood glucose before and 15 min after infusion", "Serum Creatinine and LFTs (sulfonylurea accumulation)", "Urine toxicological screen for oral hypoglycemic agents"],
        therapeutic_monitoring=["Check capillary blood glucose every 15-30 min until stable > 100 mg/dL, then hourly for 12-24 hours"],
        urgent_interventions=["If conscious and able to swallow: 15-20g rapid-acting oral carbohydrates (juice, glucose tablets)", "If sulfonylurea-induced (glibenclamide/glimepiride): admit for 48-hour continuous surveillance due to recurrent prolonged hypoglycemia", "Give Thiamine 100mg IV prior to dextrose in chronic alcoholism to prevent Wernicke encephalopathy"],
        clinical_pearls="Never administer oral liquids to an obtunded or actively seizing hypoglycemic patient due to catastrophic pulmonary aspiration risk."
    ),

    "COMMUNITY_ACQUIRED_PNEUMONIA": ClinicalSTGProtocol(
        disease_key="COMMUNITY_ACQUIRED_PNEUMONIA",
        disease_name="Severe Community-Acquired Pneumonia (CURB-65 >= 3)",
        category="PULMONARY",
        first_line_regimen=[
            PrescriptionItem("Ceftriaxone", "2g", 50.0, "2g/day", "IV", "OD", 7, "Coverage against Streptococcus pneumoniae and Haemophilus"),
            PrescriptionItem("Azithromycin", "500mg", 10.0, "500mg/day", "IV", "OD", 5, "Atypical coverage (Mycoplasma, Legionella, Chlamydia)"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "ORAL", "TDS", 5, "Antipyretic and pleuritic chest comfort")
        ],
        alternative_regimen=[
            PrescriptionItem("Levofloxacin", "750mg", 10.0, "750mg/day", "IV", "OD", 7, "Respiratory fluoroquinolone monotherapy if severe beta-lactam anaphylaxis"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "ORAL", "TDS", 5, "Antipyretic")
        ],
        mandatory_baseline_labs=["Chest X-Ray / CT Thorax", "Blood cultures x 2 and Sputum Gram stain/culture", "Serum Creatinine and Blood Urea Nitrogen (CURB-65 calculation)", "Complete Blood Count", "SpO2 / ABG"],
        therapeutic_monitoring=["Respiratory rate and work of breathing every 2 hours", "Temperature curve", "SpO2 (target 92-96%)"],
        urgent_interventions=["Supplemental humidified oxygen", "Chest physiotherapy and early mobilization", "Consider ICU transfer if septic shock or requiring mechanical ventilation"],
        clinical_pearls="Combination beta-lactam + macrolide demonstrates statistically significant mortality reduction compared to monotherapy in severe CAP requiring hospitalization."
    ),

    "DENGUE_WITH_WARNING_SIGNS": ClinicalSTGProtocol(
        disease_key="DENGUE_WITH_WARNING_SIGNS",
        disease_name="Dengue Fever with Warning Signs / Severe Dengue",
        category="INFECTIOUS",
        first_line_regimen=[
            PrescriptionItem("Paracetamol", "500mg", 10.0, "2000mg/day", "ORAL", "TDS", 5, "Antipyretic strictly capped at 2g/day; STRICTLY PROHIBIT NSAIDs/Aspirin"),
            PrescriptionItem("Normal Saline", "500ml", 5.0, None, "IV", "STAT", 1, "Isotonic crystalloid fluid titration: 5-7 mL/kg/h for 1-2h, then taper to 3-5 mL/kg/h")
        ],
        alternative_regimen=[
            PrescriptionItem("Ringer Lactate", "500ml", 5.0, None, "IV", "STAT", 1, "Balanced crystalloid alternative for plasma leakage resuscitation")
        ],
        mandatory_baseline_labs=["Serial Hematocrit and Platelet count every 6-12 hours", "Dengue NS1 Antigen (Day 1-5) and IgM/IgG ELISA (Day >= 5)", "Liver Function Tests (AST/ALT)", "Serum Creatinine", "USG Abdomen for gall bladder wall thickening, ascites, and pleural effusion"],
        therapeutic_monitoring=["Hematocrit rising > 20% indicates worsening plasma leakage into third spaces", "Urine output strictly maintained > 0.5 mL/kg/h", "BP and pulse pressure (< 20 mmHg indicates dengue shock syndrome)"],
        urgent_interventions=["Strictly avoid intramuscular injections which produce massive muscle hematomas", "Prophylactic platelet transfusions are NOT recommended even if count < 20,000 unless refractory clinical bleeding", "Step down fluids as critical phase ends (48h) to prevent pulmonary edema"],
        clinical_pearls="NSAIDs (Ibuprofen, Diclofenac, Mefenamic acid) cause fatal gastric hemorrhage and precipitate hepatic failure in dengue."
    ),

    "FALCIPARUM_MALARIA": ClinicalSTGProtocol(
        disease_key="FALCIPARUM_MALARIA",
        disease_name="Severe / Cerebral Falciparum Malaria",
        category="INFECTIOUS",
        first_line_regimen=[
            PrescriptionItem("Artesunate", "120mg", 2.4, "120mg", "IV", "STAT", 3, "2.4 mg/kg IV at 0, 12, and 24 hours, then OD for minimum 3 doses until oral intake"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "ORAL", "TDS", 3, "Antipyretic"),
            PrescriptionItem("Artemether-Lumefantrine", "80mg", 1.5, "80mg", "ORAL", "BD", 3, "Full oral 3-day ACT course upon patient regaining consciousness")
        ],
        alternative_regimen=[
            PrescriptionItem("Quinine", "600mg", 20.0, "600mg", "IV", "TDS", 7, "Quinine infusion if IV Artesunate unavailable; requires continuous ECG and glucose monitoring")
        ],
        mandatory_baseline_labs=["Peripheral Blood Smear (Giemsa thick & thin) / Rapid Diagnostic Test", "Point-of-care Blood Glucose every 4 hours (Artesunate & Quinine cause profound hypoglycemia)", "CBC with Platelets and Bilirubin", "Serum Creatinine and ABG with Lactate"],
        therapeutic_monitoring=["GCS and neurological status every 1 hour", "Blood glucose monitoring every 2-4 hours", "Serial parasite clearance smears"],
        urgent_interventions=["Maintain strict fluid balance to prevent both acute renal failure and non-cardiogenic pulmonary edema", "Seizure precautions", "Parenteral Artesunate saves 35% more lives than IV Quinine"],
        clinical_pearls="Never fluid overload a cerebral malaria patient — pulmonary edema in severe malaria is non-cardiogenic and carries > 80% mortality."
    ),

    "STATUS_EPILEPTICUS": ClinicalSTGProtocol(
        disease_key="STATUS_EPILEPTICUS",
        disease_name="Convulsive Status Epilepticus (Seizure Duration > 5 min)",
        category="NEUROLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Lorazepam", "4mg", 0.1, "4mg", "IV", "STAT", 1, "Slow IV push over 2 min; repeat once at 5-10 min if seizure persists"),
            PrescriptionItem("Levetiracetam", "3000mg", 60.0, "4500mg", "IV", "STAT", 1, "Second-line anti-seizure infusion over 10 min (60 mg/kg up to 4500mg)"),
            PrescriptionItem("Phenytoin", "1000mg", 20.0, "1500mg", "IV", "STAT", 1, "Alternative 20 mg/kg in NS at max 50 mg/min under continuous cardiac monitoring")
        ],
        alternative_regimen=[
            PrescriptionItem("Midazolam", "10mg", 0.2, "10mg", "IM", "STAT", 1, "If IV access not immediately secured; 10mg IM (>40kg) or 5mg (13-40kg)"),
            PrescriptionItem("Valproate", "2000mg", 40.0, "3000mg", "IV", "STAT", 1, "Second-line loading 40 mg/kg over 10 min")
        ],
        mandatory_baseline_labs=["STAT Capillary Blood Glucose (rule out hypoglycemia instantly)", "Serum Electrolytes (Na, Ca, Mg)", "Toxicology screen and anti-seizure medication blood levels", "Non-contrast Head CT after seizure cessation"],
        therapeutic_monitoring=["Continuous pulse oximetry, ECG, and respiratory monitoring", "Watch for respiratory depression following benzodiazepine administration"],
        urgent_interventions=["Airway protection, high-flow oxygen, recovery position", "Do NOT insert tongue depressors or metal objects between clenched teeth", "Prepare for intubation and general anesthesia (Propofol/Midazolam) if seizure exceeds 30 min (refractory status)"],
        clinical_pearls="Time is brain: prolonged status epilepticus (>30 min) causes excitotoxic neuronal death, hyperthermia, rhabdomyolysis, and permanent cognitive impairment."
    ),

    "ACUTE_ISCHEMIC_STROKE": ClinicalSTGProtocol(
        disease_key="ACUTE_ISCHEMIC_STROKE",
        disease_name="Acute Ischemic Stroke (Thrombolytic Window < 4.5 Hours)",
        category="NEUROLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Alteplase", "70mg", None, None, "IV", "STAT", 1, "0.9 mg/kg (max 90mg): 10% as IV bolus over 1 min, remaining 90% over 60 min"),
            PrescriptionItem("Aspirin", "150mg", None, None, "ORAL", "OD", 30, "Initiate ONLY AFTER 24 hours post-thrombolysis following repeat clear CT scan")
        ],
        alternative_regimen=[
            PrescriptionItem("Aspirin", "300mg", None, None, "ORAL", "STAT", 1, "If outside thrombolysis window (>4.5h) or contraindication to thrombolysis"),
            PrescriptionItem("Clopidogrel", "75mg", None, None, "ORAL", "OD", 21, "Dual antiplatelet therapy for high-risk TIA / minor stroke (NIHSS <= 3)")
        ],
        mandatory_baseline_labs=["STAT Non-contrast Head CT to exclude intracerebral hemorrhage", "Point-of-care Blood Glucose", "PT/INR, aPTT, and Platelet count", "12-Lead ECG"],
        therapeutic_monitoring=["Neurological checks and NIHSS every 15 min during infusion, then q30m for 6h, then hourly for 24h", "Blood pressure strictly maintained < 180/105 mmHg during and after thrombolysis"],
        urgent_interventions=["Emergency Stroke Code activation; Door-to-Needle target < 60 min", "Immediate CT Angiography to assess for Large Vessel Occlusion (LVO) eligible for mechanical thrombectomy (up to 24h)"],
        clinical_pearls="Never lower blood pressure precipitously unless > 185/110 mmHg if thrombolysis planned, or > 220/120 mmHg if non-thrombolytic, to preserve ischemic penumbra collateral perfusion."
    ),

    "AORTIC_DISSECTION": ClinicalSTGProtocol(
        disease_key="AORTIC_DISSECTION",
        disease_name="Acute Aortic Dissection (Stanford Type A / Type B)",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Labetalol", "20mg", None, None, "IV", "STAT", 1, "Bolus 20mg over 2 min, then 2-8 mg/min infusion; target HR 55-60 bpm, then SBP 100-120"),
            PrescriptionItem("Nitroprusside", "50mg", None, None, "IV", "CONTINUOUS_INFUSION", 1, "Vasodilator added ONLY AFTER adequate beta-blockade to prevent reflex tachycardia"),
            PrescriptionItem("Morphine", "5mg", None, None, "IV", "STAT", 1, "Adequate analgesia reduces sympathetic drive and dP/dt shear stress")
        ],
        alternative_regimen=[
            PrescriptionItem("Esmolol", "500mcg/kg", None, None, "IV", "STAT", 1, "Ultra-short-acting beta-blocker titrated to HR < 60 bpm"),
            PrescriptionItem("Nicardipine", "5mg", None, None, "IV", "CONTINUOUS_INFUSION", 1, "Alternative calcium channel blocker vasodilator")
        ],
        mandatory_baseline_labs=["CT Angiography Chest, Abdomen & Pelvis (Triple rule-out)", "Transesophageal Echocardiogram (TEE)", "CBC, Crossmatch 6 units PRBC", "Serum Creatinine and Troponin"],
        therapeutic_monitoring=["Continuous arterial line blood pressure and ECG telemetry", "Bilateral arm blood pressure surveillance for pulse deficit"],
        urgent_interventions=["Immediate Cardiothoracic Surgery consultation for emergent open repair if Type A (involves ascending aorta)", "Type B (descending) treated medically in ICU unless malperfusion or rupture", "Target heart rate < 60 bpm and systolic BP 100-120 mmHg within 20 minutes"],
        clinical_pearls="Giving vasodilators like hydralazine or nitroprusside without prior beta-blockade increases ventricular ejection velocity (dP/dt) and propagates the dissection tear to fatal rupture."
    ),

    "TENSION_PNEUMOTHORAX": ClinicalSTGProtocol(
        disease_key="TENSION_PNEUMOTHORAX",
        disease_name="Tension Pneumothorax",
        category="PULMONARY",
        first_line_regimen=[
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 3, "Post-interventional pain control"),
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "TDS", 2, "Supplemental chest tube analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Morphine", "5mg", 0.05, "5mg", "IV", "PRN", 2, "Severe chest wall trauma analgesia")
        ],
        mandatory_baseline_labs=["Immediate clinical diagnosis — DO NOT WAIT FOR CHEST X-RAY", "Post-decompression Chest X-Ray to confirm tube placement and lung re-expansion", "ABG"],
        therapeutic_monitoring=["Continuous SpO2, respiratory rate, blood pressure, and heart rate", "Monitor chest drain under-water seal for air bubbling and swinging column"],
        urgent_interventions=["IMMEDIATE NEEDLE DECOMPRESSION: 14-gauge catheter in 2nd intercostal space mid-clavicular line or 4th/5th ICS anterior axillary line", "Followed immediately by formal Chest Tube insertion (28-32 Fr tube in 5th intercostal space anterior to mid-axillary line)", "100% High-flow oxygen via non-rebreather mask"],
        clinical_pearls="Tension pneumothorax is a purely clinical diagnosis: tracheal deviation, absent breath sounds, hypotension, and distended neck veins require instantaneous needle decompression; ordering a chest X-ray first is fatal malpractice."
    ),

    "PULMONARY_EMBOLISM": ClinicalSTGProtocol(
        disease_key="PULMONARY_EMBOLISM",
        disease_name="Acute Massive / Submassive Pulmonary Embolism",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Alteplase", "100mg", None, None, "IV", "CONTINUOUS_INFUSION", 1, "Thrombolysis for massive PE with hemodynamic collapse: 100mg over 2 hours"),
            PrescriptionItem("Heparin", "5000 units", None, None, "IV", "STAT", 1, "80 units/kg bolus followed by 18 units/kg/h infusion (target aPTT 1.5-2.5x control)"),
            PrescriptionItem("Enoxaparin", "60mg", 1.0, "100mg", "SC", "BD", 5, "1 mg/kg SC q12h for stable submassive / non-massive PE")
        ],
        alternative_regimen=[
            PrescriptionItem("Enoxaparin", "60mg", 1.0, "100mg", "SC", "BD", 5, "Low molecular weight heparin if normotensive / non-massive PE"),
            PrescriptionItem("Warfarin", "5mg", None, None, "ORAL", "OD", 90, "Overlap with heparin until INR 2.0-3.0 for 2 consecutive days")
        ],
        mandatory_baseline_labs=["CT Pulmonary Angiography (CTPA)", "Bedside Echocardiography (McConnell's sign, RV dilatation, pulmonary hypertension)", "Serum Troponin and NT-proBNP (RV strain markers)", "ABG (hypoxemia, hypocapnia)", "Coagulation profile (PT/INR, aPTT)"],
        therapeutic_monitoring=["Continuous blood pressure, telemetry, and pulse oximetry", "Serial aPTT every 6 hours if unfractionated heparin used"],
        urgent_interventions=["Immediate therapeutic anticoagulation upon high clinical suspicion before imaging if no contraindications", "Catheter-directed embolectomy or surgical embolectomy if thrombolysis contraindicated", "Supplemental oxygen (SpO2 > 90%)"],
        clinical_pearls="In hemodynamically unstable PE (systolic BP < 90 mmHg), systemic thrombolysis with Alteplase 100mg IV over 2h is the treatment of choice unless absolute hemorrhage contraindications exist."
    ),

    "DIABETIC_KETOACIDOSIS": ClinicalSTGProtocol(
        disease_key="DIABETIC_KETOACIDOSIS",
        disease_name="Diabetic Ketoacidosis (DKA)",
        category="ENDOCRINE_METABOLIC",
        first_line_regimen=[
            PrescriptionItem("Normal Saline", "1000ml", 10.0, "1000ml", "IV", "STAT", 1, "1000 mL 0.9% NaCl in first hour, then 250-500 mL/h adjusted for hydration"),
            PrescriptionItem("Insulin Regular", "10 units", 0.1, "10 units", "IV", "CONTINUOUS_INFUSION", 2, "0.1 units/kg/h infusion; target glucose reduction 50-75 mg/dL/h"),
            PrescriptionItem("Potassium Chloride", "20 mEq", 0.5, "20 mEq", "IV", "CONTINUOUS_INFUSION", 2, "Add 20-30 mEq/L fluid once serum K+ < 5.2 mEq/L; HOLD if K+ < 3.3 until replaced")
        ],
        alternative_regimen=[
            PrescriptionItem("Dextrose 10%", "500ml", 5.0, "500ml", "IV", "CONTINUOUS_INFUSION", 1, "Add 5-10% dextrose to fluids once blood glucose falls < 200 mg/dL while continuing insulin to clear ketones")
        ],
        mandatory_baseline_labs=["STAT Blood Glucose and repeat hourly", "Serum Electrolytes (calculate Anion Gap = Na - (Cl + HCO3)) every 2 hours", "Venous Blood Gas (pH and bicarbonate)", "Urine and serum ketones (Beta-hydroxybutyrate)", "Serum Creatinine and BUN"],
        therapeutic_monitoring=["Hourly capillary blood glucose", "Electrolytes and anion gap every 2-4 hours until closure (anion gap <= 12 and HCO3 >= 18)", "Strict intake and output chart"],
        urgent_interventions=["NEVER start insulin if baseline potassium is < 3.3 mEq/L — insulin drives K+ intracellularly causing fatal cardiac arrest", "Continue IV insulin until acidosis and anion gap resolve, not merely until blood sugar normalizes", "Switch to SC insulin 1-2 hours before stopping IV insulin infusion"],
        clinical_pearls="Prematurely stopping insulin when glucose drops to 200 mg/dL will cause rebound ketoacidosis; add dextrose to IV fluids and keep insulin running to suppress lipolysis and ketogenesis."
    ),

    "POSTPARTUM_HEMORRHAGE": ClinicalSTGProtocol(
        disease_key="POSTPARTUM_HEMORRHAGE",
        disease_name="Severe Postpartum Hemorrhage (PPH > 500mL vaginal / > 1000mL cesarean)",
        category="OBSTETRIC_GYNECOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Oxytocin", "20 units", None, None, "IV", "CONTINUOUS_INFUSION", 1, "20 units in 500mL Normal Saline at 125-250 mL/h (or 10 units IM stat)"),
            PrescriptionItem("Tranexamic Acid", "1000mg", None, None, "IV", "STAT", 1, "1g IV over 10 min within 3 hours of birth; repeat once if bleeding persists at 30 min"),
            PrescriptionItem("Misoprostol", "800mcg", None, None, "RECTAL", "STAT", 1, "800 mcg sublingually or per rectum for uterine atony")
        ],
        alternative_regimen=[
            PrescriptionItem("Methylergometrine", "0.2mg", None, None, "IM", "STAT", 1, "0.2mg IM; STRICTLY CONTRAINDICATED in hypertension or pre-eclampsia"),
            PrescriptionItem("Carboprost", "250mcg", None, None, "IM", "STAT", 1, "PGF2-alpha 250mcg deep IM; contraindicated in active asthma")
        ],
        mandatory_baseline_labs=["Crossmatch 4-6 units Packed RBCs and 4 units FFP", "CBC and Platelet count", "Coagulation profile (PT, aPTT, Fibrinogen < 200 mg/dL indicates consumptive coagulopathy)"],
        therapeutic_monitoring=["Continuous blood pressure, pulse, SpO2, and urine output", "Quantify cumulative blood loss using gravimetric drapes"],
        urgent_interventions=["Bimanual uterine compression and vigorous fundal massage", "Bakri intrauterine balloon tamponade", "Activate Massive Transfusion Protocol (1:1:1 PRBC:FFP:Platelets)", "Emergency surgical intervention (B-Lynch suture, uterine artery ligation, peripartum hysterectomy) if medical therapy fails"],
        clinical_pearls="WOMAN Trial: Tranexamic acid 1g IV administered within 3 hours of bleeding onset reduces death due to bleeding by nearly one-third."
    ),

    "ACUTE_PANCREATITIS": ClinicalSTGProtocol(
        disease_key="ACUTE_PANCREATITIS",
        disease_name="Acute Pancreatitis (Atlanta Classification)",
        category="GASTROINTESTINAL",
        first_line_regimen=[
            PrescriptionItem("Ringer Lactate", "1000ml", 10.0, "1000ml", "IV", "STAT", 1, "Goal-directed fluid resuscitation: 200-250 mL/h titrated to hematocrit and BUN"),
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "TDS", 3, "Analgesia; or Fentanyl for severe pain"),
            PrescriptionItem("Pantoprazole", "40mg", 1.0, "40mg", "IV", "OD", 5, "Proton pump inhibitor stress ulcer prophylaxis")
        ],
        alternative_regimen=[
            PrescriptionItem("Morphine", "5mg", 0.05, "5mg", "IV", "PRN", 2, "Adequate analgesia (Sphincter of Oddi spasm theory is clinically unproven)"),
            PrescriptionItem("Meropenem", "1g", 20.0, "3g/day", "IV", "TDS", 7, "ONLY in documented infected necrotizing pancreatitis; prophylactic antibiotics PROHIBITED")
        ],
        mandatory_baseline_labs=["Serum Lipase and Amylase (> 3x upper limit of normal)", "Hematocrit, BUN, and Serum Creatinine (assess hemoconcentration)", "Serum Calcium and Triglycerides (etiology & prognostic)", "LFTs (ALT > 150 U/L suggests gallstone pancreatitis)", "USG Abdomen (cholelithiasis/biliary dilatation)"],
        therapeutic_monitoring=["Serial BUN and Creatinine every 12-24 hours (rising BUN reflects inadequate resuscitation)", "Vitals, urine output, and BISAP / Ranson prognostic scoring"],
        urgent_interventions=["Early oral feeding with low-fat solid diet as soon as abdominal pain improves and ileus resolves", "Prophylactic antibiotics are strictly NOT recommended in mild or sterile necrosis", "Urgent ERCP within 24 hours if gallstone pancreatitis with acute cholangitis"],
        clinical_pearls="Ringer's Lactate is superior to Normal Saline: it reduces systemic inflammatory response syndrome (SIRS) and prevents hyperchloremic metabolic acidosis."
    ),

    "FEBRILE_NEUTROPENIA": ClinicalSTGProtocol(
        disease_key="FEBRILE_NEUTROPENIA",
        disease_name="Febrile Neutropenia (Absolute Neutrophil Count < 500/uL + Single Temp >= 38.3C)",
        category="HEMATOLOGY_ONCOLOGY",
        first_line_regimen=[
            PrescriptionItem("Piperacillin-Tazobactam", "4.5g", 100.0, "18g/day", "IV", "TDS", 7, "First-line anti-pseudomonal monotherapy; infuse within 60 min"),
            PrescriptionItem("Vancomycin", "1000mg", 15.0, "2000mg/day", "IV", "BD", 7, "Add if catheter infection, hypotension, mucositis, or MRSA colonization"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "ORAL", "TDS", 3, "Antipyretic comfort")
        ],
        alternative_regimen=[
            PrescriptionItem("Meropenem", "1g", 20.0, "3g/day", "IV", "TDS", 7, "If severe penicillin anaphylaxis or ESBL colonization"),
            PrescriptionItem("Cefepime", "2g", 50.0, "6g/day", "IV", "TDS", 7, "Alternative 4th gen cephalosporin anti-pseudomonal")
        ],
        mandatory_baseline_labs=["Blood cultures x 2 (one peripheral, one from each central lumen) prior to antibiotic infusion", "Complete Blood Count with absolute neutrophil count (ANC)", "Serum Creatinine and LFTs", "Chest X-Ray / High-resolution chest CT"],
        therapeutic_monitoring=["Monitor temperature curve and hemodynamic stability", "If fever persists after 4-7 days of broad-spectrum antibiotics, initiate empirical anti-fungal (Voriconazole/Amphotericin B)"],
        urgent_interventions=["Medical Emergency: administer first dose of anti-pseudomonal antibiotic within 60 minutes of triage", "Strict protective reverse isolation, hand hygiene, no fresh flowers or unpasteurized foods", "Do NOT perform digital rectal exam due to bacteremia risk"],
        clinical_pearls="Never wait for culture results before starting broad-spectrum antibiotics in febrile neutropenia; rapid progression to fatal septic shock occurs within hours."
    ),

    "TESTICULAR_TORSION": ClinicalSTGProtocol(
        disease_key="TESTICULAR_TORSION",
        disease_name="Acute Testicular Torsion",
        category="RENAL_UROLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "STAT", 1, "Acute pain relief prior to surgical exploration"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 3, "Post-operative analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Morphine", "5mg", 0.05, "5mg", "IV", "STAT", 1, "Severe acute scrotal pain analgesia")
        ],
        mandatory_baseline_labs=["Urgent Color Doppler Scrotal Ultrasound (absent blood flow)", "Urinalysis and urine culture (rule out epididymo-orchitis)", "Coagulation profile and crossmatch for urgent surgery"],
        therapeutic_monitoring=["Pain scores and scrotal edema"],
        urgent_interventions=["EMERGENCY UROLOGICAL CONSULT FOR IMMEDIATE SCROTAL EXPLORATION", "Golden window is < 6 hours for > 90% testicular salvage rate; drops to < 10% at 24 hours", "Manual detorsion ('open book' lateral rotation) attempted gently if surgical delay inevitable", "Bilateral orchidopexy mandatory during surgery to prevent contralateral torsion"],
        clinical_pearls="If clinical suspicion is high and Doppler US will cause delay, bypass imaging and proceed straight to the operating room; a negative exploration is far safer than a necrotic testicle."
    ),

    "ACUTE_CHOLECYSTITIS": ClinicalSTGProtocol(
        disease_key="ACUTE_CHOLECYSTITIS",
        disease_name="Acute Calculous Cholecystitis",
        category="GASTROINTESTINAL",
        first_line_regimen=[
            PrescriptionItem("Ceftriaxone", "1g", 50.0, "2g/day", "IV", "BD", 5, "Biliary antibiotic coverage"),
            PrescriptionItem("Metronidazole", "500mg", 7.5, "1500mg/day", "IV", "TDS", 5, "Anaerobic coverage"),
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "TDS", 3, "Analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Ciprofloxacin", "400mg", 10.0, "800mg/day", "IV", "BD", 5, "Fluoroquinolone in penicillin anaphylaxis"),
            PrescriptionItem("Metronidazole", "500mg", 7.5, "1500mg/day", "IV", "TDS", 5, "Anaerobic coverage")
        ],
        mandatory_baseline_labs=["USG Upper Abdomen (gallstones, acoustic shadowing, wall thickening > 4mm, pericholecystic fluid, sonographic Murphy's sign)", "CBC with differential", "LFTs (elevated bilirubin/ALP suggests choledocholithiasis)", "Lipase (rule out gallstone pancreatitis)"],
        therapeutic_monitoring=["Vitals, temperature, and RUQ peritoneal signs"],
        urgent_interventions=["Keep NPO with IV hydration", "Emergency surgical consult for early laparoscopic cholecystectomy (within 72 hours of symptom onset)"],
        clinical_pearls="Charcot's triad (RUQ pain, fever, jaundice) signals acute cholangitis, a life-threatening emergency requiring urgent ERCP decompression."
    ),

    "ACUTE_DECOMPENSATED_HEART_FAILURE": ClinicalSTGProtocol(
        disease_key="ACUTE_DECOMPENSATED_HEART_FAILURE",
        disease_name="Acute Decompensated Heart Failure (Flash Pulmonary Edema)",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Furosemide", "40mg", 1.0, "160mg", "IV", "STAT", 1, "40-80mg IV bolus (or 2.5x home oral dose); venodilates within 5 min, diuresis within 30 min"),
            PrescriptionItem("Nitroglycerin", "0.5mg", None, None, "SUBLINGUAL", "STAT", 1, "Followed by 10-200 mcg/min IV infusion if SBP > 110 mmHg to reduce preload and afterload")
        ],
        alternative_regimen=[
            PrescriptionItem("Furosemide", "80mg", 1.0, "160mg", "IV", "STAT", 1, "High dose loop diuretic"),
            PrescriptionItem("Spironolactone", "25mg", None, None, "ORAL", "OD", 30, "Mineralocorticoid receptor antagonist upon stabilization")
        ],
        mandatory_baseline_labs=["NT-proBNP / BNP", "12-Lead ECG (ischemia, atrial fibrillation)", "Chest X-Ray (cardiomegaly, Kerley B lines, alveolar edema)", "Serum Creatinine and Electrolytes (K+ and Na+)", "Echocardiogram (EF, diastolic function, valvular lesions)"],
        therapeutic_monitoring=["Hourly urine output and daily weights", "Continuous SpO2 and BP every 15 min during IV nitrate titration", "Electrolytes (watch for hypokalemia and worsening renal function)"],
        urgent_interventions=["Upright seated posture with legs dangling off the bed", "Non-invasive positive pressure ventilation (CPAP 5-10 cmH2O or BiPAP) to reduce work of breathing and preload", "Supplemental oxygen strictly to target SpO2 92-96%"],
        clinical_pearls="Routine Morphine in acute pulmonary edema is no longer recommended by ESC/ACC guidelines; it is associated with increased intubation rates, ICU admissions, and mortality."
    ),

    "ACUTE_INTESTINAL_OBSTRUCTION": ClinicalSTGProtocol(
        disease_key="ACUTE_INTESTINAL_OBSTRUCTION",
        disease_name="Acute Mechanical Bowel Obstruction",
        category="GASTROINTESTINAL",
        first_line_regimen=[
            PrescriptionItem("Ringer Lactate", "1000ml", 10.0, "1000ml", "IV", "STAT", 1, "Aggressive volume resuscitation to replace third-space fluid sequestered in bowel lumen"),
            PrescriptionItem("Ceftriaxone", "1g", 50.0, "2g/day", "IV", "BD", 3, "Prophylaxis against bacterial translocation and peritonitis"),
            PrescriptionItem("Metronidazole", "500mg", 7.5, "1500mg/day", "IV", "TDS", 3, "Anaerobic bacteroides coverage")
        ],
        alternative_regimen=[
            PrescriptionItem("Ciprofloxacin", "400mg", 10.0, "800mg/day", "IV", "BD", 3, "If severe beta-lactam anaphylaxis"),
            PrescriptionItem("Metronidazole", "500mg", 7.5, "1500mg/day", "IV", "TDS", 3, "Anaerobic coverage")
        ],
        mandatory_baseline_labs=["Abdominal X-Ray erect and supine (multiple air-fluid levels, step-ladder pattern, dilated loops > 3cm, absence of colonic gas)", "CT Abdomen with IV contrast (transition point, strangulation, closed loop)", "Serum Electrolytes, Creatinine, and Lactate (elevated lactate indicates bowel ischemia)"],
        therapeutic_monitoring=["Abdominal girth measurements every 4 hours", "Serial physical exams for localized peritoneal signs or involuntary guarding", "Nasogastric tube aspirate volume and character (bilious vs feculent)"],
        urgent_interventions=["Decompression via wide-bore (16-18 Fr) Nasogastric Tube connected to low intermittent suction", "Strictly NPO", "Immediate General Surgical consult for laparotomy if closed loop obstruction, volvulus, hernia strangulation, or signs of bowel necrosis"],
        clinical_pearls="Never administer prokinetic agents (Metoclopramide, Domperidone) in mechanical obstruction — forcing peristalsis against a physical obstruction causes bowel perforation."
    ),

    "ACUTE_MESENTERIC_ISCHEMIA": ClinicalSTGProtocol(
        disease_key="ACUTE_MESENTERIC_ISCHEMIA",
        disease_name="Acute Mesenteric Ischemia",
        category="GASTROINTESTINAL",
        first_line_regimen=[
            PrescriptionItem("Heparin", "5000 units", None, None, "IV", "STAT", 1, "Immediate therapeutic heparinization to prevent thrombus propagation"),
            PrescriptionItem("Piperacillin-Tazobactam", "4.5g", 100.0, "18g/day", "IV", "TDS", 5, "Broad coverage for transmural gut translocation"),
            PrescriptionItem("Morphine", "5mg", 0.05, "5mg", "IV", "PRN", 2, "Adequate analgesia for excruciating visceral ischemic pain")
        ],
        alternative_regimen=[
            PrescriptionItem("Meropenem", "1g", 20.0, "3g/day", "IV", "TDS", 5, "Carbapenem broad coverage alternative"),
            PrescriptionItem("Heparin", "5000 units", None, None, "IV", "STAT", 1, "Anticoagulation")
        ],
        mandatory_baseline_labs=["CT Angiography of Abdomen (Biphasic mesenteric CTA: filling defect in SMA, bowel wall thickening, pneumatosis intestinalis)", "Serum Lactate (metabolic acidosis)", "ABG, CBC, and Coagulation profile"],
        therapeutic_monitoring=["Hourly vitals, urine output, and serial lactate clearance", "Peritoneal signs indicating bowel infarction"],
        urgent_interventions=["Immediate Vascular / General Surgery consult for emergent revascularization (surgical embolectomy, stenting) and resection of non-viable bowel", "Fluid resuscitation with crystalloids", "NPO with nasogastric decompression"],
        clinical_pearls="The hallmark of early mesenteric ischemia is 'pain out of proportion to physical exam findings' — an agonized patient with an unremarkable soft abdomen until gangrene ensues."
    ),

    "ACUTE_PERICARDITIS": ClinicalSTGProtocol(
        disease_key="ACUTE_PERICARDITIS",
        disease_name="Acute Pericarditis",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Aspirin", "650mg", None, None, "ORAL", "TDS", 14, "High-dose anti-inflammatory therapy (or Ibuprofen 600mg TDS)"),
            PrescriptionItem("Colchicine", "0.5mg", None, None, "ORAL", "OD", 90, "0.5mg BD (or OD if < 70kg) for 3 months to prevent recurrent pericarditis"),
            PrescriptionItem("Pantoprazole", "40mg", None, None, "ORAL", "OD", 14, "Gastroprotection during high-dose NSAID/aspirin therapy")
        ],
        alternative_regimen=[
            PrescriptionItem("Prednisolone", "25mg", 0.5, "50mg", "ORAL", "OD", 14, "Second-line for refractory cases or contraindications to NSAIDs; taper slowly to prevent rebound"),
            PrescriptionItem("Colchicine", "0.5mg", None, None, "ORAL", "OD", 90, "Recurrence prevention")
        ],
        mandatory_baseline_labs=["12-Lead ECG (widespread concave upward ST elevation with PR depression in limb leads, PR elevation in aVR)", "Transthoracic Echocardiogram (rule out pericardial effusion and tamponade)", "Cardiac Troponin (rule out myopericarditis)", "ESR and CRP (objective markers of inflammation)"],
        therapeutic_monitoring=["Serial ECGs and echocardiographic monitoring for developing effusion", "Pain resolution and inflammatory marker normalization"],
        urgent_interventions=["Physical activity restriction until symptoms resolve and CRP normalizes", "Rule out cardiac tamponade (Beck's triad, pulsus paradoxus)"],
        clinical_pearls="Steroids should be strictly avoided as first-line therapy because they dramatically increase the rate of recurrent, steroid-dependent pericarditis."
    ),

    "ACUTE_UPPER_GI_BLEED": ClinicalSTGProtocol(
        disease_key="ACUTE_UPPER_GI_BLEED",
        disease_name="Acute Upper Gastrointestinal Bleeding (Peptic Ulcer / Variceal)",
        category="GASTROINTESTINAL",
        first_line_regimen=[
            PrescriptionItem("Pantoprazole", "80mg", 1.0, "80mg", "IV", "STAT", 1, "80mg IV bolus followed by 8mg/h continuous infusion for 72 hours"),
            PrescriptionItem("Octreotide", "50mcg", None, None, "IV", "STAT", 1, "50mcg IV bolus followed by 50mcg/h infusion (splanchnic vasoconstrictor for suspected varices)"),
            PrescriptionItem("Ceftriaxone", "1g", 50.0, "2g/day", "IV", "OD", 7, "Mandatory antibiotic prophylaxis in cirrhotic patients to prevent SBP and rebleeding"),
            PrescriptionItem("Tranexamic Acid", "1000mg", None, None, "IV", "STAT", 1, "Systemic antifibrinolytic stabilization")
        ],
        alternative_regimen=[
            PrescriptionItem("Pantoprazole", "80mg", 1.0, "80mg", "IV", "STAT", 1, "Standard PPI bolus and infusion"),
            PrescriptionItem("Ciprofloxacin", "400mg", 10.0, "800mg/day", "IV", "BD", 7, "Alternative cirrhotic antibiotic prophylaxis if cephalosporin allergy")
        ],
        mandatory_baseline_labs=["STAT Crossmatch and Type for 4-6 units PRBC", "CBC with Platelets (hemoglobin drop may be delayed due to hemoconcentration)", "Coagulation profile (PT/INR, aPTT)", "LFTs and Serum Creatinine (hepatorenal syndrome risk)", "Blood Urea Nitrogen (elevated BUN with normal Cr reflects upper GI blood digestion)"],
        therapeutic_monitoring=["Continuous heart rate and blood pressure monitoring", "Serial hemoglobin every 4-6 hours", "Nasogastric lavage / emesis character surveillance"],
        urgent_interventions=["Two large-bore (16-gauge) IV cannulas and immediate crystalloid resuscitation", "Restrictive transfusion strategy: target Hb 7-8 g/dL (overtransfusion increases portal pressures and induces fatal variceal rebleeding)", "Urgent Endoscopy (EGD) within 12-24 hours for endoscopic band ligation or clipping"],
        clinical_pearls="HALT-IT Trial: High-dose tranexamic acid does not reduce deaths from GI bleed and increases venous thromboembolism; focus on PPI, splanchnic vasoconstrictors, and urgent endoscopy."
    ),

    "ACUTE_URINARY_RETENTION": ClinicalSTGProtocol(
        disease_key="ACUTE_URINARY_RETENTION",
        disease_name="Acute Urinary Retention",
        category="RENAL_UROLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Tamsulosin", "0.4mg", None, None, "ORAL", "OD", 30, "Alpha-1 blocker to relax bladder neck and prostatic smooth muscle before trial without catheter"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "ORAL", "TDS", 3, "Comfort analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Alfuzosin", "10mg", None, None, "ORAL", "OD", 30, "Alternative uroselective alpha-1 blocker")
        ],
        mandatory_baseline_labs=["Serum Creatinine and BUN (rule out obstructive uropathy / post-renal acute kidney injury)", "Serum Electrolytes (potassium)", "Urinalysis and urine culture (exclude urinary tract infection)", "Bedside Bladder Scan / USG Pelvis (> 300-500 mL retained volume)"],
        therapeutic_monitoring=["Decompression volume recorded immediately upon catheterization", "Monitor for post-obstructive diuresis (> 200 mL/h for > 2h requiring fluid replacement)", "Watch for decompression hematuria or hypotension"],
        urgent_interventions=["IMMEDIATE URETHRAL CATHETERIZATION with a 14-16 Fr Foley catheter under strict aseptic technique", "If urethral catheterization fails due to urethral stricture or severe BPH: consult urology for emergent Suprapubic Cystostomy", "Trial without catheter (TWOC) after 3-7 days of alpha-blocker therapy"],
        clinical_pearls="Never clamp the catheter after draining 1000 mL under the outdated myth of avoiding bladder hemorrhage — clinical trials prove complete rapid decompression is safe and relieves agonizing pain immediately."
    ),

    "ATRIAL_FIBRILLATION_RVR": ClinicalSTGProtocol(
        disease_key="ATRIAL_FIBRILLATION_RVR",
        disease_name="Atrial Fibrillation with Rapid Ventricular Response (AF with RVR)",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Metoprolol", "5mg", None, None, "IV", "STAT", 1, "5mg slow IV over 2 min; repeat every 5 min up to 15mg to achieve rate control (HR < 110)"),
            PrescriptionItem("Diltiazem", "20mg", None, None, "IV", "STAT", 1, "0.25 mg/kg IV over 2 min (or 15-20mg) if beta-blocker contraindicated (reactive airway disease)"),
            PrescriptionItem("Enoxaparin", "60mg", 1.0, "100mg", "SC", "BD", 5, "Therapeutic anticoagulation based on CHA2DS2-VASc score (stroke prevention)")
        ],
        alternative_regimen=[
            PrescriptionItem("Amiodarone", "150mg", None, None, "IV", "STAT", 1, "150mg IV over 10 min for rate control in heart failure with reduced ejection fraction (HFrEF)"),
            PrescriptionItem("Digoxin", "0.5mg", None, None, "IV", "STAT", 1, "Alternative rate control in sedentary patients with severe heart failure")
        ],
        mandatory_baseline_labs=["12-Lead ECG (irregularly irregular rhythm, absent P waves, fibrillatory waves)", "Serum Electrolytes (K+ and Mg2+ depletion triggers refractory tachyarrhythmias)", "Thyroid Stimulating Hormone (TSH to exclude thyrotoxicosis)", "Transthoracic Echocardiogram (atrial size, EF, valvular disease)"],
        therapeutic_monitoring=["Continuous ECG telemetry and automated BP every 5-15 min during IV rate-control administration", "Target heart rate < 110 bpm at rest (lenient rate control)"],
        urgent_interventions=["If HEMODYNAMICALLY UNSTABLE (hypotension, pulmonary edema, angina, altered mental status): IMMEDIATE SYNCHRONIZED DIRECT CURRENT CARDIOVERSION (120-200 J biphasic)", "If stable and AF duration > 48 hours: DO NOT CARDIOVERT pharmacologically or electrically without prior 3 weeks therapeutic anticoagulation or transesophageal echo to exclude left atrial appendage thrombus"],
        clinical_pearls="Never administer Diltiazem, Verapamil, or Digoxin in Atrial Fibrillation with Wolff-Parkinson-White (pre-excited AF with wide bizarre QRS) — blocking the AV node shunts conduction down the accessory pathway, precipitating ventricular fibrillation and cardiac arrest. Use IV Procainamide or synchronized cardioversion."
    ),

    "CARDIAC_TAMPONADE": ClinicalSTGProtocol(
        disease_key="CARDIAC_TAMPONADE",
        disease_name="Acute Cardiac Tamponade",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Normal Saline", "1000ml", 10.0, "1000ml", "IV", "STAT", 1, "Aggressive volume expansion (500-1000 mL bolus) to increase right ventricular filling pressures while preparing drainage"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 3, "Post-procedural comfort")
        ],
        alternative_regimen=[
            PrescriptionItem("Ringer Lactate", "1000ml", 10.0, "1000ml", "IV", "STAT", 1, "Volume expansion")
        ],
        mandatory_baseline_labs=["EMERGENCY BEDSIDE ECHOCARDIOGRAPHY (POCUS): pericardial effusion, right ventricular diastolic collapse, right atrial systolic collapse, plethoric non-collapsing IVC", "12-Lead ECG (electrical alternans, low voltage QRS)", "Chest X-Ray ('water-bottle' cardiac silhouette)", "Crossmatch 2-4 units PRBC"],
        therapeutic_monitoring=["Continuous arterial blood pressure, pulsus paradoxus (> 10 mmHg drop in SBP during inspiration)", "Telemetry for ventricular arrhythmias during pericardiocentesis"],
        urgent_interventions=["EMERGENCY PERICARDIOCENTESIS: ultrasound-guided subxiphoid or apical drainage; even removing 20-50 mL of fluid dramatically relieves intrapericardial pressure and restores stroke volume", "Strictly AVOID positive pressure ventilation / mechanical ventilation if possible (positive intrathoracic pressure obliterates venous return and induces total cardiovascular collapse)", "Vasodilators and diuretics are LETHALLY CONTRAINDICATED"],
        clinical_pearls="Beck's Triad (hypotension, jugular venous distension, muffled heart sounds) is present in only a minority of acute cases; bedside echocardiographic demonstration of RV diastolic collapse is the diagnostic gold standard."
    ),

    "CARDIOGENIC_SHOCK": ClinicalSTGProtocol(
        disease_key="CARDIOGENIC_SHOCK",
        disease_name="Cardiogenic Shock (Pump Failure)",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Norepinephrine", "4mg", 0.05, None, "IV", "CONTINUOUS_INFUSION", 3, "First-line vasopressor: titrate 0.05-1.5 mcg/kg/min to restore coronary perfusion (target MAP >= 65)"),
            PrescriptionItem("Dobutamine", "250mg", 2.5, None, "IV", "CONTINUOUS_INFUSION", 3, "Inotrope: titrate 2.5-15 mcg/kg/min once MAP > 65 to augment stroke volume and cardiac index"),
            PrescriptionItem("Aspirin", "300mg", None, None, "ORAL", "STAT", 1, "Chewed immediately if acute coronary syndrome etiology"),
            PrescriptionItem("Heparin", "5000 units", None, None, "IV", "STAT", 1, "Therapeutic anticoagulation for acute coronary syndrome")
        ],
        alternative_regimen=[
            PrescriptionItem("Epinephrine", "1mg", 0.05, None, "IV", "CONTINUOUS_INFUSION", 3, "Inodilator/vasopressor alternative in refractory shock"),
            PrescriptionItem("Milrinone", "10mg", 0.375, None, "IV", "CONTINUOUS_INFUSION", 3, "Phosphodiesterase inhibitor inotrope (caution: vasodilates; avoid if hypotensive)")
        ],
        mandatory_baseline_labs=["Bedside Echocardiography (EF, regional wall motion, acute mitral regurgitation, VSD)", "Serum Lactate and serial clearances", "Arterial Blood Gas (severe metabolic acidosis)", "Cardiac Troponin and 12-Lead ECG", "Serum Creatinine and LFTs"],
        therapeutic_monitoring=["Invasive arterial line and central venous pressure monitoring", "ScvO2 (central venous oxygen saturation target > 65%)", "Serial bedside cardiac output calculations"],
        urgent_interventions=["Immediate activation of Cardiac Catheterization Lab for emergency PCI / revascularization (SHOCK trial proven mortality reduction)", "Mechanical Circulatory Support (Intra-aortic balloon pump / Impella / ECMO) evaluation", "Judicious fluid challenge (250 mL) only if RV infarction and clear lung fields"],
        clinical_pearls="Avoid aggressive IV fluid boluses in LV failure — flooded non-compliant left ventricles rapidly push hydrostatic pressures into alveolar pulmonary edema and precipitate asystolic arrest."
    ),

    "DISSEMINATED_INTRAVASCULAR_COAGULATION": ClinicalSTGProtocol(
        disease_key="DISSEMINATED_INTRAVASCULAR_COAGULATION",
        disease_name="Disseminated Intravascular Coagulation (DIC)",
        category="HEMATOLOGY_ONCOLOGY",
        first_line_regimen=[
            PrescriptionItem("Tranexamic Acid", "1000mg", None, None, "IV", "STAT", 1, "Use with extreme caution ONLY in hyperfibrinolytic bleeding; contraindicated if thrombotic DIC"),
            PrescriptionItem("Heparin", "2500 units", None, None, "IV", "CONTINUOUS_INFUSION", 3, "Low dose unfractionated heparin (5-10 units/kg/h) ONLY in predominant thrombotic phenotype (purpura fulminans / organ ischemia)")
        ],
        alternative_regimen=[
            PrescriptionItem("Enoxaparin", "40mg", None, None, "SC", "OD", 3, "Prophylactic low molecular weight heparin in non-bleeding thrombotic DIC")
        ],
        mandatory_baseline_labs=["Serial ISTH DIC score: Platelet count, PT/INR, Fibrinogen level, D-Dimer / Fibrin degradation products (FDP)", "Peripheral Blood Smear (schistocytes, red cell fragmentation)", "Blood cultures, ABG, and Serum Lactate"],
        therapeutic_monitoring=["Serial coagulation profile and fibrinogen every 4-6 hours", "Clinical bleeding from venipuncture sites, mucosal surfaces, and surgical wounds"],
        urgent_interventions=["THE CORNERSTONE OF TREATMENT IS AGGRESSIVE IDENTIFICATION AND ERADICATION OF THE UNDERLYING CAUSE (sepsis, obstetric catastrophe, trauma, malignancy)", "Component Replacement Therapy: Transfuse Platelets if < 50,000/uL with active bleeding (or < 20,000 with high risk)", "Cryoprecipitate (10 units) to maintain Fibrinogen > 150 mg/dL", "Fresh Frozen Plasma (15-30 mL/kg) for prolonged PT/aPTT in bleeding patient"],
        clinical_pearls="Treating laboratory numbers alone in a non-bleeding DIC patient is harmful; transfusions of platelets and plasma are indicated ONLY in the presence of active bleeding or prior to invasive procedures."
    ),

    "HYPERTENSIVE_EMERGENCY": ClinicalSTGProtocol(
        disease_key="HYPERTENSIVE_EMERGENCY",
        disease_name="Hypertensive Emergency with Acute End-Organ Damage",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Labetalol", "20mg", None, None, "IV", "STAT", 1, "20mg slow IV over 2 min; repeat 40-80mg q10m (max 300mg) or infuse 1-2 mg/min"),
            PrescriptionItem("Nicardipine", "5mg", None, None, "IV", "CONTINUOUS_INFUSION", 1, "Titrate 5-15 mg/h IV infusion; excellent titratability and cerebral safety")
        ],
        alternative_regimen=[
            PrescriptionItem("Nitroprusside", "50mg", None, None, "IV", "CONTINUOUS_INFUSION", 1, "0.5-2.0 mcg/kg/min IV; watch for cyanide toxicity if prolonged"),
            PrescriptionItem("Hydralazine", "10mg", None, None, "IV", "STAT", 1, "Alternative in eclamptic pregnancy")
        ],
        mandatory_baseline_labs=["Fundoscopy for papilledema, flame hemorrhages, and cotton wool spots", "Non-contrast Head CT (rule out stroke, hemorrhage, PRES)", "Serum Creatinine and Urinalysis (hematuria, proteinuria, RBC casts)", "12-Lead ECG, Troponin, and Chest X-Ray (pulmonary edema, aortic dissection)"],
        therapeutic_monitoring=["Invasive arterial line blood pressure monitoring", "Neurological checks every 30 minutes"],
        urgent_interventions=["GOAL: Reduce Mean Arterial Pressure (MAP) by no more than 20-25% in the first hour, then to 160/100 mmHg over 2-6 hours", "EXCEPTIONS: Acute Aortic Dissection (rapidly drop SBP to < 120 in 20 min) and Acute Ischemic Stroke thrombolysis (< 185/110)"],
        clinical_pearls="Do NOT drop blood pressure precipitously — chronic hypertensives have right-shifted cerebral autoregulation curves; rapid normalization of BP causes watershed cerebral infarction, acute blindness, and acute renal tubular necrosis."
    ),

    "INTRACEREBRAL_HEMORRHAGE": ClinicalSTGProtocol(
        disease_key="INTRACEREBRAL_HEMORRHAGE",
        disease_name="Spontaneous Acute Intracerebral Hemorrhage (ICH)",
        category="NEUROLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Labetalol", "20mg", None, None, "IV", "STAT", 1, "Target systolic BP 130-140 mmHg immediately to arrest hematoma expansion"),
            PrescriptionItem("Nicardipine", "5mg", None, None, "IV", "CONTINUOUS_INFUSION", 1, "Smooth IV infusion titrated to maintain SBP 130-140 mmHg"),
            PrescriptionItem("Tranexamic Acid", "1000mg", None, None, "IV", "STAT", 1, "1g IV over 10 min if presentation within 2 hours (hematoma stabilization)")
        ],
        alternative_regimen=[
            PrescriptionItem("Mannitol", "100ml", 0.5, "100ml", "IV", "STAT", 1, "20% Mannitol 0.5-1.0 g/kg over 20 min ONLY for acute herniation / pupillary asymmetry"),
            PrescriptionItem("Hypertonic Saline", "150ml", 3.0, "150ml", "IV", "STAT", 1, "3% NaCl 150 mL bolus for elevated intracranial pressure")
        ],
        mandatory_baseline_labs=["STAT Non-contrast Head CT (hematoma volume, intraventricular extension, midline shift)", "Coagulation profile (PT/INR, aPTT, Platelets) to identify anticoagulant coagulopathy", "CBC and Serum Creatinine", "Repeat CT at 24 hours to monitor hematoma expansion"],
        therapeutic_monitoring=["Hourly GCS, pupil reactivity, and focal neurological deficits", "Continuous automated BP surveillance"],
        urgent_interventions=["Immediate reversal of anticoagulants: 4-Factor Prothrombin Complex Concentrate (PCC) + Vitamin K for Warfarin; Idarucizumab for Dabigatran; Andexanet alfa for Apixaban/Rivaroxaban", "Urgent Neurosurgical consult for decompression craniotomy or EVD if cerebellar hemorrhage (> 3cm) or hydrocephalus", "Elevate head of bed 30 degrees, maintain normothermia and euglycemia"],
        clinical_pearls="INTERACT-2 / ATTACH-2 trials: Rapid, smooth reduction of SBP to 130-140 mmHg is safe and arrests catastrophic hematoma growth, but avoid dropping SBP < 120 mmHg."
    ),

    "INTUSSUSCEPTION": ClinicalSTGProtocol(
        disease_key="INTUSSUSCEPTION",
        disease_name="Acute Intussusception",
        category="PEDIATRIC",
        first_line_regimen=[
            PrescriptionItem("Normal Saline", "200ml", 20.0, "500ml", "IV", "STAT", 1, "20 mL/kg IV bolus for dehydration and hypovolemia"),
            PrescriptionItem("Ceftriaxone", "500mg", 50.0, "1000mg", "IV", "STAT", 1, "Pre-procedural prophylactic antimicrobial coverage"),
            PrescriptionItem("Metronidazole", "150mg", 7.5, "500mg", "IV", "STAT", 1, "Anaerobic gut flora coverage")
        ],
        alternative_regimen=[
            PrescriptionItem("Paracetamol", "250mg", 15.0, "1000mg/day", "ORAL", "TDS", 3, "Post-reduction analgesia")
        ],
        mandatory_baseline_labs=["Targeted Abdominal Ultrasound ('target sign' / 'doughnut sign' / 'pseudokidney sign')", "CBC and Serum Electrolytes (hypokalemia and metabolic alkalosis from vomiting)", "Abdominal X-Ray (rule out free air / perforation before enema)"],
        therapeutic_monitoring=["Hourly abdominal exam and repeat ultrasound post-reduction to confirm absence of recurrence"],
        urgent_interventions=["FIRST-LINE NON-SURGICAL REDUCTION: Ultrasound-guided or fluoroscopic air-contrast pneumatic enema (success rate > 85%)", "STRICT CONTRAINDICATION TO ENEMA: Peritonitis, bowel perforation, hemodynamic shock, or prolonged bowel gangrene", "Emergency Pediatric Surgery consult on standby during enema; immediate laparotomy if perforation or non-reducible mass"],
        clinical_pearls="Classical triad of paroxysmal colicky abdominal pain, sausage-shaped abdominal mass, and 'currant jelly' stools is present in only 30% of infants; ultrasound is mandatory in unexplained infant lethargy with vomiting."
    ),

    "NECROTIZING_FASCIITIS": ClinicalSTGProtocol(
        disease_key="NECROTIZING_FASCIITIS",
        disease_name="Necrotizing Fasciitis (Type I Polymicrobial / Type II Monomicrobial GAS)",
        category="DERMATOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Piperacillin-Tazobactam", "4.5g", 100.0, "18g/day", "IV", "TDS", 7, "Broad spectrum gram-negative and anaerobic coverage"),
            PrescriptionItem("Vancomycin", "1000mg", 15.0, "2000mg/day", "IV", "BD", 7, "MRSA coverage"),
            PrescriptionItem("Clindamycin", "900mg", 10.0, "2700mg/day", "IV", "TDS", 7, "Suppresses bacterial protein synthesis and toxin/superantigen production")
        ],
        alternative_regimen=[
            PrescriptionItem("Meropenem", "1g", 20.0, "3g/day", "IV", "TDS", 7, "Carbapenem alternative in severe penicillin allergy"),
            PrescriptionItem("Vancomycin", "1000mg", 15.0, "2000mg/day", "IV", "BD", 7, "MRSA coverage"),
            PrescriptionItem("Clindamycin", "900mg", 10.0, "2700mg/day", "IV", "TDS", 7, "Antitoxin effect")
        ],
        mandatory_baseline_labs=["LRINEC Score (Laboratory Risk Indicator for Necrotizing Fasciitis: CRP, WBC, Hb, Na, Cr, Glucose)", "Blood cultures x 2 and intra-operative tissue Gram stain and cultures (NOT superficial swabs)", "Serum Lactate and ABG (severe septic shock)", "Plain radiograph or CT of affected area (subcutaneous gas along fascial planes)"],
        therapeutic_monitoring=["Mark margins of erythema with a surgical skin marker every 1 hour to assess rapid progression", "Continuous hemodynamic and ICU monitoring"],
        urgent_interventions=["IMMEDIATE SURGICAL CONSULTATION FOR RADICAL DEBRIDEMENT: Surgery must not be delayed for imaging or lab tests", "Aggressive crystalloid fluid resuscitation for septic shock", "Planned 'second-look' surgical debridement within 24 hours"],
        clinical_pearls="Severe pain out of proportion to mild physical skin findings is the earliest hallmark; 'dishwater' foul fluid and skin numbness develop as cutaneous nerves thrombose."
    ),

    "NEONATAL_SEPSIS": ClinicalSTGProtocol(
        disease_key="NEONATAL_SEPSIS",
        disease_name="Early / Late-Onset Neonatal Sepsis",
        category="PEDIATRIC",
        first_line_regimen=[
            PrescriptionItem("Ampicillin", "100mg", 50.0, "200mg/kg", "IV", "BD", 10, "50 mg/kg IV q12h (Group B Streptococcus and Listeria monocytogenes)"),
            PrescriptionItem("Gentamicin", "10mg", 5.0, "5mg/kg", "IV", "OD", 7, "5 mg/kg IV q24-36h (gram-negative enteric coverage; monitor renal/ototoxicity)")
        ],
        alternative_regimen=[
            PrescriptionItem("Cefotaxime", "100mg", 50.0, "200mg/kg", "IV", "BD", 10, "Alternative cephalosporin; STRICTLY AVOID Ceftriaxone in neonates due to kernicterus and calcium precipitation"),
            PrescriptionItem("Amikacin", "15mg", 15.0, "15mg/kg", "IV", "OD", 7, "Alternative aminoglycoside")
        ],
        mandatory_baseline_labs=["Blood culture (minimum 1 mL blood in pediatric bottle) before antibiotics", "Lumbar Puncture (CSF analysis and culture mandatory in suspected neonatal sepsis)", "CBC with differential (Immature to Total neutrophil ratio I:T > 0.2 is highly sensitive)", "Micro-ESR and CRP", "Serum Bilirubin and Blood Glucose"],
        therapeutic_monitoring=["Continuous temperature regulation (incubator / radiant warmer)", "SpO2, apnea, bradycardia monitoring", "Serum creatinine and therapeutic aminoglycoside monitoring"],
        urgent_interventions=["Thermal protection (prevent hypothermia)", "Immediate IV access and gentle fluid bolus (10 mL/kg Normal Saline over 30 min if in shock)", "Oxygen support / CPAP for grunting, retracting neonate"],
        clinical_pearls="NEVER PRESCRIBE CEFTRIAXONE IN NEONATES: it displaces bilirubin from albumin, causing kernicterus, and precipitates with calcium to form lethal cardiopulmonary crystal emboli. Use Cefotaxime."
    ),

    "OVARIAN_TORSION": ClinicalSTGProtocol(
        disease_key="OVARIAN_TORSION",
        disease_name="Acute Ovarian / Adnexal Torsion",
        category="OBSTETRIC_GYNECOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "STAT", 1, "Acute visceral analgesia prior to theatre"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 3, "Post-operative multimodal analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Morphine", "5mg", 0.05, "5mg", "IV", "STAT", 1, "Severe acute pelvic pain analgesia")
        ],
        mandatory_baseline_labs=["Pelvic Ultrasound with Color Doppler (enlarged edematous ovary > 4cm, peripheral follicles, whirlpool sign of twisted vascular pedicle, absent venous/arterial Doppler flow)", "STAT Serum beta-hCG (rule out ectopic pregnancy)", "CBC, Type & Screen for surgery"],
        therapeutic_monitoring=["Pain scores and serial abdominal peritoneal assessments"],
        urgent_interventions=["EMERGENCY GYNECOLOGY CONSULT FOR IMMEDIATE DIAGNOSTIC LAPAROSCOPY", "Laparoscopic detorsion and ovarian preservation (ovariopexy/cystectomy) is the standard of care regardless of dark congested ovarian appearance — viable function recovers in > 90% of detorsed ovaries", "Keep strictly NPO"],
        clinical_pearls="Normal Doppler arterial flow does NOT rule out ovarian torsion; venous outflow is occluded first while dual arterial blood supply (uterine and ovarian arteries) can persist intermittently."
    ),

    "PERFORATED_PEPTIC_ULCER": ClinicalSTGProtocol(
        disease_key="PERFORATED_PEPTIC_ULCER",
        disease_name="Perforated Peptic Ulcer with Generalized Peritonitis",
        category="GASTROINTESTINAL",
        first_line_regimen=[
            PrescriptionItem("Pantoprazole", "80mg", 1.0, "80mg", "IV", "STAT", 1, "80mg IV bolus followed by 8mg/h infusion or 40mg IV BD"),
            PrescriptionItem("Ceftriaxone", "1g", 50.0, "2g/day", "IV", "BD", 7, "Broad spectrum peritonitis coverage"),
            PrescriptionItem("Metronidazole", "500mg", 7.5, "1500mg/day", "IV", "TDS", 7, "Anaerobic bacteroides coverage"),
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "TDS", 3, "Analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Piperacillin-Tazobactam", "4.5g", 100.0, "18g/day", "IV", "TDS", 7, "Broad monotherapy for severe contamination"),
            PrescriptionItem("Pantoprazole", "40mg", 1.0, "40mg", "IV", "BD", 7, "High-dose acid suppression")
        ],
        mandatory_baseline_labs=["Erect Chest X-Ray / Left Lateral Decubitus (free air under right hemidiaphragm / pneumoperitoneum)", "Non-contrast Abdominal CT if X-ray equivocal", "CBC, Serum Electrolytes, BUN, and Creatinine", "Serum Lactate and ABG"],
        therapeutic_monitoring=["Hourly vitals, urine output via Foley catheter (> 0.5 mL/kg/h)", "Signs of septic shock and abdominal compartment syndrome"],
        urgent_interventions=["IMMEDIATE GENERAL SURGERY CONSULT FOR EMERGENCY LAPAROTOMY / LAPAROSCOPIC OMENTAL PATCH REPAIR (Graham patch)", "Aggressive fluid resuscitation with warm Ringer's Lactate (minimum 2-3 Liters)", "Nasogastric tube insertion on continuous suction to decompress peritoneal chemical soiling"],
        clinical_pearls="Mortality increases by 2% for every single hour of surgical delay beyond 6 hours from perforation onset."
    ),

    "RUPTURED_ECTOPIC_PREGNANCY": ClinicalSTGProtocol(
        disease_key="RUPTURED_ECTOPIC_PREGNANCY",
        disease_name="Ruptured Ectopic Pregnancy with Hemoperitoneum",
        category="OBSTETRIC_GYNECOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Normal Saline", "1000ml", 10.0, "1000ml", "IV", "STAT", 1, "Immediate rapid fluid resuscitation via two wide-bore (14-16G) IV lines"),
            PrescriptionItem("Tranexamic Acid", "1000mg", None, None, "IV", "STAT", 1, "1g IV over 10 min for active intra-abdominal hemorrhage"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 3, "Post-operative analgesia")
        ],
        alternative_regimen=[
            PrescriptionItem("Ringer Lactate", "1000ml", 10.0, "1000ml", "IV", "STAT", 1, "Balanced fluid resuscitation")
        ],
        mandatory_baseline_labs=["STAT Point-of-care Urine Pregnancy Test and Serum quantitative beta-hCG", "Bedside FAST Ultrasound: free fluid in pouch of Douglas / Morrison's pouch; empty uterine cavity", "STAT Blood Type, Crossmatch 4 units PRBC and FFP", "CBC (baseline Hb may underestimate acute blood loss)"],
        therapeutic_monitoring=["Continuous heart rate and blood pressure every 5 minutes", "Watch for peritoneal signs, shoulder tip pain (diaphragmatic irritation from hemoperitoneum)"],
        urgent_interventions=["IMMEDIATE OBSTETRICS & GYNECOLOGY SURGICAL CONSULT FOR EMERGENCY EXPLORATORY LAPAROSCOPY / LAPAROTOMY AND SALPINGECTOMY", "Activate Massive Transfusion Protocol immediately if hemodynamically collapsed", "Rh-negative non-sensitized mothers must receive Anti-D Immunoglobulin within 72 hours"],
        clinical_pearls="Never delay emergency surgery in a shocked patient with positive pregnancy test and free peritoneal fluid to wait for quantitative beta-hCG results."
    ),

    "SCRUB_TYPHUS": ClinicalSTGProtocol(
        disease_key="SCRUB_TYPHUS",
        disease_name="Scrub Typhus (Orientia tsutsugamushi)",
        category="INFECTIOUS",
        first_line_regimen=[
            PrescriptionItem("Doxycycline", "100mg", 2.2, "100mg", "ORAL", "BD", 7, "100mg PO BD for 7 days (or 2.2 mg/kg BD in children < 45kg)"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "ORAL", "TDS", 5, "Antipyretic comfort")
        ],
        alternative_regimen=[
            PrescriptionItem("Azithromycin", "500mg", 10.0, "500mg/day", "ORAL", "OD", 5, "Preferred first-line in PREGNANCY and severe pediatric cases where doxycycline avoided"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "ORAL", "TDS", 5, "Antipyretic")
        ],
        mandatory_baseline_labs=["Careful search for pathognomonic cutaneous ESCHAR in hidden skin folds (axillae, groin, perineum, submammary)", "Scrub Typhus IgM ELISA / Rapid Card Test", "Complete Blood Count (thrombocytopenia and leukocytosis)", "LFTs (transaminitis and elevated alkaline phosphatase)", "Serum Creatinine and Chest X-Ray (watch for ARDS)"],
        therapeutic_monitoring=["Temperature defervescence typically occurs within 24-48 hours of starting Doxycycline", "Monitor SpO2 and respiratory rate (ARDS is a major fatal complication)"],
        urgent_interventions=["Immediate empirical initiation of Doxycycline or Azithromycin upon clinical suspicion — do NOT delay for serological confirmation", "Supportive care for multi-organ dysfunction (ARDS, AKI, myocarditis) in ICU"],
        clinical_pearls="AAP and CDC guidelines endorse Doxycycline for up to 14 days in children of any age for life-threatening rickettsial infections without significant tooth staining risk; Azithromycin is the drug of choice in pregnant females."
    ),

    "STEVENS_JOHNSON_SYNDROME_TEN": ClinicalSTGProtocol(
        disease_key="STEVENS_JOHNSON_SYNDROME_TEN",
        disease_name="Stevens-Johnson Syndrome / Toxic Epidermal Necrolysis (SJS / TEN)",
        category="DERMATOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 5, "Analgesia; STRICTLY PROHIBIT ALL NSAIDs, Sulfonamides, and Anticonvulsants"),
            PrescriptionItem("Normal Saline", "1000ml", 10.0, "1000ml", "IV", "CONTINUOUS_INFUSION", 5, "Fluid replacement calculated using Parkland-like formula for detached skin area"),
            PrescriptionItem("Tramadol", "50mg", 1.0, "200mg/day", "IV", "TDS", 3, "Severe denudation pain management")
        ],
        alternative_regimen=[
            PrescriptionItem("Cyclosporine", "3mg/kg", 3.0, "300mg", "ORAL", "BD", 10, "Targeted immunosuppressive therapy to halt epidermal apoptosis"),
            PrescriptionItem("Fentanyl", "25mcg", 0.5, "50mcg", "IV", "PRN", 2, "Severe dressing change analgesia")
        ],
        mandatory_baseline_labs=["SCORTEN Prognostic Score calculated within first 24 hours (Age, Heart rate, Malignancy, BSA detached > 10%, BUN, Glucose, Bicarbonate)", "Skin Biopsy (full-thickness epidermal necrosis with minimal dermal inflammation)", "Electrolytes, Blood Urea Nitrogen, Albumin", "Blood and wound cultures (surveillance for S. aureus and Pseudomonas superinfection)"],
        therapeutic_monitoring=["Exact mapping of body surface area detachment (Nikolsky sign positive)", "Ophthalmology consult on Day 1 (amniotic membrane grafting to prevent permanent blindness)", "Fluid and electrolyte balance"],
        urgent_interventions=["IMMEDIATE WITHDRAWAL OF ALL POTENTIALLY CAUSATIVE MEDICATIONS (Allopurinol, Carbamazepine, Phenytoin, Cotrimoxazole, NSAIDs)", "Transfer immediately to a specialized Burn Unit or Intensive Care Unit", "Meticulous non-adherent wound dressing (petrolatum gauze); strictly avoid silver sulfadiazine (contains sulfonamide)", "Aggressive eye care with lubricating drops every 1 hour"],
        clinical_pearls="Early withdrawal of the culprit drug is the single most powerful determinant of patient survival; each day of delay doubles the mortality risk."
    ),

    "SUBARACHNOID_HEMORRHAGE": ClinicalSTGProtocol(
        disease_key="SUBARACHNOID_HEMORRHAGE",
        disease_name="Aneurysmal Subarachnoid Hemorrhage (aSAH)",
        category="NEUROLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Nimodipine", "60mg", None, None, "ORAL", "QID", 21, "60mg PO q4h for 21 days; proven neuroprotection reducing delayed cerebral ischemia"),
            PrescriptionItem("Labetalol", "20mg", None, None, "IV", "STAT", 1, "Target systolic BP < 140-160 mmHg prior to aneurysm securing to prevent catastrophic re-bleeding"),
            PrescriptionItem("Tranexamic Acid", "1000mg", None, None, "IV", "STAT", 1, "Short-term antifibrinolytic until surgical/endovascular securing if delayed"),
            PrescriptionItem("Paracetamol", "1000mg", 15.0, "4000mg/day", "IV", "TDS", 7, "Analgesia; avoid NSAIDs due to antiplatelet bleeding risk")
        ],
        alternative_regimen=[
            PrescriptionItem("Nicardipine", "5mg", None, None, "IV", "CONTINUOUS_INFUSION", 1, "Alternative IV titration to maintain SBP < 140 mmHg"),
            PrescriptionItem("Nimodipine", "60mg", None, None, "ORAL", "QID", 21, "Neuroprotective calcium channel blocker")
        ],
        mandatory_baseline_labs=["STAT Non-contrast Head CT (hyperdensity in basal cisterns / sylvian fissures; sensitivity > 98% in first 6 hours)", "Lumbar Puncture (xanthochromia on spectrophotometry) if CT negative and thunderclap headache > 6h", "CT Angiography of Circle of Willis / Digital Subtraction Angiography (DSA)", "Serum Sodium every 6 hours (watch for Cerebral Salt Wasting vs SIADH)"],
        therapeutic_monitoring=["Continuous GCS, pupil reactivity, and Hunt & Hess / Fisher grade assessment", "Transcranial Doppler (TCD) daily from Day 3 to 14 to monitor cerebral vasospasm"],
        urgent_interventions=["EMERGENCY NEUROSURGICAL / INTERVENTIONAL NEURORADIOLOGY CONSULT FOR EARLY ANEURYSM SECURING (endovascular coiling or surgical clipping within 24 hours)", "Strict bed rest, quiet dark room, stool softeners to prevent Valsalva re-rupture", "EVD (external ventricular drain) for acute hydrocephalus"],
        clinical_pearls="Never administer IV Nimodipine: accidental intravenous injection of oral Nimodipine solution produces fatal cardiovascular collapse and severe refractory hypotension."
    ),

    "VENTRICULAR_TACHYCARDIA": ClinicalSTGProtocol(
        disease_key="VENTRICULAR_TACHYCARDIA",
        disease_name="Ventricular Tachycardia (Monomorphic / Polymorphic)",
        category="CARDIOVASCULAR",
        first_line_regimen=[
            PrescriptionItem("Amiodarone", "150mg", 5.0, "150mg", "IV", "STAT", 1, "150mg IV over 10 min for stable monomorphic VT; repeat 150mg in 10 min, then 1 mg/min infusion x 6h"),
            PrescriptionItem("Magnesium Sulfate", "2g", 50.0, "2000mg", "IV", "STAT", 1, "2g IV over 1-2 min; DRUG OF CHOICE for Polymorphic VT / Torsades de Pointes")
        ],
        alternative_regimen=[
            PrescriptionItem("Lidocaine", "100mg", 1.0, "100mg", "IV", "STAT", 1, "1.0-1.5 mg/kg IV push; preferred alternative if ischemia/AMI or prolonged QT"),
            PrescriptionItem("Procainamide", "100mg", 10.0, "100mg", "IV", "STAT", 1, "20-50 mg/min up to 17 mg/kg for stable wide complex tachycardia")
        ],
        mandatory_baseline_labs=["12-Lead ECG (wide QRS > 120ms, AV dissociation, fusion/capture beats, Brugada criteria)", "Serum Potassium and Magnesium (STAT)", "Cardiac Troponin and arterial blood gas", "Serum toxicology screen / drug levels (Digoxin, antiarrhythmics)"],
        therapeutic_monitoring=["Continuous cardiac rhythm telemetry with defibrillation pads in place", "Blood pressure every 2-5 minutes"],
        urgent_interventions=["IF PULSELESS VENTRICULAR TACHYCARDIA: IMMEDIATE DEFIBRILLATION (200 J biphasic unsynchronized) + CPR (ACLS protocol)", "IF UNSTABLE VT WITH PULSE (hypotension, altered sensorium, pulmonary edema, angina): IMMEDIATE SYNCHRONIZED CARDIOVERSION (100 J biphasic)", "Correct hypokalemia (target K+ > 4.0 mEq/L) and hypomagnesemia (target Mg2+ > 2.0 mg/dL)"],
        clinical_pearls="Never administer Verapamil, Diltiazem, or Adenosine to an undifferentiated wide-complex tachycardia — in 80% of cases the rhythm is VT, and calcium channel blockers cause immediate cardiovascular collapse."
    ),

    "PRE_ECLAMPSIA_WITH_SEVERE_FEATURES": ClinicalSTGProtocol(
        disease_key="PRE_ECLAMPSIA_WITH_SEVERE_FEATURES",
        disease_name="Pre-eclampsia with Severe Features / Impending Eclampsia",
        category="OBSTETRIC_GYNECOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Magnesium Sulfate", "4g", 50.0, "4000mg", "IV", "STAT", 1, "4g IV loading dose in 100mL over 20 min, followed by 1g/hour continuous IV maintenance"),
            PrescriptionItem("Labetalol", "20mg", None, None, "IV", "STAT", 1, "20mg IV bolus over 2 min; repeat 40mg then 80mg q10min up to 220mg max for SBP >= 160 or DBP >= 110"),
            PrescriptionItem("Nifedipine", "10mg", None, None, "ORAL", "PRN", 1, "10mg orally if IV access delayed; repeat in 30 min if SBP >= 160 or DBP >= 110")
        ],
        alternative_regimen=[
            PrescriptionItem("Hydralazine", "5mg", None, None, "IV", "STAT", 1, "5mg IV slowly over 1-2 min; repeat 5-10mg q20-30min up to 20mg max"),
            PrescriptionItem("Methyldopa", "500mg", None, None, "ORAL", "TDS", 7, "500mg oral maintenance for step-down control")
        ],
        mandatory_baseline_labs=["Complete Blood Count with Platelets", "Serum Creatinine", "AST / ALT / LDH", "Urine Protein:Creatinine Ratio", "Fetal Cardiotocography (CTG)"],
        therapeutic_monitoring=["Hourly deep tendon patellar reflex (withhold MgSO4 if absent)", "Hourly respiratory rate (must be >= 16/min)", "Strict hourly urine output via Foley catheter (must be >= 30 mL/hr)"],
        urgent_interventions=["Keep bedside 10% IV Calcium Gluconate (10 mL) immediately available as Magnesium toxicity antidote", "Expedite maternal stabilization and obstetric delivery evaluation", "Insert wide-bore IV line and Foley catheter with urometer"],
        clinical_pearls="Never administer ACE Inhibitors or ARBs (severe fetopathy). Delivery of the placenta is the only definitive cure for pre-eclampsia."
    ),

    "POLYCYSTIC_OVARY_SYNDROME": ClinicalSTGProtocol(
        disease_key="POLYCYSTIC_OVARY_SYNDROME",
        disease_name="Polycystic Ovary Syndrome (PCOS) - Metabolic & Ovulatory Management",
        category="OBSTETRIC_GYNECOLOGICAL",
        first_line_regimen=[
            PrescriptionItem("Metformin", "500mg", None, None, "ORAL", "BD", 90, "Titrate to 1000mg BD after 2 weeks with meals for insulin sensitization"),
            PrescriptionItem("Ethinylestradiol + Cyproterone acetate", "0.035mg/2mg", None, None, "ORAL", "OD", 84, "21 days on, 7 days off for cycle regulation and clinical hyperandrogenism control"),
            PrescriptionItem("Medroxyprogesterone acetate", "10mg", None, None, "ORAL", "OD", 14, "10mg daily for 12-14 days every 2-3 months for endometrial protection if OCP contraindicated")
        ],
        alternative_regimen=[
            PrescriptionItem("Spironolactone", "50mg", None, None, "ORAL", "OD", 90, "50-100mg daily for persistent hirsutism (strict barrier contraception mandatory)"),
            PrescriptionItem("Inositol", "2g", None, None, "ORAL", "BD", 90, "Myo-inositol 2g + D-chiro-inositol 50mg BD for metabolic support")
        ],
        mandatory_baseline_labs=["Fasting Plasma Glucose & 2-Hour 75g OGTT", "Fasting Lipid Profile", "Serum TSH & Prolactin", "Total & Free Testosterone", "Pelvic Ultrasound"],
        therapeutic_monitoring=["BMI and waist circumference quarterly", "Annual screening for Type 2 Diabetes and dyslipidemia"],
        urgent_interventions=["Prescribe mandatory barrier contraception if Spironolactone is used due to feminization risk in male fetus", "Dietary lifestyle counseling targeting 5-10% weight reduction"],
        clinical_pearls="Screen for endometrial hyperplasia in any PCOS patient with amenorrhea > 3 months."
    ),

    "PEDIATRIC_STATUS_ASTHMATICUS": ClinicalSTGProtocol(
        disease_key="PEDIATRIC_STATUS_ASTHMATICUS",
        disease_name="Pediatric Status Asthmaticus / Severe Acute Wheezing Attack",
        category="PEDIATRIC",
        first_line_regimen=[
            PrescriptionItem("Salbutamol", "2.5mg", 0.15, "5.0mg", "INHALATION", "STAT", 1, "2.5-5.0 mg nebulized with 100% Oxygen every 20 min for 3 doses (or continuous 0.5 mg/kg/hr)"),
            PrescriptionItem("Ipratropium Bromide", "250mcg", 0.05, "500mcg", "INHALATION", "STAT", 1, "250 mcg nebulized mixed with Salbutamol every 20 min for 3 doses in first hour"),
            PrescriptionItem("Hydrocortisone", "100mg", 4.0, "200mg", "IV", "STAT", 1, "4 mg/kg IV stat, followed by 2 mg/kg q6h; switch to oral prednisolone when tolerated"),
            PrescriptionItem("Magnesium Sulfate", "1g", 50.0, "2000mg", "IV", "STAT", 1, "50 mg/kg IV in 100 mL Normal Saline over 20 min for severe refractory bronchospasm")
        ],
        alternative_regimen=[
            PrescriptionItem("Prednisolone", "20mg", 1.0, "40mg/day", "ORAL", "OD", 5, "1-2 mg/kg oral solution once daily for 3-5 days"),
            PrescriptionItem("Aminophylline", "50mg", 5.0, "250mg", "IV", "STAT", 1, "5 mg/kg IV loading dose over 20 min with ECG monitoring if ICU admitted")
        ],
        mandatory_baseline_labs=["Continuous Pulse Oximetry (SpO2)", "Peak Expiratory Flow (PEFR if age > 5)", "Blood Gas (Capillary / Venous / Arterial) for CO2 retention", "Chest X-Ray to rule out pneumothorax or foreign body"],
        therapeutic_monitoring=["Continuous SpO2 (target 94-98%)", "Respiratory rate, sternocleidomastoid retractions, and silent chest signs every 15 min"],
        urgent_interventions=["High-flow humidified Oxygen via face mask with reservoir", "Immediate Pediatric ICU consult for Non-Invasive Ventilation (BiPAP) or ketamine bronchodilation if tiring"],
        clinical_pearls="A 'silent chest' with no audible wheeze in a severe dyspneic child indicates near-fatal airflow limitation requiring immediate resuscitation."
    ),

    "PEDIATRIC_DIARRHEA_SEVERE_DEHYDRATION": ClinicalSTGProtocol(
        disease_key="PEDIATRIC_DIARRHEA_SEVERE_DEHYDRATION",
        disease_name="Pediatric Acute Diarrheal Disease with Severe Dehydration (WHO Plan C)",
        category="PEDIATRIC",
        first_line_regimen=[
            PrescriptionItem("Ringer Lactate", "500ml", 100.0, "2000ml", "IV", "STAT", 1, "WHO Plan C: 100 mL/kg IV. Age <1y: 30 mL/kg in 1h, then 70 mL/kg in 5h. Age >=1y: 30 mL/kg in 30min, then 70 mL/kg in 2.5h"),
            PrescriptionItem("Zinc Sulfate", "20mg", 20.0, "20mg/day", "ORAL", "OD", 14, "20mg daily for 14 days (10mg if age < 6 months) to reduce diarrheal duration and relapse"),
            PrescriptionItem("Oral Rehydration Salts (ORS)", "1 sachet", None, None, "ORAL", "PRN", 5, "5 mL/kg/hour as soon as child can drink orally alongside IV therapy")
        ],
        alternative_regimen=[
            PrescriptionItem("Normal Saline 0.9%", "500ml", 100.0, "2000ml", "IV", "STAT", 1, "Alternative crystalloid if Ringer Lactate unavailable"),
            PrescriptionItem("Ceftriaxone", "500mg", 50.0, "1000mg", "IV", "OD", 3, "Only if bloody diarrhea (shigellosis) with systemic toxicity")
        ],
        mandatory_baseline_labs=["Serum Electrolytes (Sodium, Potassium, Bicarbonate)", "Blood Urea & Serum Creatinine", "Capillary Blood Glucose (rule out hypoglycemia)", "Stool Routine & Microscopy"],
        therapeutic_monitoring=["Reassess radial pulse and fontanelle every 15-30 minutes until strong pulse returns", "Monitor skin pinch and consciousness level hourly"],
        urgent_interventions=["If peripheral IV access fails twice within 90 seconds in shock, establish emergency Intraosseous (IO) access in proximal tibia", "Check and correct hypoglycemia with 5 mL/kg 10% Dextrose bolus"],
        clinical_pearls="Never administer antimotility agents (Loperamide) or antiemetic metoclopramide to young children — risk of paralytic ileus and fatal extrapyramidal crisis."
    )
}


# ====================================================================================================
# JAN AUSHADHI (PMBJP) GENERIC FORMULARY CATALOG (PHASE 39)
# ====================================================================================================

PMBJP_GENERIC_CATALOG: Dict[str, Dict[str, Any]] = {
    "aspirin": {
        "generic_name": "Aspirin (Acetylsalicylic Acid)",
        "pmbjp_drug_code": "PMBJP-0012",
        "dosage_form": "Tablet 75mg / 150mg / 300mg",
        "pmbjp_mrp_inr": 4.50,
        "market_brand_mrp_inr": 35.00,
        "estimated_patient_savings_percent": 87.1
    },
    "clopidogrel": {
        "generic_name": "Clopidogrel",
        "pmbjp_drug_code": "PMBJP-0158",
        "dosage_form": "Tablet 75mg",
        "pmbjp_mrp_inr": 18.00,
        "market_brand_mrp_inr": 110.00,
        "estimated_patient_savings_percent": 83.6
    },
    "atorvastatin": {
        "generic_name": "Atorvastatin Calcium",
        "pmbjp_drug_code": "PMBJP-0089",
        "dosage_form": "Tablet 10mg / 20mg / 40mg / 80mg",
        "pmbjp_mrp_inr": 12.00,
        "market_brand_mrp_inr": 95.00,
        "estimated_patient_savings_percent": 87.4
    },
    "ceftriaxone": {
        "generic_name": "Ceftriaxone Sodium",
        "pmbjp_drug_code": "PMBJP-0245",
        "dosage_form": "Injection 1g vial",
        "pmbjp_mrp_inr": 28.00,
        "market_brand_mrp_inr": 140.00,
        "estimated_patient_savings_percent": 80.0
    },
    "metronidazole": {
        "generic_name": "Metronidazole",
        "pmbjp_drug_code": "PMBJP-0312",
        "dosage_form": "Tablet 400mg / IV Infusion 500mg/100ml",
        "pmbjp_mrp_inr": 8.50,
        "market_brand_mrp_inr": 48.00,
        "estimated_patient_savings_percent": 82.3
    },
    "paracetamol": {
        "generic_name": "Paracetamol (Acetaminophen)",
        "pmbjp_drug_code": "PMBJP-0001",
        "dosage_form": "Tablet 500mg / 650mg / Syrup 120mg/5ml",
        "pmbjp_mrp_inr": 5.00,
        "market_brand_mrp_inr": 32.00,
        "estimated_patient_savings_percent": 84.4
    },
    "ciprofloxacin": {
        "generic_name": "Ciprofloxacin HCl",
        "pmbjp_drug_code": "PMBJP-0115",
        "dosage_form": "Tablet 500mg / Eye Drops 0.3%",
        "pmbjp_mrp_inr": 19.50,
        "market_brand_mrp_inr": 90.00,
        "estimated_patient_savings_percent": 78.3
    },
    "tramadol": {
        "generic_name": "Tramadol HCl",
        "pmbjp_drug_code": "PMBJP-0420",
        "dosage_form": "Capsule 50mg / Injection 50mg/ml",
        "pmbjp_mrp_inr": 14.00,
        "market_brand_mrp_inr": 72.00,
        "estimated_patient_savings_percent": 80.6
    },
    "amoxicillin": {
        "generic_name": "Amoxicillin / Amoxicillin-Clavulanate",
        "pmbjp_drug_code": "PMBJP-0052",
        "dosage_form": "Tablet 500mg / 625mg",
        "pmbjp_mrp_inr": 45.00,
        "market_brand_mrp_inr": 210.00,
        "estimated_patient_savings_percent": 78.6
    },
    "azithromycin": {
        "generic_name": "Azithromycin",
        "pmbjp_drug_code": "PMBJP-0077",
        "dosage_form": "Tablet 500mg",
        "pmbjp_mrp_inr": 38.00,
        "market_brand_mrp_inr": 145.00,
        "estimated_patient_savings_percent": 73.8
    },
    "pantoprazole": {
        "generic_name": "Pantoprazole Sodium",
        "pmbjp_drug_code": "PMBJP-0360",
        "dosage_form": "Tablet 40mg / Injection 40mg",
        "pmbjp_mrp_inr": 11.00,
        "market_brand_mrp_inr": 85.00,
        "estimated_patient_savings_percent": 87.1
    },
    "metformin": {
        "generic_name": "Metformin Hydrochloride",
        "pmbjp_drug_code": "PMBJP-0298",
        "dosage_form": "Tablet 500mg / SR 1000mg",
        "pmbjp_mrp_inr": 6.50,
        "market_brand_mrp_inr": 42.00,
        "estimated_patient_savings_percent": 84.5
    },
    "ondansetron": {
        "generic_name": "Ondansetron HCl",
        "pmbjp_drug_code": "PMBJP-0340",
        "dosage_form": "Tablet 4mg / Injection 2mg/ml",
        "pmbjp_mrp_inr": 7.00,
        "market_brand_mrp_inr": 45.00,
        "estimated_patient_savings_percent": 84.4
    },
    "salbutamol": {
        "generic_name": "Salbutamol Sulphate",
        "pmbjp_drug_code": "PMBJP-0390",
        "dosage_form": "Inhaler 100mcg (200 metered doses) / Respules",
        "pmbjp_mrp_inr": 65.00,
        "market_brand_mrp_inr": 185.00,
        "estimated_patient_savings_percent": 64.9
    }
}


def generate_vernacular_guidance(disease_name: str, calculated_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates plain-language, 5th-grade reading level patient-facing instructions and red flags
    in English, Hindi (हिन्दी), and Bengali (বাংলা).
    """
    med_names = ", ".join(o["drug_name"] for o in calculated_orders)
    return {
        "en": {
            "language": "English",
            "plain_language_summary": f"Prescription guidance for {disease_name}. You have been prescribed: {med_names}.",
            "dosage_schedule_instructions": [
                f"{o['drug_name']}: {o['prescribed_dose']} via {o['route'].lower()}, frequency: {o['frequency']}. {o['instructions']}"
                for o in calculated_orders
            ],
            "critical_red_flags": [
                "Seek immediate emergency medical care if you experience severe chest pain, shortness of breath, sudden dizziness, facial swelling, or an extensive skin rash.",
                "Never abruptly stop taking prescribed medications without consulting your treating doctor."
            ],
            "jan_aushadhi_affordability_note": "High-quality, certified generic alternatives for these medicines are available at Pradhan Mantri Bhartiya Janaushadhi Kendras (PMBJP) at 50% to 90% lower cost."
        },
        "hi": {
            "language": "Hindi (हिन्दी)",
            "plain_language_summary": f"{disease_name} के लिए आवश्यक दवा निर्देश। आपको ये दवाइयाँ परामर्श की गई हैं: {med_names}।",
            "dosage_schedule_instructions": [
                f"{o['drug_name']}: मात्रा {o['prescribed_dose']}, सेवन विधि: {o['route']}, समय: {o['frequency']}। {o['instructions']}"
                for o in calculated_orders
            ],
            "critical_red_flags": [
                "यदि सीने में तेज दर्द, सांस लेने में अत्यधिक तकलीफ, अचानक चक्कर आना, चेहरे या होंठों पर सूजन, या त्वचा पर लाल चकत्ते हों तो तुरंत नजदीकी अस्पताल के आपातकालीन कक्ष (Emergency) में जाएं।",
                "चिकित्सक से परामर्श किए बिना अपनी दवाइयाँ कभी भी बीच में बंद न करें।"
            ],
            "jan_aushadhi_affordability_note": "इन दवाओं के उच्च गुणवत्ता वाले प्रमाणित जेनेरिक विकल्प प्रधानमंत्री भारतीय जन औषधि केंद्र (PMBJP) पर 50% से 90% तक कम कीमत पर उपलब्ध हैं।"
        },
        "bn": {
            "language": "Bengali (বাংলা)",
            "plain_language_summary": f"{disease_name}-এর চিকিৎসার জন্য ঔষধ নির্দেশিকা। আপনার জন্য নির্ধারিত ঔষধগুলি হলো: {med_names}।",
            "dosage_schedule_instructions": [
                f"{o['drug_name']}: মাত্রা {o['prescribed_dose']}, সেবনপদ্ধতি: {o['route']}, সময়: {o['frequency']}। {o['instructions']}"
                for o in calculated_orders
            ],
            "critical_red_flags": [
                "বুকে তীব্র ব্যথা, শ্বাসকষ্ট, হঠাৎ মাথা ঘোরা, রক্তপাত, মুখ বা ঠোঁট ফুলে যাওয়া, বা শরীরে লাল ফুসকুড়ি দেখা দিলে অবিলম্বে নিকটস্থ হাসপাতালের জরুরি বিভাগে যোগাযোগ করুন।",
                "চিকিৎসকের পরামর্শ ছাড়া কোনো ঔষধ সেবন হঠাৎ বন্ধ করবেন না।"
            ],
            "jan_aushadhi_affordability_note": "এই ওষুধগুলির উচ্চমানের শংসাপত্রপ্রাপ্ত জেনেরিক বিকল্পগুলি প্রধানমন্ত্রী ভারতীয় জনঔষধী কেন্দ্র (PMBJP) থেকে ৫০% থেকে ৯০% সাশ্রয়ী মূল্যে সংগ্রহ করা যেতে পারে।"
        }
    }


class PrescriptionProtocolEngine:
    """
    Standard Treatment Guideline (STG) Prescription Generation Engine.
    Produces evidence-based, pediatric-adjusted, pre-screened clinical prescriptions
    for all acute emergency conditions.
    """

    def __init__(self):
        self.catalog = STG_PROTOCOL_CATALOG

    def get_protocol(self, disease_key: str) -> Optional[ClinicalSTGProtocol]:
        return self.catalog.get(disease_key.strip().upper())

    def list_available_diseases(self) -> List[Dict[str, str]]:
        return [
            {"disease_key": k, "name": v.disease_name, "category": v.category}
            for k, v in sorted(self.catalog.items())
        ]

    def generate_prescription_protocol(
        self,
        disease_key: str,
        patient_age: Optional[int] = None,
        patient_weight_kg: Optional[float] = None,
        patient_egfr: Optional[float] = None,
        is_pregnant: Optional[bool] = False,
        known_allergies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generates an individualized clinical prescription order adhering to STGs.
        Pre-screens the final regimen against the CPOE Formulary Engine to guarantee safety.
        """
        clean_key = disease_key.strip().upper()
        protocol = self.get_protocol(clean_key)
        if not protocol:
            return {
                "status": "NOT_FOUND",
                "error": f"Standard Treatment Guideline for '{disease_key}' not found in registry.",
                "available_protocols_count": len(self.catalog)
            }

        allergies = [a.lower().strip() for a in (known_allergies or [])]
        is_peds = (patient_age is not None and patient_age < 18)
        regimen_type = RegimenType.FIRST_LINE
        selection_rationale = "Standard first-line guideline regimen."

        # Allergy-driven flags
        has_penicillin_allergy = any("penicillin" in a or "beta-lactam" in a for a in allergies)
        has_cephalosporin_allergy = any("cephalosporin" in a or "ceftriaxone" in a for a in allergies)
        has_nsaid_allergy = any("nsaid" in a or "aspirin" in a for a in allergies)

        chosen_items = protocol.first_line_regimen
        teratogens = ["warfarin", "methotrexate", "valproate", "doxycycline", "ciprofloxacin", "enalapril", "atorvastatin"]

        def evaluate_item_contraindications(items: List[PrescriptionItem]) -> List[str]:
            issues = []
            drug_names_lower = [it.drug_name.lower() for it in items]
            if is_pregnant and any(any(t in d for t in teratogens) for d in drug_names_lower):
                issues.append("PREGNANCY_TERATOGEN")
            if (has_penicillin_allergy and any("penicillin" in d or "ampicillin" in d or "piperacillin" in d for d in drug_names_lower)) or \
               (has_cephalosporin_allergy and any("cef" in d for d in drug_names_lower)) or \
               (has_nsaid_allergy and any("aspirin" in d or "ibuprofen" in d for d in drug_names_lower)):
                issues.append("DOCUMENTED_ALLERGY")
            if patient_egfr is not None and patient_egfr < 30.0:
                nephrotoxic = ["gentamicin", "amikacin", "vancomycin", "furosemide", "nsaid"]
                if any(any(n in d for n in nephrotoxic) for d in drug_names_lower):
                    issues.append("SEVERE_RENAL_IMPAIRMENT")
            return issues

        first_line_issues = evaluate_item_contraindications(protocol.first_line_regimen)

        if first_line_issues:
            if protocol.alternative_regimen:
                alt_issues = evaluate_item_contraindications(protocol.alternative_regimen)
                if not alt_issues or len(alt_issues) < len(first_line_issues):
                    chosen_items = protocol.alternative_regimen
                    if "PREGNANCY_TERATOGEN" in first_line_issues and "DOCUMENTED_ALLERGY" in first_line_issues:
                        regimen_type = RegimenType.ALTERNATIVE_PREGNANCY
                        selection_rationale = f"Switched to alternative regimen due to dual contraindications: pregnancy teratogenicity and documented allergy ({', '.join(allergies)})."
                    elif "PREGNANCY_TERATOGEN" in first_line_issues:
                        regimen_type = RegimenType.ALTERNATIVE_PREGNANCY
                        selection_rationale = "Switched to alternative regimen to protect against known teratogenic risk in pregnancy."
                    elif "DOCUMENTED_ALLERGY" in first_line_issues:
                        regimen_type = RegimenType.ALTERNATIVE_ALLERGY
                        selection_rationale = f"Switched to alternative regimen due to documented drug allergy ({', '.join(allergies)})."
                    elif "SEVERE_RENAL_IMPAIRMENT" in first_line_issues:
                        regimen_type = RegimenType.ALTERNATIVE_RENAL
                        selection_rationale = f"Switched to alternative regimen due to severe renal impairment (eGFR {patient_egfr} mL/min)."
                else:
                    chosen_items = protocol.alternative_regimen
                    regimen_type = RegimenType.ALTERNATIVE_ALLERGY if "DOCUMENTED_ALLERGY" in first_line_issues else RegimenType.ALTERNATIVE_PREGNANCY
                    selection_rationale = f"Warning: Alternative regimen selected but patient exhibits overlapping contraindications ({', '.join(first_line_issues)})."
            else:
                selection_rationale = f"Alert: First-line regimen exhibits contraindications ({', '.join(first_line_issues)}) with no pre-defined alternative."

        # Build computed order items with pediatric weight adjustments and dose capping
        calculated_orders = []
        is_weight_valid = (patient_weight_kg is not None and patient_weight_kg > 0)

        for it in chosen_items:
            prescribed_dose = it.dose_adult
            dose_note = "Standard adult dose"

            if is_peds and it.pediatric_dose_mg_per_kg:
                if is_weight_valid:
                    calc_mg = round(it.pediatric_dose_mg_per_kg * patient_weight_kg, 1)

                    # Determine maximum allowable pediatric limit (from max_pediatric_dose or adult dose)
                    max_allowed_mg = None
                    if it.max_pediatric_dose:
                        m = re.search(r"(\d+(?:\.\d+)?)\s*(g|mg)", it.max_pediatric_dose, re.IGNORECASE)
                        if m:
                            val = float(m.group(1))
                            unit = m.group(2).lower()
                            max_allowed_mg = val * 1000.0 if unit == "g" else val

                    if max_allowed_mg is None and it.dose_adult:
                        m_adult = re.search(r"(\d+(?:\.\d+)?)\s*(g|mg)", it.dose_adult, re.IGNORECASE)
                        if m_adult:
                            val_a = float(m_adult.group(1))
                            unit_a = m_adult.group(2).lower()
                            max_allowed_mg = val_a * 1000.0 if unit_a == "g" else val_a

                    # Cap dose if it exceeds allowable clinical maximum
                    is_capped = False
                    if max_allowed_mg is not None and calc_mg > max_allowed_mg:
                        calc_mg = max_allowed_mg
                        is_capped = True

                    prescribed_dose = f"{calc_mg}mg"
                    dose_note = f"Pediatric weight-based dose ({it.pediatric_dose_mg_per_kg} mg/kg x {patient_weight_kg} kg)"
                    if is_capped:
                        dose_note += f" [Capped at maximum recommended limit {max_allowed_mg}mg]"
                    elif it.max_pediatric_dose:
                        dose_note += f" [Max: {it.max_pediatric_dose}]"
                else:
                    dose_note = "Weight not provided or non-positive; pediatric dose adjustment deferred."

            calculated_orders.append({
                "drug_name": it.drug_name,
                "prescribed_dose": prescribed_dose,
                "route": it.route,
                "frequency": it.frequency,
                "duration_days": it.duration_days,
                "instructions": it.instructions,
                "dose_rationale": dose_note
            })

        # Pre-screen generated regimen through NLEM Formulary Engine
        drug_names = [o["drug_name"] for o in calculated_orders]
        screen_res = global_nlem_formulary_engine.screen_prescription_regimen(
            drugs_prescribed=drug_names,
            patient_is_pregnant=bool(is_pregnant),
            patient_egfr=patient_egfr,
            patient_allergies=known_allergies
        )

        import uuid
        prescription_id = f"RX-PROT-{uuid.uuid4().hex[:10].upper()}"

        # Match Jan Aushadhi (PMBJP) Generic Equivalents
        jan_aushadhi_matches = []
        for o in calculated_orders:
            drug_clean = o["drug_name"].strip().lower()
            match = None
            for pmbjp_key, pmbjp_data in PMBJP_GENERIC_CATALOG.items():
                if pmbjp_key in drug_clean or drug_clean in pmbjp_key:
                    match = pmbjp_data
                    break
            if match:
                jan_aushadhi_matches.append({
                    "prescribed_drug": o["drug_name"],
                    "pmbjp_generic_name": match["generic_name"],
                    "pmbjp_drug_code": match["pmbjp_drug_code"],
                    "dosage_form": match["dosage_form"],
                    "pmbjp_mrp_inr": match["pmbjp_mrp_inr"],
                    "market_brand_mrp_inr": match["market_brand_mrp_inr"],
                    "estimated_savings_percent": match["estimated_patient_savings_percent"]
                })

        vernacular_guidance = generate_vernacular_guidance(protocol.disease_name, calculated_orders)

        return {
            "status": "GENERATED",
            "legal_status": "DRAFT_DECISION_SUPPORT_REQUIRES_PHYSICIAN_SIGNATURE",
            "statutory_disclaimer": "REQUIRES VERIFICATION AND DIGITAL SIGNATURE BY NMC REGISTERED MEDICAL PRACTITIONER (RMP) UNDER NMC ACT 2019. DISPENSING PROHIBITED WITHOUT PHYSICIAN SIGNATURE. DRAFT CLINICAL DECISION SUPPORT ONLY — NOT AN AUTONOMOUS PRESCRIPTION UNDER TELEMEDICINE PRACTICE GUIDELINES 2020.",
            "is_physician_signed": False,
            "signed_by_rmp": None,
            "prescription_id": prescription_id,
            "disease_key": protocol.disease_key,
            "disease_name": protocol.disease_name,
            "category": protocol.category,
            "regimen_type": regimen_type.value,
            "selection_rationale": selection_rationale,
            "patient_context": {
                "patient_age": patient_age,
                "is_pediatric": is_peds,
                "patient_weight_kg": patient_weight_kg,
                "patient_egfr": patient_egfr,
                "is_pregnant": is_pregnant,
                "known_allergies": known_allergies or []
            },
            "prescribed_items": calculated_orders,
            "mandatory_baseline_labs": protocol.mandatory_baseline_labs,
            "therapeutic_monitoring": protocol.therapeutic_monitoring,
            "urgent_interventions": protocol.urgent_interventions,
            "clinical_pearls": protocol.clinical_pearls,
            "vernacular_patient_guidance": vernacular_guidance,
            "jan_aushadhi_generic_equivalents": jan_aushadhi_matches,
            "formulary_safety_certification": {
                "safe_to_prescribe": screen_res.get("is_safe_to_dispense", True),
                "lethal_hard_stops": screen_res.get("lethal_violations", []),
                "clinical_warnings": screen_res.get("clinical_warnings", []),
                "ismp_high_alert_items": screen_res.get("high_alert_medications", [])
            }
        }


# Global singleton instance
global_prescription_protocol_engine = PrescriptionProtocolEngine()
