"""
Seed Databases — Loads all JSON data files into SQLite.
Run this once before starting the demo pipeline.

Usage:
    python seed_databases.py
"""

import json
import sqlite3
import sys
from pathlib import Path

# Add parent to path so we can import db modules
sys.path.insert(0, str(Path(__file__).parent))

from db.setup import create_tables, DB_PATH

DATA_DIR = Path(__file__).parent / "data"


def seed_conditions(conn: sqlite3.Connection):
    """Seed the conditions table from conditions.json."""
    data = json.loads((DATA_DIR / "conditions.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for c in data:
        cursor.execute(
            "INSERT OR REPLACE INTO conditions VALUES (?,?,?,?,?,?,?,?)",
            (c["condition_id"], c["name"], c["icd10_code"], c["snomed_code"],
             c["urgency"], c["body_system"], c.get("description", ""), c.get("source", ""))
        )
    conn.commit()
    print(f"  ✓ conditions: {len(data)} rows")


def seed_symptom_map(conn: sqlite3.Connection):
    """Seed symptom-condition mappings from symptoms_map.json."""
    data = json.loads((DATA_DIR / "symptoms_map.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for s in data:
        cursor.execute(
            "INSERT INTO symptom_condition_map (condition_id, symptom, snomed_code, is_cardinal) VALUES (?,?,?,?)",
            (s["condition_id"], s["symptom"], s.get("snomed", ""), 1 if s.get("is_cardinal") else 0)
        )
    conn.commit()
    print(f"  ✓ symptom_condition_map: {len(data)} rows")


def seed_drug_interactions(conn: sqlite3.Connection):
    """Seed drug interactions from drug_interactions.json."""
    data = json.loads((DATA_DIR / "drug_interactions.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for d in data:
        cursor.execute(
            "INSERT INTO drug_interactions (drug_name, interacts_with, severity, description, source) VALUES (?,?,?,?,?)",
            (d["drug_name"], d["interacts_with"], d["severity"], d["description"], d.get("source", ""))
        )
    conn.commit()
    print(f"  ✓ drug_interactions: {len(data)} rows")


def seed_treatments(conn: sqlite3.Connection):
    """Seed treatment guidelines from treatments.json."""
    data = json.loads((DATA_DIR / "treatments.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for t in data:
        cursor.execute(
            "INSERT INTO treatment_guidelines (condition_id, urgency_level, recommendation, self_care, specialist_type, source) VALUES (?,?,?,?,?,?)",
            (t["condition_id"], t["urgency_level"], t["recommendation"],
             json.dumps(t["self_care"]), t.get("specialist_type", ""), t.get("source", ""))
        )
    conn.commit()
    print(f"  ✓ treatment_guidelines: {len(data)} rows")


def seed_emergency_rules(conn: sqlite3.Connection):
    """Seed emergency detection rules from emergency_rules.json."""
    data = json.loads((DATA_DIR / "emergency_rules.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for r in data:
        cursor.execute(
            "INSERT OR REPLACE INTO emergency_rules (rule_name, required_symptoms, risk_factors, action, confidence_boost) VALUES (?,?,?,?,?)",
            (r["rule_name"], json.dumps(r["required_symptoms"]), json.dumps(r.get("risk_factors", {})),
             r["action"], r.get("confidence_boost", 0.0))
        )
    conn.commit()
    print(f"  ✓ emergency_rules: {len(data)} rows")


def seed_specialists(conn: sqlite3.Connection):
    """Seed specialist directory from specialists.json."""
    data = json.loads((DATA_DIR / "specialists.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for s in data:
        cursor.execute(
            "INSERT INTO specialists (specialist_type, condition_ids, body_systems, description) VALUES (?,?,?,?)",
            (s["specialist_type"], json.dumps(s["condition_ids"]),
             json.dumps(s["body_systems"]), s["description"])
        )
    conn.commit()
    print(f"  ✓ specialists: {len(data)} rows")


def seed_ontology(conn: sqlite3.Connection):
    """Seed ontology terms from ontology_terms.json."""
    data = json.loads((DATA_DIR / "ontology_terms.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for t in data:
        cursor.execute(
            "INSERT INTO ontology_terms (term, snomed_code, snomed_label, icd10_code, semantic_type) VALUES (?,?,?,?,?)",
            (t["term"], t["snomed_code"], t.get("snomed_label", ""), t.get("icd10_code", ""), t.get("semantic_type", ""))
        )
    conn.commit()
    print(f"  ✓ ontology_terms: {len(data)} rows")


def seed_synonyms(conn: sqlite3.Connection):
    """Seed lay-term synonyms from synonyms.json."""
    data = json.loads((DATA_DIR / "synonyms.json").read_text(encoding="utf-8"))
    cursor = conn.cursor()
    for s in data:
        cursor.execute(
            "INSERT INTO synonyms (synonym, canonical) VALUES (?,?)",
            (s["synonym"], s["canonical"])
        )
    conn.commit()
    print(f"  ✓ synonyms: {len(data)} rows")


def verify_database(conn: sqlite3.Connection):
    """Run quick verification queries."""
    cursor = conn.cursor()
    print("\n  ── Verification ──")

    tables = ["conditions", "symptom_condition_map", "drug_interactions",
              "treatment_guidelines", "emergency_rules", "specialists",
              "ontology_terms", "synonyms"]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:30s} → {count:4d} rows")

    # Quick test: look up chest pain
    cursor.execute("SELECT term, snomed_code FROM ontology_terms WHERE term = 'chest pain'")
    row = cursor.fetchone()
    if row:
        print(f"\n  Test: 'chest pain' → SNOMED {row['snomed_code']} ✓")

    cursor.execute("SELECT drug_name, interacts_with, severity FROM drug_interactions WHERE drug_name = 'warfarin' AND interacts_with = 'aspirin'")
    row = cursor.fetchone()
    if row:
        print(f"  Test: warfarin+aspirin → {row['severity']} ✓")


def main():
    print("=" * 55)
    print("  NeuroHealth — Database Seeding")
    print("=" * 55)

    # Delete existing DB
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"\n  Deleted existing {DB_PATH.name}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    print(f"\n  Creating tables in {DB_PATH.name}...")
    create_tables(conn)

    print(f"\n  Seeding from {DATA_DIR}/...")
    seed_conditions(conn)
    seed_symptom_map(conn)
    seed_drug_interactions(conn)
    seed_treatments(conn)
    seed_emergency_rules(conn)
    seed_specialists(conn)
    seed_ontology(conn)
    seed_synonyms(conn)

    verify_database(conn)
    conn.close()

    size_kb = DB_PATH.stat().st_size / 1024
    print(f"\n  Database: {DB_PATH} ({size_kb:.1f} KB)")
    print("=" * 55)
    print("  ✅ Database ready!")
    print("=" * 55)


if __name__ == "__main__":
    main()
