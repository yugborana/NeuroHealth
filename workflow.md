# NeuroHealth — Complete Workflow Walkthrough

> Tracing **three hard scenarios** through the entire 16-agent pipeline. Each user query includes medications, allergies, medical history, and demographics to fully exercise the Drug Interaction Agent, Contraindication Agent, Risk Adjustment, and Feedback Loop.

## Scenario A: 🟢 ROUTINE — Migraine in a Complex Patient

### User Query
> *"I've had a throbbing headache on one side for the past 6 hours with nausea and sensitivity to light. I am 34 years old, female. I take Sertraline (an antidepressant) and birth control pills. I am allergic to aspirin. I have a history of migraines and anxiety."*

---

### Layer 1: Input Understanding

#### I1 — Intent Classifier
| Field | Value |
|-------|-------|
| **Input** | Full user text |
| **Output** | `{intent: "symptom_check", confidence: 0.93}` |

#### I2 — Symptom Extractor
| Field | Value |
|-------|-------|
| **Output** | `{symptoms: ["headache", "nausea", "sensitivity to light"], duration: "6 hours", severity: "moderate"}` |

#### I3 — Ontology Normalizer
| Field | Value |
|-------|-------|
| **DB Used** | **DB 3: Ontology Map** |
| **SQL** | `SELECT snomed_code, icd10_code FROM ontology_terms WHERE term IN ('headache', 'nausea', 'photophobia')` |

**DB 3 Returns:**

| term | SNOMED | ICD-10 |
|------|--------|--------|
| headache | 25064002 | R51 |
| nausea | 422587007 | R11.0 |
| photophobia | 409668002 | H53.14 |

| Field | Value |
|-------|-------|
| **Output** | `{normalized: [{term: "headache", SNOMED: "25064002"}, {term: "nausea", SNOMED: "422587007"}, {term: "photophobia", SNOMED: "409668002"}]}` |

#### I4 — Context Extractor
| Field | Value |
|-------|-------|
| **DB Used** | **DB 4: User Profile** (writes) |
| **Output** | `{age: 34, gender: "female", history: ["migraines", "anxiety"], medications: ["sertraline", "birth control pills"], allergies: ["aspirin"]}` |

---

### Layer 2: Knowledge Retrieval (Parallel)

#### K1 — Medical Knowledge Agent
| Field | Value |
|-------|-------|
| **DB Used** | **DB 1: Medical KB** |
| **SQL** | `SELECT c.name, SUM(csm.importance) AS score FROM conditions c JOIN condition_symptom_map csm ON ... WHERE csm.snomed_code IN ('25064002','422587007','409668002') GROUP BY c.name ORDER BY score DESC` |

**DB 1 Returns:**

| condition | urgency | match_score |
|-----------|---------|-------------|
| Migraine with aura | routine | 2.1 |
| Tension headache | routine | 0.9 |
| Meningitis | emergency | 0.6 |

#### K4 — Vector RAG Agent
| Field | Value |
|-------|-------|
| **DB Used** | **DB 2: Vector Store** |
| **Query** | `"throbbing headache one side nausea light sensitivity"` |
| **Top Results** | 1. "Mayo Clinic: Migraine" (0.93), 2. "AHS: Migraine Treatment Guidelines" (0.88), 3. "NICE: Headache Management" (0.81) |

#### K2 — Drug Interaction Agent ⚠️ KEY AGENT HERE
| Field | Value |
|-------|-------|
| **DB Used** | **DB 1: Medical KB** (drug_interactions table) |
| **Input** | `{medications: ["sertraline", "birth control pills"]}` |
| **SQL** | `SELECT * FROM drug_interactions WHERE drug_name IN ('sertraline', 'birth control pills')` |

**DB 1 Returns — The Blacklist:**

| drug | interacts_with | severity | description |
|------|---------------|----------|-------------|
| sertraline | **triptans** (sumatriptan) | **MAJOR** | Serotonin Syndrome risk — potentially fatal |
| sertraline | **tramadol** | major | Serotonin Syndrome risk |
| sertraline | NSAIDs (ibuprofen) | moderate | Increased GI bleeding risk |

