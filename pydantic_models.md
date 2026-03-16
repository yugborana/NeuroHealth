# NeuroHealth — Complete Pydantic Models Reference

> All data models in the system **except** agent output formats (covered in [agent_output_formats.md](file:///C:/Users/DELL/.gemini/antigravity/brain/9545116e-fdcf-48f5-aa7d-663122bd566d/agent_output_formats.md)).

---

## File Structure

All models live in `neurohealth/schemas/`:

```
neurohealth/schemas/
├── models.py              # Shared domain models (this file)
├── state.py               # LangGraph PipelineState
├── db_models.py           # Database ORM / table models
├── api_models.py          # API request / response schemas
├── config_models.py       # Configuration + threshold models
└── agent_outputs.py       # Agent output models (separate artifact)
```

---
---

## 1. LangGraph Pipeline State (`state.py`)

This is the single shared state dictionary that flows through the entire LangGraph state machine. Every agent reads from and writes to this state.

```python
# neurohealth/schemas/state.py
"""LangGraph PipelineState — the shared state across all agents."""

from typing import TypedDict, Annotated
import operator


class PipelineState(TypedDict):
    """
    The single state object that flows through the entire LangGraph pipeline.
    Each agent reads the fields it needs and writes its own output fields.
    LangGraph uses this TypedDict to validate state transitions.
    """

    # ─── Layer 1: Input Understanding ────────────────────────
    user_input: str                       # Raw user message
    conversation_history: list[dict]      # Previous turns [{role, content}]
    intent: dict                          # From I1: {intent: str, confidence: float}
    extracted_symptoms: list[dict]        # From I2: [{name, raw_text, negated}]
    normalized_terms: list[dict]          # From I3: [{term, snomed_code, icd10_code}]
    user_profile: dict                    # From I4: {age, gender, history[], allergies[], medications[]}

    # ─── Layer 2: Knowledge Retrieval ────────────────────────
    retrieved_conditions: list[dict]      # From K1: [{condition_id, name, urgency, match_score}]
    rag_articles: list[dict]              # From K4: [{title, source, snippet, relevance}]
    drug_interactions: list[dict]         # From K2: [{user_drug, interacts_with, severity}]

    # ─── Layer 3: Clinical Reasoning ─────────────────────────
    diagnosis_scores: list[dict]          # From R1: [{condition, score, urgency}]
    urgency_level: dict                   # From R2: {urgency, confidence, reason}
    treatment_suggestion: dict            # From R3: {recommendation, self_care[], specialist_type}

    # ─── Layer 4: Safety ─────────────────────────────────────
    emergency_flag: dict                  # From S1: {emergency: bool, action: str}
    contraindication_flags: dict          # From S2: {blocked[], warnings[], safe_suggestions[]}
    uncertainty_flag: dict                # From S3: {uncertain: bool, action: str}
    safety_router_decision: str           # From SR: "emergency_bypass" | "routine" | "urgent"

    # ─── Layer 5: Personalization (empty on emergency) ───────
    risk_adjustment: dict                 # From P1: {adjusted_urgency, risk_multiplier, risk_note}
    lifestyle_tips: list[str]             # From P2: ["Keep migraine diary", ...]
    specialist_info: dict                 # From K3: {specialist_type, condition, consult_reason}

    # ─── Layer 6: Output ─────────────────────────────────────
    explanation: str                      # From O1: Full formatted text
    appointment: dict | None              # From O2: {specialist, date, time} or None
    followup_plan: dict | None            # From O3: {check_in_after, message} or None

    # ─── System ──────────────────────────────────────────────
    session_id: str                       # UUID for this conversation session
    errors: Annotated[list, operator.add] # Accumulated errors from all agents
```

### How LangGraph Uses This

```python
# neurohealth/orchestrator/pipeline.py
from langgraph.graph import StateGraph, END
from neurohealth.schemas.state import PipelineState

graph = StateGraph(PipelineState)

# Add nodes (each is an agent function)
graph.add_node("I1_IntentClassifier", intent_classifier)
graph.add_node("I2_SymptomExtractor", symptom_extractor)
# ... all other agents ...

# Add edges (sequential within layers)
graph.add_edge("I1_IntentClassifier", "I2_SymptomExtractor")
graph.add_edge("I2_SymptomExtractor", "I3_OntologyNormalizer")
# ...

# Conditional edge at Safety Router
graph.add_conditional_edges(
    "SR_SafetyRouter",
    safety_router_decision,
    {
        "emergency_bypass": "O1_ExplanationGenerator",
        "personalization": "P1_RiskAdjustment",
    }
)

pipeline = graph.compile()
```

---
---

## 2. Shared Domain Models (`models.py`)

These models are used across multiple agents and layers. They define the core data structures of the medical domain.

```python
# neurohealth/schemas/models.py
"""Shared domain models used across multiple agents and layers."""

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4


# ═══════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════

class UrgencyLevel(str, Enum):
    """Three-tier triage classification."""
    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"


class IntentType(str, Enum):
    """What the user is trying to do."""
    SYMPTOM_CHECK = "symptom_check"
    MEDICATION_QUESTION = "medication_question"
    APPOINTMENT_REQUEST = "appointment_request"
    EMERGENCY_HELP = "emergency_help"
    HEALTH_EDUCATION = "health_education"


class Severity(str, Enum):
    """Symptom severity as described by the user."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class SemanticType(str, Enum):
    """Medical concept categories from SNOMED-CT."""
    SIGN_OR_SYMPTOM = "Sign or Symptom"
    CLINICAL_FINDING = "Clinical Finding"
    DISEASE_OR_SYNDROME = "Disease or Syndrome"
    BODY_STRUCTURE = "Body Structure"


class DrugSeverity(str, Enum):
    """Drug interaction severity levels."""
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"


class ReliabilityTier(str, Enum):
    """Trust level for medical sources."""
    TIER_1 = "tier_1"   # Peer-reviewed clinical guidelines (AHA, ESC, NICE)
    TIER_2 = "tier_2"   # Government encyclopedias (MedlinePlus, Mayo Clinic)
    TIER_3 = "tier_3"   # General health websites


class FeedbackType(str, Enum):
    """Types of user feedback."""
    CORRECTION = "correction"        # "Actually, it's not chest pain, it's throat pain"
    CONFIRMATION = "confirmation"    # "Yes, that sounds right"
    NEW_SYMPTOMS = "new_symptoms"    # "I also have a rash now"
    NONE = "none"


class SafetyDecision(str, Enum):
    """Safety Router's routing decision."""
    EMERGENCY_BYPASS = "emergency_bypass"
    ROUTINE = "routine"
    URGENT = "urgent"


# ═══════════════════════════════════════════════════════════
# CORE DOMAIN MODELS
# ═══════════════════════════════════════════════════════════

class Symptom(BaseModel):
    """A single symptom extracted from user input."""
    name: str                           # "chest pain"
    raw_text: str = ""                  # "severe crushing chest pain" (original phrase)
    negated: bool = False               # True if "I do NOT have fever"
    duration: str = "unknown"           # "2 hours", "3 days"
    severity: Severity = Severity.UNKNOWN


class NormalizedSymptom(BaseModel):
    """A symptom after ontology normalization (SNOMED/ICD-10 coded)."""
    original_term: str                  # "chest pain"
    snomed_code: str                    # "29857009"
    snomed_label: str                   # "Chest pain (finding)"
    icd10_code: str                     # "R07.9"
    semantic_type: SemanticType = SemanticType.SIGN_OR_SYMPTOM


class UserProfile(BaseModel):
    """User demographics and medical context (written to DB 4)."""
    user_id: UUID = Field(default_factory=uuid4)
    age: int | None = None
    gender: str | None = None
    medical_history: list[str] = []     # ["diabetes", "atrial fibrillation"]
    allergies: list[str] = []           # ["aspirin", "penicillin"]
    current_medications: list[str] = [] # ["warfarin", "atenolol"]
    lifestyle_factors: list[str] = []   # ["smoker", "sedentary"]
    language: str = "en"
    preferred_units: str = "metric"


class MedicalCondition(BaseModel):
    """A medical condition from DB 1."""
    condition_id: str                   # "MI_001"
    name: str                           # "Myocardial infarction"
    description: str = ""
    icd10_code: str = ""                # "I21.9"
    snomed_code: str = ""               # "22298006"
    urgency: UrgencyLevel
    body_system: str = ""               # "cardiovascular"
    source: str = ""                    # "AHA Guideline 2023"


class SymptomConditionMapping(BaseModel):
    """Maps a symptom to a condition with importance weight (from DB 1)."""
    condition_id: str
    snomed_code: str                    # Symptom's SNOMED code
    symptom_name: str                   # "chest pain"
    importance: float = Field(ge=0.0, le=1.0)
    is_cardinal: bool = False           # True = defining symptom


class DrugInteraction(BaseModel):
    """A drug interaction record from DB 1."""
    drug_name: str                      # "warfarin"
    interacts_with: str                 # "aspirin"
    contraindicated_allergies: list[str] = []
    contraindicated_conditions: list[str] = []
    severity: DrugSeverity
    description: str = ""               # "Extreme bleeding risk"
    source: str = ""                    # "DrugBank"


class EmergencyRule(BaseModel):
    """A hard-coded emergency triage rule from DB 1."""
    rule_name: str                      # "cardiac_emergency"
    required_symptoms: list[str]        # ["chest pain", "shortness of breath"]
    risk_factors: dict = {}             # {"min_age": 50, "conditions": ["diabetes"]}
    action: str                         # "Call 911 immediately"
    confidence_boost: float = 0.0


class TreatmentGuideline(BaseModel):
    """Treatment protocol for a condition from DB 1."""
    condition_id: str
    urgency_level: UrgencyLevel
    recommendation: str                 # "Call emergency services immediately"
    self_care: list[str] = []           # ["Chew aspirin", "Sit upright"]
    specialist_type: str = ""           # "cardiologist"
    source: str = ""
    source_url: str = ""


class SpecialistInfo(BaseModel):
    """Specialist directory entry from DB 1."""
    specialist_type: str                # "Cardiologist"
    condition_ids: list[str] = []       # ["MI_001", "UA_001"]
    body_systems: list[str] = []        # ["cardiovascular"]
    description: str = ""


class OntologyTerm(BaseModel):
    """A term in the ontology mapping from DB 3."""
    term: str                           # "chest pain"
    snomed_code: str                    # "29857009"
    snomed_label: str                   # "Chest pain (finding)"
    icd10_code: str = ""
    umls_cui: str = ""                  # "C0008031"
    semantic_type: SemanticType = SemanticType.SIGN_OR_SYMPTOM


class OntologySynonym(BaseModel):
    """Lay-term synonym mapping from DB 3."""
    synonym: str                        # "tummy ache"
    canonical_term: str                 # "abdominal pain"
    language: str = "en"
    source: str = ""                    # "manual", "UMLS"


class VectorDocument(BaseModel):
    """A document chunk in the vector store (DB 2)."""
    id: str                             # UUID
    text: str                           # The actual text chunk
    source: str                         # "Mayo Clinic", "AHA"
    source_url: str                     # "https://..."
    topic: str                          # "Heart Attack"
    body_system: str = ""               # "cardiovascular"
    chunk_index: int = 0
    total_chunks: int = 1
    publish_date: str = ""
    reliability_tier: ReliabilityTier = ReliabilityTier.TIER_2


class Citation(BaseModel):
    """A citation attached to the final explanation."""
    title: str                          # "Heart Attack Warning Signs"
    source: str                         # "AHA"
    url: str                            # "https://www.heart.org/..."
    reliability_tier: ReliabilityTier = ReliabilityTier.TIER_2


# ═══════════════════════════════════════════════════════════
# SESSION & CONVERSATION MODELS
# ═══════════════════════════════════════════════════════════

class ConversationTurn(BaseModel):
    """A single turn in the conversation history."""
    role: str                           # "user" | "assistant"
    content: str                        # The message text
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationSession(BaseModel):
    """A full conversation session."""
    session_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    turns: list[ConversationTurn] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    final_urgency: UrgencyLevel | None = None
    final_confidence: float | None = None


class BlockedTreatment(BaseModel):
    """A treatment that was blocked by the Contraindication Agent."""
    treatment: str                      # "Chew 325mg aspirin"
    reason: str                         # "aspirin allergy + warfarin interaction"
    blocked_by: str                     # "K2_blacklist + DB4_allergy"
    severity: DrugSeverity
    alternative: str = ""               # "Use Acetaminophen instead"
```

---
---

## 3. Database ORM Models (`db_models.py`)

These map directly to the PostgreSQL tables and Elasticsearch index. Used by the `db/` layer for queries.

```python
# neurohealth/schemas/db_models.py
"""SQLAlchemy-style models for all 5 databases."""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4


# ═══════════════════════════════════════════════════════════
# DB 1: MEDICAL KNOWLEDGE BASE (PostgreSQL)
# ═══════════════════════════════════════════════════════════

class ConditionRow(BaseModel):
    """Row from the `conditions` table."""
    condition_id: str                   # PK: "MI_001"
    name: str                           # "Myocardial infarction"
    description: str = ""
    icd10_code: str = ""
    snomed_code: str = ""
    urgency: str                        # "emergency" | "urgent" | "routine"
    body_system: str = ""
    source: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConditionSymptomMapRow(BaseModel):
    """Row from the `condition_symptom_map` table."""
    id: int                             # PK auto
    condition_id: str                   # FK → conditions
    snomed_code: str                    # Symptom's SNOMED code
    symptom_name: str = ""
    importance: float = Field(ge=0.0, le=1.0)
    is_cardinal: bool = False
    source: str = ""


class TreatmentGuidelineRow(BaseModel):
    """Row from the `treatment_guidelines` table."""
    id: int
    condition_id: str                   # FK → conditions
    urgency_level: str
    recommendation: str
    self_care: list[str] = []           # PostgreSQL TEXT[]
    specialist_type: str = ""
    source: str = ""
    source_url: str = ""


class DrugInteractionRow(BaseModel):
    """Row from the `drug_interactions` table."""
    id: int
    drug_name: str
    interacts_with: str = ""
    contraindicated_allergies: list[str] = []   # TEXT[]
    contraindicated_conditions: list[str] = []  # TEXT[]
    severity: str                               # "major" | "moderate" | "minor"
    description: str = ""
    source: str = ""


class EmergencyRuleRow(BaseModel):
    """Row from the `emergency_rules` table."""
    id: int
    rule_name: str = ""
    required_symptoms: list[str]        # TEXT[]
    risk_factors: dict = {}             # JSONB
    action: str
    confidence_boost: float = 0.0
    source: str = ""


class SpecialistDirectoryRow(BaseModel):
    """Row from the `specialist_directory` table."""
    id: int
    specialist_type: str
    condition_ids: list[str] = []       # TEXT[]
    body_systems: list[str] = []        # TEXT[]
    description: str = ""


# ═══════════════════════════════════════════════════════════
# DB 3: ONTOLOGY MAPPING (PostgreSQL)
# ═══════════════════════════════════════════════════════════

class OntologyTermRow(BaseModel):
    """Row from the `ontology_terms` table."""
    id: int
    term: str                           # "chest pain"
    snomed_code: str = ""
    snomed_label: str = ""
    icd10_code: str = ""
    umls_cui: str = ""
    semantic_type: str = ""


class OntologySynonymRow(BaseModel):
    """Row from the `ontology_synonyms` table."""
    id: int
    synonym: str                        # "tummy ache"
    canonical_term: str                 # "abdominal pain"
    language: str = "en"
    source: str = ""


class OntologyHierarchyRow(BaseModel):
    """Row from the `ontology_hierarchy` table."""
    id: int
    parent_code: str                    # SNOMED code of parent
    child_code: str                     # SNOMED code of child
    relationship: str = "is_a"          # "is_a" | "part_of" | "associated_with"


# ═══════════════════════════════════════════════════════════
# DB 4: USER PROFILE (PostgreSQL with pgcrypto)
# ═══════════════════════════════════════════════════════════

class UserProfileRow(BaseModel):
    """
    Row from the `user_profiles` table.
    NOTE: In the actual database, age/gender/medical_history/allergies/medications
    are stored as BYTEA (encrypted). This model represents the DECRYPTED view
    that agents work with in memory.
    """
    user_id: UUID = Field(default_factory=uuid4)
    age: int | None = None
    gender: str | None = None
    medical_history: list[str] = []         # Decrypted from BYTEA → JSON → list
    allergies: list[str] = []               # Decrypted from BYTEA → JSON → list
    current_medications: list[str] = []     # Decrypted from BYTEA → JSON → list
    language: str = "en"
    preferred_units: str = "metric"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationSessionRow(BaseModel):
    """Row from the `conversation_sessions` table."""
    session_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    final_urgency: str | None = None
    final_confidence: float | None = None


# ═══════════════════════════════════════════════════════════
# DB 2: VECTOR STORE (Qdrant — not SQL, schema is in Python)
# ═══════════════════════════════════════════════════════════

class VectorPointPayload(BaseModel):
    """Payload stored alongside each vector in Qdrant."""
    text: str                           # The text chunk
    source: str                         # "Mayo Clinic", "AHA"
    source_url: str
    topic: str                          # "Heart Attack"
    body_system: str = ""
    chunk_index: int = 0
    total_chunks: int = 1
    publish_date: str = ""
    reliability_tier: str = "tier_2"    # "tier_1" | "tier_2" | "tier_3"


class VectorSearchResult(BaseModel):
    """A result from a Qdrant similarity search."""
    id: str
    score: float                        # Cosine similarity 0.0–1.0
    payload: VectorPointPayload


# ═══════════════════════════════════════════════════════════
# DB 5: AUDIT LOG (Elasticsearch)
# ═══════════════════════════════════════════════════════════

class AuditLogEntry(BaseModel):
    """A single agent execution log entry in Elasticsearch."""
    session_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_name: str                     # "IntentClassifier", "EmergencyDetection"
    layer: str                          # "input", "knowledge", "reasoning", ...
    input_data: dict                    # What the agent received
    output_data: dict                   # What the agent produced
    confidence: float = 0.0
    evidence_sources: list[str] = []
    reasoning_trace: str = ""           # Step-by-step reasoning text
    processing_time_ms: float = 0.0
    db_queries_made: int = 0
    errors: list[str] = []


class SessionSummaryLog(BaseModel):
    """Session-level summary logged to Elasticsearch after pipeline completes."""
    session_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_agents_run: int               # 16 (routine) or 11 (emergency)
    final_urgency: str
    final_confidence: float
    pipeline_time_ms: float
    emergency_detected: bool
    conditions_found: list[str]         # ["Myocardial infarction"]
    treatments_blocked: list[str]       # ["aspirin"]
    safety_router_decision: str         # "emergency_bypass" | "routine" | "urgent"
```

---
---

## 4. API Request / Response Models (`api_models.py`)

These are the models for the REST API or WebSocket interface between the frontend and the backend.

```python
# neurohealth/schemas/api_models.py
"""API request and response schemas for the NeuroHealth backend."""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4


# ═══════════════════════════════════════════════════════════
# REQUEST MODELS (Frontend → Backend)
# ═══════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """User sends a message."""
    session_id: UUID | None = None      # None = start new session
    user_id: UUID | None = None         # None = anonymous user
    message: str                        # "I have chest pain and I take Warfarin..."
    language: str = "en"


class FeedbackRequest(BaseModel):
    """User provides feedback/correction on the system's response."""
    session_id: UUID
    feedback_type: str                  # "correction" | "confirmation" | "new_symptoms"
    message: str                        # "Actually, it's throat pain, not chest pain"


class AppointmentBookingRequest(BaseModel):
    """User confirms an appointment."""
    session_id: UUID
    specialist: str                     # "Dr. Sharma (Neurologist)"
    date: str                           # "Monday, March 17"
    time: str                           # "3:00 PM"


# ═══════════════════════════════════════════════════════════
# RESPONSE MODELS (Backend → Frontend)
# ═══════════════════════════════════════════════════════════

class ChatResponse(BaseModel):
    """Full pipeline response to the user."""
    session_id: UUID
    urgency: str                        # "emergency" | "urgent" | "routine"
    safety_router_decision: str         # "emergency_bypass" | "routine" | "urgent"

    # Main content (from O1)
    explanation: str                    # The formatted text the user reads
    citations: list[dict] = []          # [{title, source, url}]

    # Safety alerts (from S2)
    blocked_treatments: list[dict] = [] # [{treatment, reason, severity, alternative}]
    warnings: list[str] = []            # Non-blocking safety notes

    # Appointment (from O2) — None on emergency
    appointment: dict | None = None     # {specialist, date, time, slots_remaining}

    # Follow-up (from O3) — None on emergency
    followup: dict | None = None        # {check_in_after, message, escalation_rule}

    # Metadata
    confidence: float
    total_agents_run: int
    pipeline_time_ms: float
    disclaimer: str = "This is not a medical diagnosis. Please consult a healthcare provider."
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FeedbackResponse(BaseModel):
    """Acknowledgement after processing user feedback."""
    session_id: UUID
    feedback_accepted: bool
    action_taken: str                   # "Pipeline re-run with corrected symptoms"
    new_response: ChatResponse | None = None  # The updated response after re-run


class AppointmentBookingResponse(BaseModel):
    """Confirmation of appointment booking."""
    session_id: UUID
    confirmed: bool
    specialist: str
    date: str
    time: str
    confirmation_code: str = ""         # "NH-2025-03-17-001"


class ErrorResponse(BaseModel):
    """Returned when something goes wrong."""
    error_code: str                     # "PIPELINE_ERROR", "INVALID_INPUT"
    message: str                        # Human-readable error message
    details: dict = {}                  # Additional context
    session_id: UUID | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """System health status."""
    status: str                         # "healthy" | "degraded" | "down"
    db1_connected: bool                 # Medical KB
    db2_connected: bool                 # Vector Store
    db3_connected: bool                 # Ontology
    db4_connected: bool                 # User Profile
    db5_connected: bool                 # Audit Log
    uptime_seconds: float
    version: str                        # "0.1.0"
```

---
---

## 5. Configuration Models (`config_models.py`)

These models define the system's tunable parameters — weights, thresholds, model names, etc.

```python
# neurohealth/schemas/config_models.py
"""Configuration and threshold models loaded from configs/default.yaml."""

from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    """Weights used in R1 (Differential Diagnosis) scoring formula."""
    symptom_match_weight: float = 0.4   # How much symptom matching matters
    risk_factor_weight: float = 0.3     # How much demographics matter
    history_weight: float = 0.3         # How much medical history matters


class UrgencyThresholds(BaseModel):
    """Thresholds for R2 (Urgency Scoring) decisions."""
    emergency_score: float = 0.85       # Score above this → emergency
    urgent_score: float = 0.60          # Score above this → urgent
    routine_score: float = 0.0          # Everything below urgent → routine
    min_age_cardiac_risk: int = 50      # Age above which cardiac becomes emergency
    confidence_uncertainty_threshold: float = 0.6  # Below this → S3 flags uncertainty


class RiskMultipliers(BaseModel):
    """Risk multipliers for P1 (Risk Adjustment)."""
    age_above_65: float = 0.3           # Added to risk multiplier if age > 65
    diabetes: float = 0.5               # Added if diabetes in history
    heart_disease: float = 0.7          # Added if heart disease in history
    ckd: float = 0.4                    # Added if CKD in history
    immunocompromised: float = 0.6      # Added if immunocompromised
    pregnancy: float = 0.3             # Added if pregnant


class EmbeddingConfig(BaseModel):
    """Configuration for K4 (Vector RAG Agent)."""
    model_name: str = "text-embedding-3-small"
    vector_dimensions: int = 1536
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 50
    top_k: int = 5                      # Number of results to retrieve
    min_relevance_score: float = 0.7    # Drop results below this


class LLMConfig(BaseModel):
    """Configuration for O1 (Explanation Generator) — the only LLM-using agent."""
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.3            # Low = more factual, less creative
    max_tokens: int = 1024
    system_prompt: str = (
        "You are a medical health assistant. Generate clear, empathetic explanations "
        "based ONLY on the structured data provided. Never invent medical facts. "
        "Always include the disclaimer that this is not a diagnosis."
    )


class DatabaseConfig(BaseModel):
    """Connection strings and settings for all 5 databases."""
    db1_medical_kb_url: str = "postgresql://user:pass@localhost:5432/neurohealth_medical"
    db2_vector_store_url: str = "http://localhost:6333"   # Qdrant
    db2_collection_name: str = "medical_knowledge"
    db3_ontology_url: str = "postgresql://user:pass@localhost:5432/neurohealth_ontology"
    db4_user_profile_url: str = "postgresql://user:pass@localhost:5432/neurohealth_users"
    db4_encryption_key: str = "CHANGE_ME_IN_PRODUCTION"   # For pgcrypto
    db5_audit_log_url: str = "http://localhost:9200"       # Elasticsearch
    db5_index_name: str = "neurohealth-audit"


class PipelineConfig(BaseModel):
    """Master configuration loaded from configs/default.yaml."""
    scoring: ScoringWeights = ScoringWeights()
    urgency: UrgencyThresholds = UrgencyThresholds()
    risk: RiskMultipliers = RiskMultipliers()
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMConfig = LLMConfig()
    database: DatabaseConfig = DatabaseConfig()
    max_pipeline_timeout_ms: int = 30000   # 30 seconds max
    enable_audit_logging: bool = True
    enable_feedback_loop: bool = True
```

### Example `configs/default.yaml`

```yaml
scoring:
  symptom_match_weight: 0.4
  risk_factor_weight: 0.3
  history_weight: 0.3

urgency:
  emergency_score: 0.85
  urgent_score: 0.60
  min_age_cardiac_risk: 50
  confidence_uncertainty_threshold: 0.6

risk:
  age_above_65: 0.3
  diabetes: 0.5
  heart_disease: 0.7
  ckd: 0.4

embedding:
  model_name: "text-embedding-3-small"
  vector_dimensions: 1536
  chunk_size_tokens: 512
  top_k: 5

llm:
  model_name: "gpt-4o-mini"
  temperature: 0.3
  max_tokens: 1024

database:
  db4_encryption_key: "${DB4_ENCRYPTION_KEY}"  # From environment variable

max_pipeline_timeout_ms: 30000
enable_audit_logging: true
enable_feedback_loop: true
```

---
---

## 6. Complete Model Dependency Map

```mermaid
graph TD
    subgraph "schemas/models.py (Shared)"
        E[Enums: UrgencyLevel, IntentType, Severity, etc.]
        S[Symptom]
        NS[NormalizedSymptom]
        UP[UserProfile]
        MC[MedicalCondition]
        DI[DrugInteraction]
        ER[EmergencyRule]
        TG[TreatmentGuideline]
        CT[Citation]
        BT[BlockedTreatment]
        CS[ConversationSession]
    end

    subgraph "schemas/state.py"
        PS[PipelineState TypedDict]
    end

    subgraph "schemas/db_models.py"
        CR[ConditionRow]
        CSM[ConditionSymptomMapRow]
        DIR[DrugInteractionRow]
        OTR[OntologyTermRow]
        UPR[UserProfileRow]
        ALE[AuditLogEntry]
    end

    subgraph "schemas/api_models.py"
        REQ[ChatRequest]
        RES[ChatResponse]
        FBR[FeedbackRequest]
        ERR[ErrorResponse]
    end

    subgraph "schemas/config_models.py"
        PC[PipelineConfig]
        SW[ScoringWeights]
        UT[UrgencyThresholds]
        EC[EmbeddingConfig]
    end

    E --> S
    E --> MC
    E --> DI
    E --> BT
    S --> PS
    NS --> PS
    UP --> PS
    MC --> CR
    DI --> DIR
    PS --> RES
    PC --> SW
    PC --> UT
    PC --> EC
```

---

## Model Count Summary

| File | Models | Description |
|:-----|:------:|:------------|
| `state.py` | 1 | PipelineState TypedDict |
| `models.py` | 10 enums + 14 classes = **24** | Shared domain models |
| `db_models.py` | **14** | Database table/document models |
| `api_models.py` | **7** | REST API schemas |
| `config_models.py` | **7** | Configuration / tuning models |
| `agent_outputs.py` | **21** | Agent output models (separate artifact) |
| **Total** | **74 models** | Complete type-safe system |
