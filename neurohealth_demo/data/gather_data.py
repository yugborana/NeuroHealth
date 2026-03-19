"""
NeuroHealth Demo — Automated Data Gathering Script
Fetches medical data from free public APIs and generates all JSON seed files.

APIs Used:
  1. MedlinePlus Connect API (conditions + articles)  — No key needed
  2. openFDA Drug Label API (drug interactions)        — No key needed
  3. SNOMED CT Snowstorm API (ontology terms)          — No key needed (reference use)
  4. Manual curated data (emergency rules, synonyms, specialists, symptom maps)

Usage:
  pip install requests
  python gather_data.py
"""

import json
import os
import re
import time
import requests
from pathlib import Path

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent
ARTICLES_DIR = DATA_DIR / "articles"
ARTICLES_DIR.mkdir(exist_ok=True)

DELAY = 0.5  # seconds between API calls to be polite


# ──────────────────────────────────────────────
# CONDITION DEFINITIONS (our 15 demo conditions)
# ──────────────────────────────────────────────
CONDITIONS = [
    {"condition_id": "MI_001",   "name": "Myocardial infarction",  "icd10": "I21.9",   "snomed": "22298006",  "urgency": "emergency", "body_system": "cardiovascular"},
    {"condition_id": "STR_001",  "name": "Stroke",                 "icd10": "I63.9",   "snomed": "230690007", "urgency": "emergency", "body_system": "neurological"},
    {"condition_id": "PE_001",   "name": "Pulmonary embolism",     "icd10": "I26.99",  "snomed": "59282003",  "urgency": "emergency", "body_system": "respiratory"},
    {"condition_id": "ANA_001",  "name": "Anaphylaxis",            "icd10": "T78.2",   "snomed": "39579001",  "urgency": "emergency", "body_system": "immune"},
    {"condition_id": "PYE_001",  "name": "Pyelonephritis",         "icd10": "N10",     "snomed": "45816000",  "urgency": "urgent",    "body_system": "renal"},
    {"condition_id": "STRP_001", "name": "Strep throat",           "icd10": "J02.0",   "snomed": "43878008",  "urgency": "urgent",    "body_system": "respiratory"},
    {"condition_id": "PNE_001",  "name": "Pneumonia",              "icd10": "J18.9",   "snomed": "233604007", "urgency": "urgent",    "body_system": "respiratory"},
    {"condition_id": "APP_001",  "name": "Appendicitis",           "icd10": "K35.80",  "snomed": "74400008",  "urgency": "urgent",    "body_system": "gastrointestinal"},
    {"condition_id": "MIG_001",  "name": "Migraine",               "icd10": "G43.909", "snomed": "37796009",  "urgency": "routine",   "body_system": "neurological"},
    {"condition_id": "COLD_001", "name": "Common cold",            "icd10": "J00",     "snomed": "82272006",  "urgency": "routine",   "body_system": "respiratory"},
    {"condition_id": "GERD_001", "name": "GERD",                   "icd10": "K21.0",   "snomed": "235595009", "urgency": "routine",   "body_system": "gastrointestinal"},
    {"condition_id": "UTI_001",  "name": "Urinary tract infection", "icd10": "N39.0",  "snomed": "68566005",  "urgency": "routine",   "body_system": "renal"},
    {"condition_id": "TH_001",   "name": "Tension headache",       "icd10": "G44.209", "snomed": "398057008", "urgency": "routine",   "body_system": "neurological"},
    {"condition_id": "AR_001",   "name": "Allergic rhinitis",      "icd10": "J30.9",   "snomed": "61582004",  "urgency": "routine",   "body_system": "respiratory"},
    {"condition_id": "GE_001",   "name": "Gastroenteritis",        "icd10": "K52.9",   "snomed": "25374005",  "urgency": "routine",   "body_system": "gastrointestinal"},
]