**K2 Output:** `{interactions: [{drug: "sertraline", interacts_with: "triptans", severity: "major", description: "Serotonin Syndrome"}, {drug: "sertraline", interacts_with: "ibuprofen", severity: "moderate", description: "GI bleeding risk"}]}`

> This blacklist is now ready and waiting for the Safety Layer.

---

### Layer 3: Clinical Reasoning

#### R1 — Differential Diagnosis

| Condition | symptom_match | risk_factor | history_weight | **Score** |
|-----------|:---:|:---:|:---:|:---:|
| Migraine with aura | 0.84 | 0.10 | 0.90 (history of migraines) | **0.57** |
| Tension headache | 0.36 | 0.05 | 0.20 | **0.20** |
| Meningitis | 0.24 | 0.05 | 0.00 | **0.11** |

**Output:** `{top_condition: "Migraine with aura", score: 0.57, confidence: 0.87}`

#### R2 — Urgency Scoring
**Rules checked:**
- ❌ No emergency keywords
- ❌ No high-risk symptom combos (no neck stiffness, no fever → rules out meningitis)
- ✅ History of migraines + typical presentation = **ROUTINE**

**Output:** `{urgency: "routine", confidence: 0.87, reason: "Typical migraine presentation in patient with migraine history"}`

#### R3 — Treatment Suggestion
| Field | Value |
|-------|-------|
| **DB Used** | **DB 1: Medical KB** |
| **SQL** | `SELECT recommendation, self_care FROM treatment_guidelines WHERE condition_id = 'MIGRAINE_001'` |

**DB 1 Returns the STANDARD treatment:**
```json
{
  "recommendation": "Rest in a dark, quiet room",
  "self_care": [
    "Take Sumatriptan (triptan) for acute relief",
    "Take Ibuprofen as backup pain relief",
    "Apply cold compress to forehead",
    "Stay hydrated"
  ]
}
```

> ⚠️ Notice: The standard treatment includes **Sumatriptan** and **Ibuprofen**. Both are dangerous for this specific user!

---

### Layer 4: Safety (Parallel)

#### S1 — Emergency Detection
| Check | Result |
|-------|--------|
| Emergency keyword scan | `{emergency: false}` |
| Emergency rule match | No match |

#### S2 — Contraindication Agent ⚠️ CRITICAL HERE
This agent receives **two inputs simultaneously:**
1. **From R3:** The proposed treatment → `["Sumatriptan", "Ibuprofen", "cold compress", "hydration"]`
2. **From K2:** The drug blacklist → `["sertraline + triptans = MAJOR", "sertraline + ibuprofen = moderate"]`
3. **From DB 4:** The user's allergies → `["aspirin"]`

**S2's decision process:**

| Proposed Treatment | Check Against K2 Blacklist | Check Against Allergies | Decision |
|-------------------|--------------------------|------------------------|----------|
| Sumatriptan (triptan) | ✅ MATCH: sertraline + triptans = **MAJOR** (Serotonin Syndrome) | — | 🚫 **BLOCKED** |
| Ibuprofen | ✅ MATCH: sertraline + ibuprofen = moderate (GI bleeding) | Also: aspirin allergy → NSAID cross-reactivity risk | 🚫 **BLOCKED** |
| Cold compress | No match | No match | ✅ Safe |
| Stay hydrated | No match | No match | ✅ Safe |

**S2 Output:**
```json
{
  "blocked": [
    "Sumatriptan — BLOCKED: Serotonin Syndrome risk with Sertraline (MAJOR)",
    "Ibuprofen — BLOCKED: GI bleeding risk with Sertraline + aspirin allergy (NSAID cross-reactivity)"
  ],
  "warnings": ["Consider Acetaminophen (Tylenol) as alternative pain relief"],
  "safe_suggestions": ["Cold compress", "Stay hydrated"]
}
```

#### S3 — Uncertainty Detector
| Field | Value |
|-------|-------|
| **Confidence** | 0.87 > threshold 0.6 |
| **Output** | `{uncertain: false}` |

