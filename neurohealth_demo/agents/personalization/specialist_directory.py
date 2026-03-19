"""P3 — Specialist Directory Agent: Recommends appropriate specialist from DB 1."""

from agents.base_agent import BaseAgent
from db.medical_kb import get_specialist


class SpecialistDirectoryAgent(BaseAgent):
    name = "SpecialistDirectory"
    layer = "personalization"

    def _process(self, state: dict) -> dict:
        diagnoses = state.get("differential_diagnosis", [])

        if not diagnoses:
            return {"specialist_info": {"type": "General Practitioner", "reason": "General evaluation recommended"}}

        top = diagnoses[0]

        # Look up specialist by condition
        spec = get_specialist(self.conn, condition_id=top["condition_id"])

        if not spec:
            # Try by body system
            candidates = state.get("candidate_conditions", [])
            for c in candidates:
                if c["condition_id"] == top["condition_id"]:
                    spec = get_specialist(self.conn, body_system=c.get("body_system", ""))
                    break

        if spec:
            return {
                "specialist_info": {
                    "type": spec["specialist_type"],
                    "reason": f"Recommended for {top['condition']}",
                    "description": spec.get("description", ""),
                }
            }

        return {
            "specialist_info": {
                "type": "General Practitioner",
                "reason": f"No specific specialist found for {top['condition']}",
            }
        }
