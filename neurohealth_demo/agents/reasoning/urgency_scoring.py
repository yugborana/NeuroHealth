"""R2 — Urgency Scoring Agent: Calculates urgency score based on diagnosis + context."""

from agents.base_agent import BaseAgent


class UrgencyScoringAgent(BaseAgent):
    name = "UrgencyScoring"
    layer = "reasoning"

    # Base urgency scores for each level
    URGENCY_BASE = {
        "emergency": 0.90,
        "urgent": 0.65,
        "routine": 0.30,
    }

    def _process(self, state: dict) -> dict:
        diagnoses = state.get("differential_diagnosis", [])
        user_context = state.get("user_context", {})
        age = user_context.get("age")
        medical_history = user_context.get("medical_history", [])

        if not diagnoses:
            return {
                "urgency_score": 0.3,
                "urgency_level": "routine",
            }

        top = diagnoses[0]
        base_urgency = self.URGENCY_BASE.get(top.get("urgency", "routine"), 0.3)

        # Start with base urgency, modulated by confidence
        score = base_urgency * top.get("confidence", 0.5)

        # Risk factor adjustments
        if age and age > 65:
            score += 0.08
        if age and age > 80:
            score += 0.05

        if "previous mi" in medical_history or "heart attack" in medical_history:
            score += 0.10
        if "diabetes" in medical_history:
            score += 0.05
        if "hypertension" in medical_history or "high blood pressure" in medical_history:
            score += 0.05

        # Multiple high-urgency conditions boost overall urgency
        emergency_count = sum(1 for d in diagnoses if d.get("urgency") == "emergency")
        if emergency_count >= 2:
            score += 0.10

        # Clamp to [0, 1]
        score = round(min(max(score, 0.0), 1.0), 2)

        # Determine level
        if score >= 0.85:
            level = "emergency"
        elif score >= 0.60:
            level = "urgent"
        else:
            level = "routine"

        return {
            "urgency_score": score,
            "urgency_level": level,
        }