---

### 🔀 Safety Router Decision: **ROUTINE**

```
SR reads: emergency=false, blocked=2 items, uncertain=false, urgency=routine
Decision → ROUTE TO PERSONALIZATION (carry the blocked list forward)
```

---

### Layer 5: Personalization

#### P1 — Risk Adjustment
| Field | Value |
|-------|-------|
| **DB Used** | **DB 4: User Profile** |
| **Input** | Age 34, history of migraines, female, on birth control |
| **Action** | Birth control + migraines with aura = slightly elevated stroke risk (clinical guideline). Adds risk note. |
| **Output** | `{adjusted_urgency: "routine", risk_multiplier: 1.2, risk_note: "Migraine with aura + oral contraceptives: discuss stroke risk with your doctor at next visit"}` |

#### P2 — Lifestyle Recommendation
**Output:** `{tips: ["Keep a migraine diary to identify triggers", "Maintain regular sleep schedule", "Reduce screen time during episodes", "Magnesium-rich foods may reduce frequency"]}`

#### K3 — Specialist Directory
| Field | Value |
|-------|-------|
| **DB Used** | **DB 1** |
| **SQL** | `SELECT specialist_type FROM specialist_directory WHERE condition_ids @> '{MIGRAINE_001}'` |
| **Output** | `{specialist: "Neurologist", condition: "Migraine with aura"}` |

---

### Layer 6: Output

#### O1 — Explanation Generator
```
🩺 Health Assessment

Your symptoms — throbbing one-sided headache with nausea and
light sensitivity — are consistent with a migraine with aura.
Given your history of migraines, this is a recognized pattern.
Urgency: Routine.

💊 Safe Recommendations:
  • Rest in a dark, quiet room
  • Apply a cold compress to your forehead
  • Stay hydrated
  • Take Acetaminophen (Tylenol) for pain relief

🚫 Safety Alerts (2 treatments blocked):
  ❌ Sumatriptan: BLOCKED — You take Sertraline. Combining
     triptans with SSRIs risks Serotonin Syndrome (potentially
     fatal). Do NOT take triptans without doctor approval.
  ❌ Ibuprofen: BLOCKED — You take Sertraline (GI bleeding
     risk) AND you are allergic to aspirin (NSAID
     cross-reactivity). Use Acetaminophen instead.

⚠️ Important Note:
  Migraine with aura + oral contraceptives carries a slightly
  elevated stroke risk. Please discuss this with your
  neurologist at your next visit.

🥗 Lifestyle Tips:
  • Keep a migraine diary to identify triggers
  • Maintain regular sleep schedule
  • Magnesium-rich foods may reduce frequency

📚 Sources:
  1. Mayo Clinic — Migraine
  2. AHS — Migraine Treatment Guidelines
  3. NICE — Headache Management in Adults

⚠️ This is not a diagnosis.
   Confidence: 87% | Session ID: routine-migraine-001
```

#### O2 — Appointment Scheduler
K3 found "Neurologist" → O2 activates:
```
📅 Specialist Available

Dr. Sharma (Neurologist)
Monday, March 17 at 3:00 PM
[Book Now]  [See Other Slots]
```

#### O3 — Follow-up Agent
Sets: *"Check in after 24 hours: Has the migraine resolved? Did Acetaminophen help?"*

---
---

## Scenario B: 🟡 URGENT — Diabetic Patient with Kidney Issues and Fever

### User Query
> *"I have a burning sensation when I urinate, lower back pain on the right side, and a fever of 101°F for 2 days. I'm 58, male. I take Metformin for type 2 diabetes and Lisinopril for blood pressure. I am allergic to Sulfa drugs. I have a history of chronic kidney disease stage 2."*

---

### Layer 1: Input Understanding

