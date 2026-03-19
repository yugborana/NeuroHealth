"""P1 — Risk Adjustment Agent: Adjusts diagnosis based on personal risk factors."""

from agents.base_agent import BaseAgent


class RiskAdjustmentAgent(BaseAgent):
    name = "RiskAdjustment"
    layer = "personalization"

    def _process(self, state: dict) -> dict:
        context = state.get("user_context", {})
        age = context.get("age")
        sex = context.get("sex")
        history = context.get("medical_history", [])

        adjustments = []

        if age and age > 65:
            adjustments.append({"factor": "age > 65", "adjustment": "+0.08 urgency", "note": "Elderly patients have higher complication risks"})
        if age and age > 80:
            adjustments.append({"factor": "age > 80", "adjustment": "+0.05 urgency", "note": "Very elderly — lower threshold for specialist referral"})

        if "diabetes" in history:
            adjustments.append({"factor": "diabetes history", "adjustment": "cardiac risk +", "note": "Diabetes increases cardiovascular risk 2-4x"})

        if "previous mi" in history or "heart attack" in history:
            adjustments.append({"factor": "previous MI", "adjustment": "cardiac risk ++", "note": "History of MI significantly increases recurrence risk"})

        if "hypertension" in history or "high blood pressure" in history:
            adjustments.append({"factor": "hypertension", "adjustment": "stroke risk +", "note": "Hypertension is the #1 modifiable stroke risk factor"})

        if "asthma" in history:
            adjustments.append({"factor": "asthma", "adjustment": "avoid NSAIDs/beta-blockers", "note": "NSAIDs and beta-blockers can trigger bronchospasm"})

        if "pregnancy" in history or "pregnant" in history:
            adjustments.append({"factor": "pregnancy", "adjustment": "restrict medications", "note": "Many drugs contraindicated in pregnancy"})

        return {
            "risk_adjustments": adjustments,
        }
