"""R3 — Treatment Suggestion Agent: Provides treatment recommendations from DB 1."""

from agents.base_agent import BaseAgent
from db.medical_kb import get_treatment


class TreatmentSuggestionAgent(BaseAgent):
    name = "TreatmentSuggestion"
    layer = "reasoning"

    def _process(self, state: dict) -> dict:
        diagnoses = state.get("differential_diagnosis", [])

        if not diagnoses:
            return {"treatment_suggestions": []}

        suggestions = []
        for diag in diagnoses[:3]:  # Top 3 conditions
            treatment = get_treatment(self.conn, diag["condition_id"])
            if treatment:
                suggestions.append({
                    "condition": diag["condition"],
                    "condition_id": diag["condition_id"],
                    "recommendation": treatment["recommendation"],
                    "self_care": treatment["self_care"],
                    "specialist_type": treatment["specialist_type"],
                    "source": treatment.get("source", ""),
                })

        return {
            "treatment_suggestions": suggestions,
        }
