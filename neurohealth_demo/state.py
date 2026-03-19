"""
PipelineState — The shared state object passed through all agents.
Uses TypedDict so every agent sees the full type contract.
"""

from typing import TypedDict, Optional


class PipelineState(TypedDict, total=False):
    # ─── Raw Input ───
    user_input: str
    session_id: str

    # ─── Layer 1: Input Understanding ───
    intent: str                          # symptom_check | drug_query | general_health
    intent_confidence: float
    extracted_symptoms: list[str]        # ["chest pain", "shortness of breath"]
    normalized_symptoms: list[dict]      # [{"term": "chest pain", "snomed": "29857009"}]
    user_context: dict                   # {"age": 68, "sex": "male", "medications": [...], ...}

    # ─── Layer 2: Knowledge Retrieval ───
    candidate_conditions: list[dict]     # [{"condition_id": "MI_001", "name": "...", "score": 3.2}]
    drug_interactions: list[dict]        # [{"drug": "warfarin", "interacts_with": "aspirin", "severity": "major"}]
    rag_context: list[dict]              # [{"text": "...", "source": "heart_attack.txt", "score": 0.96}]

    # ─── Layer 3: Clinical Reasoning ───
    differential_diagnosis: list[dict]   # [{"condition": "MI", "confidence": 0.94, "rank": 1}]
    urgency_score: float                 # 0.0-1.0
    urgency_level: str                   # "emergency" | "urgent" | "routine"
    treatment_suggestions: list[dict]    # [{"recommendation": "...", "self_care": [...]}]

    # ─── Layer 4: Safety ───
    emergency_flag: dict                 # {"is_emergency": True, "rule": "cardiac_emergency", ...}
    contraindications: list[dict]        # [{"drug": "aspirin", "reason": "allergy + warfarin"}]
    uncertainty_flag: dict               # {"is_uncertain": False, "confidence": 0.97}
    safety_router_decision: str          # "emergency_bypass" | "normal" | "uncertain_referral"

    # ─── Layer 5: Personalization ───
    risk_adjustments: list[dict]         # [{"factor": "age>65", "adjustment": "+0.1"}]
    lifestyle_recommendations: list[str] # ["Reduce sodium intake", ...]
    specialist_info: dict                # {"type": "Cardiologist", "reason": "..."}

    # ─── Layer 6: Output ───
    explanation: str                     # Final plain-language explanation
    appointment: dict                    # {"recommended": True, "urgency": "immediate", ...}
    followup_plan: dict                  # {"timeline": "24h", "steps": [...]}

    # ─── Metadata ───
    agent_trace: list[dict]              # [{agent, time_ms, input_summary, output_summary}]
    errors: list[str]
