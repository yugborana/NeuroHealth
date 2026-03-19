"""I3 — Ontology Normalizer: Maps extracted symptoms to SNOMED/ICD-10 codes via DB 3."""

from agents.base_agent import BaseAgent
from db.ontology import normalize_with_synonym


class OntologyNormalizer(BaseAgent):
    name = "OntologyNormalizer"
    layer = "input"

    def _process(self, state: dict) -> dict:
        symptoms = state.get("extracted_symptoms", [])
        normalized = []

        for symptom in symptoms:
            result = normalize_with_synonym(self.conn, symptom)
            if result:
                normalized.append({
                    "term": result["term"],
                    "original": symptom,
                    "snomed_code": result["snomed_code"],
                    "snomed_label": result.get("snomed_label", ""),
                    "icd10_code": result.get("icd10_code", ""),
                    "resolved_via": result.get("resolved_via", "direct"),
                })
            else:
                # Keep unresolved symptoms with a flag
                normalized.append({
                    "term": symptom,
                    "original": symptom,
                    "snomed_code": None,
                    "resolved_via": "unresolved",
                })

        return {
            "normalized_symptoms": normalized,
        }
