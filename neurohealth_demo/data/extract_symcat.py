"""
Extract real symptom-condition probabilities from the SymCat dataset (CDC-sourced).
Filters for our 15 demo conditions and outputs a new JSON file.

Source: SymCat (symcat.com) — scraped by teliov/symcat-to-synthea
        Original data derived from CDC patient records.

Usage:
    python extract_symcat.py

Requires:
    symcat_diseases.csv (downloaded from GitHub)
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent

# ──────────────────────────────────────────────
# MAP: Our condition IDs → SymCat disease names
# ──────────────────────────────────────────────
CONDITION_MAP = {
    "MI_001":   {"symcat_name": "Heart attack",                          "our_name": "Myocardial infarction"},
    "STR_001":  {"symcat_name": "Stroke",                                "our_name": "Stroke"},
    "PE_001":   {"symcat_name": "Pulmonary embolism",                    "our_name": "Pulmonary embolism"},
    "ANA_001":  {"symcat_name": "Anaphylaxis",                           "our_name": "Anaphylaxis"},
    "PYE_001":  {"symcat_name": "Pyelonephritis",                        "our_name": "Pyelonephritis"},
    "STRP_001": {"symcat_name": "Strep throat",                          "our_name": "Strep throat"},
    "PNE_001":  {"symcat_name": "Pneumonia",                             "our_name": "Pneumonia"},
    "APP_001":  {"symcat_name": "Appendicitis",                          "our_name": "Appendicitis"},
    "MIG_001":  {"symcat_name": "Migraine",                              "our_name": "Migraine"},
    "COLD_001": {"symcat_name": "Common cold",                           "our_name": "Common cold"},
    "GERD_001": {"symcat_name": "Gastroesophageal reflux disease (GERD)", "our_name": "GERD"},
    "UTI_001":  {"symcat_name": "Urinary tract infection",               "our_name": "Urinary tract infection"},
    "TH_001":   {"symcat_name": "Tension headache",                      "our_name": "Tension headache"},
    "AR_001":   {"symcat_name": "Allergic rhinitis",                     "our_name": "Allergic rhinitis"},
    "GE_001":   {"symcat_name": "Noninfectious gastroenteritis",         "our_name": "Gastroenteritis"},
}

# Build reverse lookup: symcat_name → condition_id
SYMCAT_TO_ID = {}
for cid, info in CONDITION_MAP.items():
    SYMCAT_TO_ID[info["symcat_name"].lower()] = cid


def parse_symcat_csv():
    """Parse the deeply nested SymCat CSV to extract all disease-symptom-probability triples."""
    csv_path = DATA_DIR / "symcat_diseases.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found!")
        print("Download it first:")
        print("  Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/teliov/symcat-to-synthea/master/symcat/symcat-801-diseases.csv' -OutFile 'symcat_diseases.csv'")
        return {}

    print(f"Reading {csv_path.name} ({csv_path.stat().st_size:,} bytes)...")

    # Find all column prefixes that have _symptoms_name
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        prefixes = set()
        for h in headers:
            if h.endswith("_symptoms_name"):
                prefix = h.replace("_symptoms_name", "")
                prefixes.add(prefix)

        print(f"  Found {len(prefixes)} nesting levels in CSV")

        # Extract all disease-symptom-probability triples
        all_pairs = {}  # (disease_lower, symptom_lower) -> probability
        for row in reader:
            for prefix in prefixes:
                disease = row.get(prefix + "_disorder_name", "").strip()
                if not disease:
                    disease = row.get(prefix + "_name", "").strip()
                symptom = row.get(prefix + "_symptoms_name", "").strip()
                prob_str = row.get(prefix + "_symptoms_probability", "").strip()

                if disease and symptom and prob_str:
                    try:
                        prob = float(prob_str)
                        key = (disease.lower(), symptom.lower())
                        if key not in all_pairs:
                            all_pairs[key] = (disease, symptom, prob)
                    except ValueError:
                        pass

    print(f"  Extracted {len(all_pairs)} total symptom-disease pairs across 801 conditions")
    return all_pairs


def filter_our_conditions(all_pairs):
    """Filter the SymCat data to only include our 15 demo conditions."""

    results = {}  # condition_id -> list of {symptom, probability}

    for (disease_lower, symptom_lower), (disease, symptom, prob) in all_pairs.items():
        if disease_lower in SYMCAT_TO_ID:
            cid = SYMCAT_TO_ID[disease_lower]
            if cid not in results:
                results[cid] = []
            results[cid].append({
                "symptom": symptom,
                "probability_pct": prob,      # e.g., 53 means 53%
                "importance": round(prob / 100, 2),  # Normalized to 0.0-1.0
            })

    # Sort each condition's symptoms by probability (highest first)
    for cid in results:
        results[cid].sort(key=lambda x: x["probability_pct"], reverse=True)

    return results


def build_output(filtered_data):
    """Build the final JSON output with our condition IDs and SymCat probabilities."""

    output = {
        "metadata": {
            "source": "SymCat (symcat.com) — derived from CDC patient records",
            "repository": "https://github.com/teliov/symcat-to-synthea",
            "description": "Symptom probabilities represent the percentage of patients with this condition who present with each symptom",
            "note": "importance = probability_pct / 100 (normalized to 0.0-1.0 scale)",
        },
        "conditions": []
    }

    for cid, info in CONDITION_MAP.items():
        symptoms = filtered_data.get(cid, [])
        condition_entry = {
            "condition_id": cid,
            "condition_name": info["our_name"],
            "symcat_name": info["symcat_name"],
            "found_in_symcat": len(symptoms) > 0,
            "symptom_count": len(symptoms),
            "symptoms": symptoms,
        }
        output["conditions"].append(condition_entry)

    return output


def main():
    print("=" * 60)
    print("  SymCat → NeuroHealth Importance Weight Extractor")
    print("=" * 60)

    # Step 1: Parse the raw CSV
    all_pairs = parse_symcat_csv()
    if not all_pairs:
        return

    # Step 2: Filter for our 15 conditions
    print(f"\nFiltering for {len(CONDITION_MAP)} conditions...")
    filtered = filter_our_conditions(all_pairs)

    # Step 3: Build and save output
    output = build_output(filtered)

    out_path = DATA_DIR / "symcat_importance_weights.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print results summary
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)

    total_symptoms = 0
    for cond in output["conditions"]:
        status = "FOUND" if cond["found_in_symcat"] else "NOT FOUND"
        count = cond["symptom_count"]
        total_symptoms += count
        print(f"\n  {cond['condition_id']:10s} | {cond['condition_name']:30s} | {status:10s} | {count} symptoms")

        if cond["found_in_symcat"]:
            # Show top 5 symptoms
            for s in cond["symptoms"][:5]:
                bar = "█" * int(s["probability_pct"] / 5)
                print(f"    {s['probability_pct']:5.0f}% {bar:20s} {s['symptom']}")
            if count > 5:
                print(f"    ... and {count - 5} more")

    print(f"\n{'=' * 60}")
    print(f"  Total: {total_symptoms} symptom-condition pairs extracted")
    print(f"  Saved to: {out_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
