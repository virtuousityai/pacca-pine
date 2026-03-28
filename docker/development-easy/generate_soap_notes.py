#!/usr/bin/env python3
"""Generate SOAP notes for patients who don't have any.
Runs against the OpenEMR MySQL database inside Docker.
Uses template-based generation with randomized clinical content."""

import subprocess
import random
import json
from datetime import datetime, timedelta

BATCH_SIZE = 20

# Realistic SOAP note templates
SUBJECTIVE_TEMPLATES = [
    "Patient presents with complaints of {complaint}. Reports onset {onset}. Denies {denial}. States symptoms are {severity}. {additional}",
    "Chief complaint: {complaint}. Patient reports {onset} onset. Associated symptoms include {associated}. Denies {denial}. {additional}",
    "Patient returns for follow-up of {complaint}. Reports {improvement}. Current medications include {meds}. Denies {denial}. {additional}",
    "Patient presents for routine {visit_type}. Reports {complaint} for the past {duration}. {additional} Denies {denial}.",
]

COMPLAINTS = [
    "persistent headaches", "lower back pain", "fatigue and malaise", "joint stiffness in both knees",
    "intermittent chest discomfort", "difficulty sleeping", "shortness of breath on exertion",
    "recurrent abdominal pain", "dizziness and lightheadedness", "chronic cough",
    "bilateral hip pain", "anxiety and restlessness", "nausea and decreased appetite",
    "numbness in extremities", "frequent urination", "skin rash on forearms",
    "sore throat and nasal congestion", "blurred vision", "muscle weakness",
    "swelling in ankles", "palpitations", "weight gain over past 3 months",
    "generalized body aches", "difficulty concentrating", "bilateral shoulder pain",
]

ONSETS = ["gradual over 2 weeks", "acute 3 days ago", "worsening over the past month",
          "intermittent for 6 weeks", "sudden onset yesterday", "progressive over several months"]

DENIALS = ["fever, chills, or night sweats", "chest pain or palpitations", "nausea, vomiting, or diarrhea",
           "recent trauma or injury", "weight loss or gain", "vision changes or hearing loss",
           "urinary symptoms", "suicidal ideation or self-harm"]

SEVERITIES = ["moderate and worsening", "mild but persistent", "severe and debilitating",
              "intermittent, rated 5/10", "constant, rated 7/10", "improving but still present"]

ASSOCIATED = ["mild fatigue", "occasional nausea", "sleep disturbance", "decreased appetite",
              "mild swelling", "morning stiffness", "intermittent cramping"]

IMPROVEMENTS = ["partial improvement with current regimen", "no significant change since last visit",
                "worsening despite treatment", "improvement with medication adjustment",
                "stable condition with good compliance"]

MEDICATIONS = [
    "metformin 500mg BID, lisinopril 10mg daily",
    "atorvastatin 20mg daily, aspirin 81mg daily",
    "omeprazole 20mg daily, acetaminophen PRN",
    "amlodipine 5mg daily, metoprolol 25mg BID",
    "levothyroxine 50mcg daily, vitamin D 2000 IU daily",
    "sertraline 50mg daily, ibuprofen 400mg PRN",
    "hydrochlorothiazide 25mg daily, potassium chloride 10mEq daily",
]

VISIT_TYPES = ["wellness exam", "annual physical", "chronic disease management", "medication review"]
DURATIONS = ["2 weeks", "1 month", "3 months", "6 weeks", "several days"]
ADDITIONALS = [
    "No recent hospitalizations.", "Family history significant for hypertension.",
    "Patient is a non-smoker.", "Reports adequate fluid intake.", "Exercises 3 times weekly.",
    "Diet has been poor recently.", "Sleeps approximately 6 hours per night.",
    "Works at a desk job with minimal physical activity.", "Reports high stress levels at work.",
    ""
]