# ──────────────────────────────────────────────
# 1. FETCH ARTICLES FROM MEDLINEPLUS CONNECT API
# ──────────────────────────────────────────────
def fetch_medlineplus_article(icd10_code: str, condition_name: str) -> str:
    """Fetch article text from MedlinePlus Connect using ICD-10 code."""
    url = (
        "https://connect.medlineplus.gov/service"
        f"?mainSearchCriteria.v.cs=2.16.840.1.113883.6.90"
        f"&mainSearchCriteria.v.c={icd10_code}"
        f"&knowledgeResponseType=application/json"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("feed", {}).get("entry", [])
        if entries:
            summary = entries[0].get("summary", {}).get("_value", "")
            # Strip HTML tags
            clean = re.sub(r"<[^>]+>", "", summary)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean
    except Exception as e:
        print(f"  ⚠ MedlinePlus failed for {condition_name} ({icd10_code}): {e}")
    return ""


def fetch_medlineplus_search(term: str) -> str:
    """Fallback: search MedlinePlus by keyword if Connect returns nothing."""
    url = f"https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term={term}&rettype=topic&retmax=1"
    try:
        resp = requests.get(url, timeout=15)
        text = resp.text
        # Extract full-summary from XML
        match = re.search(r"<full-summary>(.*?)</full-summary>", text, re.DOTALL)
        if match:
            summary = match.group(1)
            # Decode HTML entities and strip tags
            summary = summary.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            clean = re.sub(r"<[^>]+>", "", summary)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean
    except Exception as e:
        print(f"  ⚠ MedlinePlus search failed for {term}: {e}")
    return ""


def gather_articles():
    """Fetch and save article texts for all conditions."""
    print("\n📚 Fetching articles from MedlinePlus...")
    for c in CONDITIONS:
        fname = c["condition_id"].lower() + ".txt"
        fpath = ARTICLES_DIR / fname
        print(f"  → {c['name']} ({c['icd10']})...", end=" ")

        text = fetch_medlineplus_article(c["icd10"], c["name"])
        if not text or len(text) < 100:
            text = fetch_medlineplus_search(c["name"])

        if text and len(text) > 50:
            fpath.write_text(text, encoding="utf-8")
            print(f"✅ {len(text)} chars")
        else:
            print("❌ No data — will use manual fallback")

        time.sleep(DELAY)
    print("  Done.\n")


# ──────────────────────────────────────────────
# 2. FETCH DRUG INTERACTIONS FROM OPENFDA
# ──────────────────────────────────────────────
DEMO_DRUGS = ["warfarin", "sertraline", "metformin", "lisinopril", "ibuprofen",
              "atenolol", "amoxicillin", "omeprazole", "sumatriptan", "aspirin"]


def fetch_openfda_interactions(drug_name: str) -> list[dict]:
    """Fetch drug interaction info from openFDA label API."""
    url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{drug_name}&limit=1"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results:
            interactions_text = results[0].get("drug_interactions", [""])[0]
            contraindications = results[0].get("contraindications", [""])[0]
            return {
                "drug_name": drug_name,
                "interactions_raw": interactions_text[:2000],
                "contraindications_raw": contraindications[:1000],
            }
    except Exception as e:
        print(f"  ⚠ openFDA failed for {drug_name}: {e}")
    return {"drug_name": drug_name, "interactions_raw": "", "contraindications_raw": ""}


def gather_drug_data_raw():
    """Fetch raw drug data from openFDA for reference."""
    print("💊 Fetching drug labels from openFDA...")
    raw_data = []
    for drug in DEMO_DRUGS:
        print(f"  → {drug}...", end=" ")
        info = fetch_openfda_interactions(drug)
        if info["interactions_raw"]:
            print(f"✅ {len(info['interactions_raw'])} chars")
        else:
            print("❌ No data")
        raw_data.append(info)
        time.sleep(DELAY)

    save_json(raw_data, "drug_labels_raw.json")
    print("  Saved drug_labels_raw.json (for reference)\n")


# ──────────────────────────────────────────────
# 3. CURATED DATA (manually defined, medically accurate)
# ──────────────────────────────────────────────

def generate_conditions_json():
    """Generate conditions.json from our definitions + fetched descriptions."""
    print("📝 Generating conditions.json...")
    output = []
    for c in CONDITIONS:
        article_path = ARTICLES_DIR / (c["condition_id"].lower() + ".txt")
        desc = ""
        if article_path.exists():
            desc = article_path.read_text(encoding="utf-8")[:500]
        output.append({
            "condition_id": c["condition_id"],
            "name": c["name"],
            "icd10_code": c["icd10"],
            "snomed_code": c["snomed"],
            "urgency": c["urgency"],
            "body_system": c["body_system"],
            "description": desc,
            "source": "MedlinePlus / NLM"
        })
    save_json(output, "conditions.json")
    print(f"  ✅ {len(output)} conditions saved\n")


def generate_symptoms_map():
    """Generate symptom-condition mappings with importance weights."""
    print("📝 Generating symptoms_map.json...")
    mappings = [
        # MI
        {"condition_id": "MI_001", "symptom": "chest pain", "snomed": "29857009", "importance": 0.95, "is_cardinal": True},
        {"condition_id": "MI_001", "symptom": "left arm pain", "snomed": "10601006", "importance": 0.80, "is_cardinal": False},
        {"condition_id": "MI_001", "symptom": "shortness of breath", "snomed": "267036007", "importance": 0.70, "is_cardinal": False},
        {"condition_id": "MI_001", "symptom": "sweating", "snomed": "415690000", "importance": 0.65, "is_cardinal": False},
        {"condition_id": "MI_001", "symptom": "nausea", "snomed": "422587007", "importance": 0.50, "is_cardinal": False},
        {"condition_id": "MI_001", "symptom": "jaw pain", "snomed": "274667000", "importance": 0.60, "is_cardinal": False},
        # Stroke
        {"condition_id": "STR_001", "symptom": "sudden weakness one side", "snomed": "26544005", "importance": 0.95, "is_cardinal": True},
        {"condition_id": "STR_001", "symptom": "speech difficulty", "snomed": "29164008", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "STR_001", "symptom": "facial drooping", "snomed": "271587009", "importance": 0.85, "is_cardinal": False},
        {"condition_id": "STR_001", "symptom": "confusion", "snomed": "40917007", "importance": 0.70, "is_cardinal": False},
        {"condition_id": "STR_001", "symptom": "severe headache", "snomed": "25064002", "importance": 0.60, "is_cardinal": False},
        # PE
        {"condition_id": "PE_001", "symptom": "shortness of breath", "snomed": "267036007", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "PE_001", "symptom": "chest pain", "snomed": "29857009", "importance": 0.80, "is_cardinal": False},
        {"condition_id": "PE_001", "symptom": "coughing blood", "snomed": "66857006", "importance": 0.85, "is_cardinal": False},
        {"condition_id": "PE_001", "symptom": "rapid heartbeat", "snomed": "3424008", "importance": 0.65, "is_cardinal": False},
        # Anaphylaxis
        {"condition_id": "ANA_001", "symptom": "swelling throat", "snomed": "267102003", "importance": 0.95, "is_cardinal": True},
        {"condition_id": "ANA_001", "symptom": "difficulty breathing", "snomed": "267036007", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "ANA_001", "symptom": "hives", "snomed": "126485001", "importance": 0.80, "is_cardinal": False},
        {"condition_id": "ANA_001", "symptom": "low blood pressure", "snomed": "45007003", "importance": 0.75, "is_cardinal": False},
        # Pyelonephritis
        {"condition_id": "PYE_001", "symptom": "burning urination", "snomed": "49650001", "importance": 0.85, "is_cardinal": True},
        {"condition_id": "PYE_001", "symptom": "flank pain", "snomed": "274743004", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "PYE_001", "symptom": "fever", "snomed": "386661006", "importance": 0.80, "is_cardinal": False},
        {"condition_id": "PYE_001", "symptom": "nausea", "snomed": "422587007", "importance": 0.50, "is_cardinal": False},
        # Strep throat
        {"condition_id": "STRP_001", "symptom": "sore throat", "snomed": "162397003", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "STRP_001", "symptom": "fever", "snomed": "386661006", "importance": 0.75, "is_cardinal": False},
        {"condition_id": "STRP_001", "symptom": "swollen lymph nodes", "snomed": "30746006", "importance": 0.70, "is_cardinal": False},
        {"condition_id": "STRP_001", "symptom": "difficulty swallowing", "snomed": "40739000", "importance": 0.65, "is_cardinal": False},
        # Pneumonia
        {"condition_id": "PNE_001", "symptom": "cough", "snomed": "49727002", "importance": 0.85, "is_cardinal": True},
        {"condition_id": "PNE_001", "symptom": "fever", "snomed": "386661006", "importance": 0.80, "is_cardinal": False},
        {"condition_id": "PNE_001", "symptom": "shortness of breath", "snomed": "267036007", "importance": 0.75, "is_cardinal": False},
        {"condition_id": "PNE_001", "symptom": "chest pain", "snomed": "29857009", "importance": 0.60, "is_cardinal": False},
        # Appendicitis
        {"condition_id": "APP_001", "symptom": "abdominal pain", "snomed": "21522001", "importance": 0.95, "is_cardinal": True},
        {"condition_id": "APP_001", "symptom": "nausea", "snomed": "422587007", "importance": 0.65, "is_cardinal": False},
        {"condition_id": "APP_001", "symptom": "vomiting", "snomed": "422400008", "importance": 0.60, "is_cardinal": False},
        {"condition_id": "APP_001", "symptom": "fever", "snomed": "386661006", "importance": 0.55, "is_cardinal": False},
        # Migraine
        {"condition_id": "MIG_001", "symptom": "headache", "snomed": "25064002", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "MIG_001", "symptom": "nausea", "snomed": "422587007", "importance": 0.70, "is_cardinal": False},
        {"condition_id": "MIG_001", "symptom": "sensitivity to light", "snomed": "409668002", "importance": 0.75, "is_cardinal": False},
        {"condition_id": "MIG_001", "symptom": "visual disturbances", "snomed": "63102001", "importance": 0.65, "is_cardinal": False},
        # Common cold
        {"condition_id": "COLD_001", "symptom": "runny nose", "snomed": "64531003", "importance": 0.85, "is_cardinal": True},
        {"condition_id": "COLD_001", "symptom": "sneezing", "snomed": "162367006", "importance": 0.75, "is_cardinal": False},
        {"condition_id": "COLD_001", "symptom": "sore throat", "snomed": "162397003", "importance": 0.65, "is_cardinal": False},
        {"condition_id": "COLD_001", "symptom": "cough", "snomed": "49727002", "importance": 0.60, "is_cardinal": False},
        # GERD
        {"condition_id": "GERD_001", "symptom": "heartburn", "snomed": "16331000", "importance": 0.95, "is_cardinal": True},
        {"condition_id": "GERD_001", "symptom": "chest pain", "snomed": "29857009", "importance": 0.60, "is_cardinal": False},
        {"condition_id": "GERD_001", "symptom": "difficulty swallowing", "snomed": "40739000", "importance": 0.55, "is_cardinal": False},
        {"condition_id": "GERD_001", "symptom": "nausea", "snomed": "422587007", "importance": 0.45, "is_cardinal": False},
        # UTI
        {"condition_id": "UTI_001", "symptom": "burning urination", "snomed": "49650001", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "UTI_001", "symptom": "frequent urination", "snomed": "162116003", "importance": 0.80, "is_cardinal": False},
        {"condition_id": "UTI_001", "symptom": "abdominal pain", "snomed": "21522001", "importance": 0.55, "is_cardinal": False},
        # Tension headache
        {"condition_id": "TH_001", "symptom": "headache", "snomed": "25064002", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "TH_001", "symptom": "neck pain", "snomed": "81680005", "importance": 0.65, "is_cardinal": False},
        {"condition_id": "TH_001", "symptom": "fatigue", "snomed": "84229001", "importance": 0.45, "is_cardinal": False},
        # Allergic rhinitis
        {"condition_id": "AR_001", "symptom": "sneezing", "snomed": "162367006", "importance": 0.85, "is_cardinal": True},
        {"condition_id": "AR_001", "symptom": "runny nose", "snomed": "64531003", "importance": 0.80, "is_cardinal": False},
        {"condition_id": "AR_001", "symptom": "itchy eyes", "snomed": "418290006", "importance": 0.75, "is_cardinal": False},
        {"condition_id": "AR_001", "symptom": "nasal congestion", "snomed": "68235000", "importance": 0.70, "is_cardinal": False},
        # Gastroenteritis
        {"condition_id": "GE_001", "symptom": "diarrhea", "snomed": "62315008", "importance": 0.90, "is_cardinal": True},
        {"condition_id": "GE_001", "symptom": "vomiting", "snomed": "422400008", "importance": 0.85, "is_cardinal": False},
        {"condition_id": "GE_001", "symptom": "abdominal pain", "snomed": "21522001", "importance": 0.70, "is_cardinal": False},
        {"condition_id": "GE_001", "symptom": "fever", "snomed": "386661006", "importance": 0.50, "is_cardinal": False},
    ]
    save_json(mappings, "symptoms_map.json")
    print(f"  ✅ {len(mappings)} mappings saved\n")


def generate_drug_interactions():
    """Generate curated drug interaction data (sourced from openFDA labels)."""
    print("📝 Generating drug_interactions.json...")
    interactions = [
        # Warfarin interactions
        {"drug_name": "warfarin", "interacts_with": "aspirin", "severity": "major", "description": "Extreme bleeding risk — aspirin inhibits platelet aggregation while warfarin inhibits clotting factors", "source": "openFDA/DrugBank"},
        {"drug_name": "warfarin", "interacts_with": "ibuprofen", "severity": "major", "description": "NSAIDs increase anticoagulant effect and GI bleeding risk", "source": "openFDA"},
        {"drug_name": "warfarin", "interacts_with": "heparin", "severity": "major", "description": "Double anticoagulation — severe hemorrhage risk", "source": "openFDA"},
        {"drug_name": "warfarin", "interacts_with": "naproxen", "severity": "major", "description": "NSAIDs increase bleeding risk with warfarin", "source": "openFDA"},
        # Sertraline interactions
        {"drug_name": "sertraline", "interacts_with": "sumatriptan", "severity": "major", "description": "Serotonin Syndrome risk — both increase serotonin levels", "source": "openFDA"},
        {"drug_name": "sertraline", "interacts_with": "tramadol", "severity": "major", "description": "Serotonin Syndrome — combined serotonergic effect", "source": "openFDA"},
        {"drug_name": "sertraline", "interacts_with": "ibuprofen", "severity": "moderate", "description": "SSRIs + NSAIDs increase GI bleeding risk", "source": "openFDA"},
        {"drug_name": "sertraline", "interacts_with": "warfarin", "severity": "moderate", "description": "SSRIs may increase anticoagulant effect of warfarin", "source": "openFDA"},
        # Metformin interactions
        {"drug_name": "metformin", "interacts_with": "contrast dye", "severity": "major", "description": "Lactic acidosis risk if kidneys cannot clear metformin after contrast", "source": "openFDA"},
        {"drug_name": "metformin", "interacts_with": "alcohol", "severity": "moderate", "description": "Increased risk of lactic acidosis and hypoglycemia", "source": "openFDA"},
        # Lisinopril interactions
        {"drug_name": "lisinopril", "interacts_with": "ibuprofen", "severity": "major", "description": "NSAIDs reduce ACE inhibitor effectiveness and worsen kidney function", "source": "openFDA"},
        {"drug_name": "lisinopril", "interacts_with": "potassium supplements", "severity": "major", "description": "ACE inhibitors + potassium = hyperkalemia (dangerously high potassium)", "source": "openFDA"},
        {"drug_name": "lisinopril", "interacts_with": "naproxen", "severity": "major", "description": "NSAIDs + ACE inhibitors = renal function decline", "source": "openFDA"},
        # Ibuprofen interactions
        {"drug_name": "ibuprofen", "interacts_with": "aspirin", "severity": "moderate", "description": "Ibuprofen can reduce cardioprotective effect of low-dose aspirin", "source": "openFDA"},
        {"drug_name": "ibuprofen", "interacts_with": "warfarin", "severity": "major", "description": "Increased bleeding risk", "source": "openFDA"},
        # Sumatriptan interactions
        {"drug_name": "sumatriptan", "interacts_with": "sertraline", "severity": "major", "description": "Serotonin Syndrome risk", "source": "openFDA"},
        {"drug_name": "sumatriptan", "interacts_with": "fluoxetine", "severity": "major", "description": "Serotonin Syndrome risk with any SSRI", "source": "openFDA"},
        # Amoxicillin
        {"drug_name": "amoxicillin", "interacts_with": "warfarin", "severity": "moderate", "description": "Antibiotics may increase INR and bleeding risk", "source": "openFDA"},
        {"drug_name": "amoxicillin", "interacts_with": "methotrexate", "severity": "major", "description": "Reduced renal clearance of methotrexate", "source": "openFDA"},
        # Atenolol
        {"drug_name": "atenolol", "interacts_with": "verapamil", "severity": "major", "description": "Combined use can cause severe bradycardia and heart block", "source": "openFDA"},
        {"drug_name": "atenolol", "interacts_with": "clonidine", "severity": "moderate", "description": "Rebound hypertension risk if clonidine stopped first", "source": "openFDA"},
    ]
    save_json(interactions, "drug_interactions.json")
    print(f"  ✅ {len(interactions)} interactions saved\n")


def generate_treatments():
    """Generate treatment guidelines for each condition."""
    print("📝 Generating treatments.json...")
    treatments = [
        {"condition_id": "MI_001", "urgency_level": "emergency", "recommendation": "Call 911/112 immediately",
         "self_care": ["Chew 325mg aspirin", "Sit upright and stay calm", "Do NOT drive yourself", "Unlock front door for paramedics"],
         "specialist_type": "cardiologist", "source": "AHA Guidelines"},
        {"condition_id": "STR_001", "urgency_level": "emergency", "recommendation": "Call 911 immediately — FAST protocol",
         "self_care": ["Note the time symptoms started", "Do NOT give food or drink", "Lay person on side if vomiting", "Do NOT take aspirin unless told"],
         "specialist_type": "neurologist", "source": "AHA/ASA Stroke Guidelines"},
        {"condition_id": "PE_001", "urgency_level": "emergency", "recommendation": "Call 911 — requires immediate anticoagulation",
         "self_care": ["Sit upright to ease breathing", "Stay calm", "Do NOT walk or exert yourself"],
         "specialist_type": "pulmonologist", "source": "ESC PE Guidelines"},
        {"condition_id": "ANA_001", "urgency_level": "emergency", "recommendation": "Use EpiPen if available, call 911",
         "self_care": ["Administer epinephrine auto-injector", "Call 911", "Lay flat with legs elevated", "Second EpiPen after 5 min if no improvement"],
         "specialist_type": "allergist", "source": "ACAAI Anaphylaxis Guidelines"},
        {"condition_id": "PYE_001", "urgency_level": "urgent", "recommendation": "See doctor within 24 hours — antibiotics needed",
         "self_care": ["Take Trimethoprim-Sulfamethoxazole (Bactrim) if prescribed", "Take Ibuprofen for pain and fever", "Drink plenty of water", "Apply heating pad to lower back"],
         "specialist_type": "urologist", "source": "AUA Guidelines"},
        {"condition_id": "STRP_001", "urgency_level": "urgent", "recommendation": "See doctor within 24-48 hours for antibiotics",
         "self_care": ["Gargle warm salt water", "Take acetaminophen for pain", "Drink warm fluids", "Rest voice"],
         "specialist_type": "ENT", "source": "IDSA Guidelines"},
        {"condition_id": "PNE_001", "urgency_level": "urgent", "recommendation": "See doctor today — may need antibiotics or chest X-ray",
         "self_care": ["Rest and stay hydrated", "Take acetaminophen for fever", "Use humidifier", "Do NOT suppress productive cough"],
         "specialist_type": "pulmonologist", "source": "ATS/IDSA Guidelines"},
        {"condition_id": "APP_001", "urgency_level": "urgent", "recommendation": "Go to ER — may need surgical evaluation",
         "self_care": ["Do NOT eat or drink (in case surgery needed)", "Do NOT take laxatives", "Apply ice pack (not heat) to abdomen", "Go to nearest ER"],
         "specialist_type": "general surgeon", "source": "SAGES Guidelines"},
        {"condition_id": "MIG_001", "urgency_level": "routine", "recommendation": "Rest in a dark, quiet room",
         "self_care": ["Take Sumatriptan (triptan) for acute relief", "Take Ibuprofen as backup pain relief", "Apply cold compress to forehead", "Stay hydrated"],
         "specialist_type": "neurologist", "source": "AHS Migraine Guidelines"},
        {"condition_id": "COLD_001", "urgency_level": "routine", "recommendation": "Self-care at home — usually resolves in 7-10 days",
         "self_care": ["Rest and stay hydrated", "Take acetaminophen or ibuprofen for symptoms", "Use saline nasal spray", "Honey for cough (adults only)"],
         "specialist_type": "", "source": "CDC Common Cold Guidelines"},
        {"condition_id": "GERD_001", "urgency_level": "routine", "recommendation": "Lifestyle changes + OTC antacids",
         "self_care": ["Take antacids (Tums, Maalox)", "Avoid trigger foods (spicy, acidic, fatty)", "Elevate head of bed 6 inches", "Don't eat 3 hours before bed"],
         "specialist_type": "gastroenterologist", "source": "ACG GERD Guidelines"},
        {"condition_id": "UTI_001", "urgency_level": "routine", "recommendation": "See doctor for antibiotics — usually resolves quickly",
         "self_care": ["Drink plenty of water", "Take AZO (phenazopyridine) for pain relief", "Avoid caffeine and alcohol", "Wipe front to back"],
         "specialist_type": "urologist", "source": "AUA Guidelines"},
        {"condition_id": "TH_001", "urgency_level": "routine", "recommendation": "OTC pain relief + stress management",
         "self_care": ["Take acetaminophen or ibuprofen", "Apply warm compress to neck/shoulders", "Practice relaxation techniques", "Ensure regular sleep schedule"],
         "specialist_type": "neurologist", "source": "AHS Headache Guidelines"},
        {"condition_id": "AR_001", "urgency_level": "routine", "recommendation": "Antihistamines + allergen avoidance",
         "self_care": ["Take cetirizine (Zyrtec) or loratadine (Claritin)", "Use nasal corticosteroid spray", "Keep windows closed during high pollen", "Shower after outdoor activity"],
         "specialist_type": "allergist", "source": "AAAAI Rhinitis Guidelines"},
        {"condition_id": "GE_001", "urgency_level": "routine", "recommendation": "Hydration and rest — see doctor if lasts >3 days",
         "self_care": ["Oral rehydration solution (ORS) or Pedialyte", "BRAT diet (bananas, rice, applesauce, toast)", "Avoid dairy and fatty foods", "Take Imodium for diarrhea if needed"],
         "specialist_type": "gastroenterologist", "source": "ACG Guidelines"},
    ]
    save_json(treatments, "treatments.json")
    print(f"  ✅ {len(treatments)} treatments saved\n")


def generate_emergency_rules():
    """Generate emergency detection rules."""
    print("📝 Generating emergency_rules.json...")
    rules = [
        {"rule_name": "cardiac_emergency", "required_symptoms": ["chest pain", "shortness of breath"],
         "risk_factors": {"min_age": 50, "conditions": ["diabetes", "heart disease", "previous MI"]},
         "action": "Call 911 immediately", "confidence_boost": 0.4},
        {"rule_name": "cardiac_classic", "required_symptoms": ["chest pain", "left arm pain", "sweating"],
         "risk_factors": {"min_age": 40}, "action": "Call 911 — classic heart attack presentation", "confidence_boost": 0.5},
        {"rule_name": "stroke_fast", "required_symptoms": ["sudden weakness one side", "speech difficulty"],
         "risk_factors": {"min_age": 40}, "action": "Call 911 — FAST protocol (Face Arms Speech Time)", "confidence_boost": 0.5},
        {"rule_name": "anaphylaxis", "required_symptoms": ["swelling throat", "difficulty breathing"],
         "risk_factors": {}, "action": "Use EpiPen + Call 911", "confidence_boost": 0.5},
        {"rule_name": "pe_signs", "required_symptoms": ["shortness of breath", "chest pain", "coughing blood"],
         "risk_factors": {}, "action": "Call 911 — possible pulmonary embolism", "confidence_boost": 0.4},
        {"rule_name": "severe_bleeding", "required_symptoms": ["vomiting blood", "blood in stool"],
         "risk_factors": {"conditions": ["liver disease"]}, "action": "Call 911 — GI hemorrhage", "confidence_boost": 0.5},
        {"rule_name": "meningitis", "required_symptoms": ["severe headache", "fever", "stiff neck"],
         "risk_factors": {}, "action": "Go to ER immediately — possible meningitis", "confidence_boost": 0.4},
        {"rule_name": "diabetic_emergency", "required_symptoms": ["confusion", "fruity breath", "rapid breathing"],
         "risk_factors": {"conditions": ["diabetes"]}, "action": "Call 911 — possible DKA", "confidence_boost": 0.4},
        {"rule_name": "seizure", "required_symptoms": ["seizure", "loss of consciousness"],
         "risk_factors": {}, "action": "Call 911 — protect head, do NOT restrain", "confidence_boost": 0.5},
        {"rule_name": "severe_allergic_reaction", "required_symptoms": ["hives", "swelling throat", "low blood pressure"],
         "risk_factors": {}, "action": "Use EpiPen + Call 911", "confidence_boost": 0.5},
    ]
    save_json(rules, "emergency_rules.json")
    print(f"  ✅ {len(rules)} rules saved\n")


def generate_ontology_terms():
    """Generate SNOMED/ICD-10 ontology mappings for all symptoms used."""
    print("📝 Generating ontology_terms.json...")
    terms = [
        {"term": "chest pain", "snomed_code": "29857009", "snomed_label": "Chest pain (finding)", "icd10_code": "R07.9", "semantic_type": "Sign or Symptom"},
        {"term": "shortness of breath", "snomed_code": "267036007", "snomed_label": "Dyspnea (finding)", "icd10_code": "R06.0", "semantic_type": "Sign or Symptom"},
        {"term": "headache", "snomed_code": "25064002", "snomed_label": "Headache (finding)", "icd10_code": "R51", "semantic_type": "Sign or Symptom"},
        {"term": "nausea", "snomed_code": "422587007", "snomed_label": "Nausea (finding)", "icd10_code": "R11.0", "semantic_type": "Sign or Symptom"},
        {"term": "vomiting", "snomed_code": "422400008", "snomed_label": "Vomiting (disorder)", "icd10_code": "R11.1", "semantic_type": "Sign or Symptom"},
        {"term": "fever", "snomed_code": "386661006", "snomed_label": "Fever (finding)", "icd10_code": "R50.9", "semantic_type": "Sign or Symptom"},
        {"term": "cough", "snomed_code": "49727002", "snomed_label": "Cough (finding)", "icd10_code": "R05", "semantic_type": "Sign or Symptom"},
        {"term": "abdominal pain", "snomed_code": "21522001", "snomed_label": "Abdominal pain (finding)", "icd10_code": "R10.9", "semantic_type": "Sign or Symptom"},
        {"term": "diarrhea", "snomed_code": "62315008", "snomed_label": "Diarrhea (finding)", "icd10_code": "R19.7", "semantic_type": "Sign or Symptom"},
        {"term": "fatigue", "snomed_code": "84229001", "snomed_label": "Fatigue (finding)", "icd10_code": "R53.83", "semantic_type": "Sign or Symptom"},
        {"term": "sweating", "snomed_code": "415690000", "snomed_label": "Diaphoresis (finding)", "icd10_code": "R61", "semantic_type": "Sign or Symptom"},
        {"term": "sore throat", "snomed_code": "162397003", "snomed_label": "Pain in throat (finding)", "icd10_code": "R07.0", "semantic_type": "Sign or Symptom"},
        {"term": "runny nose", "snomed_code": "64531003", "snomed_label": "Nasal discharge (finding)", "icd10_code": "R09.89", "semantic_type": "Sign or Symptom"},
        {"term": "burning urination", "snomed_code": "49650001", "snomed_label": "Dysuria (finding)", "icd10_code": "R30.0", "semantic_type": "Sign or Symptom"},
        {"term": "left arm pain", "snomed_code": "10601006", "snomed_label": "Pain in left arm (finding)", "icd10_code": "M79.602", "semantic_type": "Sign or Symptom"},
        {"term": "jaw pain", "snomed_code": "274667000", "snomed_label": "Pain in jaw (finding)", "icd10_code": "R68.84", "semantic_type": "Sign or Symptom"},
        {"term": "sensitivity to light", "snomed_code": "409668002", "snomed_label": "Photophobia (finding)", "icd10_code": "H53.14", "semantic_type": "Sign or Symptom"},
        {"term": "flank pain", "snomed_code": "274743004", "snomed_label": "Flank pain (finding)", "icd10_code": "R10.9", "semantic_type": "Sign or Symptom"},
        {"term": "frequent urination", "snomed_code": "162116003", "snomed_label": "Urinary frequency (finding)", "icd10_code": "R35.0", "semantic_type": "Sign or Symptom"},
        {"term": "heartburn", "snomed_code": "16331000", "snomed_label": "Heartburn (finding)", "icd10_code": "R12", "semantic_type": "Sign or Symptom"},
        {"term": "sneezing", "snomed_code": "162367006", "snomed_label": "Sneezing (finding)", "icd10_code": "R06.7", "semantic_type": "Sign or Symptom"},
        {"term": "difficulty swallowing", "snomed_code": "40739000", "snomed_label": "Dysphagia (disorder)", "icd10_code": "R13.10", "semantic_type": "Sign or Symptom"},
        {"term": "rapid heartbeat", "snomed_code": "3424008", "snomed_label": "Tachycardia (finding)", "icd10_code": "R00.0", "semantic_type": "Sign or Symptom"},
        {"term": "confusion", "snomed_code": "40917007", "snomed_label": "Confusion (finding)", "icd10_code": "R41.0", "semantic_type": "Sign or Symptom"},
        {"term": "swollen lymph nodes", "snomed_code": "30746006", "snomed_label": "Lymphadenopathy (disorder)", "icd10_code": "R59.9", "semantic_type": "Clinical Finding"},
        {"term": "hives", "snomed_code": "126485001", "snomed_label": "Urticaria (disorder)", "icd10_code": "L50.9", "semantic_type": "Clinical Finding"},
        {"term": "neck pain", "snomed_code": "81680005", "snomed_label": "Neck pain (finding)", "icd10_code": "M54.2", "semantic_type": "Sign or Symptom"},
        {"term": "itchy eyes", "snomed_code": "418290006", "snomed_label": "Itching of eye (finding)", "icd10_code": "H57.19", "semantic_type": "Sign or Symptom"},
        {"term": "nasal congestion", "snomed_code": "68235000", "snomed_label": "Nasal congestion (finding)", "icd10_code": "R09.81", "semantic_type": "Sign or Symptom"},
        {"term": "visual disturbances", "snomed_code": "63102001", "snomed_label": "Visual disturbance (finding)", "icd10_code": "H53.9", "semantic_type": "Sign or Symptom"},
        {"term": "facial drooping", "snomed_code": "271587009", "snomed_label": "Facial asymmetry (finding)", "icd10_code": "R29.810", "semantic_type": "Sign or Symptom"},
        {"term": "speech difficulty", "snomed_code": "29164008", "snomed_label": "Dysarthria (finding)", "icd10_code": "R47.1", "semantic_type": "Sign or Symptom"},
        {"term": "swelling throat", "snomed_code": "267102003", "snomed_label": "Swelling of throat (finding)", "icd10_code": "R22.1", "semantic_type": "Sign or Symptom"},
        {"term": "low blood pressure", "snomed_code": "45007003", "snomed_label": "Hypotension (disorder)", "icd10_code": "I95.9", "semantic_type": "Clinical Finding"},
        {"term": "coughing blood", "snomed_code": "66857006", "snomed_label": "Hemoptysis (finding)", "icd10_code": "R04.2", "semantic_type": "Sign or Symptom"},
        {"term": "sudden weakness one side", "snomed_code": "26544005", "snomed_label": "Hemiparesis (finding)", "icd10_code": "G81.9", "semantic_type": "Clinical Finding"},
        {"term": "difficulty breathing", "snomed_code": "267036007", "snomed_label": "Dyspnea (finding)", "icd10_code": "R06.0", "semantic_type": "Sign or Symptom"},
    ]
    save_json(terms, "ontology_terms.json")
    print(f"  ✅ {len(terms)} terms saved\n")


def generate_synonyms():
    """Generate lay-term to medical-term synonym mappings."""
    print("📝 Generating synonyms.json...")
    synonyms = [
        {"synonym": "tummy ache", "canonical": "abdominal pain"},
        {"synonym": "stomach ache", "canonical": "abdominal pain"},
        {"synonym": "belly pain", "canonical": "abdominal pain"},
        {"synonym": "cant breathe", "canonical": "shortness of breath"},
        {"synonym": "hard to breathe", "canonical": "shortness of breath"},
        {"synonym": "out of breath", "canonical": "shortness of breath"},
        {"synonym": "heart racing", "canonical": "rapid heartbeat"},
        {"synonym": "heart pounding", "canonical": "rapid heartbeat"},
        {"synonym": "throwing up", "canonical": "vomiting"},
        {"synonym": "puking", "canonical": "vomiting"},
        {"synonym": "being sick", "canonical": "vomiting"},
        {"synonym": "feeling sick", "canonical": "nausea"},
        {"synonym": "queasy", "canonical": "nausea"},
        {"synonym": "pins and needles", "canonical": "numbness"},
        {"synonym": "runny nose", "canonical": "runny nose"},
        {"synonym": "stuffy nose", "canonical": "nasal congestion"},
        {"synonym": "blocked nose", "canonical": "nasal congestion"},
        {"synonym": "peeing a lot", "canonical": "frequent urination"},
        {"synonym": "pee burns", "canonical": "burning urination"},
        {"synonym": "hurts to pee", "canonical": "burning urination"},
        {"synonym": "burning when I pee", "canonical": "burning urination"},
        {"synonym": "head pounding", "canonical": "headache"},
        {"synonym": "head hurts", "canonical": "headache"},
        {"synonym": "migraine", "canonical": "headache"},
        {"synonym": "the runs", "canonical": "diarrhea"},
        {"synonym": "loose stool", "canonical": "diarrhea"},
        {"synonym": "watery stool", "canonical": "diarrhea"},
        {"synonym": "acid reflux", "canonical": "heartburn"},
        {"synonym": "indigestion", "canonical": "heartburn"},
        {"synonym": "tired all the time", "canonical": "fatigue"},
        {"synonym": "exhausted", "canonical": "fatigue"},
        {"synonym": "no energy", "canonical": "fatigue"},
        {"synonym": "chest tightness", "canonical": "chest pain"},
        {"synonym": "chest pressure", "canonical": "chest pain"},
        {"synonym": "throat hurts", "canonical": "sore throat"},
        {"synonym": "scratchy throat", "canonical": "sore throat"},
        {"synonym": "hard to swallow", "canonical": "difficulty swallowing"},
        {"synonym": "food gets stuck", "canonical": "difficulty swallowing"},
        {"synonym": "high temperature", "canonical": "fever"},
        {"synonym": "hot forehead", "canonical": "fever"},
        {"synonym": "chills", "canonical": "fever"},
        {"synonym": "cold sweat", "canonical": "sweating"},
        {"synonym": "profuse sweating", "canonical": "sweating"},
        {"synonym": "blurry vision", "canonical": "visual disturbances"},
        {"synonym": "seeing spots", "canonical": "visual disturbances"},
        {"synonym": "light hurts eyes", "canonical": "sensitivity to light"},
        {"synonym": "eyes watering", "canonical": "itchy eyes"},
        {"synonym": "back pain", "canonical": "flank pain"},
        {"synonym": "side pain", "canonical": "flank pain"},
        {"synonym": "swollen glands", "canonical": "swollen lymph nodes"},
        {"synonym": "welts on skin", "canonical": "hives"},
        {"synonym": "rash", "canonical": "hives"},
        {"synonym": "face drooping", "canonical": "facial drooping"},
        {"synonym": "slurred speech", "canonical": "speech difficulty"},
        {"synonym": "cant talk properly", "canonical": "speech difficulty"},
    ]
    save_json(synonyms, "synonyms.json")
    print(f"  ✅ {len(synonyms)} synonyms saved\n")


def generate_specialists():
    """Generate specialist directory."""
    print("📝 Generating specialists.json...")
    specialists = [
        {"specialist_type": "Cardiologist", "condition_ids": ["MI_001"], "body_systems": ["cardiovascular"], "description": "Heart and blood vessel specialist"},
        {"specialist_type": "Neurologist", "condition_ids": ["STR_001", "MIG_001", "TH_001"], "body_systems": ["neurological"], "description": "Brain and nervous system specialist"},
        {"specialist_type": "Pulmonologist", "condition_ids": ["PE_001", "PNE_001"], "body_systems": ["respiratory"], "description": "Lung and respiratory specialist"},
        {"specialist_type": "Allergist", "condition_ids": ["ANA_001", "AR_001"], "body_systems": ["immune"], "description": "Allergy and immunology specialist"},
        {"specialist_type": "Urologist", "condition_ids": ["PYE_001", "UTI_001"], "body_systems": ["renal"], "description": "Urinary tract and kidney specialist"},
        {"specialist_type": "ENT", "condition_ids": ["STRP_001"], "body_systems": ["respiratory"], "description": "Ear, Nose, and Throat specialist"},
        {"specialist_type": "General Surgeon", "condition_ids": ["APP_001"], "body_systems": ["gastrointestinal"], "description": "Surgical specialist"},
        {"specialist_type": "Gastroenterologist", "condition_ids": ["GERD_001", "GE_001"], "body_systems": ["gastrointestinal"], "description": "Digestive system specialist"},
    ]
    save_json(specialists, "specialists.json")
    print(f"  ✅ {len(specialists)} specialists saved\n")


# ──────────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────────
def save_json(data, filename):
    fpath = DATA_DIR / filename
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  NEUROHEALTH — Automated Data Gathering Script")
    print("=" * 60)

    # Phase 1: Fetch from APIs
    gather_articles()
    gather_drug_data_raw()

    # Phase 2: Generate curated JSON files
    generate_conditions_json()
    generate_symptoms_map()
    generate_drug_interactions()
    generate_treatments()
    generate_emergency_rules()
    generate_ontology_terms()
    generate_synonyms()
    generate_specialists()

    print("=" * 60)
    print("  ✅ ALL DATA FILES GENERATED!")
    print("=" * 60)
    print(f"\n  Output directory: {DATA_DIR}")
    print(f"  Files created:")
    for f in sorted(DATA_DIR.glob("*.json")):
        size = f.stat().st_size
        print(f"    📄 {f.name:30s} {size:>6,} bytes")
    article_count = len(list(ARTICLES_DIR.glob("*.txt")))
    print(f"    📁 articles/  ({article_count} articles)")
    print()


if __name__ == "__main__":
    main()
