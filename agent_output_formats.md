# NeuroHealth — Agent Output Formats & Final Output Schema

> Complete specification of what every agent produces, the Pydantic models that enforce the structure, and how the final output is assembled for the user.

---

## Core Principle: Every Agent Follows the Same Contract

Every agent in NeuroHealth wraps its domain-specific output inside a universal envelope:

```python
from pydantic import BaseModel, Field
import time

class AgentOutput(BaseModel):
    """Universal wrapper — every agent returns this."""
    agent_name: str                          # "IntentClassifier", "EmergencyDetection"
    layer: str                               # "input", "knowledge", "reasoning", "safety", "personalization", "output"
    input_data: dict                         # What the agent received
    output_data: dict                        # ← THE DOMAIN-SPECIFIC OUTPUT (see below)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_sources: list[str] = []         # Citations / DB references
    processing_time_ms: float                # Wall-clock time
    errors: list[str] = []                   # Any warnings or failures
```

**Example envelope for the Intent Classifier:**
```json
{
  "agent_name": "IntentClassifier",
  "layer": "input",
  "input_data": {"user_input": "I have chest pain and I take Warfarin..."},
  "output_data": {"intent": "symptom_check", "confidence": 0.95},
  "confidence": 0.95,
  "evidence_sources": ["keyword_match: chest pain, sweating"],
  "processing_time_ms": 12.3,
  "errors": []
}
```

The `output_data` field is what varies per agent. The rest of this document defines the exact schema of `output_data` for every agent.

---
---

## Layer 1: Input Understanding

### I1 — Intent Classifier Agent

```python
class IntentOutput(BaseModel):
    intent: str        # "symptom_check" | "medication_question" | "appointment_request" | "emergency_help" | "health_education"
    confidence: float  # 0.0 – 1.0
```

**Example `output_data`:**
```json
{
  "intent": "symptom_check",
  "confidence": 0.95
}
```

---

### I2 — Symptom Extraction Agent

```python
class ExtractedSymptom(BaseModel):
    name: str          # "chest pain", "nausea"
    raw_text: str      # The exact phrase from user input: "crushing chest pain"
    negated: bool      # True if user said "I do NOT have fever"

class SymptomExtractionOutput(BaseModel):
    symptoms: list[ExtractedSymptom]
    duration: str      # "6 hours", "2 days", "unknown"
    severity: str      # "mild" | "moderate" | "severe" | "unknown"
```

**Example `output_data`:**
```json
{
  "symptoms": [
    {"name": "chest pain", "raw_text": "severe crushing chest pain", "negated": false},
    {"name": "sweating", "raw_text": "sweating heavily", "negated": false},
    {"name": "nausea", "raw_text": "feel like I'm going to throw up", "negated": false}
  ],
  "duration": "20 minutes",
  "severity": "severe"
}
```

---

### I3 — Ontology Normalizer Agent

```python
class NormalizedTerm(BaseModel):
    original_term: str     # "chest pain" (from I2)
    snomed_code: str       # "29857009"
    snomed_label: str      # "Chest pain (finding)"
    icd10_code: str        # "R07.9"
    semantic_type: str     # "Sign or Symptom" | "Clinical Finding"

class OntologyNormalizerOutput(BaseModel):
    normalized_symptoms: list[NormalizedTerm]
    unresolved_terms: list[str]  # Terms that could not be mapped
```

**Example `output_data`:**
```json
{
  "normalized_symptoms": [
    {
      "original_term": "chest pain",
      "snomed_code": "29857009",
      "snomed_label": "Chest pain (finding)",
      "icd10_code": "R07.9",
      "semantic_type": "Sign or Symptom"
    },
    {
      "original_term": "sweating",
      "snomed_code": "415690000",
      "snomed_label": "Diaphoresis (finding)",
      "icd10_code": "R61",
      "semantic_type": "Sign or Symptom"
    },
    {
      "original_term": "nausea",
      "snomed_code": "422587007",
      "snomed_label": "Nausea (finding)",
      "icd10_code": "R11.0",
      "semantic_type": "Sign or Symptom"
    }
  ],
  "unresolved_terms": []
}
```

