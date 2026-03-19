"""I2 — Symptom Extractor: Pulls symptoms from user's natural language input."""

import re
from agents.base_agent import BaseAgent


class SymptomExtractor(BaseAgent):
    name = "SymptomExtractor"
    layer = "input"

    # Known symptoms to match against (covers our demo data)
    KNOWN_SYMPTOMS = [
        "chest pain", "sharp chest pain", "left arm pain", "arm pain", "jaw pain",
        "shortness of breath", "difficulty breathing",
        "headache", "severe headache", "migraine",
        "nausea", "vomiting",
        "fever", "high temperature", "chills",
        "cough", "coughing blood",
        "abdominal pain", "stomach pain",
        "diarrhea", "heartburn",
        "sweating", "cold sweat",
        "sore throat", "difficulty swallowing",
        "burning urination", "frequent urination",
        "runny nose", "nasal congestion", "sneezing",
        "fatigue", "weakness",
        "sensitivity to light", "visual disturbances", "blurry vision",
        "flank pain", "back pain", "side pain",
        "swelling throat", "hives",
        "rapid heartbeat", "heart racing",
        "confusion", "dizziness",
        "facial drooping", "speech difficulty", "slurred speech",
        "sudden weakness one side",
        "neck pain", "stiff neck",
        "itchy eyes",
        "swollen lymph nodes", "swollen glands",
        "low blood pressure",
    ]

    def _process(self, state: dict) -> dict:
        text = state.get("user_input", "").lower()

        # Match known symptoms (longest match first to avoid partial hits)
        sorted_symptoms = sorted(self.KNOWN_SYMPTOMS, key=len, reverse=True)
        found = []
        remaining_text = text

        for symptom in sorted_symptoms:
            if symptom in remaining_text:
                found.append(symptom)
                # Remove matched text to avoid double-counting
                remaining_text = remaining_text.replace(symptom, " ", 1)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for s in found:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return {
            "extracted_symptoms": unique,
        }