| Agent | Key Output |
|-------|-----------|
| **I1** | `{intent: "symptom_check", confidence: 0.94}` |
| **I2** | `{symptoms: ["burning urination", "lower back pain", "fever"], duration: "2 days", severity: "moderate"}` |
| **I3** | DB 3 → `[{dysuria, 49650001}, {flank pain, 274743004}, {fever, 386661006}]` |
| **I4** | DB 4 write → `{age: 58, gender: "male", history: ["type 2 diabetes", "CKD stage 2"], medications: ["metformin", "lisinopril"], allergies: ["sulfa drugs"]}` |

---

### Layer 2: Knowledge Retrieval (Parallel)

#### K1 — Medical Knowledge Agent
**DB 1 Returns:**

| condition | urgency | match_score |
|-----------|---------|-------------|
| Pyelonephritis (kidney infection) | urgent | 2.3 |
| UTI (lower urinary tract) | routine | 1.5 |
| Kidney stones | urgent | 1.0 |

#### K4 — Vector RAG Agent
**DB 2 Returns:** "AUA: UTI Guidelines" (0.91), "NICE: Pyelonephritis Management" (0.87), "ADA: Infections in Diabetic Patients" (0.83)

#### K2 — Drug Interaction Agent ⚠️
**Input:** `{medications: ["metformin", "lisinopril"]}`
**SQL:** `SELECT * FROM drug_interactions WHERE drug_name IN ('metformin', 'lisinopril')`

**DB 1 Returns — The Blacklist:**

| drug | interacts_with | severity | description |
|------|---------------|----------|-------------|
| metformin | **contrast dye** | major | Lactic acidosis if kidneys can't clear it |
| metformin | alcohol | moderate | Hypoglycemia risk |
| lisinopril | **potassium supplements** | major | Hyperkalemia (dangerous high potassium) |
| lisinopril | **NSAIDs** (ibuprofen) | major | Reduces kidney function further |

**K2 Output:** `{interactions: [{drug: "lisinopril", interacts_with: "NSAIDs", severity: "major", description: "Worsens CKD"}, {drug: "metformin", interacts_with: "contrast dye", severity: "major"}]}`

---

### Layer 3: Clinical Reasoning

#### R1 — Differential Diagnosis

| Condition | symptom_match | risk_factor | history_weight | **Score** |
|-----------|:---:|:---:|:---:|:---:|
| Pyelonephritis | 0.92 | 0.70 (diabetes + CKD) | 0.50 | **0.73** |
| UTI | 0.60 | 0.30 | 0.20 | **0.38** |
| Kidney stones | 0.40 | 0.20 | 0.30 | **0.30** |

#### R2 — Urgency Scoring
**Rules checked:**
- ✅ Fever + flank pain + diabetes + CKD = **URGENT** (kidney infection in compromised patient)
- Not emergency because vitals are stable and patient is communicating normally

**Output:** `{urgency: "urgent", confidence: 0.88, reason: "Probable pyelonephritis in diabetic patient with CKD — needs antibiotics within 24 hours"}`

#### R3 — Treatment Suggestion
**DB 1 Query:** `SELECT treatment FROM guidelines WHERE condition = 'Pyelonephritis' AND urgency = 'urgent'`

**Standard treatment returned:**
```json
{
  "recommendation": "See a doctor within 24 hours — likely needs antibiotics",
  "self_care": [
    "Take Trimethoprim-Sulfamethoxazole (Bactrim) if prescribed",
    "Take Ibuprofen for pain and fever",
    "Drink plenty of water to flush bacteria",
    "Apply heating pad to lower back"
  ]
}
```

> ⚠️ The standard treatment includes **Bactrim (a Sulfa drug)** and **Ibuprofen** — both are dangerous for this user!

---

### Layer 4: Safety (Parallel)

#### S1 — Emergency Detection
`{emergency: false}` — No immediate danger signs (no sepsis markers)

#### S2 — Contraindication Agent ⚠️ CRITICAL

| Proposed Treatment | K2 Blacklist Check | Allergy Check | CKD Check | Decision |
|-------------------|-------------------|---------------|-----------|----------|
| Bactrim (TMP-SMX) | — | ✅ **Sulfa allergy** | Also risky with CKD | 🚫 **BLOCKED** |
| Ibuprofen | ✅ **lisinopril + NSAIDs = MAJOR** (worsens kidney) | — | ✅ CKD stage 2 = avoid NSAIDs | 🚫 **BLOCKED** |
| Drink water | — | — | — | ✅ Safe |
| Heating pad | — | — | — | ✅ Safe |