---

### I4 — Context Extractor Agent

```python
class UserProfile(BaseModel):
    age: int | None
    gender: str | None             # "male" | "female" | "other" | None
    medical_history: list[str]     # ["diabetes", "atrial fibrillation"]
    allergies: list[str]           # ["aspirin", "penicillin"]
    current_medications: list[str] # ["warfarin", "atenolol"]
    lifestyle_factors: list[str]   # ["smoker", "sedentary"] (if mentioned)

class ContextExtractorOutput(BaseModel):
    user_profile: UserProfile
    profile_completeness: float    # 0.0–1.0: how much info was extracted
    profile_written_to_db4: bool   # Confirms DB 4 write
```

**Example `output_data`:**
```json
{
  "user_profile": {
    "age": 68,
    "gender": "male",
    "medical_history": ["atrial fibrillation", "previous MI", "high cholesterol"],
    "allergies": ["aspirin", "penicillin"],
    "current_medications": ["warfarin", "atenolol"],
    "lifestyle_factors": []
  },
  "profile_completeness": 0.90,
  "profile_written_to_db4": true
}
```

---
---

## Layer 2: Knowledge Retrieval

### K1 — Medical Knowledge Agent

```python
class MatchedCondition(BaseModel):
    condition_id: str           # "MI_001"
    condition_name: str         # "Myocardial infarction"
    icd10_code: str             # "I21.9"
    urgency: str                # "emergency" | "urgent" | "routine"
    match_score: float          # Sum of symptom importance weights
    matched_symptoms: list[str] # Which of the user's symptoms matched
    cardinal_match: bool        # True if a cardinal symptom was matched

class MedicalKnowledgeOutput(BaseModel):
    conditions: list[MatchedCondition]  # Ranked by match_score DESC
    db_queries_made: int
```

**Example `output_data`:**
```json
{
  "conditions": [
    {
      "condition_id": "MI_001",
      "condition_name": "Myocardial infarction",
      "icd10_code": "I21.9",
      "urgency": "emergency",
      "match_score": 3.2,
      "matched_symptoms": ["chest pain", "diaphoresis", "nausea"],
      "cardinal_match": true
    },
    {
      "condition_id": "UA_001",
      "condition_name": "Unstable angina",
      "icd10_code": "I20.0",
      "urgency": "emergency",
      "match_score": 2.1,
      "matched_symptoms": ["chest pain", "diaphoresis"],
      "cardinal_match": true
    }
  ],
  "db_queries_made": 2
}
```

---

### K2 — Drug Interaction Agent

```python
class DrugInteraction(BaseModel):
    user_drug: str              # "warfarin" (what the user takes)
    interacts_with: str         # "aspirin" (what would be dangerous to add)
    severity: str               # "major" | "moderate" | "minor"
    description: str            # "Extreme bleeding risk — potentially fatal"
    source: str                 # "DrugBank" | "openFDA"

class DrugInteractionOutput(BaseModel):
    interactions: list[DrugInteraction]  # THE BLACKLIST
    medications_checked: list[str]      # What K2 looked up
    db_queries_made: int
```

**Example `output_data`:**
```json
{
  "interactions": [
    {
      "user_drug": "warfarin",
      "interacts_with": "aspirin",
      "severity": "major",
      "description": "Extreme bleeding risk — potentially fatal",
      "source": "DrugBank"
    },
    {
      "user_drug": "warfarin",
      "interacts_with": "NSAIDs",
      "severity": "major",
      "description": "Increased bleeding and bruising",
      "source": "openFDA"
    },
    {
      "user_drug": "warfarin",
      "interacts_with": "heparin",
      "severity": "major",
      "description": "Double anticoagulation — hemorrhage risk",
      "source": "DrugBank"
    }
  ],
  "medications_checked": ["warfarin", "atenolol"],
  "db_queries_made": 2
}
```

---

### K4 — Vector RAG Agent

