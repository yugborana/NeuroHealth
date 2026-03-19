"""
Pipeline Orchestrator — Wires all agents into a sequential pipeline with Safety Router branching.
This simulates the LangGraph orchestrator from the production architecture.
"""

import uuid
from pathlib import Path

from db.setup import get_connection
from db.audit_log import AuditLog

# Layer 1: Input Understanding
from agents.input.intent_classifier import IntentClassifier
from agents.input.symptom_extractor import SymptomExtractor
from agents.input.ontology_normalizer import OntologyNormalizer
from agents.input.context_extractor import ContextExtractor

# Layer 2: Knowledge Retrieval
from agents.knowledge.medical_knowledge import MedicalKnowledgeAgent
from agents.knowledge.drug_interaction import DrugInteractionAgent
from agents.knowledge.vector_rag import VectorRAGAgent

# Layer 3: Clinical Reasoning
from agents.reasoning.differential_diagnosis import DifferentialDiagnosisAgent
from agents.reasoning.urgency_scoring import UrgencyScoringAgent
from agents.reasoning.treatment_suggestion import TreatmentSuggestionAgent

# Layer 4: Safety
from agents.safety.emergency_detection import EmergencyDetectionAgent
from agents.safety.contraindication import ContraindicationAgent
from agents.safety.uncertainty_detector import UncertaintyDetector
from agents.safety.safety_router import SafetyRouter

# Layer 5: Personalization
from agents.personalization.risk_adjustment import RiskAdjustmentAgent
from agents.personalization.lifestyle_recommendation import LifestyleRecommendationAgent
from agents.personalization.specialist_directory import SpecialistDirectoryAgent

# Layer 6: Output
from agents.output.explanation_generator import ExplanationGenerator
from agents.output.appointment_scheduler import AppointmentScheduler
from agents.output.followup_agent import FollowUpAgent


DATA_DIR = Path(__file__).parent / "data"


def run_pipeline(user_input: str, session_id: str = None) -> dict:
    """Run the full NeuroHealth pipeline for a given user input.
    Returns the final PipelineState dict."""

    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    conn = get_connection()
    audit = AuditLog()
    articles_dir = DATA_DIR / "articles"

    # Initialize state
    state = {
        "user_input": user_input,
        "session_id": session_id,
        "agent_trace": [],
        "errors": [],
    }

    agent_kwargs = {"conn": conn, "audit": audit}

    # ─── Layer 1: Input Understanding ───
    IntentClassifier(**agent_kwargs).run(state)
    SymptomExtractor(**agent_kwargs).run(state)
    OntologyNormalizer(**agent_kwargs).run(state)
    ContextExtractor(**agent_kwargs).run(state)

    # ─── Layer 2: Knowledge Retrieval ───
    MedicalKnowledgeAgent(**agent_kwargs).run(state)
    DrugInteractionAgent(**agent_kwargs).run(state)
    VectorRAGAgent(**agent_kwargs, articles_dir=articles_dir).run(state)

    # ─── Layer 3: Clinical Reasoning ───
    DifferentialDiagnosisAgent(**agent_kwargs).run(state)
    UrgencyScoringAgent(**agent_kwargs).run(state)
    TreatmentSuggestionAgent(**agent_kwargs).run(state)

    # ─── Layer 4: Safety ───
    EmergencyDetectionAgent(**agent_kwargs).run(state)
    ContraindicationAgent(**agent_kwargs).run(state)
    UncertaintyDetector(**agent_kwargs).run(state)
    SafetyRouter(**agent_kwargs).run(state)

    # ─── Safety Router Decision ───
    decision = state.get("safety_router_decision", "normal")

    if decision == "emergency_bypass":
        # Skip personalization, go straight to output
        pass
    elif decision == "uncertain_referral":
        # Skip personalization, generate cautious output
        pass
    else:
        # ─── Layer 5: Personalization (Normal flow only) ───
        RiskAdjustmentAgent(**agent_kwargs).run(state)
        LifestyleRecommendationAgent(**agent_kwargs).run(state)
        SpecialistDirectoryAgent(**agent_kwargs).run(state)

    # ─── Layer 6: Output (Always runs) ───
    ExplanationGenerator(**agent_kwargs).run(state)
    AppointmentScheduler(**agent_kwargs).run(state)
    FollowUpAgent(**agent_kwargs).run(state)

    conn.close()
    return state
