"""O3 — Follow-Up Agent: Generates a follow-up care plan."""

from agents.base_agent import BaseAgent


class FollowUpAgent(BaseAgent):
    name = "FollowUpAgent"
    layer = "output"

    def _process(self, state: dict) -> dict:
        urgency = state.get("urgency_level", "routine")
        diagnoses = state.get("differential_diagnosis", [])
        treatments = state.get("treatment_suggestions", [])
        lifestyle = state.get("lifestyle_recommendations", [])
        router = state.get("safety_router_decision", "normal")

        if router == "emergency_bypass":
            return {
                "followup_plan": {
                    "timeline": "Immediate",
                    "steps": [
                        "Call 911 or go to the nearest emergency room immediately",
                        "Do not drive yourself — have someone else drive or call an ambulance",
                        "If prescribed, take any emergency medications (e.g., nitroglycerin, epinephrine)",
                        "Stay calm and try to rest while waiting for help",
                    ],
                    "monitoring": "Continuous until seen by emergency medical team",
                    "follow_up_appointment": "ER physician will advise on follow-up",
                }
            }

        steps = []
        timeline = "1-2 weeks"

        if urgency == "urgent":
            timeline = "24-48 hours"
            steps.append("See a doctor within 24 hours")
        else:
            steps.append("Schedule a regular check-up with your doctor")

        # Add self-care from treatment suggestions
        if treatments:
            top = treatments[0]
            for sc in top.get("self_care", [])[:3]:
                steps.append(sc)

        # Add lifestyle recommendations
        for rec in lifestyle[:2]:
            steps.append(rec)

        # Monitoring advice
        monitoring = "Track your symptoms daily and note any changes"
        if diagnoses:
            monitoring = f"Monitor for changes in: {', '.join(diagnoses[0].get('matched_symptoms', ['symptoms']))}"

        return {
            "followup_plan": {
                "timeline": timeline,
                "steps": steps,
                "monitoring": monitoring,
                "follow_up_appointment": f"Schedule with {state.get('specialist_info', {}).get('type', 'your doctor')}",
            }
        }