```python
class RetrievedArticle(BaseModel):
    title: str                  # "Heart Attack Warning Signs"
    source: str                 # "AHA", "Mayo Clinic"
    source_url: str             # "https://..."
    content_snippet: str        # First 200 chars of the chunk
    relevance_score: float      # Cosine similarity 0.0–1.0
    reliability_tier: str       # "tier_1" | "tier_2" | "tier_3"
    chunk_index: int            # Which chunk of the article

class VectorRAGOutput(BaseModel):
    articles: list[RetrievedArticle]   # Top-k results
    query_text: str                     # The semantic search query used
    total_chunks_searched: int
```

**Example `output_data`:**
```json
{
  "articles": [
    {
      "title": "Heart Attack Warning Signs",
      "source": "AHA",
      "source_url": "https://www.heart.org/...",
      "content_snippet": "Heart attack symptoms include crushing chest pain, sweating, nausea, and pain radiating to the arm...",
      "relevance_score": 0.96,
      "reliability_tier": "tier_1",
      "chunk_index": 1
    },
    {
      "title": "Acute Coronary Syndrome Protocol",
      "source": "ESC Guideline",
      "source_url": "https://www.escardio.org/...",
      "content_snippet": "Acute chest pain triage: assess within 10 minutes, obtain ECG, administer aspirin unless...",
      "relevance_score": 0.94,
      "reliability_tier": "tier_1",
      "chunk_index": 3
    }
  ],
  "query_text": "crushing chest pain radiating left arm sweating nausea",
  "total_chunks_searched": 28000
}
```

---
---

## Layer 3: Clinical Reasoning

### R1 — Differential Diagnosis Agent

```python
class DiagnosisCandidate(BaseModel):
    condition: str              # "Myocardial infarction"
    condition_id: str           # "MI_001"
    urgency: str                # "emergency"
    score: float                # Final weighted score (0.0–1.0)
    symptom_match_weight: float # Contribution from symptom matching
    risk_factor_weight: float   # Contribution from demographics/history
    history_weight: float       # Contribution from past conditions
    rag_support: bool           # Whether RAG articles confirmed this

class DifferentialDiagnosisOutput(BaseModel):
    ranked_conditions: list[DiagnosisCandidate]  # Sorted by score DESC
    scoring_formula: str                          # For auditability
```

**Example `output_data`:**
```json
{
  "ranked_conditions": [
    {
      "condition": "Myocardial infarction",
      "condition_id": "MI_001",
      "urgency": "emergency",
      "score": 0.94,
      "symptom_match_weight": 0.96,
      "risk_factor_weight": 0.95,
      "history_weight": 0.90,
      "rag_support": true
    },
    {
      "condition": "Unstable angina",
      "condition_id": "UA_001",
      "urgency": "emergency",
      "score": 0.64,
      "symptom_match_weight": 0.70,
      "risk_factor_weight": 0.70,
      "history_weight": 0.50,
      "rag_support": true
    }
  ],
  "scoring_formula": "score = symptom_match * 0.4 + risk_factor * 0.3 + history * 0.3"
}
```

---

### R2 — Urgency Scoring Agent

```python
class UrgencyScoringOutput(BaseModel):
    urgency: str                # "emergency" | "urgent" | "routine"
    confidence: float           # 0.0–1.0
    reason: str                 # Human-readable reason
    rules_triggered: list[str]  # Which emergency/urgency rules fired
    risk_factors: list[str]     # What boosted the score
```

**Example `output_data`:**
```json
{
  "urgency": "emergency",
  "confidence": 0.97,
  "reason": "Classic MI presentation + previous MI + AFib + age 68",
  "rules_triggered": [
    "cardiac_emergency: chest pain + radiating arm + sweating + age > 60",
    "recurrence_rule: previous MI within 5 years"
  ],
  "risk_factors": ["age 68 > 60", "previous MI", "atrial fibrillation", "high cholesterol"]
}
```

---

### R3 — Treatment Suggestion Agent

