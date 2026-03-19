"""
NeuroHealth Demo — Main Entry Point
Run the full 16-agent pipeline and display results.

Usage:
    python main.py
    python main.py "I have chest pain and shortness of breath, I'm 68 years old male taking warfarin"
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import run_pipeline


# ── Color codes for terminal output ──
class C:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def print_header():
    print(f"\n{C.BOLD}{C.CYAN}{'=' * 65}")
    print(f"  NeuroHealth — Multi-Agent Health Assistant Demo")
    print(f"  16 Agents · 6 Layers · Real-time Pipeline")
    print(f"{'=' * 65}{C.END}\n")


def print_agent_trace(state: dict):
    """Print the agent execution trace with timing."""
    trace = state.get("agent_trace", [])
    total_ms = sum(t.get("time_ms", 0) for t in trace)

    print(f"\n{C.BOLD}{'─' * 65}")
    print(f"  PIPELINE TRACE ({len(trace)} agents, {total_ms:.1f}ms total)")
    print(f"{'─' * 65}{C.END}")

    current_layer = ""
    layer_colors = {
        "input": C.BLUE,
        "knowledge": C.CYAN,
        "reasoning": C.GREEN,
        "safety": C.RED,
        "personalization": C.YELLOW,
        "output": C.HEADER,
    }

    for t in trace:
        layer = t.get("layer", "")
        if layer != current_layer:
            current_layer = layer
            color = layer_colors.get(layer, "")
            print(f"\n  {color}{C.BOLD}▸ Layer: {layer.upper()}{C.END}")

        color = layer_colors.get(layer, "")
        error = f" {C.RED}ERROR: {t['error']}{C.END}" if t.get("error") else ""
        print(f"  {color}  ├─ {t['agent']:30s} {t['time_ms']:6.1f}ms{error}{C.END}")


def print_results(state: dict):
    """Print the pipeline results in a readable format."""
    decision = state.get("safety_router_decision", "normal")

    # ── Router Decision ──
    print(f"\n{C.BOLD}{'─' * 65}")
    print(f"  SAFETY ROUTER DECISION")
    print(f"{'─' * 65}{C.END}")

    if decision == "emergency_bypass":
        print(f"  {C.RED}{C.BOLD}🚨 EMERGENCY BYPASS — Skipped personalization{C.END}")
    elif decision == "uncertain_referral":
        print(f"  {C.YELLOW}{C.BOLD}⚠️  UNCERTAIN — Referring to professional{C.END}")
    else:
        print(f"  {C.GREEN}{C.BOLD}✅ NORMAL FLOW — Full pipeline executed{C.END}")

    # ── Extracted Info ──
    print(f"\n{C.BOLD}{'─' * 65}")
    print(f"  INPUT UNDERSTANDING")
    print(f"{'─' * 65}{C.END}")
    print(f"  Intent:    {state.get('intent', '?')} (confidence: {state.get('intent_confidence', 0):.0%})")
    print(f"  Symptoms:  {state.get('extracted_symptoms', [])}")

    normalized = state.get("normalized_symptoms", [])
    if normalized:
        for n in normalized:
            via = f" (via {n['resolved_via']})" if n.get("resolved_via") != "direct" else ""
            snomed = n.get("snomed_code", "?")
            print(f"    → {n['term']:25s} SNOMED: {snomed}{via}")

    ctx = state.get("user_context", {})
    if any(ctx.values()):
        print(f"  Age:       {ctx.get('age', '?')}")
        print(f"  Sex:       {ctx.get('sex', '?')}")
        print(f"  Meds:      {ctx.get('medications', [])}")
        print(f"  Allergies: {ctx.get('allergies', [])}")
        print(f"  History:   {ctx.get('medical_history', [])}")

    # ── Diagnosis ──
    diagnoses = state.get("differential_diagnosis", [])
    if diagnoses:
        print(f"\n{C.BOLD}{'─' * 65}")
        print(f"  DIFFERENTIAL DIAGNOSIS")
        print(f"{'─' * 65}{C.END}")
        for d in diagnoses:
            bar_len = int(d["confidence"] * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            print(f"  #{d['rank']}  {d['condition']:30s} {bar} {d['confidence']:.0%}")

    # ── Urgency ──
    print(f"\n{C.BOLD}{'─' * 65}")
    print(f"  URGENCY ASSESSMENT")
    print(f"{'─' * 65}{C.END}")
    urgency = state.get("urgency_level", "routine")
    score = state.get("urgency_score", 0)
    icons = {"emergency": "🔴", "urgent": "🟡", "routine": "🟢"}
    print(f"  {icons.get(urgency, '⚪')} {urgency.upper()} (score: {score:.2f})")

    emergency = state.get("emergency_flag", {})
    if emergency.get("is_emergency"):
        print(f"  {C.RED}Rule: {emergency.get('rule')}{C.END}")
        print(f"  {C.RED}Action: {emergency.get('action')}{C.END}")

    # ── Drug Interactions ──
    interactions = state.get("drug_interactions", [])
    if interactions:
        print(f"\n{C.BOLD}{'─' * 65}")
        print(f"  DRUG INTERACTIONS")
        print(f"{'─' * 65}{C.END}")
        for i in interactions:
            sev_color = C.RED if i["severity"] == "major" else C.YELLOW
            print(f"  {sev_color}[{i['severity'].upper():8s}]{C.END}  {i['drug_name']} + {i['interacts_with']}")

    # ── Contraindications ──
    contras = state.get("contraindications", [])
    if contras:
        print(f"\n{C.BOLD}{C.RED}{'─' * 65}")
        print(f"  ⚠️  CONTRAINDICATION ALERTS")
        print(f"{'─' * 65}{C.END}")
        for c in contras:
            print(f"  {C.RED}• {c['action']}{C.END}")

    # ── Treatment ──
    treatments = state.get("treatment_suggestions", [])
    if treatments:
        print(f"\n{C.BOLD}{'─' * 65}")
        print(f"  TREATMENT SUGGESTIONS")
        print(f"{'─' * 65}{C.END}")
        for t in treatments[:2]:
            print(f"  {C.BOLD}{t['condition']}:{C.END}")
            print(f"    {t['recommendation']}")

    # ── Appointment ──
    appt = state.get("appointment", {})
    if appt:
        print(f"\n{C.BOLD}{'─' * 65}")
        print(f"  APPOINTMENT")
        print(f"{'─' * 65}{C.END}")
        print(f"  Timeframe:  {appt.get('timeframe')}")
        print(f"  Specialist: {appt.get('specialist')}")

    # ── Follow-up ──
    followup = state.get("followup_plan", {})
    if followup:
        print(f"\n{C.BOLD}{'─' * 65}")
        print(f"  FOLLOW-UP PLAN")
        print(f"{'─' * 65}{C.END}")
        print(f"  Timeline: {followup.get('timeline')}")
        for step in followup.get("steps", []):
            print(f"    • {step}")

    # ── Explanation ──
    explanation = state.get("explanation", "")
    if explanation:
        print(f"\n{C.BOLD}{'─' * 65}")
        print(f"  FULL EXPLANATION")
        print(f"{'─' * 65}{C.END}")
        for line in explanation.split("\n"):
            print(f"  {line}")

    print(f"\n{C.DIM}{'─' * 65}{C.END}")


def main():
    print_header()

    # Get input
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        # Default demo scenarios
        scenarios = [
            "I have severe chest pain and shortness of breath, I'm a 68 year old male taking warfarin and I'm allergic to aspirin. History of previous MI and diabetes",
            "I have a bad headache, nausea, and sensitivity to light",
            "My child has a sore throat, fever, and swollen glands",
        ]
        print("  Choose a demo scenario:\n")
        for i, s in enumerate(scenarios, 1):
            print(f"  {C.BOLD}[{i}]{C.END} {s[:70]}...")
        print(f"\n  {C.BOLD}[4]{C.END} Enter your own query\n")

        choice = input(f"  {C.CYAN}Select (1-4): {C.END}").strip()

        if choice == "4":
            user_input = input(f"\n  {C.CYAN}Enter your health query: {C.END}")
        elif choice in ("1", "2", "3"):
            user_input = scenarios[int(choice) - 1]
        else:
            user_input = scenarios[0]

    print(f"\n  {C.DIM}Query: {user_input}{C.END}")
    print(f"  {C.DIM}Running pipeline...{C.END}")

    start = time.perf_counter()
    state = run_pipeline(user_input)
    elapsed = (time.perf_counter() - start) * 1000

    print_agent_trace(state)
    print_results(state)

    # Errors
    errors = state.get("errors", [])
    if errors:
        print(f"\n  {C.RED}Errors: {errors}{C.END}")

    print(f"\n  {C.DIM}Total pipeline time: {elapsed:.1f}ms{C.END}")
    print(f"  {C.DIM}Session: {state.get('session_id')}{C.END}")
    print()


if __name__ == "__main__":
    main()
