"""K1 — Medical Knowledge Agent: Queries DB 1 for candidate conditions matching symptoms."""

from agents.base_agent import BaseAgent
from db.medical_kb import get_candidate_conditions


class MedicalKnowledgeAgent(BaseAgent):
    name = "MedicalKnowledge"
    layer = "knowledge"

    def _process(self, state: dict) -> dict:
        normalized = state.get("normalized_symptoms", [])

        # Collect SNOMED codes (skip unresolved)
        snomed_codes = [s["snomed_code"] for s in normalized if s.get("snomed_code")]

        candidates = get_candidate_conditions(self.conn, snomed_codes)

        return {
            "candidate_conditions": candidates,
        }
