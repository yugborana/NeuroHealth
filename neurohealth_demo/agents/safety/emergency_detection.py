"""S1 — Emergency Detection Agent: Checks if symptom combination triggers emergency rules."""

from agents.base_agent import BaseAgent
from db.medical_kb import get_emergency_rules


class EmergencyDetectionAgent(BaseAgent):
    name = "EmergencyDetection"
    layer = "safety"

    def _process(self, state: dict) -> dict:
        symptoms = [s.lower() for s in state.get("extracted_symptoms", [])]
        user_context = state.get("user_context", {})
        urgency_score = state.get("urgency_score", 0.0)
        age = user_context.get("age")

        rules = get_emergency_rules(self.conn)
        matched_rule = None
        max_boost = 0.0

        for rule in rules:
            required = [s.lower() for s in rule["required_symptoms"]]

            # Check if all required symptoms are present
            matched_count = sum(1 for r in required if any(r in s for s in symptoms))

            # Need at least 2 required symptoms matched, or all if only 1-2 required
            threshold = min(2, len(required))
            if matched_count >= threshold:
                # Check risk factors
                risk_met = True
                risk_factors = rule.get("risk_factors", {})
                if "age_over" in risk_factors and age:
                    if age < risk_factors["age_over"]:
                        risk_met = False

                if matched_count >= len(required) or (matched_count >= threshold and risk_met):
                    if rule["confidence_boost"] > max_boost:
                        max_boost = rule["confidence_boost"]
                        matched_rule = rule

        if matched_rule:
            boosted_score = min(urgency_score + max_boost, 1.0)
            return {
                "emergency_flag": {
                    "is_emergency": True,
                    "rule": matched_rule["rule_name"],
                    "action": matched_rule["action"],
                    "matched_symptoms": symptoms,
                    "original_urgency": urgency_score,
                    "boosted_urgency": round(boosted_score, 2),
                },
                "urgency_score": round(boosted_score, 2),
                "urgency_level": "emergency",
            }

        return {
            "emergency_flag": {
                "is_emergency": False,
                "rule": None,
                "action": None,
            },
        }
