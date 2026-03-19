"""
Database Setup — Creates all SQLite tables for the demo.
Run via seed_databases.py (not directly).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "neurohealth_demo.db"


def create_tables(conn: sqlite3.Connection):
    """Create all tables matching our database schema."""
    cursor = conn.cursor()

    # ─── DB 1: Medical Knowledge Base ───

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conditions (
            condition_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            icd10_code TEXT,
            snomed_code TEXT,
            urgency TEXT CHECK(urgency IN ('emergency','urgent','routine')),
            body_system TEXT,
            description TEXT,
            source TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symptom_condition_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            condition_id TEXT NOT NULL,
            symptom TEXT NOT NULL,
            snomed_code TEXT,
            is_cardinal INTEGER DEFAULT 0,
            FOREIGN KEY (condition_id) REFERENCES conditions(condition_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drug_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_name TEXT NOT NULL,
            interacts_with TEXT NOT NULL,
            severity TEXT CHECK(severity IN ('major','moderate','minor')),
            description TEXT,
            source TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS treatment_guidelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            condition_id TEXT NOT NULL,
            urgency_level TEXT,
            recommendation TEXT,
            self_care TEXT,
            specialist_type TEXT,
            source TEXT,
            FOREIGN KEY (condition_id) REFERENCES conditions(condition_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL UNIQUE,
            required_symptoms TEXT NOT NULL,
            risk_factors TEXT,
            action TEXT NOT NULL,
            confidence_boost REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS specialists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            specialist_type TEXT NOT NULL,
            condition_ids TEXT,
            body_systems TEXT,
            description TEXT
        )
    """)

    # ─── DB 3: Ontology Mappings ───

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ontology_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,
            snomed_code TEXT,
            snomed_label TEXT,
            icd10_code TEXT,
            semantic_type TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            synonym TEXT NOT NULL,
            canonical TEXT NOT NULL
        )
    """)

    # ─── DB 4: User Profiles ───

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            session_id TEXT PRIMARY KEY,
            age INTEGER,
            sex TEXT,
            medications TEXT,
            allergies TEXT,
            medical_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for fast lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symptom_condition ON symptom_condition_map(symptom)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symptom_snomed ON symptom_condition_map(snomed_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_drug_name ON drug_interactions(drug_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ontology_term ON ontology_terms(term)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_synonym ON synonyms(synonym)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_treatment_cond ON treatment_guidelines(condition_id)")

    conn.commit()
    print("  ✓ All tables created")


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn
