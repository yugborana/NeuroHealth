"""P2 — Lifestyle Recommendation Agent: Provides lifestyle advice based on condition."""

from agents.base_agent import BaseAgent


class LifestyleRecommendationAgent(BaseAgent):
    name = "LifestyleRecommendation"
    layer = "personalization"

    RECOMMENDATIONS = {
        "cardiovascular": [
            "Maintain a heart-healthy diet low in saturated fat and sodium",
            "Exercise at least 150 minutes per week (brisk walking, cycling)",
            "Monitor blood pressure regularly",
            "Quit smoking if applicable",
        ],
        "respiratory": [
            "Avoid exposure to smoke and pollutants",
            "Practice deep breathing exercises",
            "Stay hydrated to keep mucus thin",
            "Get annual flu vaccination",
        ],
        "neurological": [
            "Maintain a regular sleep schedule (7-9 hours)",
            "Manage stress through meditation or relaxation techniques",
            "Stay hydrated — dehydration can trigger headaches",
            "Keep a symptom diary to identify triggers",
        ],
        "gastrointestinal": [
            "Eat smaller, more frequent meals",
            "Avoid spicy, acidic, and fatty foods",
            "Don't lie down immediately after eating",
            "Stay well-hydrated",
        ],
        "urological": [
            "Drink plenty of water (8+ glasses per day)",
            "Urinate regularly — don't hold it",
            "Wipe front to back to prevent infection",
            "Avoid irritating feminine products",
        ],
        "general": [
            "Get 7-9 hours of sleep per night",
            "Stay hydrated with water throughout the day",
            "Exercise regularly (at least 30 min/day)",
            "Manage stress through healthy coping mechanisms",
        ],
    }

    def _process(self, state: dict) -> dict:
        diagnoses = state.get("differential_diagnosis", [])

        if not diagnoses:
            return {"lifestyle_recommendations": self.RECOMMENDATIONS["general"]}

        top = diagnoses[0]
        body_system = None

        # Map to body system from candidate conditions
        candidates = state.get("candidate_conditions", [])
        for c in candidates:
            if c["condition_id"] == top["condition_id"]:
                body_system = c.get("body_system", "").lower()
                break

        recs = self.RECOMMENDATIONS.get(body_system, self.RECOMMENDATIONS["general"])

        return {
            "lifestyle_recommendations": recs,
        }