```python
class TreatmentSuggestionOutput(BaseModel):
    top_condition: str          # "Myocardial infarction"
    urgency: str                # "emergency"
    recommendation: str         # "Call 911 immediately"
    self_care: list[str]        # Step-by-step actions
    specialist_type: str        # "cardiologist" (from treatment_guidelines table)
    source: str                 # "ESC Acute Coronary Syndrome Protocol 2023"
    source_url: str             # URL for citation
```

**Example `output_data`:**
```json
{
  "top_condition": "Myocardial infarction",
  "urgency": "emergency",
  "recommendation": "Call 911/112 immediately",
  "self_care": [
    "Chew 325mg aspirin",
    "Sit upright and stay calm",
    "Do NOT drive yourself",
    "Unlock front door for paramedics",
    "Do NOT take additional heart medications without instruction"
  ],
  "specialist_type": "cardiologist",
  "source": "ESC Acute Coronary Syndrome Protocol 2023",
  "source_url": "https://www.escardio.org/Guidelines/ACS"
}
```

> ⚠️ Note: This is the **standard** treatment. It has NOT been safety-checked yet. The self_care list may contain items dangerous for this specific user (e.g., aspirin for someone allergic to it). The Safety Layer handles that next.

---
---

## Layer 4: Safety

### S1 — Emergency Detection Agent

```python
class EmergencyDetectionOutput(BaseModel):
    emergency: bool             # True if emergency detected
    action: str                 # "ROUTE TO EMERGENCY BYPASS" | ""
    triggers: list[str]         # What caused the detection
    override_urgency: bool      # True if this overrides R2's scoring
```

**Example `output_data`:**
```json
{
  "emergency": true,
  "action": "ROUTE TO EMERGENCY BYPASS",
  "triggers": [
    "keyword_match: severe chest pain",
    "R2_urgency: emergency",
    "emergency_rules_match: cardiac_emergency"
  ],
  "override_urgency": false
}
```

---

### S2 — Contraindication Agent

```python
class BlockedTreatment(BaseModel):
    treatment: str              # "Chew 325mg aspirin"
    reason: str                 # "Patient allergic to aspirin + warfarin interaction"
    source: str                 # "K2_blacklist" | "DB4_allergy" | "DB4_condition"
    severity: str               # "major" | "moderate" | "minor"

class ContraindicationOutput(BaseModel):
    blocked: list[BlockedTreatment]      # Treatments that MUST be removed
    warnings: list[str]                   # Non-blocking but important notes
    safe_suggestions: list[str]           # Confirmed safe items from R3
    alternatives: list[str]              # Suggested replacements for blocked items
```

**Example `output_data`:**
```json
{
  "blocked": [
    {
      "treatment": "Chew 325mg aspirin",
      "reason": "DOUBLE BLOCKED: (1) aspirin allergy (DB4), (2) warfarin + aspirin = fatal hemorrhage (K2 blacklist)",
      "source": "K2_blacklist + DB4_allergy",
      "severity": "major"
    }
  ],
  "warnings": [
    "Patient is already anticoagulated with Warfarin — inform 911 dispatcher",
    "Hospital must check INR immediately on arrival"
  ],
  "safe_suggestions": [
    "Sit upright and stay calm",
    "Do NOT drive yourself",
    "Unlock front door for paramedics"
  ],
  "alternatives": []
}
```

---

### S3 — Uncertainty Detector Agent

```python
class UncertaintyDetectorOutput(BaseModel):
    uncertain: bool             # True if confidence is too low
    confidence_value: float     # The actual confidence from R2
    threshold: float            # The minimum acceptable confidence (0.6)
    action: str                 # "Recommend consulting a doctor" | ""
    conflicting_signals: list[str]  # What caused uncertainty (if any)
```

**Example `output_data`:**
```json
{
  "uncertain": false,
  "confidence_value": 0.97,
  "threshold": 0.6,
  "action": "",
  "conflicting_signals": []
}
```

---

### SR — Safety Router (Decision Node)

```python
class SafetyRouterOutput(BaseModel):
    decision: str               # "emergency_bypass" | "routine" | "urgent"
    emergency_flag: bool
    blocked_count: int
    uncertainty_flag: bool
    next_nodes: list[str]       # What agents run next
    skipped_nodes: list[str]    # What agents are skipped
```

