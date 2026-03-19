"""S3 — Uncertainty Detector: Flags when the system is not confident in its diagnosis."""

from agents.base_agent import BaseAgent


class UncertaintyDetector(BaseAgent):
    name = "UncertaintyDetector"
    layer = "safety"

    CONFIDENCE_THRESHOLD = 0.40    # Below this = uncertain
    MARGIN_THRESHOLD = 0.10        # If top 2 diagnoses are this close = uncertain

    def _process(self, state: dict) -> dict:
        diagnoses = state.get("differential_diagnosis", [])
        symptoms = state.get("extracted_symptoms", [])

        reasons = []

        # 1. No diagnosis found
        if not diagnoses:
            return {
                "uncertainty_flag": {
                    "is_uncertain": True,
                    "confidence": 0.0,
                    "reasons": ["No matching conditions found for the reported symptoms"],
                }
            }

        top_confidence = diagnoses[0].get("confidence", 0)

        # 2. Low confidence in top diagnosis
        if top_confidence < self.CONFIDENCE_THRESHOLD:
            reasons.append(f"Top diagnosis confidence is low ({top_confidence:.0%})")

        # 3. Top two diagnoses are too close (ambiguous)
        if len(diagnoses) >= 2:
            margin = top_confidence - diagnoses[1].get("confidence", 0)
            if margin < self.MARGIN_THRESHOLD:
                reasons.append(
                    f"Top two diagnoses are closely matched: "
                    f"{diagnoses[0]['condition']} ({diagnoses[0]['confidence']:.0%}) vs "
                    f"{diagnoses[1]['condition']} ({diagnoses[1]['confidence']:.0%})"
                )

        # 4. Very few symptoms provided
        if len(symptoms) < 2:
            reasons.append(f"Only {len(symptoms)} symptom(s) reported — more information needed")

        is_uncertain = len(reasons) > 0

        return {
            "uncertainty_flag": {
                "is_uncertain": is_uncertain,
                "confidence": round(top_confidence, 2),
                "reasons": reasons,
            }
        }
