"""I4 — Context Extractor: Extracts demographics, medications, allergies from user input.
Also writes to DB 4 (User Profile)."""

import re
from agents.base_agent import BaseAgent
from db.user_profile import save_user_profile


class ContextExtractor(BaseAgent):
    name = "ContextExtractor"
    layer = "input"

    KNOWN_DRUGS = [
        "warfarin", "aspirin", "ibuprofen", "sertraline", "metformin",
        "lisinopril", "atenolol", "amoxicillin", "omeprazole", "sumatriptan",
        "naproxen", "heparin", "tramadol", "fluoxetine", "verapamil",
        "acetaminophen", "tylenol", "advil", "motrin",
    ]

    KNOWN_ALLERGENS = [
        "aspirin", "penicillin", "sulfa", "sulfamethoxazole", "ibuprofen",
        "nsaids", "latex", "peanut", "shellfish", "codeine", "morphine",
        "amoxicillin", "cephalosporin",
    ]

    KNOWN_CONDITIONS = [
        "diabetes", "heart disease", "hypertension", "high blood pressure",
        "asthma", "previous mi", "heart attack", "stroke", "liver disease",
        "kidney disease", "cancer", "copd", "depression", "anxiety",
        "pregnancy", "pregnant",
    ]

    def _process(self, state: dict) -> dict:
        text = state.get("user_input", "").lower()

        context = {
            "age": self._extract_age(text),
            "sex": self._extract_sex(text),
            "medications": self._extract_list(text, self.KNOWN_DRUGS),
            "allergies": self._extract_allergies(text),
            "medical_history": self._extract_list(text, self.KNOWN_CONDITIONS),
        }

        # Save to DB 4
        session_id = state.get("session_id", "demo_session")
        if self.conn:
            save_user_profile(self.conn, session_id, context)

        return {
            "user_context": context,
        }

    def _extract_age(self, text: str) -> int | None:
        patterns = [
            r"(?:i am|i'm|age|aged)\s*(\d{1,3})",
            r"(\d{1,3})\s*(?:year|yr|y/?o|years?\s*old)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                age = int(match.group(1))
                if 0 < age < 130:
                    return age
        return None

    def _extract_sex(self, text: str) -> str | None:
        if re.search(r"\b(male|man|boy|he|his)\b", text):
            return "male"
        if re.search(r"\b(female|woman|girl|she|her)\b", text):
            return "female"
        return None

    def _extract_list(self, text: str, known_items: list[str]) -> list[str]:
        found = []
        for item in known_items:
            if item in text:
                found.append(item)
        return found

    def _extract_allergies(self, text: str) -> list[str]:
        # Look for allergy mentions
        allergy_section = ""
        patterns = [
            r"allerg(?:ic|y|ies)\s+(?:to\s+)?(.{5,80}?)(?:\.|,\s*(?:history|i |my |age)|\band\b.{0,30}(?:\.|$))",
            r"allerg(?:ic|y|ies)\s+(?:to\s+)?(.{5,80})$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                allergy_section = match.group(1)
                break

        if not allergy_section:
            allergy_section = text

        found = []
        for allergen in self.KNOWN_ALLERGENS:
            if allergen in allergy_section:
                found.append(allergen)

        return found