**Example `output_data` — Emergency path:**
```json
{
  "decision": "emergency_bypass",
  "emergency_flag": true,
  "blocked_count": 1,
  "uncertainty_flag": false,
  "next_nodes": ["O1_ExplanationGenerator"],
  "skipped_nodes": ["P1_RiskAdjustment", "P2_LifestyleRecommendation", "K3_SpecialistDirectory", "O2_AppointmentScheduler", "O3_FollowupAgent"]
}
```

**Example `output_data` — Routine/Urgent path:**
```json
{
  "decision": "routine",
  "emergency_flag": false,
  "blocked_count": 2,
  "uncertainty_flag": false,
  "next_nodes": ["P1_RiskAdjustment", "P2_LifestyleRecommendation", "K3_SpecialistDirectory", "O1_ExplanationGenerator", "O2_AppointmentScheduler", "O3_FollowupAgent"],
  "skipped_nodes": []
}
```

---
---

## Layer 5: Personalization

### P1 — Risk Adjustment Agent

```python
class RiskAdjustmentOutput(BaseModel):
    original_urgency: str       # What R2 scored
    adjusted_urgency: str       # May stay the same or escalate
    risk_multiplier: float      # 1.0 = no change, >1.0 = higher risk
    risk_factors_applied: list[str]  # What factors changed the risk
    risk_note: str              # Advisory note for the user
```

**Example `output_data`:**
```json
{
  "original_urgency": "routine",
  "adjusted_urgency": "routine",
  "risk_multiplier": 1.2,
  "risk_factors_applied": ["migraine with aura + oral contraceptives = stroke risk"],
  "risk_note": "Migraine with aura + oral contraceptives: discuss stroke risk with your doctor at next visit"
}
```

---

### P2 — Lifestyle Recommendation Agent

```python
class LifestyleRecommendationOutput(BaseModel):
    tips: list[str]             # Personalized lifestyle advice
    based_on: list[str]         # What profile data drove these tips
```

**Example `output_data`:**
```json
{
  "tips": [
    "Keep a migraine diary to identify triggers",
    "Maintain regular sleep schedule",
    "Reduce screen time during episodes",
    "Magnesium-rich foods may reduce frequency"
  ],
  "based_on": ["history: migraines", "condition: migraine with aura"]
}
```

---

### K3 — Specialist Directory Agent

```python
class SpecialistDirectoryOutput(BaseModel):
    specialist_type: str        # "Neurologist", "Cardiologist"
    condition: str              # The condition requiring the specialist
    body_system: str            # "cardiovascular", "neurological"
    consult_reason: str         # Why this specialist is recommended
```

**Example `output_data`:**
```json
{
  "specialist_type": "Neurologist",
  "condition": "Migraine with aura",
  "body_system": "neurological",
  "consult_reason": "Recurring migraines with aura + oral contraceptive interaction requires specialist evaluation"
}
```

---
---

## Layer 6: Output

### O1 — Explanation Generator Agent

```python
class ExplanationGeneratorOutput(BaseModel):
    explanation_text: str           # The full formatted message shown to the user
    urgency_level: str              # "emergency" | "urgent" | "routine"
    is_emergency_bypass: bool       # True if personalization was skipped
    citations: list[dict]           # [{title, source, url}]
    blocked_treatments_shown: int   # How many blocked treatments were mentioned
    disclaimer: str                 # "This is not a diagnosis..."
```

**Example `output_data`:**
```json
{
  "explanation_text": "🚨 EMERGENCY ALERT — POSSIBLE HEART ATTACK\n\nYour symptoms — severe crushing chest pain radiating to your left arm and jaw...\n\n⚡ CALL 911 RIGHT NOW.\n\n🚫 Do NOT chew aspirin — you are allergic...",
  "urgency_level": "emergency",
  "is_emergency_bypass": true,
  "citations": [
    {"title": "Heart Attack Warning Signs", "source": "AHA", "url": "https://www.heart.org/..."},
    {"title": "Acute Coronary Syndrome Protocol", "source": "ESC", "url": "https://www.escardio.org/..."}
  ],
  "blocked_treatments_shown": 1,
  "disclaimer": "This is NOT a diagnosis. A medical team must evaluate you IMMEDIATELY."
}
```