**S2 Output:**
```json
{
  "blocked": [
    "Bactrim (TMP-SMX) — BLOCKED: Patient has Sulfa drug allergy",
    "Ibuprofen — BLOCKED: lisinopril + NSAID = worsens kidney function (MAJOR) + CKD stage 2"
  ],
  "warnings": [
    "Alternative antibiotics: Ciprofloxacin or Amoxicillin-Clavulanate (doctor to decide)",
    "Alternative pain relief: Acetaminophen (kidney-safe at standard doses)"
  ]
}
```

#### S3 — Uncertainty Detector
`{uncertain: false}` — Confidence 0.88 > 0.6

---

### 🔀 Safety Router Decision: **URGENT**

```
SR reads: emergency=false, blocked=2 items, uncertain=false, urgency=urgent
Decision → ROUTE TO PERSONALIZATION
```

---

### Layer 5: Personalization

#### P1 — Risk Adjustment
| Field | Value |
|-------|-------|
| **Input** | Age 58, male, diabetes, CKD stage 2 |
| **Action** | Diabetes + CKD + kidney infection = **HIGH RISK** patient. Kidney infections can rapidly progress to sepsis in diabetics. Bumps urgency note. |
| **Output** | `{adjusted_urgency: "urgent", risk_multiplier: 1.8, risk_note: "Diabetic + CKD: kidney infections can escalate to sepsis rapidly. See doctor TODAY, not tomorrow."}` |

#### P2 — Lifestyle Recommendation
**Output:** `{tips: ["Monitor blood sugar closely — infections cause spikes in diabetics", "Track urine color — dark/cloudy = worsening", "Avoid dehydration — critical for CKD patients"]}`

#### K3 — Specialist Directory
**Output:** `{specialist: "Urologist or Nephrologist", condition: "Pyelonephritis + CKD"}`

---

### Layer 6: Output

#### O1 — Explanation Generator
```
🩺 Health Assessment

Your symptoms — burning urination, right-sided lower back
pain, and fever (101°F) for 2 days — strongly suggest a
kidney infection (pyelonephritis). Urgency: URGENT.

Because you have diabetes and CKD stage 2, kidney infections
can escalate to sepsis more rapidly. Please see a doctor TODAY.

💊 Safe Recommendations:
  • Take Acetaminophen (Tylenol) for pain and fever
  • Drink plenty of water to help flush bacteria
  • Apply a heating pad to your lower back for comfort
  • Monitor your blood sugar closely — infections cause spikes

🚫 Safety Alerts (2 treatments blocked):
  ❌ Bactrim (TMP-SMX): BLOCKED — You have a Sulfa drug allergy.
     Your doctor will prescribe an alternative antibiotic
     (e.g., Ciprofloxacin or Amoxicillin-Clavulanate).
  ❌ Ibuprofen: BLOCKED — You take Lisinopril. NSAIDs + ACE
     inhibitors severely worsen kidney function, especially
     with your CKD stage 2. Use Acetaminophen instead.

⚠️ CKD Alert:
  If your doctor orders imaging with contrast dye, remind them
  you take Metformin — it may need to be paused temporarily
  to prevent lactic acidosis.

📚 Sources:
  1. AUA — Urinary Tract Infection Guidelines
  2. NICE — Pyelonephritis Management
  3. ADA — Managing Infections in Diabetic Patients

⚠️ This is not a diagnosis.
   Confidence: 88% | Session ID: urgent-pyelo-002
```

#### O2 — Appointment Scheduler
```
📅 URGENT Appointment

Dr. Patel (Urologist)
Today, March 14 at 4:30 PM — 2 slots remaining
[Book Now]  [See Other Slots]
```

#### O3 — Follow-up Agent
Sets: *"Check in tonight at 9 PM: Has your fever gone down? Did you see the doctor? If fever exceeds 103°F, escalate to EMERGENCY."*

