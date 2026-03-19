"""R1 — Differential Diagnosis Agent: Ranks candidate conditions by likelihood."""

from agents.base_agent import BaseAgent


class DifferentialDiagnosisAgent(BaseAgent):
    name = "DifferentialDiagnosis"
    layer = "reasoning"

    def _process(self, state: dict) -> dict:
        candidates = state.get("candidate_conditions", [])
        user_context = state.get("user_context", {})
        age = user_context.get("age")

        if not candidates:
            return {"differential_diagnosis": []}

        # Normalize scores to 0-1 confidence range
        max_score = candidates[0]["score"] if candidates else 1
        diagnoses = []

        for rank, c in enumerate(candidates[:5], 1):  # Top 5 only
            confidence = round(c["score"] / max_score, 2) if max_score > 0 else 0

            # Age-based adjustment
            if age:
                confidence = self._adjust_for_age(confidence, c, age)

            diagnoses.append({
                "condition_id": c["condition_id"],
                "condition": c["name"],
                "confidence": min(confidence, 0.99),
                "rank": rank,
                "matched_symptoms": c.get("matched_symptoms", []),
                "urgency": c.get("urgency", "routine"),
            })

        return {
            "differential_diagnosis": diagnoses,
        }

    def _adjust_for_age(self, confidence: float, condition: dict, age: int) -> float:
        """Adjust confidence based on age-condition relationships."""
        cid = condition.get("condition_id", "")

        # Heart attack more likely in older adults
        if cid == "MI_001" and age > 50:
            confidence *= 1.15
        elif cid == "MI_001" and age < 30:
            confidence *= 0.6

        # Stroke more likely in older adults
        if cid == "STR_001" and age > 55:
            confidence *= 1.1
        elif cid == "STR_001" and age < 30:
            confidence *= 0.5

        # UTI more common in women/younger (we don't have sex here, just age)
        if cid == "UTI_001" and age < 40:
            confidence *= 1.05

        # Common cold more likely in younger people
        if cid == "COLD_001" and age < 20:
            confidence *= 1.1

        return round(min(confidence, 0.99), 2)
