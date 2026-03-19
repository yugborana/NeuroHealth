"""O2 — Appointment Scheduler: Generates appointment recommendations."""

from agents.base_agent import BaseAgent


class AppointmentScheduler(BaseAgent):
    name = "AppointmentScheduler"
    layer = "output"

    def _process(self, state: dict) -> dict:
        urgency = state.get("urgency_level", "routine")
        specialist = state.get("specialist_info", {})
        router = state.get("safety_router_decision", "normal")

        if router == "emergency_bypass":
            return {
                "appointment": {
                    "recommended": True,
                    "urgency": "immediate",
                    "type": "Emergency Room",
                    "timeframe": "NOW — Call 911 or go to nearest ER",
                    "specialist": "Emergency Medicine",
                }
            }

        if urgency == "urgent":
            return {
                "appointment": {
                    "recommended": True,
                    "urgency": "urgent",
                    "type": "Urgent Care or Specialist",
                    "timeframe": "Within 24 hours",
                    "specialist": specialist.get("type", "General Practitioner"),
                }
            }

        return {
            "appointment": {
                "recommended": True,
                "urgency": "routine",
                "type": "Primary Care or Specialist",
                "timeframe": "Within 1-2 weeks",
                "specialist": specialist.get("type", "General Practitioner"),
            }
        }
