"""DB 1 — Medical Knowledge Base queries."""

import json
import sqlite3
import math


def get_candidate_conditions(conn: sqlite3.Connection, snomed_codes: list[str]) -> list[dict]:
    """Find conditions matching the given symptom SNOMED codes.
    Uses TF-IDF-style scoring: symptoms appearing in fewer conditions score higher."""

    if not snomed_codes:
        return []

    cursor = conn.cursor()

    # Step 1: Count total conditions (for IDF)
    cursor.execute("SELECT COUNT(DISTINCT condition_id) FROM conditions")
    total_conditions = cursor.fetchone()[0]

    # Step 2: For each symptom, find which conditions it maps to
    placeholders = ",".join("?" * len(snomed_codes))
    cursor.execute(f"""
        SELECT scm.condition_id, scm.symptom, scm.snomed_code, scm.is_cardinal,
               c.name, c.urgency, c.body_system
        FROM symptom_condition_map scm
        JOIN conditions c ON scm.condition_id = c.condition_id
        WHERE scm.snomed_code IN ({placeholders})
    """, snomed_codes)

    rows = cursor.fetchall()

    # Step 3: Compute IDF for each matched symptom
    symptom_condition_counts = {}
    for code in snomed_codes:
        cursor.execute(
            "SELECT COUNT(DISTINCT condition_id) FROM symptom_condition_map WHERE snomed_code = ?",
            (code,)
        )
        count = cursor.fetchone()[0]
        symptom_condition_counts[code] = count

    # Step 4: Score each condition
    condition_scores = {}
    for row in rows:
        cid = row["condition_id"]
        snomed = row["snomed_code"]

        idf = math.log((total_conditions + 1) / (symptom_condition_counts.get(snomed, 1) + 1)) + 1
        cardinal_boost = 1.5 if row["is_cardinal"] else 1.0
        score = idf * cardinal_boost

        if cid not in condition_scores:
            condition_scores[cid] = {
                "condition_id": cid,
                "name": row["name"],
                "urgency": row["urgency"],
                "body_system": row["body_system"],
                "score": 0.0,
                "matched_symptoms": [],
            }
        condition_scores[cid]["score"] += score
        condition_scores[cid]["matched_symptoms"].append(row["symptom"])

    # Sort by score descending
    results = sorted(condition_scores.values(), key=lambda x: x["score"], reverse=True)
    return results


def get_drug_interactions(conn: sqlite3.Connection, drug_names: list[str]) -> list[dict]:
    """Find all interactions for the given drugs."""
    if not drug_names:
        return []

    lower_names = [d.lower() for d in drug_names]
    placeholders = ",".join("?" * len(lower_names))

    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT drug_name, interacts_with, severity, description, source
        FROM drug_interactions
        WHERE LOWER(drug_name) IN ({placeholders})
           OR LOWER(interacts_with) IN ({placeholders})
    """, lower_names + lower_names)

    results = []
    for row in cursor.fetchall():
        results.append({
            "drug_name": row["drug_name"],
            "interacts_with": row["interacts_with"],
            "severity": row["severity"],
            "description": row["description"],
        })
    return results


def get_treatment(conn: sqlite3.Connection, condition_id: str) -> dict | None:
    """Get treatment guidelines for a condition."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT condition_id, urgency_level, recommendation, self_care, specialist_type, source
        FROM treatment_guidelines WHERE condition_id = ?
    """, (condition_id,))

    row = cursor.fetchone()
    if row:
        return {
            "condition_id": row["condition_id"],
            "urgency_level": row["urgency_level"],
            "recommendation": row["recommendation"],
            "self_care": json.loads(row["self_care"]) if row["self_care"] else [],
            "specialist_type": row["specialist_type"],
            "source": row["source"],
        }
    return None


def get_emergency_rules(conn: sqlite3.Connection) -> list[dict]:
    """Get all emergency detection rules."""
    cursor = conn.cursor()
    cursor.execute("SELECT rule_name, required_symptoms, risk_factors, action, confidence_boost FROM emergency_rules")

    results = []
    for row in cursor.fetchall():
        results.append({
            "rule_name": row["rule_name"],
            "required_symptoms": json.loads(row["required_symptoms"]),
            "risk_factors": json.loads(row["risk_factors"]) if row["risk_factors"] else {},
            "action": row["action"],
            "confidence_boost": row["confidence_boost"],
        })
    return results


def get_specialist(conn: sqlite3.Connection, condition_id: str = None, body_system: str = None) -> dict | None:
    """Find a specialist by condition or body system."""
    cursor = conn.cursor()

    if condition_id:
        cursor.execute("SELECT * FROM specialists")
        for row in cursor.fetchall():
            cids = json.loads(row["condition_ids"]) if row["condition_ids"] else []
            if condition_id in cids:
                return {
                    "specialist_type": row["specialist_type"],
                    "description": row["description"],
                    "body_systems": json.loads(row["body_systems"]) if row["body_systems"] else [],
                }

    if body_system:
        cursor.execute("SELECT * FROM specialists")
        for row in cursor.fetchall():
            systems = json.loads(row["body_systems"]) if row["body_systems"] else []
            if body_system in systems:
                return {
                    "specialist_type": row["specialist_type"],
                    "description": row["description"],
                    "body_systems": systems,
                }
    return None
