"""DB 3 — Ontology mapping queries."""

import sqlite3


def normalize_term(conn: sqlite3.Connection, term: str) -> dict | None:
    """Look up a symptom term and return its SNOMED/ICD-10 codes."""
    cursor = conn.cursor()

    # Direct match
    cursor.execute(
        "SELECT term, snomed_code, snomed_label, icd10_code, semantic_type FROM ontology_terms WHERE LOWER(term) = ?",
        (term.lower(),)
    )
    row = cursor.fetchone()
    if row:
        return {
            "term": row["term"],
            "snomed_code": row["snomed_code"],
            "snomed_label": row["snomed_label"],
            "icd10_code": row["icd10_code"],
            "semantic_type": row["semantic_type"],
        }
    return None


def resolve_synonym(conn: sqlite3.Connection, term: str) -> str:
    """Resolve a lay-term synonym to its canonical medical term."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT canonical FROM synonyms WHERE LOWER(synonym) = ?",
        (term.lower(),)
    )
    row = cursor.fetchone()
    if row:
        return row["canonical"]
    return term  # Return original if no synonym found


def normalize_with_synonym(conn: sqlite3.Connection, term: str) -> dict | None:
    """Try direct lookup, then synonym resolution, then partial match."""

    # 1. Direct match
    result = normalize_term(conn, term)
    if result:
        return result

    # 2. Synonym resolution
    canonical = resolve_synonym(conn, term)
    if canonical != term:
        result = normalize_term(conn, canonical)
        if result:
            result["original_term"] = term
            result["resolved_via"] = "synonym"
            return result

    # 3. Partial match (LIKE query)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT term, snomed_code, snomed_label, icd10_code, semantic_type FROM ontology_terms WHERE LOWER(term) LIKE ?",
        (f"%{term.lower()}%",)
    )
    row = cursor.fetchone()
    if row:
        return {
            "term": row["term"],
            "snomed_code": row["snomed_code"],
            "snomed_label": row["snomed_label"],
            "icd10_code": row["icd10_code"],
            "semantic_type": row["semantic_type"],
            "original_term": term,
            "resolved_via": "partial_match",
        }

    return None
