"""I1 — Intent Classifier: Determines what the user is asking about."""

import re
from agents.base_agent import BaseAgent


class IntentClassifier(BaseAgent):
    name = "IntentClassifier"
    layer = "input"

    # Keyword patterns for intent classification
    PATTERNS = {
        "symptom_check": [
            r"\b(pain|ache|hurt|sore|burning|swelling|fever|cough|nausea|dizz|vomit|bleed|breath)\b",
            r"\b(symptom|feeling|feel sick|unwell|suffering)\b",
            r"\b(chest|head|stomach|throat|back|arm|leg|eye)\b.{0,20}\b(pain|hurt|ache)\b",
        ],
        "drug_query": [
            r"\b(medication|medicine|drug|prescription|dosage|side effect|interact)\b",
            r"\b(taking|prescribed|pill|tablet|capsule)\b",
        ],
        "general_health": [
            r"\b(diet|exercise|sleep|stress|weight|nutrition|lifestyle|prevent)\b",
            r"\b(healthy|wellness|fitness|mental health)\b",
        ],
    }

    def _process(self, state: dict) -> dict:
        text = state.get("user_input", "").lower()

        scores = {}
        for intent, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text)
                score += len(matches)
            scores[intent] = score

        # Pick highest scoring intent
        if not any(scores.values()):
            best_intent = "symptom_check"  # Default
            confidence = 0.5
        else:
            best_intent = max(scores, key=scores.get)
            total = sum(scores.values())
            confidence = round(scores[best_intent] / total, 2) if total > 0 else 0.5

        return {
            "intent": best_intent,
            "intent_confidence": min(confidence, 0.99),
        }
