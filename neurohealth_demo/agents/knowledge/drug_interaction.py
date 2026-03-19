"""K2 — Drug Interaction Agent: Checks user's medications for interactions via DB 1."""

from agents.base_agent import BaseAgent
from db.medical_kb import get_drug_interactions


class DrugInteractionAgent(BaseAgent):
    name = "DrugInteraction"
    layer = "knowledge"

    def _process(self, state: dict) -> dict:
        context = state.get("user_context", {})
        medications = context.get("medications", [])

        if not medications:
            return {"drug_interactions": []}

        interactions = get_drug_interactions(self.conn, medications)

        # Also check if any treatment suggestions conflict with user's meds
        # (This will be used by the Contraindication agent later)

        return {
            "drug_interactions": interactions,
        }