# Objective templates
OBJECTIVE_TEMPLATES = [
    "VS: BP {bp}, HR {hr}, RR {rr}, Temp {temp}F, SpO2 {spo2}%, BMI {bmi}. General: {general}. {systems}",
    "Vitals: Blood pressure {bp}, pulse {hr}, respirations {rr}, temperature {temp}F, oxygen saturation {spo2}%. Weight {weight} lbs. {general}. {systems}",
]

BPS = ["120/80", "130/85", "142/92", "118/76", "135/88", "128/82", "150/95", "122/78", "138/90", "126/84"]
HRS = ["72", "78", "84", "68", "88", "76", "92", "70", "80", "66"]
RRS = ["16", "18", "20", "14", "17"]
TEMPS = ["98.6", "98.4", "99.1", "98.8", "97.9", "100.2"]
SPO2S = ["98", "97", "99", "96", "95", "98"]
BMIS = ["24.5", "28.3", "31.2", "22.8", "26.7", "33.1", "25.4", "29.8", "27.1", "23.6"]
WEIGHTS = ["165", "182", "210", "145", "198", "155", "230", "172", "188", "140"]
GENERALS = [
    "Alert and oriented x3, in no acute distress",
    "Well-appearing, well-nourished, cooperative",
    "Appears fatigued but in no distress",
    "Alert, oriented, mildly anxious",
]
SYSTEMS = [
    "HEENT: PERRLA, EOMI, oropharynx clear. Neck: supple, no lymphadenopathy. Lungs: CTA bilaterally. CV: RRR, no murmurs. Abd: soft, non-tender, non-distended.",
    "Cardiac: Regular rate and rhythm, S1/S2 normal. Lungs: Clear to auscultation. Abdomen: Soft, non-distended, bowel sounds present. Extremities: No edema.",
    "Skin: Warm, dry, intact. Musculoskeletal: Full ROM in all extremities, no joint effusion. Neuro: CN II-XII intact, DTRs 2+ symmetric.",
    "Respiratory: No wheezing or rales. Cardiovascular: Normal S1/S2, no gallops. GI: Non-tender, no hepatosplenomegaly. Musculoskeletal: Mild tenderness to palpation.",
]

# Assessment templates
ASSESSMENT_TEMPLATES = [
    "1. {dx1} - {status1}\n2. {dx2} - {status2}\n{extra}",
    "{dx1}: {status1}. {dx2}: {status2}. {extra}",
    "Primary: {dx1} ({status1}). Secondary: {dx2} ({status2}). {extra}",
]

DIAGNOSES = [
    ("Essential hypertension", "controlled on current regimen"),
    ("Essential hypertension", "suboptimally controlled, needs adjustment"),
    ("Type 2 diabetes mellitus", "A1c at goal"),
    ("Type 2 diabetes mellitus", "A1c elevated, needs intervention"),
    ("Hyperlipidemia", "stable on statin therapy"),
    ("Major depressive disorder", "improving with SSRI"),
    ("Generalized anxiety disorder", "moderate symptoms"),
    ("Chronic low back pain", "managed with conservative measures"),
    ("Osteoarthritis", "progressive, affecting daily activities"),
    ("GERD", "well controlled on PPI"),
    ("Hypothyroidism", "TSH within normal limits"),
    ("Obesity", "BMI >30, counseled on lifestyle changes"),
    ("Insomnia", "responding to sleep hygiene measures"),
    ("Chronic kidney disease stage 2", "stable creatinine"),
    ("Vitamin D deficiency", "supplementing"),
    ("Iron deficiency anemia", "improving with supplementation"),
    ("Allergic rhinitis", "seasonal, managed with antihistamines"),
    ("Migraine without aura", "frequency reduced with preventive therapy"),
    ("Benign prostatic hyperplasia", "stable symptoms"),
    ("Asthma", "well controlled, no recent exacerbations"),
]

EXTRAS = [
    "Labs ordered for follow-up.", "Will reassess at next visit.", "Patient counseled on lifestyle modifications.",
    "Screening labs reviewed, within normal limits.", "Discussed risks and benefits of treatment options.",
    "Patient understands plan and agrees.", ""
]