---

### O2 — Appointment Scheduler Agent

```python
class AppointmentSlot(BaseModel):
    specialist: str             # "Dr. Sharma (Neurologist)"
    date: str                   # "Monday, March 17"
    time: str                   # "3:00 PM"
    slots_remaining: int

class AppointmentSchedulerOutput(BaseModel):
    appointment_needed: bool
    appointment: AppointmentSlot | None
    urgency_note: str           # "See within 24 hours" | "Next available" | ""
```

**Example `output_data` — Routine:**
```json
{
  "appointment_needed": true,
  "appointment": {
    "specialist": "Dr. Sharma (Neurologist)",
    "date": "Monday, March 17",
    "time": "3:00 PM",
    "slots_remaining": 3
  },
  "urgency_note": "Next available appointment"
}
```

**Example `output_data` — Emergency (SKIPPED):**
```json
{
  "appointment_needed": false,
  "appointment": null,
  "urgency_note": "SKIPPED — Emergency bypass active. Call 911."
}
```

---

### O3 — Follow-up Agent

```python
class FollowupAgentOutput(BaseModel):
    followup_needed: bool
    check_in_after: str         # "24 hours" | "5 days" | ""
    followup_message: str       # "Are symptoms improving?"
    escalation_rule: str | None # "If fever > 103°F, escalate to EMERGENCY"
```

**Example `output_data` — Urgent:**
```json
{
  "followup_needed": true,
  "check_in_after": "24 hours",
  "followup_message": "Did you see the doctor? Has your fever gone down?",
  "escalation_rule": "If fever exceeds 103°F or you develop chills/confusion, escalate to EMERGENCY."
}
```

**Example `output_data` — Emergency (SKIPPED):**
```json
{
  "followup_needed": false,
  "check_in_after": "",
  "followup_message": "SKIPPED — Hospital handles post-emergency follow-up.",
  "escalation_rule": null
}
```

---

### F1 — User Feedback Agent

```python
class FeedbackAgentOutput(BaseModel):
    feedback_type: str          # "correction" | "confirmation" | "new_symptoms" | "none"
    new_symptoms: list[str]     # ["sore throat"] (if user corrects)
    removed_symptoms: list[str] # ["chest pain"] (if user says "actually no chest pain")
    route_to: str               # "I2" (always routes back to Symptom Extractor)
    requires_rerun: bool        # True if pipeline must re-execute
```

**Example `output_data`:**
```json
{
  "feedback_type": "correction",
  "new_symptoms": ["sore throat"],
  "removed_symptoms": ["chest pain"],
  "route_to": "I2",
  "requires_rerun": true
}
```

---
---

## Final Assembled Output (What the User Sees)

The **OUT node** collects outputs from O1, O2, and O3 and assembles the final response:

```python
class FinalOutput(BaseModel):
    session_id: str                     # UUID for this conversation
    urgency: str                        # "emergency" | "urgent" | "routine"
    safety_router_decision: str         # "emergency_bypass" | "routine" | "urgent"

    # From O1
    explanation: str                    # Main text the user reads
    citations: list[dict]               # [{title, source, url}]
    blocked_treatments: list[dict]      # [{treatment, reason, severity}]

    # From O2 (None on emergency)
    appointment: dict | None            # {specialist, date, time}

    # From O3 (None on emergency)
    followup: dict | None               # {check_in_after, message, escalation_rule}

    # Metadata
    total_agents_run: int               # 16 (routine) or 11 (emergency)
    total_pipeline_time_ms: float
    confidence: float                   # Final confidence from R2
    disclaimer: str
```