---
---

## Scenario C: 🔴 EMERGENCY — Heart Attack in Patient on Blood Thinners

### User Query
> *"I have severe crushing chest pain that started 20 minutes ago, radiating to my left arm and jaw. I'm sweating heavily and feel like I'm going to throw up. I am 68 years old, male. I take Warfarin (blood thinner) for atrial fibrillation and Atenolol for heart rate. I am allergic to aspirin and penicillin. I have a history of atrial fibrillation, a previous heart attack 3 years ago, and high cholesterol."*

---

### Layer 1: Input Understanding

| Agent | Key Output |
|-------|-----------|
| **I1** | `{intent: "symptom_check", confidence: 0.97}` |
| **I2** | `{symptoms: ["chest pain", "left arm pain", "jaw pain", "sweating", "nausea"], duration: "20 minutes", severity: "severe"}` |
| **I3** | DB 3 → `[{chest pain, 29857009}, {radiating pain left arm, 10601006}, {jaw pain, 274667000}, {diaphoresis, 415690000}, {nausea, 422587007}]` |
| **I4** | DB 4 write → `{age: 68, gender: "male", history: ["atrial fibrillation", "previous MI", "high cholesterol"], medications: ["warfarin", "atenolol"], allergies: ["aspirin", "penicillin"]}` |

---

### Layer 2: Knowledge Retrieval (Parallel)

#### K1 — Medical Knowledge Agent
**DB 1 Returns:**

| condition | urgency | match_score |
|-----------|---------|-------------|
| Myocardial infarction (MI) | emergency | 3.2 |
| Unstable angina | emergency | 2.1 |
| Aortic dissection | emergency | 1.3 |

#### K4 — Vector RAG Agent
**DB 2 Returns:** "AHA: Heart Attack Warning Signs" (0.96), "ESC: Acute Coronary Syndrome Protocol" (0.94), "ACC: STEMI Management" (0.91)

#### K2 — Drug Interaction Agent ⚠️
**Input:** `{medications: ["warfarin", "atenolol"]}`

**DB 1 Returns — The Blacklist:**

| drug | interacts_with | severity | description |
|------|---------------|----------|-------------|
| warfarin | **aspirin** | **MAJOR** | Extreme bleeding risk — potentially fatal |
| warfarin | **NSAIDs** (ibuprofen) | major | Increased bleeding |
| warfarin | **heparin** | major | Double anticoagulation — hemorrhage risk |
| atenolol | **calcium channel blockers** | moderate | Severe bradycardia |

**K2 Output:** `{interactions: [{drug: "warfarin", interacts_with: "aspirin", severity: "MAJOR", description: "Fatal bleeding risk"}, {drug: "warfarin", interacts_with: "NSAIDs", severity: "major"}, {drug: "warfarin", interacts_with: "heparin", severity: "major"}]}`

---

### Layer 3: Clinical Reasoning

#### R1 — Differential Diagnosis

| Condition | symptom_match | risk_factor | history_weight | **Score** |
|-----------|:---:|:---:|:---:|:---:|
| Myocardial infarction | 0.96 | 0.95 (prev MI + AFib + cholesterol) | 0.90 | **0.94** |
| Unstable angina | 0.70 | 0.70 | 0.50 | **0.64** |
| Aortic dissection | 0.52 | 0.30 | 0.20 | **0.35** |