# Plan templates
PLAN_TEMPLATES = [
    "1. {action1}\n2. {action2}\n3. {action3}\nFollow up in {followup}.",
    "- {action1}\n- {action2}\n- {action3}\nReturn to clinic in {followup}.",
    "{action1}. {action2}. {action3}. Schedule follow-up in {followup}.",
]

ACTIONS = [
    "Continue current medications as prescribed",
    "Increase lisinopril to 20mg daily",
    "Order CBC, CMP, lipid panel, and HbA1c",
    "Refer to physical therapy for 6 weeks",
    "Start metformin 500mg BID with meals",
    "Counsel on diet and exercise program",
    "Order chest X-ray and pulmonary function tests",
    "Add omeprazole 20mg daily before breakfast",
    "Switch from HCTZ to amlodipine 5mg daily",
    "Refill all current prescriptions for 90 days",
    "Order TSH and free T4 levels",
    "Schedule colonoscopy screening",
    "Prescribe acetaminophen 500mg PRN for pain",
    "Refer to psychiatry for medication management",
    "Order echocardiogram",
    "Recommend smoking cessation program",
    "Start sertraline 25mg daily, titrate to 50mg in 1 week",
    "Order urinalysis and urine culture",
    "Prescribe albuterol inhaler PRN",
    "Apply topical hydrocortisone cream BID to affected area",
    "Recommend DASH diet for blood pressure management",
    "Order bone density scan (DEXA)",
    "Check vitamin B12 and folate levels",
    "Increase atorvastatin to 40mg daily",
]

FOLLOWUPS = ["2 weeks", "4 weeks", "6 weeks", "3 months", "6 months", "1 month"]


def generate_soap():
    """Generate a random but realistic SOAP note."""
    # Subjective
    s_template = random.choice(SUBJECTIVE_TEMPLATES)
    subjective = s_template.format(
        complaint=random.choice(COMPLAINTS),
        onset=random.choice(ONSETS),
        denial=random.choice(DENIALS),
        severity=random.choice(SEVERITIES),
        associated=random.choice(ASSOCIATED),
        improvement=random.choice(IMPROVEMENTS),
        meds=random.choice(MEDICATIONS),
        visit_type=random.choice(VISIT_TYPES),
        duration=random.choice(DURATIONS),
        additional=random.choice(ADDITIONALS),
    )

    # Objective
    o_template = random.choice(OBJECTIVE_TEMPLATES)
    objective = o_template.format(
        bp=random.choice(BPS), hr=random.choice(HRS), rr=random.choice(RRS),
        temp=random.choice(TEMPS), spo2=random.choice(SPO2S), bmi=random.choice(BMIS),
        weight=random.choice(WEIGHTS), general=random.choice(GENERALS), systems=random.choice(SYSTEMS),
    )

    # Assessment
    dx1 = random.choice(DIAGNOSES)
    dx2 = random.choice([d for d in DIAGNOSES if d != dx1])
    a_template = random.choice(ASSESSMENT_TEMPLATES)
    assessment = a_template.format(
        dx1=dx1[0], status1=dx1[1], dx2=dx2[0], status2=dx2[1],
        extra=random.choice(EXTRAS),
    )

    # Plan
    actions = random.sample(ACTIONS, 3)
    p_template = random.choice(PLAN_TEMPLATES)
    plan = p_template.format(
        action1=actions[0], action2=actions[1], action3=actions[2],
        followup=random.choice(FOLLOWUPS),
    )

    return subjective, objective, assessment, plan


def run_sql(sql, params=None):
    """Execute SQL inside the Docker container."""
    cmd = [
        "docker", "compose", "exec", "-T", "openemr",
        "mariadb", "-u", "root", "-proot", "openemr", "-e", sql
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                          cwd="/Users/sathiyankutty/Documents/claude-code/openemr/docker/development-easy")
    if result.returncode != 0:
        print(f"SQL Error: {result.stderr}")
    return result.stdout