**Example — Final JSON sent to frontend (Routine Migraine):**
```json
{
  "session_id": "a3b8d1b6-0b3b-4b1a-9c1a-routine-migraine-001",
  "urgency": "routine",
  "safety_router_decision": "routine",

  "explanation": "🩺 Health Assessment\n\nYour symptoms — throbbing one-sided headache with nausea and light sensitivity — are consistent with a migraine with aura...\n\n💊 Safe Recommendations:\n  • Rest in a dark, quiet room\n  • Take Acetaminophen (Tylenol) for pain relief\n\n🚫 Safety Alerts:\n  ❌ Sumatriptan: BLOCKED — Serotonin Syndrome risk with Sertraline\n  ❌ Ibuprofen: BLOCKED — GI bleeding risk + aspirin allergy\n\n🥗 Lifestyle Tips:\n  • Keep a migraine diary\n  • Maintain regular sleep schedule",

  "citations": [
    {"title": "Migraine", "source": "Mayo Clinic", "url": "https://mayoclinic.org/..."},
    {"title": "Migraine Treatment Guidelines", "source": "AHS", "url": "https://americanheadachesociety.org/..."}
  ],

  "blocked_treatments": [
    {"treatment": "Sumatriptan", "reason": "sertraline + triptans = Serotonin Syndrome", "severity": "major"},
    {"treatment": "Ibuprofen", "reason": "sertraline + NSAIDs + aspirin allergy", "severity": "moderate"}
  ],

  "appointment": {
    "specialist": "Dr. Sharma (Neurologist)",
    "date": "Monday, March 17",
    "time": "3:00 PM"
  },

  "followup": {
    "check_in_after": "24 hours",
    "message": "Has the migraine resolved? Did Acetaminophen help?",
    "escalation_rule": null
  },

  "total_agents_run": 16,
  "total_pipeline_time_ms": 1847.5,
  "confidence": 0.87,
  "disclaimer": "⚠️ This is not a diagnosis. Confidence: 87%"
}
```

---

## Agent Output Size Summary

| Agent | Layer | Key Output Fields | Typical JSON Size |
|:------|:------|:---|:---|
| I1 — Intent Classifier | Input | intent, confidence | ~50 bytes |
| I2 — Symptom Extractor | Input | symptoms[], duration, severity | ~300 bytes |
| I3 — Ontology Normalizer | Input | normalized_symptoms[], unresolved | ~500 bytes |
| I4 — Context Extractor | Input | user_profile (age, meds, allergies, history) | ~400 bytes |
| K1 — Medical Knowledge | Knowledge | conditions[] with match scores | ~600 bytes |
| K2 — Drug Interaction | Knowledge | interactions[] (THE BLACKLIST) | ~500 bytes |
| K4 — Vector RAG | Knowledge | articles[] with snippets + scores | ~1.2 KB |
| R1 — Differential Diagnosis | Reasoning | ranked_conditions[] with weight breakdown | ~700 bytes |
| R2 — Urgency Scoring | Reasoning | urgency, confidence, rules triggered | ~300 bytes |
| R3 — Treatment Suggestion | Reasoning | recommendation, self_care[] | ~400 bytes |
| S1 — Emergency Detection | Safety | emergency flag, triggers | ~200 bytes |
| S2 — Contraindication | Safety | blocked[], warnings[], alternatives | ~600 bytes |
| S3 — Uncertainty Detector | Safety | uncertain flag, conflicting signals | ~150 bytes |
| SR — Safety Router | Safety | decision, next/skipped nodes | ~300 bytes |
| P1 — Risk Adjustment | Personalization | multiplier, risk note | ~300 bytes |
| P2 — Lifestyle | Personalization | tips[], based_on[] | ~250 bytes |
| K3 — Specialist Directory | Personalization | specialist type, reason | ~200 bytes |
| O1 — Explanation Generator | Output | full text, citations, disclaimer | ~2 KB |
| O2 — Appointment Scheduler | Output | specialist, date, time | ~200 bytes |
| O3 — Follow-up Agent | Output | check_in, message, escalation | ~200 bytes |
| F1 — Feedback Agent | Feedback | new/removed symptoms, route_to | ~150 bytes |
| **Final Output** | — | Combined O1 + O2 + O3 + metadata | **~4 KB** |
