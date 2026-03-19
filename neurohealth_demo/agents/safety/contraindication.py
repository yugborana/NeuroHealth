"""S2 — Contraindication Agent: Checks if treatments conflict with user's meds/allergies."""

from agents.base_agent import BaseAgent


class ContraindicationAgent(BaseAgent):
    name = "Contraindication"
    layer = "safety"

    def _process(self, state: dict) -> dict:
        user_context = state.get("user_context", {})
        allergies = [a.lower() for a in user_context.get("allergies", [])]
        medications = [m.lower() for m in user_context.get("medications", [])]
        drug_interactions = state.get("drug_interactions", [])
        treatment_suggestions = state.get("treatment_suggestions", [])

        contraindications = []

        # 1. Check for known drug interactions the user is already exposed to
        for interaction in drug_interactions:
            if interaction["severity"] == "major":
                drug1 = interaction["drug_name"].lower()
                drug2 = interaction["interacts_with"].lower()
                if drug1 in medications and drug2 in medications:
                    contraindications.append({
                        "type": "active_interaction",
                        "drug": drug1,
                        "conflicts_with": drug2,
                        "severity": "major",
                        "reason": interaction["description"],
                        "action": "ALERT: Patient is currently taking both drugs",
                    })

        # 2. Check if suggested treatments conflict with allergies
        for suggestion in treatment_suggestions:
            self_care = suggestion.get("self_care", [])
            for step in self_care:
                step_lower = step.lower()
                for allergy in allergies:
                    if allergy in step_lower:
                        contraindications.append({
                            "type": "allergy_conflict",
                            "treatment": step,
                            "allergen": allergy,
                            "condition": suggestion["condition"],
                            "severity": "major",
                            "action": f"DO NOT use {step} — patient is allergic to {allergy}",
                        })

        # 3. Check if suggested treatments conflict with current meds
        for suggestion in treatment_suggestions:
            self_care = suggestion.get("self_care", [])
            for step in self_care:
                step_lower = step.lower()
                for interaction in drug_interactions:
                    drug2 = interaction["interacts_with"].lower()
                    if drug2 in step_lower and interaction["severity"] in ("major", "moderate"):
                        contraindications.append({
                            "type": "treatment_interaction",
                            "treatment": step,
                            "conflicts_with": interaction["drug_name"],
                            "severity": interaction["severity"],
                            "condition": suggestion["condition"],
                            "action": f"CAUTION: {step} may interact with {interaction['drug_name']}",
                        })

        return {
            "contraindications": contraindications,
        }
