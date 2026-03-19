"""
Database Integration Test — Verifies all DB query functions work correctly.
Run after seed_databases.py.

Usage:
    python test_db.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db.setup import get_connection
from db.medical_kb import (
    get_candidate_conditions, get_drug_interactions,
    get_treatment, get_emergency_rules, get_specialist
)
from db.ontology import normalize_term, resolve_synonym, normalize_with_synonym
from db.user_profile import save_user_profile, get_user_profile
from db.audit_log import AuditLog

PASS = 0
FAIL = 0


def check(test_name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {test_name}")
    else:
        FAIL += 1
        print(f"  ❌ {test_name} — {detail}")


def test_ontology(conn):
    print("\n━━━ ONTOLOGY (DB 3) ━━━")

    # Direct lookup
    result = normalize_term(conn, "chest pain")
    check("Direct lookup: 'chest pain'",
          result is not None and result["snomed_code"] == "29857009",
          f"Got: {result}")

    result = normalize_term(conn, "fever")
    check("Direct lookup: 'fever'",
          result is not None and result["snomed_code"] == "386661006",
          f"Got: {result}")

    # Case insensitive
    result = normalize_term(conn, "Chest Pain")
    check("Case insensitive: 'Chest Pain'",
          result is not None and result["snomed_code"] == "29857009",
          f"Got: {result}")

    # Synonym resolution
    canonical = resolve_synonym(conn, "tummy ache")
    check("Synonym: 'tummy ache' → 'abdominal pain'",
          canonical == "abdominal pain",
          f"Got: {canonical}")

    canonical = resolve_synonym(conn, "cant breathe")
    check("Synonym: 'cant breathe' → 'shortness of breath'",
          canonical == "shortness of breath",
          f"Got: {canonical}")

    # Unknown term returns itself
    canonical = resolve_synonym(conn, "xyzzy")
    check("Unknown synonym returns original",
          canonical == "xyzzy",
          f"Got: {canonical}")

    # Full pipeline: synonym → ontology
    result = normalize_with_synonym(conn, "tummy ache")
    check("Full pipeline: 'tummy ache' → SNOMED via synonym",
          result is not None and result["snomed_code"] == "21522001"
          and result.get("resolved_via") == "synonym",
          f"Got: {result}")

    # Partial match
    result = normalize_with_synonym(conn, "urination")
    check("Partial match: 'urination' finds 'burning urination'",
          result is not None and "urination" in result["term"].lower(),
          f"Got: {result}")

    # Non-existent term
    result = normalize_with_synonym(conn, "quantum entanglement")
    check("Non-existent term returns None",
          result is None,
          f"Got: {result}")


def test_candidate_conditions(conn):
    print("\n━━━ CANDIDATE CONDITIONS (DB 1) ━━━")

    # Heart attack symptoms: chest pain + shortness of breath
    snomed_codes = ["29857009", "267036007"]  # chest pain, shortness of breath
    results = get_candidate_conditions(conn, snomed_codes)
    check("Chest pain + SOB returns conditions",
          len(results) > 0,
          f"Got {len(results)} results")

    if results:
        top = results[0]
        check("Top result is MI (heart attack)",
              top["condition_id"] == "MI_001",
              f"Got: {top['condition_id']} — {top['name']}")

        check("MI has both symptoms matched",
              len(top["matched_symptoms"]) == 2,
              f"Matched: {top['matched_symptoms']}")

        # Print all candidates for visibility
        print("  ── Candidates ranked by TF-IDF score:")
        for r in results[:5]:
            print(f"     {r['score']:6.2f}  {r['name']:30s}  matched: {r['matched_symptoms']}")

    # Migraine symptom: headache only
    results = get_candidate_conditions(conn, ["25064002"])  # headache
    check("Headache returns migraine + tension headache",
          len(results) >= 2,
          f"Got {len(results)} results")

    if results:
        condition_ids = [r["condition_id"] for r in results]
        check("Both MIG_001 and TH_001 in results",
              "MIG_001" in condition_ids and "TH_001" in condition_ids,
              f"IDs: {condition_ids}")

    # Empty input
    results = get_candidate_conditions(conn, [])
    check("Empty input returns empty list",
          results == [],
          f"Got: {results}")


def test_drug_interactions(conn):
    print("\n━━━ DRUG INTERACTIONS (DB 1) ━━━")

    # Warfarin interactions
    results = get_drug_interactions(conn, ["warfarin"])
    check("Warfarin has multiple interactions",
          len(results) >= 3,
          f"Got {len(results)} interactions")

    # Check specific interaction
    aspirin_hit = [r for r in results if r["interacts_with"] == "aspirin" or r["drug_name"] == "aspirin"]
    check("Warfarin-aspirin interaction found",
          len(aspirin_hit) > 0,
          f"Results: {[r['interacts_with'] for r in results]}")

    if aspirin_hit:
        check("Warfarin-aspirin is 'major' severity",
              aspirin_hit[0]["severity"] == "major",
              f"Got: {aspirin_hit[0]['severity']}")

    # Multiple drugs at once
    results = get_drug_interactions(conn, ["warfarin", "sertraline", "ibuprofen"])
    check("Multi-drug query returns interactions",
          len(results) >= 5,
          f"Got {len(results)} interactions")

    print("  ── Interactions found:")
    for r in results:
        print(f"     {r['drug_name']:15s} + {r['interacts_with']:20s} → {r['severity']}")

    # Unknown drug
    results = get_drug_interactions(conn, ["unobtainium"])
    check("Unknown drug returns empty",
          len(results) == 0,
          f"Got {len(results)} results")


def test_treatments(conn):
    print("\n━━━ TREATMENT GUIDELINES (DB 1) ━━━")

    # MI treatment
    result = get_treatment(conn, "MI_001")
    check("MI treatment found",
          result is not None,
          "Not found")

    if result:
        check("MI treatment has self-care list",
              isinstance(result["self_care"], list) and len(result["self_care"]) > 0,
              f"Got: {result['self_care']}")

        check("MI specialist is cardiologist",
              result["specialist_type"] == "cardiologist",
              f"Got: {result['specialist_type']}")

    # Migraine treatment
    result = get_treatment(conn, "MIG_001")
    check("Migraine treatment found",
          result is not None and "Sumatriptan" in str(result.get("self_care", "")),
          f"Got: {result}")

    # Non-existent condition
    result = get_treatment(conn, "FAKE_001")
    check("Non-existent condition returns None",
          result is None,
          f"Got: {result}")


def test_emergency_rules(conn):
    print("\n━━━ EMERGENCY RULES (DB 1) ━━━")

    rules = get_emergency_rules(conn)
    check("Emergency rules loaded",
          len(rules) == 10,
          f"Got {len(rules)} rules")

    # Check structure
    cardiac = [r for r in rules if r["rule_name"] == "cardiac_emergency"]
    check("cardiac_emergency rule exists",
          len(cardiac) == 1,
          "Not found")

    if cardiac:
        rule = cardiac[0]
        check("Cardiac rule has required_symptoms as list",
              isinstance(rule["required_symptoms"], list) and "chest pain" in rule["required_symptoms"],
              f"Got: {rule['required_symptoms']}")

        check("Cardiac rule has confidence_boost",
              rule["confidence_boost"] > 0,
              f"Got: {rule['confidence_boost']}")

    print("  ── All rules:")
    for r in rules:
        print(f"     {r['rule_name']:25s}  symptoms: {r['required_symptoms']}  boost: {r['confidence_boost']}")


def test_specialists(conn):
    print("\n━━━ SPECIALIST DIRECTORY (DB 1) ━━━")

    # By condition
    result = get_specialist(conn, condition_id="MI_001")
    check("MI → Cardiologist",
          result is not None and result["specialist_type"] == "Cardiologist",
          f"Got: {result}")

    result = get_specialist(conn, condition_id="MIG_001")
    check("Migraine → Neurologist",
          result is not None and result["specialist_type"] == "Neurologist",
          f"Got: {result}")

    # By body system
    result = get_specialist(conn, body_system="respiratory")
    check("respiratory → Pulmonologist",
          result is not None and result["specialist_type"] == "Pulmonologist",
          f"Got: {result}")


def test_user_profile(conn):
    print("\n━━━ USER PROFILES (DB 4) ━━━")

    test_context = {
        "age": 68,
        "sex": "male",
        "medications": ["warfarin", "metformin"],
        "allergies": ["aspirin", "penicillin"],
        "medical_history": ["previous MI", "diabetes"],
    }

    # Save
    save_user_profile(conn, "test_session_001", test_context)
    check("Profile saved without error", True)

    # Retrieve
    profile = get_user_profile(conn, "test_session_001")
    check("Profile retrieved",
          profile is not None,
          "Not found")

    if profile:
        check("Age decoded correctly",
              profile["age"] == 68,
              f"Got: {profile['age']}")

        check("Medications decoded from base64",
              profile["medications"] == ["warfarin", "metformin"],
              f"Got: {profile['medications']}")

        check("Allergies decoded from base64",
              profile["allergies"] == ["aspirin", "penicillin"],
              f"Got: {profile['allergies']}")

        check("Medical history decoded",
              profile["medical_history"] == ["previous MI", "diabetes"],
              f"Got: {profile['medical_history']}")

    # Non-existent profile
    profile = get_user_profile(conn, "nonexistent_session")
    check("Non-existent session returns None",
          profile is None,
          f"Got: {profile}")

    # Cleanup
    conn.execute("DELETE FROM user_profiles WHERE session_id = 'test_session_001'")
    conn.commit()


def test_audit_log():
    print("\n━━━ AUDIT LOG (DB 5) ━━━")

    import tempfile
    log_path = Path(tempfile.mktemp(suffix=".json"))

    audit = AuditLog(log_path)

    # Log entries
    audit.log({"agent": "IntentClassifier", "output": "symptom_check", "time_ms": 12.3})
    audit.log({"agent": "SymptomExtractor", "output": ["chest pain"], "time_ms": 8.1})
    audit.log({"agent": "EmergencyDetection", "output": {"is_emergency": True}, "time_ms": 5.0})

    check("3 entries logged",
          len(audit.get_all()) == 3,
          f"Got {len(audit.get_all())} entries")

    # Summary
    summary = audit.get_summary()
    check("Summary total agents = 3",
          summary["total_agents_run"] == 3,
          f"Got: {summary['total_agents_run']}")

    check("Summary total time = 25.4ms",
          abs(summary["total_time_ms"] - 25.4) < 0.01,
          f"Got: {summary['total_time_ms']}")

    # File exists
    check("Log file written to disk",
          log_path.exists() and log_path.stat().st_size > 0,
          f"Path: {log_path}")

    # Cleanup
    log_path.unlink(missing_ok=True)


def main():
    global PASS, FAIL

    print("=" * 55)
    print("  NeuroHealth — Database Integration Tests")
    print("=" * 55)

    conn = get_connection()

    test_ontology(conn)
    test_candidate_conditions(conn)
    test_drug_interactions(conn)
    test_treatments(conn)
    test_emergency_rules(conn)
    test_specialists(conn)
    test_user_profile(conn)
    test_audit_log()

    conn.close()

    print("\n" + "=" * 55)
    total = PASS + FAIL
    if FAIL == 0:
        print(f"  ✅ ALL {total} TESTS PASSED!")
    else:
        print(f"  ⚠️  {PASS}/{total} passed, {FAIL} FAILED")
    print("=" * 55)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
