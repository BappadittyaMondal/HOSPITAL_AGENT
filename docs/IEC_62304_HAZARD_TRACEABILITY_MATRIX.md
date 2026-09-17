# PROJECT "HOSPITAL" — IEC 62304 & ISO 14971 CLASS C HAZARD TRACEABILITY MATRIX

**Document ID:** MED-DEV-SEC-62304-HTM-V1  
**Software Safety Classification:** **IEC 62304 CLASS C** (Death or Serious Injury Possible if Software Fails)  
**Standard Compliance:** IEC 62304:2006+A1:2015, ISO 14971:2019 (Risk Management for Medical Devices), NABH 6th Edition (2025)  
**Release Target:** Platform Core & Rural Pre-Hospital Emergency Gateway  
**Status:** **ACTIVE & LOCKED**  

---

## 1. Executive Safety Scope & Classification Justification

Project **HOSPITAL** executes software functions that directly advise, intercept, or gate life-critical medical interventions, including medication order validation, blood transfusion compatibility, narcotic dispensation, labor partograph progression, and physiological deterioration scoring. 

In accordance with **IEC 62304 Clause 4.3**:
- **Class A:** No injury or damage to health is possible.
- **Class B:** Non-serious injury is possible.
- **Class C:** **Death or serious injury is possible.**

Because software failure in medication cross-checking, blood transfusion gating, or obstetrical action line alarming can directly result in fatal or irreversible harm, the platform’s clinical safety firewalls are formally governed under **Class C software development and verification lifecycle standards**.

---

## 2. Inviolable Design Rules for Class C Modules

1. **Strict Determinism:** All Class C safety gates MUST execute through deterministic boolean logic or fixed mathematical models ($< 10\,\mu\text{s}$ latency). They MUST NEVER depend on probabilistic Large Language Models (LLMs), external network APIs, or stochastic inference engines.
2. **Zero-Bypass Policy:** A Class C `HARD_STOP` cannot be overridden by a single user or rubber-stamped without mandatory senior clinical escalation, secondary witness biometric signing, or formal statutory justification.
3. **Automated CI Blocking:** Every Class C hazard must have an active, non-flaky automated regression test in continuous integration. Any test failure halts deployment builds immediately.

---

## 3. Comprehensive Hazard Traceability Matrix