def get_patients_without_soap():
    """Get list of patients who have no SOAP notes."""
    sql = """
    SELECT pd.pid, pd.fname, pd.lname
    FROM patient_data pd
    LEFT JOIN form_soap fs ON fs.pid = pd.pid AND fs.activity = 1
    WHERE fs.id IS NULL
    ORDER BY pd.pid;
    """
    output = run_sql(sql)
    patients = []
    for line in output.strip().split("\n")[1:]:  # skip header
        parts = line.split("\t")
        if len(parts) >= 3:
            patients.append({"pid": int(parts[0]), "fname": parts[1], "lname": parts[2]})
    return patients


def get_encounters_for_patient(pid):
    """Get encounter IDs for a patient."""
    sql = f"SELECT encounter FROM form_encounter WHERE pid = {pid} ORDER BY date DESC LIMIT 3;"
    output = run_sql(sql)
    encounters = []
    for line in output.strip().split("\n")[1:]:
        line = line.strip()
        if line:
            encounters.append(int(line))
    return encounters


def insert_soap(pid, encounter, subjective, objective, assessment, plan):
    """Insert a SOAP note into form_soap and register in forms table."""
    # Escape single quotes for SQL
    s = subjective.replace("'", "\\'")
    o = objective.replace("'", "\\'")
    a = assessment.replace("'", "\\'")
    p = plan.replace("'", "\\'")

    # Random date within last 6 months
    days_ago = random.randint(1, 180)
    note_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")

    # Insert into form_soap
    sql_soap = f"""
    INSERT INTO form_soap (date, pid, user, groupname, authorized, activity, subjective, objective, assessment, plan)
    VALUES ('{note_date}', {pid}, 'admin', 'Default', 1, 1, '{s}', '{o}', '{a}', '{p}');
    SELECT LAST_INSERT_ID();
    """
    output = run_sql(sql_soap)
    # Parse the LAST_INSERT_ID
    lines = output.strip().split("\n")
    form_id = None
    for line in lines:
        line = line.strip()
        if line.isdigit():
            form_id = int(line)
    if not form_id:
        print(f"  ERROR: Could not get form_id for pid={pid}")
        return False

    # Register in forms table
    sql_forms = f"""
    INSERT INTO forms (date, encounter, form_name, form_id, pid, user, groupname, authorized, deleted, formdir)
    VALUES ('{note_date}', {encounter}, 'SOAP', {form_id}, {pid}, 'admin', 'Default', 1, 0, 'soap');
    """
    run_sql(sql_forms)
    return True


def main():
    print("=" * 60)
    print("SOAP Note Generator for Pacca PINE")
    print("=" * 60)

    patients = get_patients_without_soap()
    total = len(patients)
    print(f"\nFound {total} patients without SOAP notes.\n")

    if total == 0:
        print("All patients already have SOAP notes!")
        return

    created = 0
    skipped = 0
    batch_num = 0

    for i in range(0, total, BATCH_SIZE):
        batch = patients[i:i + BATCH_SIZE]
        batch_num += 1
        print(f"--- Batch {batch_num} ({i + 1}-{min(i + BATCH_SIZE, total)} of {total}) ---")

        for patient in batch:
            pid = patient["pid"]
            name = f"{patient['fname']} {patient['lname']}"

            # Get encounters for this patient
            encounters = get_encounters_for_patient(pid)
            if not encounters:
                print(f"  SKIP: {name} (pid={pid}) - no encounters")
                skipped += 1
                continue

            # Create 1-2 SOAP notes per patient
            num_notes = random.choice([1, 1, 1, 2])  # 75% get 1, 25% get 2
            for n in range(min(num_notes, len(encounters))):
                enc = encounters[n]
                s, o, a, p = generate_soap()
                success = insert_soap(pid, enc, s, o, a, p)
                if success:
                    created += 1
                    print(f"  OK: {name} (pid={pid}, enc={enc})")

        print(f"  Batch {batch_num} complete. Total created so far: {created}\n")

    print("=" * 60)
    print(f"DONE! Created {created} SOAP notes. Skipped {skipped} patients (no encounters).")
    print("=" * 60)


if __name__ == "__main__":
    main()
