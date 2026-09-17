#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18.2: RURAL PRE-HOSPITAL SYNDROMIC PROTOCOL ENGINE
====================================================================================================
Module: services/core-api/syndromic_protocol_engine.py
Purpose: Evidence-based emergency triage and 5-10 hour supportive holding care plan generator
         for remote rural healthcare centers where tertiary hospital transfer requires hours.
         Covers 8 Universal Syndromic Archetypes with deterministic safety firewalls, strict
         contraindication blacklists, and trilingual caregiver instructions (Bengali/Hindi/English).
Inviolable Rule: Deterministic clinical protocols precede any AI layer; every supportive medication
                 order is validated against CPOEDREEngine before issuance.
====================================================================================================
"""
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from cpoe_dre_engine import CPOEDREEngine


class SyndromicArchetype(str, Enum):
    ACUTE_CORONARY_SYNDROME = "ACUTE_CORONARY_SYNDROME"
    ACUTE_ISCHEMIC_STROKE = "ACUTE_ISCHEMIC_STROKE"
    ACUTE_RESPIRATORY_DISTRESS = "ACUTE_RESPIRATORY_DISTRESS"
    ACUTE_ABDOMEN_SURGICAL = "ACUTE_ABDOMEN_SURGICAL"
    SEPTIC_SHOCK_FEBRILE = "SEPTIC_SHOCK_FEBRILE"
    OBSTETRIC_EMERGENCY = "OBSTETRIC_EMERGENCY"
    TOXICOLOGY_SNAKEBITE = "TOXICOLOGY_SNAKEBITE"
    SEVERE_TRAUMA_FRACTURE = "SEVERE_TRAUMA_FRACTURE"


@dataclass
class BridgeMedicationOrder:
    drug_name: str
    dose_mg_or_units: float
    route: str
    frequency_or_timing: str
    safety_justification: str
    dre_status: str = "PENDING"
    dre_messages: List[str] = field(default_factory=list)


@dataclass
class HoldingCarePlan:
    plan_id: str
    patient_id: str
    syndrome: SyndromicArchetype
    urgency_tier: str  # RESUSCITATION, STAT_EMERGENT, URGENT_HOLD
    estimated_transit_hours: float
    primary_diagnostic_hypothesis: str
    supportive_medications: List[BridgeMedicationOrder]
    inviolable_blacklists: List[str]  # Absolute "DO NOT DO" rules
    monitoring_schedule_hourly: List[str]
    vernacular_caregiver_guidance: Dict[str, List[str]]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SyndromicProtocolEngine:
    """
    Deterministic rural pre-hospital emergency holding engine.
    Formulates safe 5-10 hour stabilization regimens prior to tertiary hospital transfer.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.dre = CPOEDREEngine(tenant_id=tenant_id)

    def generate_holding_plan(
        self,
        patient_id: str,
        syndrome: SyndromicArchetype,
        patient_age: int,
        is_female: bool,
        patient_weight_kg: float,
        vitals: Dict[str, float],
        current_medications: List[str],
        known_allergies: List[str],
        is_pregnant: bool = False,
        estimated_transit_hours: float = 6.0
    ) -> HoldingCarePlan:
        """
        Synthesizes an evidence-based supportive holding plan for the specific archetype,
        validating every proposed bridge medication through the DRE safety firewall.
        """
        plan_id = f"PLAN-HOLD-{uuid.uuid4().hex[:8].upper()}"

        plan = self._build_archetype_plan(
            plan_id=plan_id,
            patient_id=patient_id,
            syndrome=syndrome,
            patient_age=patient_age,
            is_female=is_female,
            patient_weight_kg=patient_weight_kg,
            vitals=vitals,
            is_pregnant=is_pregnant,
            estimated_transit_hours=estimated_transit_hours
        )

        # Run all proposed bridge medications through DRE
        safe_meds = []
        for med in plan.supportive_medications:
            eval_res = self.dre.evaluate_order(
                patient_id=patient_id,
                drug_name=med.drug_name,
                prescribed_dose=med.dose_mg_or_units,
                route=med.route,
                patient_weight_kg=patient_weight_kg,
                patient_bsa_m2=1.7,
                serum_creatinine=vitals.get("serum_creatinine", 1.0),
                patient_age=patient_age,
                is_female=is_female,
                current_medications=current_medications,
                known_allergies=known_allergies,
                is_pregnant=is_pregnant
            )

            med.dre_status = eval_res["status"]
            med.dre_messages = eval_res["hard_stops"] + eval_res["warnings"]

            # If BLOCKED by DRE, exclude or replace with safe alternative
            if eval_res["status"] != "BLOCKED":
                safe_meds.append(med)
            else:
                plan.inviolable_blacklists.append(
                    f"BLOCKED BY SAFETY FIREWALL: {med.drug_name} cancelled due to: {'; '.join(eval_res['hard_stops'])}"
                )

        plan.supportive_medications = safe_meds
        return plan

    def _build_archetype_plan(
        self,
        plan_id: str,
        patient_id: str,
        syndrome: SyndromicArchetype,
        patient_age: int,
        is_female: bool,
        patient_weight_kg: float,
        vitals: Dict[str, float],
        is_pregnant: bool,
        estimated_transit_hours: float
    ) -> HoldingCarePlan:
        sbp = vitals.get("systolic_bp", 120.0)
        spo2 = vitals.get("spo2", 98.0)

        meds: List[BridgeMedicationOrder] = []
        blacklists: List[str] = []
        monitoring: List[str] = []
        guidance: Dict[str, List[str]] = {"en": [], "bn": [], "hi": []}
        hypothesis = ""
        urgency = "STAT_EMERGENT"

        if syndrome == SyndromicArchetype.ACUTE_CORONARY_SYNDROME:
            hypothesis = "Acute Myocardial Infarction / Unstable Angina"
            urgency = "RESUSCITATION"
            # Aspirin 300mg chewable STAT
            meds.append(BridgeMedicationOrder(
                drug_name="Aspirin chewable",
                dose_mg_or_units=300.0,
                route="ORAL",
                frequency_or_timing="STAT once",
                safety_justification="Platelet COX-1 inhibition reduces acute coronary occlusion mortality"
            ))
            # Nitroglycerin sublingual only if SBP >= 90
            if sbp >= 100.0:
                meds.append(BridgeMedicationOrder(
                    drug_name="Nitroglycerin sublingual",
                    dose_mg_or_units=0.5,
                    route="SUBLINGUAL",
                    frequency_or_timing="Every 5 min PRN chest pain (max 3 doses)",
                    safety_justification="Coronary vasodilation and preload reduction"
                ))
            else:
                blacklists.append("DO NOT ADMINISTER NITROGLYCERIN: Systolic BP < 100 mmHg (severe shock hazard).")

            blacklists.extend([
                "DO NOT ALLOW PATIENT TO WALK OR EXERT: Strictly resting, stretcher transport.",
                "DO NOT GIVE INTRAMUSCULAR INJECTIONS: Thrombolysis / PCI hematoma risk."
            ])
            monitoring = [
                "Hourly: BP, Pulse, SpO2, Respiratory Rate, and Pain Score (1-10)",
                "Continuous cardiac rhythm monitoring if defibrillator/monitor available"
            ]
            guidance["en"] = [
                "Keep the patient sitting upright and calm. Do not let them walk.",
                "Chew the aspirin tablet completely before swallowing.",
                "Rush to the nearest hospital with an emergency heart unit."
            ]
            guidance["bn"] = [
                "রোগীকে সোজা বসিয়ে রাখুন এবং শান্ত রাখুন। হাঁটাচলা করতে দেবেন না।",
                "অ্যাসপিরিন ট্যাবলেটটি গিলে ফেলার আগে ভালো করে চিবিয়ে খেতে হবে।",
                "অবিলম্বে হার্ট কেয়ার সুবিধাযুক্ত হাসপাতালে নিয়ে যান।"
            ]
            guidance["hi"] = [
                "मरीज़ को सीधा बैठाकर रखें और शांत रखें। चलने न दें।",
                "एस्पिरिन की गोली को निगलने से पहले पूरी तरह चबा लें।",
                "तुरंत हृदय रोग सुविधा वाले अस्पताल ले जाएं।"
            ]

        elif syndrome == SyndromicArchetype.ACUTE_ISCHEMIC_STROKE:
            hypothesis = "Acute Stroke (FAST Positive, Cerebral Ischemia)"
            urgency = "RESUSCITATION"
            blacklists.extend([
                "DO NOT GIVE ASPIRIN OR ANTICOAGULANTS until non-contrast CT head rules out hemorrhagic stroke.",
                "DO NOT LOWER BLOOD PRESSURE AGGRESSIVELY: Permissive hypertension required for cerebral perfusion unless SBP > 220 mmHg.",
                "STRICT NPO (Nothing by Mouth): High aspiration pneumonitis risk due to impaired gag reflex."
            ])
            monitoring = [
                "Hourly: Glasgow Coma Scale (GCS), Pupillary size/reaction, Blood Glucose, Blood Pressure",
                "Maintain head elevation at 30 degrees; turn patient every 2 hours to protect skin"
            ]
            guidance["en"] = [
                "Do NOT give any water, food, or medicines by mouth (danger of choking).",
                "Keep patient lying on their side to prevent choking on saliva.",
                "Note the exact minute symptoms started; this is vital for emergency clot-dissolving medicine."
            ]
            guidance["bn"] = [
                "মুখে কোনো জল, খাবার বা ওষুধ দেবেন না (শ্বাসরোধের বিপদ)।",
                "লালা যাতে শ্বাসনালীতে না যায় সেজন্য রোগীকে একদিকে কাত করে শোওয়ান।",
                "লক্ষণগুলো ঠিক কখন শুরু হয়েছে সেই সঠিক সময় লিখে রাখুন।"
            ]
            guidance["hi"] = [
                "मुंह से कोई पानी, खाना या दवाई न दें (दम घुटने का खतरा)।",
                "मरीज़ को एक करवट लिटाकर रखें ताकि लार सांस की नली में न जाए।",
                "लक्षण शुरू होने का सही समय नोट करें, यह अस्पताल में इलाज के लिए जरूरी है।"
            ]

        elif syndrome == SyndromicArchetype.SEVERE_TRAUMA_FRACTURE:
            hypothesis = "Major Skeletal Trauma / Femoral Fracture"
            urgency = "STAT_EMERGENT"
            # Paracetamol IV/Oral
            meds.append(BridgeMedicationOrder(
                drug_name="Paracetamol",
                dose_mg_or_units=1000.0 if patient_weight_kg >= 50 else (patient_weight_kg * 15.0),
                route="IV" if vitals.get("vomiting_active", False) else "ORAL",
                frequency_or_timing="Every 6 hours PRN pain",
                safety_justification="Safe central analgesia with zero nephrotoxicity or platelet inhibition"
            ))
            # Blacklist NSAIDs in elderly or bleeding
            if patient_age >= 65:
                blacklists.append(
                    "DO NOT ADMINISTER NSAIDs (Ibuprofen, Diclofenac, Ketorolac): Extreme Acute Kidney Injury and GI bleeding risk in geriatric trauma."
                )
            blacklists.extend([
                "DO NOT MANIPULATE OR ATTEMPT TO SET THE FRACTURE: Apply splint in position found.",
                "DO NOT APPLY HEAT OR VIGOROUS MASSAGE to injured limb."
            ])
            monitoring = [
                "Every 2 hours: Check peripheral pulses (Dorsalis Pedis), capillary refill (< 2s), and toe sensation",
                "Hourly: Heart rate and blood pressure for early hypovolemic shock detection"
            ]
            guidance["en"] = [
                "Keep the injured leg completely still. Support both sides with folded blankets or splints.",
                "Check that the toes remain warm and pink. If they turn blue or cold, loosen bandages slightly.",
                "Transport gently on a firm stretcher without bending the hip."
            ]
            guidance["bn"] = [
                "আহত পা একদম নাড়াচাড়া করবেন না। দুপাশে তোয়ালে বা কাঠের তক্তা দিয়ে সোজা বেঁধে রাখুন।",
                "পায়ের আঙুল গরম ও স্বাভাবিক আছে কিনা দেখুন। নীল বা ঠান্ডা হলে বাঁধন হালকা আলগা করুন।",
                "শক্ত স্ট্রেচারে সাবধানে স্থানান্তর করুন, কোমর বাঁকাবেন না।"
            ]
            guidance["hi"] = [
                "चोट लगे पैर को बिल्कुल न हिलाएं। दोनों तरफ तकिया या पटरी लगाकर स्थिर रखें।",
                "पैर की उंगलियां गर्म हैं या नहीं देखते रहें। उंगलियां नीली पड़ें तो पट्टी हल्की ढीली करें।",
                "मरीज़ को सख्त स्ट्रेचर पर बिना मोड़े सावधानी से ले जाएं।"
            ]

        elif syndrome == SyndromicArchetype.TOXICOLOGY_SNAKEBITE:
            hypothesis = "Suspected Venomous Snakebite Envenomation"
            urgency = "RESUSCITATION"
            blacklists.extend([
                "STRICTLY FORBIDDEN: DO NOT APPLY ARTERIAL TOURNIQUETS (causes ischemic gangrene).",
                "STRICTLY FORBIDDEN: DO NOT CUT, INCISE, OR SUCK THE BITE WOUND.",
                "DO NOT APPLY HERBAL PASTES, CHEMICALS, ICE, OR ELECTRIC SHOCKS.",
                "DO NOT ADMINISTER NSAIDs: Exacerbates hemotoxic venom coagulopathy and internal bleeding."
            ])
            monitoring = [
                "Every 30 minutes: 20-Minute Whole Blood Clotting Test (20WBCT) - if blood does not clot, systemic coagulopathy is present",
                "Every 30 minutes: Assess for ptosis (drooping eyelids), difficulty swallowing, or shallow breathing (neurotoxic signs)"
            ]
            guidance["en"] = [
                "Keep the patient calm and completely still. Movement spreads venom rapidly.",
                "Immobilize the bitten limb with a splint at heart level, exactly like a fractured limb.",
                "Rush to the hospital immediately for Anti-Snake Venom (ASV)."
            ]
            guidance["bn"] = [
                "রোগীকে সম্পূর্ণ শান্ত ও স্থির রাখুন। হাঁটাচলা করলে বিষ দ্রুত সারা শরীরে ছড়ায়।",
                "কামড়ানো অঙ্গটি ভাঙা হাড়ের মতো তক্তা দিয়ে বেঁধে বুকের সমান স্তরে রাখুন।",
                "দড়ি বা বাঁধন দেবেন না, ক্ষতস্থানে কাটবেন না। অবিলম্বে এন্টিভেনমযুক্ত হাসপাতালে নিয়ে যান।"
            ]
            guidance["hi"] = [
                "मरीज़ को बिल्कुल शांत और स्थिर रखें। हिलने-डुलने से ज़हर तेजी से फैलता है।",
                "काटे गए अंग को टूटी हड्डी की तरह पटरी बांधकर दिल के स्तर पर रखें।",
                "रस्सी या कसकर पट्टी न बांधें, चीरा न लगाएं। तुरंत एंटी-स्नेक वेनम वाले अस्पताल ले जाएं।"
            ]

        elif syndrome == SyndromicArchetype.ACUTE_ABDOMEN_SURGICAL:
            hypothesis = "Acute Surgical Abdomen / Peritonitis / Bowel Obstruction"
            urgency = "STAT_EMERGENT"
            blacklists.extend([
                "STRICT NPO (Nothing by Mouth): Absolutely no food, water, tea, or oral medicine.",
                "DO NOT ADMINISTER OPIOIDS OR ORAL ANALGESICS that mask acute surgical peritoneal signs.",
                "DO NOT GIVE LAXATIVES OR ENEMAS: High risk of bowel perforation in appendicitis/obstruction."
            ])
            monitoring = [
                "Hourly: Pulse, BP, Abdominal Girth, and temperature",
                "Monitor for progressive abdominal rigidity, guarding, or vomiting"
            ]
            guidance["en"] = [
                "Do NOT give anything to eat or drink, not even a sip of water.",
                "Keep patient lying with knees bent slightly to ease belly tension.",
                "Transport immediately to a hospital with an active operating theater."
            ]
            guidance["bn"] = [
                "এক ফোঁটা জল বা কোনো খাবার মুখে দেবেন না।",
                "রোগীকে হাঁটু সামান্য ভাঁজ করে শুইয়ে রাখুন যাতে পেটের চাপ কমে।",
                "জরুরি সার্জারি সুবিধা সম্পন্ন হাসপাতালে দ্রুত নিয়ে যান।"
            ]
            guidance["hi"] = [
                "मरीज़ को एक घूंट पानी या कोई खाना बिल्कुल न दें।",
                "मरीज़ के घुटनों को थोड़ा मोड़कर लिटाएं ताकि पेट का तनाव कम हो।",
                "तुरंत ऑपरेशन की सुविधा वाले अस्पताल ले जाएं।"
            ]

        elif syndrome == SyndromicArchetype.SEPTIC_SHOCK_FEBRILE:
            hypothesis = "Severe Sepsis / Early Septic Shock"
            urgency = "RESUSCITATION"
            # Broad spectrum empiric antibiotic bridge
            meds.append(BridgeMedicationOrder(
                drug_name="Ceftriaxone",
                dose_mg_or_units=2000.0,
                route="IV",
                frequency_or_timing="STAT once",
                safety_justification="Empiric broad-spectrum coverage for severe bacterial sepsis"
            ))
            # Paracetamol for high fever
            meds.append(BridgeMedicationOrder(
                drug_name="Paracetamol",
                dose_mg_or_units=1000.0 if patient_weight_kg >= 50 else (patient_weight_kg * 15.0),
                route="ORAL" if sbp >= 90 else "IV",
                frequency_or_timing="Every 6 hours PRN fever > 38.5C",
                safety_justification="Fever and metabolic workload reduction"
            ))
            monitoring = [
                "Hourly: Blood pressure (alert if SBP < 90), Heart rate, Respiratory rate",
                "Track urine output: Alert if < 30 mL/hour"
            ]
            guidance["en"] = [
                "Keep patient warm and hydrated if able to swallow, or start IV fluid drip.",
                "Sepsis is a medical emergency requiring urgent intravenous antibiotics in hospital."
            ]
            guidance["bn"] = [
                "রোগীকে উষ্ণ রাখুন। রক্তচাপ কমে গেলে দ্রুত স্যালাইন চালু করা প্রয়োজন।",
                "এটি তীব্র ব্যাকটেরিয়াল ইনফেকশন, দ্রুত হাসপাতালে শিরায় অ্যান্টিবায়োটিক দরকার।"
            ]
            guidance["hi"] = [
                "मरीज़ को गर्म रखें। तुरंत अस्पताल में नसों द्वारा एंटीबायोटिक की जरूरत है।"
            ]

        elif syndrome == SyndromicArchetype.OBSTETRIC_EMERGENCY:
            hypothesis = "Obstetric Hemorrhage (PPH) or Severe Eclampsia"
            urgency = "RESUSCITATION"
            # Misoprostol 800mcg sublingual for PPH
            meds.append(BridgeMedicationOrder(
                drug_name="Misoprostol",
                dose_mg_or_units=0.8, # 800 mcg
                route="SUBLINGUAL",
                frequency_or_timing="STAT once",
                safety_justification="Potent uterotonic contraction to arrest postpartum hemorrhage"
            ))
            blacklists.extend([
                "DO NOT ALLOW SUPINE POSITION: Maintain 15-30 degree left-lateral tilt.",
                "DO NOT DELAY TRANSFER for non-essential local interventions."
            ])
            monitoring = [
                "Every 15 min: Uterine firmness check (fundal massage), Pad count for blood loss",
                "Every 30 min: Maternal blood pressure and pulse"
            ]
            guidance["en"] = [
                "Place mother on her left side immediately to ensure blood flow to baby and heart.",
                "Massage the lower belly firmly to keep the womb contracted and stop bleeding.",
                "Rush to an emergency maternity center with blood transfusion facilities."
            ]
            guidance["bn"] = [
                "প্রসূতি মাকে অবিলম্বে বাঁ দিকে কাত করে শোওয়ান।",
                "রক্তপাত কমাতে তলপেটে আলতো করে ম্যাসাজ করে জরায়ু শক্ত রাখুন।",
                "অবিলম্বে ব্লাড ব্যাংক ও প্রসূতি বিশেষজ্ঞযুক্ত হাসপাতালে স্থানান্তর করুন।"
            ]
            guidance["hi"] = [
                "मां को तुरंत बाईं करवट लिटाएं।",
                "रक्तस्राव रोकने के लिए पेट के निचले हिस्से की मालिश करें।",
                "तुरंत ब्लड बैंक वाले प्रसूति अस्पताल ले जाएं।"
            ]

        elif syndrome == SyndromicArchetype.ACUTE_RESPIRATORY_DISTRESS:
            hypothesis = "Acute Hypoxic Respiratory Distress / Severe Bronchospasm"
            urgency = "RESUSCITATION"
            blacklists.extend([
                "DO NOT ALLOW PATIENT TO LIE FLAT (Orthopnea precipitating respiratory arrest).",
                "DO NOT ADMINISTER SEDATIVES OR OPIOIDS that suppress respiratory drive."
            ])
            monitoring = [
                "Every 15 min: SpO2, Respiratory rate, use of accessory breathing muscles",
                "Monitor for mental confusion or somnolence signaling acute hypercapnia"
            ]
            guidance["en"] = [
                "Keep the patient sitting upright at 90 degrees.",
                "Deliver oxygen through face mask or open ambulance windows to maximize airflow.",
                "Rush to hospital with mechanical ventilation capabilities."
            ]
            guidance["bn"] = [
                "রোগীকে সোজা ৯০ ডিগ্রি কোণে বসিয়ে রাখুন। শোওয়াবেন না।",
                "মাস্ক দিয়ে অক্সিজেন দিন অথবা প্রচুর বাতাস চলাচল করতে দিন।",
                "জরুরি ভেন্টিলেটর সুবিধাযুক্ত হাসপাতালে নিয়ে যান।"
            ]
            guidance["hi"] = [
                "मरीज़ को सीधा ९० डिग्री बैठाकर रखें। लेटने न दें।",
                "ऑक्सीजन दें और ताजी हवा आने दें। तुरंत वेंटिलेटर वाले अस्पताल ले जाएं।"
            ]

        return HoldingCarePlan(
            plan_id=plan_id,
            patient_id=patient_id,
            syndrome=syndrome,
            urgency_tier=urgency,
            estimated_transit_hours=estimated_transit_hours,
            primary_diagnostic_hypothesis=hypothesis,
            supportive_medications=meds,
            inviolable_blacklists=blacklists,
            monitoring_schedule_hourly=monitoring,
            vernacular_caregiver_guidance=guidance
        )