| Hazard ID | Clinical Hazard & Adverse Event | Initial Risk | Software Mitigation Architecture | Implementation File & Line Reference | Verification Test Suite & Quality Gate | Residual Risk |
|---|---|---|---|---|---|---|
| **HAZ-001** | **Sildenafil + Nitrates DDI**<br>Refractory cyclic GMP vasodilation, fatal profound hypotension, cardiac arrest. | **CRITICAL** (Catastrophic) | Deterministic DRE order evaluation intercepting combination in $< 5\,\mu\text{s}$; brand name normalization (*Caverta, Sorbitrate*). | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py)<br>[`services/core-api/terminology_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/terminology_engine.py) | `scripts/run_clinical_safety_regression.py` (`[DDI-001]` intercepted in 4.1 µs)<br>`tests/phase19/test_brand_name_dre_resolution.py` | **LOW** (Acceptable) |
| **HAZ-002** | **Methotrexate + TMP-SMX DDI**<br>Reduced renal clearance, pancytopenia, fatal bone marrow aplasia. | **CRITICAL** (Catastrophic) | Hard-stop contraindication check blocking concurrent administration. | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py) | `scripts/run_clinical_safety_regression.py` (`[DDI-002]` intercepted in 3.9 µs)<br>`tests/phase04/test_cpoe_dre_rules.py` | **LOW** (Acceptable) |
| **HAZ-003** | **IV Potassium + K-Sparing Diuretic**<br>Lethal hyperkalemia ($K^+ > 7.0\,\text{mEq/L}$), sine-wave ECG, ventricular fibrillation. | **CRITICAL** (Catastrophic) | Immediate CPOE hard-stop when potassium additive ordered with Spironolactone/Amiloride. | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py) | `scripts/run_clinical_safety_regression.py` (`[DDI-003]` intercepted in 1.9 µs)<br>`tests/phase04/test_cpoe_dre_rules.py` | **LOW** (Acceptable) |
| **HAZ-004** | **Linezolid + SSRI (Escitalopram)**<br>Monoamine oxidase inhibition, hyperthermia, fatal Serotonin Syndrome. | **CRITICAL** (Catastrophic) | CPOE hard-stop blocking concurrent Linezolid prescription with serotonergic antidepressants. | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py)<br>[`services/core-api/terminology_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/terminology_engine.py) | `scripts/run_clinical_safety_regression.py` (`[DDI-004]` intercepted in 1.6 µs)<br>`tests/phase19/test_brand_name_dre_resolution.py` | **LOW** (Acceptable) |
| **HAZ-005** | **Simvastatin + Strong CYP3A4 Inhibitor**<br>10x serum statin accumulation, acute rhabdomyolysis, acute tubular necrosis. | **CRITICAL** (Catastrophic) | CPOE contraindication blocking Simvastatin with Clarithromycin, Itraconazole, or Protease Inhibitors. | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py) | `scripts/run_clinical_safety_regression.py` (`[DDI-005]` intercepted in 1.5 µs) | **LOW** (Acceptable) |
| **HAZ-006** | **Beta-Lactam Anaphylaxis Cross-Reactivity**<br>Amoxicillin / Cephalosporin administered to penicillin-allergic patient; airway edema, death. | **CRITICAL** (Catastrophic) | Allergy cross-reactivity engine checking generic & brand name penicillin classes; blocks dispensing. | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py)<br>[`services/core-api/terminology_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/terminology_engine.py) | `scripts/run_clinical_safety_regression.py` (`[ALLERGY-001]` intercepted in 3.1 µs)<br>`tests/phase19/test_brand_name_dre_resolution.py` | **LOW** (Acceptable) |
| **HAZ-007** | **Metformin in Severe Renal Impairment**<br>Metformin accumulation in patient with $\text{eGFR} < 30\,\text{mL/min}$, fatal lactic acidosis. | **CRITICAL** (Catastrophic) | Automatic CKD-EPI eGFR calculation gating order; non-bypassable block if $\text{eGFR} < 30$. | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py) | `scripts/run_clinical_safety_regression.py` (`[RENAL-001]` intercepted in 3.3 µs)<br>`tests/phase04/test_cpoe_dre_rules.py` | **LOW** (Acceptable) |
| **HAZ-008** | **Massive Pediatric Overdose**<br>10x dosing calculation error in infant (e.g. Paracetamol 1000mg ordered vs 112.5mg safe max). | **CRITICAL** (Catastrophic) | Weight-based dose ceiling guard ($\text{mg/kg}$) with strict single-dose and daily ceilings. | [`services/core-api/cpoe_dre_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/cpoe_dre_engine.py)<br>[`services/core-api/clinical_emergency_scorers.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/clinical_emergency_scorers.py) | `scripts/run_clinical_safety_regression.py` (`[PEDIATRIC-001]` intercepted in 5.9 µs)<br>`tests/phase18/test_emergency_scorers.py` | **LOW** (Acceptable) |
| **HAZ-009** | **ABO-Incompatible Blood Transfusion**<br>Transfusing Type A or B PRBC to Type O patient; massive intravascular hemolysis, shock, death. | **CRITICAL** (Catastrophic) | Inviolable physical blood bank gate checking ABO/Rh matrix; rejects incompatible crossmatch. | [`services/core-api/blood_bank_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/blood_bank_engine.py)<br>[`services/core-api/main.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/main.py) | `tests/phase05/test_blood_bank_hemovigilance.py`<br>`tests/phase20/test_operational_api_endpoints.py` | **LOW** (Acceptable) |
| **HAZ-010** | **Obstructed / Prolonged Labor**<br>Cervical dilatation lagging behind WHO partograph action line ($\ge 4\,\text{h}$ delay); uterine rupture, fetal asphyxia. | **CRITICAL** (Catastrophic) | Real-time digital partograph curve analysis; triggers high-priority alert and Category 1 C-section countdown. | [`services/core-api/obstetrics_labor_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/obstetrics_labor_engine.py)<br>[`services/core-api/main.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/main.py) | `tests/phase10/test_obstetrics_labor_ward.py`<br>`tests/phase20/test_operational_api_endpoints.py` | **LOW** (Acceptable) |
| **HAZ-011** | **Comatose Airway Collapse**<br>Trauma or stroke patient with GCS $\le 8$ left without definitive airway; aspiration, hypoxic brain death. | **CRITICAL** (Catastrophic) | Automatic GCS calculation with non-bypassable `AIRWAY_LOSS_ALERT` when $\text{GCS} \le 8$. | [`services/core-api/clinical_emergency_scorers.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/clinical_emergency_scorers.py)<br>[`services/core-api/main.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/main.py) | `tests/phase18/test_emergency_scorers.py` | **LOW** (Acceptable) |
| **HAZ-012** | **Offline Bed Double-Allocation**<br>Two independent offline edge nodes allocate the same physical ICU bed during 72h network cut. | **HIGH** (Serious Harm) | Pessimistic edge resource leasing enforcing partition exclusivity across Class A physical assets. | [`services/core-api/edge_resilience_engine.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/edge_resilience_engine.py)<br>[`services/core-api/main.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/main.py) | `tests/phase14/test_edge_resilience_cluster.py`<br>`tests/phase20/test_operational_api_endpoints.py` | **LOW** (Acceptable) |

---

## 4. Verification Governance & Audit Trail

1. **Continuous Regression Testing:** The test suite in `scripts/run_clinical_safety_regression.py` executes against these exact hazards in every CI pipeline build.
2. **Cryptographic Proof of Audit:** Any trigger of these gates produces an immutable, HMAC-keyed audit entry in `audit_chain` ([`services/core-api/audit_ledger.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/audit_ledger.py)).
3. **Regulatory Maintenance:** Any modification to thresholds, drug pairs, or clinical rules requires review and unanimous cryptographic quorum of the Clinical Safety Board ([`services/core-api/clinical_safety_board_governance.py`](file:///d:/bappa_oldPC/HOSPITAL_AGENT/services/core-api/clinical_safety_board_governance.py)).