#### R2 — Urgency Scoring
**Rules checked:**
- ✅ `chest pain + radiating to arm + sweating + age > 60` → **EMERGENCY** (Rule #1)
- ✅ Previous MI = cardiac recurrence risk
- ✅ Atrial fibrillation = clot risk factor

**Output:** `{urgency: "emergency", confidence: 0.97, reason: "Classic MI presentation + previous MI + AFib + age 68"}`

#### R3 — Treatment Suggestion
**DB 1 Query:** `SELECT treatment FROM guidelines WHERE condition = 'MI' AND urgency = 'emergency'`

**Standard emergency treatment returned:**
```json
{
  "recommendation": "Call 911/112 immediately",
  "self_care": [
    "Chew 325mg aspirin",
    "Sit upright and stay calm",
    "Do NOT drive yourself",
    "Unlock front door for paramedics",
    "Do NOT take additional heart medications without instruction"
  ]
}
```

> ⚠️ The #1 standard instruction for heart attacks is "Chew aspirin." This patient is **allergic to aspirin** AND on **Warfarin** (which interacts dangerously with aspirin). This is the hardest possible safety scenario!

---

### Layer 4: Safety (Parallel)

#### S1 — Emergency Detection
**Multiple triggers:**
- "chest pain" + "radiating" + "sweating" → emergency keyword match
- Urgency already scored as "emergency"

`{emergency: true, action: "ROUTE TO EMERGENCY BYPASS"}`

#### S2 — Contraindication Agent ⚠️ LIFE-SAVING CHECK

| Proposed Treatment | K2 Blacklist Check | Allergy Check | Decision |
|-------------------|-------------------|---------------|----------|
| **Chew 325mg aspirin** | ✅ **warfarin + aspirin = MAJOR** (fatal bleeding) | ✅ **aspirin allergy** | 🚫 **BLOCKED — DOUBLE FLAGGED** |
| Sit upright | — | — | ✅ Safe |
| Don't drive | — | — | ✅ Safe |
| Unlock front door | — | — | ✅ Safe |
| Don't take additional heart meds | — | — | ✅ Safe |

**S2 Output:**
```json
{
  "blocked": [
    "Aspirin — DOUBLE BLOCKED: (1) Patient allergic to aspirin, (2) Patient on Warfarin — aspirin + warfarin = fatal hemorrhage risk"
  ],
  "warnings": [
    "Patient is already anticoagulated with Warfarin — inform 911 dispatcher and paramedics",
    "Hospital must check INR immediately on arrival"
  ],
  "safe_suggestions": ["Sit upright", "Do not drive", "Unlock front door"]
}
```

#### S3 — Uncertainty Detector
`{uncertain: false}` — Confidence 0.97 > 0.6

---

### 🔀 Safety Router Decision: **EMERGENCY**

```
SR reads: emergency=TRUE, blocked=1 (aspirin), warnings=2
Decision → EMERGENCY BYPASS — Skip P1, P2, K3 entirely
Carry the FULL package (including S2's blocked list and warnings) to O1
```

**What gets skipped (and why):**

| Agent | Skipped? | Reason |
|-------|----------|--------|
| P1 — Risk Adjustment | ✅ SKIPPED | No time for demographic math — every second counts |
| P2 — Lifestyle | ✅ SKIPPED | Diet advice during MI is dangerous distraction |
| K3 — Specialist Directory | ✅ SKIPPED | You need an ER, not a scheduled cardiology appointment |
| O2 — Appointment Scheduler | ✅ SKIPPED | 911 replaces appointments |
| O3 — Follow-up Agent | ✅ SKIPPED | Hospital handles post-MI care |

**What still reaches O1:**
The Safety Router carries every safety flag:
- Emergency status from S1
- The aspirin block + Warfarin warnings from S2
- The confidence level from S3
- The original treatment guidelines (minus the blocked items)

---

### Layer 6: Output (Emergency Mode)

#### O1 — Explanation Generator
```
🚨 EMERGENCY ALERT — POSSIBLE HEART ATTACK

Your symptoms — severe crushing chest pain radiating to your
left arm and jaw, heavy sweating, and nausea — combined with
your age (68), previous heart attack, and atrial fibrillation,
indicate a likely heart attack.

⚡ CALL 911 / 112 RIGHT NOW.
   Do NOT drive yourself to the hospital.

📋 While waiting for paramedics:
  • Sit upright and stay as calm as possible
  • Loosen any tight clothing
  • Unlock your front door for paramedics

🚫 CRITICAL SAFETY ALERT:
  ❌ Do NOT chew aspirin — you are allergic to aspirin AND
     you take Warfarin. Aspirin + Warfarin = risk of fatal
     internal bleeding.

⚠️ TELL THE 911 DISPATCHER AND PARAMEDICS:
  1. "I take Warfarin for atrial fibrillation"
  2. "I am allergic to aspirin AND penicillin"
  3. "I had a heart attack 3 years ago"
  4. "I also take Atenolol"
  → Hospital must check your INR (blood clotting level)
    immediately on arrival.

📚 Sources:
  1. American Heart Association — Heart Attack Warning Signs
  2. ESC — Acute Coronary Syndrome Protocol
  3. ACC — STEMI Management Guidelines

⚠️ This is NOT a diagnosis. A medical team must evaluate you
   IMMEDIATELY.
   Confidence: 97% | Session ID: emergency-mi-003
```

#### O2 — Appointment Scheduler
**NOT ACTIVATED.** Emergency bypass skipped this agent.

#### O3 — Follow-up Agent
**NOT ACTIVATED.** Hospital handles all post-MI follow-up.

---
---

## Safety Router Summary Table

| Scenario | S1 (Emergency) | S2 (Contraindications) | S3 (Uncertainty) | Router | Agents Activated | Agents Skipped |
|:---------|:-:|:-:|:-:|:---|:---|:---|
| 🟢 **Routine** (Migraine) | false | 2 blocked (triptan, ibuprofen) | false | → Personalization | All 16 | None |
| 🟡 **Urgent** (Kidney Infection) | false | 2 blocked (Bactrim, ibuprofen) | false | → Personalization | All 16 | None |
| 🔴 **Emergency** (Heart Attack) | **TRUE** | 1 blocked (aspirin—double flagged) | false | → **BYPASS** | 11 agents | P1, P2, K3, O2, O3 |

---

## Database Usage Summary

| Database | Routine (Migraine) | Urgent (Kidney) | Emergency (MI) |
|:---------|:-:|:-:|:-:|
| **DB 1: Medical KB** | ✅ conditions, treatments, drug interactions (sertraline) | ✅ conditions, treatments, drug interactions (metformin, lisinopril) | ✅ conditions, treatments, drug interactions (warfarin), emergency rules |
| **DB 2: Vector Store** | ✅ Mayo Clinic, AHS articles | ✅ AUA, NICE, ADA articles | ✅ AHA, ESC, ACC guidelines |
| **DB 3: Ontology Map** | ✅ headache, nausea, photophobia | ✅ dysuria, flank pain, fever | ✅ chest pain, radiating pain, diaphoresis, nausea |
| **DB 4: User Profile** | ✅ Write + Read (age, meds: sertraline, allergies: aspirin) | ✅ Write + Read (age, meds: metformin+lisinopril, allergies: sulfa, history: CKD) | ✅ Write + Read (age, meds: warfarin+atenolol, allergies: aspirin+penicillin, history: prev MI+AFib) |
| **DB 5: Audit Log** | ✅ Full 16-agent trace | ✅ Full 16-agent trace | ✅ 11-agent trace (5 skipped logged as "BYPASSED") |

---

## Contraindication Agent — Decision Matrix Across All 3 Scenarios

| Scenario | Proposed Treatment | Blocked By (Source) | Alternative Suggested |
|:---------|:---|:---|:---|
| 🟢 Migraine | Sumatriptan | K2: sertraline + triptans = Serotonin Syndrome | Acetaminophen |
| 🟢 Migraine | Ibuprofen | K2: sertraline + NSAIDs + aspirin allergy | Acetaminophen |
| 🟡 Kidney | Bactrim (TMP-SMX) | DB4: Sulfa allergy | Ciprofloxacin / Amox-Clav |
| 🟡 Kidney | Ibuprofen | K2: lisinopril + NSAIDs + CKD | Acetaminophen |
| 🔴 Heart Attack | Aspirin (325mg) | K2: warfarin + aspirin + DB4: aspirin allergy | None (inform paramedics) |

> This matrix proves the Contraindication Agent (S2) handles drug-drug interactions (via K2), allergy checks (via DB4), and condition-specific contraindications — all in parallel, all in real-time.


