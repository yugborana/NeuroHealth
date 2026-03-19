"""O1 — Explanation Generator: Uses Groq LLM to assemble a plain-language explanation from all agent outputs."""

import os
import json
from groq import Groq
from agents.base_agent import BaseAgent


class ExplanationGenerator(BaseAgent):
    name = "ExplanationGenerator"
    layer = "output"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Using the provided Groq API key and model
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        try:
            self.client = Groq(api_key=self.groq_api_key)
        except Exception as e:
            self.client = None
            print(f"Failed to initialize Groq client: {e}")

    def _process(self, state: dict) -> dict:
        diagnoses = state.get("differential_diagnosis", [])
        urgency_level = state.get("urgency_level", "routine")
        emergency = state.get("emergency_flag", {})
        contraindications = state.get("contraindications", [])
        uncertainty = state.get("uncertainty_flag", {})
        rag_context = state.get("rag_context", [])
        symptoms = state.get("extracted_symptoms", [])
        router = state.get("safety_router_decision", "normal")
        user_context = state.get("user_context", {})

        # If LLM client is unavailable, fallback to rule-based string building (stubbed for brevity)
        if not self.client:
            return {"explanation": "Error: Groq LLM API is unavailable for generating the explanation."}

        # Build a structured prompt context from all previous agent outputs
        context_payload = {
            "router_decision": router,
            "patient_context": user_context,
            "reported_symptoms": symptoms,
            "top_diagnoses": [
                {"condition": d["condition"], "confidence": f"{d['confidence']:.0%}"} 
                for d in diagnoses[:3]
            ],
            "urgency": urgency_level,
            "emergency_alerts": emergency if emergency.get("is_emergency") else "None",
            "contraindications": [c["action"] for c in contraindications] if contraindications else "None",
            "medical_references": [ctx["source"] for ctx in rag_context[:3]] if rag_context else "None"
        }

        system_prompt = """You are the Explanation Generator agent for NeuroHealth, an advanced multi-agent health assistant.
Your job is to read the structured JSON data analyzed by 15 preceding expert agents, and synthesize it into a clear, empathetic, and professional explanation for the patient.

CRITICAL RULES:
1. If the router decision is 'emergency_bypass', start your response with a clear, bold emergency warning advising them to seek immediate help.
2. Clearly explain the most likely conditions without making a definitive medical diagnosis.
3. Emphasize any 'contraindications' (e.g., drug interactions or allergy warnings) heavily.
4. Keep the tone compassionate, professional, and easy to understand for a layperson.
5. Do not invent data; only rely on the JSON payload provided.
6. End with a standard disclaimer that this is AI-generated informational material, not professional medical advice."""

        user_prompt = f"Please generate the patient explanation based on the following synthesized pipeline state:\n\n{json.dumps(context_payload, indent=2)}"

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
                model=self.model,
                temperature=0.3, # Keep it relatively deterministic for medical info
            )
            
            explanation_text = chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            explanation_text = f"An error occurred while generating the explanation via Groq: {str(e)}"

        return {
            "explanation": explanation_text,
        }
