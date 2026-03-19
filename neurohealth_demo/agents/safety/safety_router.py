"""Safety Router — The critical decision point that determines pipeline flow.
NOT an agent itself, but the conditional branching logic."""

from agents.base_agent import BaseAgent


class SafetyRouter(BaseAgent):
    name = "SafetyRouter"
    layer = "safety"

    def _process(self, state: dict) -> dict:
        emergency = state.get("emergency_flag", {})
        uncertainty = state.get("uncertainty_flag", {})
        urgency_level = state.get("urgency_level", "routine")

        # Decision 1: Emergency bypass
        if emergency.get("is_emergency") or urgency_level == "emergency":
            return {
                "safety_router_decision": "emergency_bypass",
            }

        # Decision 2: Too uncertain — refer to professional
        if uncertainty.get("is_uncertain") and uncertainty.get("confidence", 1.0) < 0.30:
            return {
                "safety_router_decision": "uncertain_referral",
            }

        # Decision 3: Normal flow
        return {
            "safety_router_decision": "normal",
        }
