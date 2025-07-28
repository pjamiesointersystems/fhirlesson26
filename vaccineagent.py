import os
import json
import requests
import iris
from typing import List
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode
import re

# === Configuration ===
LMSTUDIO_API_BASE = "http://localhost:1234/v1"
MODEL = "mistral-7b-instruct-v0.3"
FHIR_BASE_URL = "http://127.0.0.1:8080/csp/healthshare/demo/fhir/r4"
FHIR_AUTH = HTTPBasicAuth("_SYSTEM", "ISCDEMO")

# === Tools ===
def GetPatientByName(name: str):
    print(f"[Tool] Looking up patient by name: {name}")
    name_parts = name.strip().split()
    last_name_fragment = ""
    if len(name_parts) >= 1:
        # Assume last name is the last word and extract first 4 alphanumeric characters
        last_name_raw = name_parts[-1]
        alphanum = re.sub(r"[^A-Za-z0-9]", "", last_name_raw)
        last_name_fragment = alphanum[:4]

    if not last_name_fragment:
        print("No usable last name fragment found.")
        return []

    query_params = urlencode({"family:contains": last_name_fragment})
    url = f"{FHIR_BASE_URL}/Patient?{query_params}"
    print(f"[Debug] FHIR Patient URL: {url}")
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
        "Prefer": "return=representation"
    }
    response = requests.get(url, headers=headers, auth=FHIR_AUTH)
    if response.status_code != 200:
        print("FHIR Patient lookup failed:", response.status_code)
        return []

    bundle = response.json()
    entries = bundle.get("entry", [])
    patients = []
    for e in entries:
        resource = e.get("resource", {})
        pid = resource.get("id")
        gender = resource.get("gender", "unknown")
        birth_date = resource.get("birthDate", "unknown")
        names = resource.get("name", [])
        display_name = "Unknown"
        if names:
            given = " ".join(names[0].get("given", []))
            family = names[0].get("family", "")
            display_name = f"{given} {family}".strip()
        patients.append({
            "id": pid,
            "name": display_name,
            "gender": gender,
            "birthDate": birth_date
        })

    return patients

def GetVaccineCodes(disease: str):
    print(f"[Tool] Fetching vaccine codes for disease: {disease}")
    conn = None
    cursor = None
    try:
        conn = iris.connect("127.0.0.1", 1972, "DEMO", "_SYSTEM", "ISCDEMO")
        cursor = conn.cursor()
        query = """
        SELECT cvx_code, short_description, full_vaccine_name
        FROM sql1.cvx_codes
        WHERE LOWER(short_description) LIKE ? OR LOWER(full_vaccine_name) LIKE ?
        """
        search = f"%{disease.lower()}%"
        print(f"[Debug] Executing Vaccine SQL Query with: {search}")
        cursor.execute(query, (search, search))
        rows = cursor.fetchall()
        return [
            {
                "cvx_code": str(row[0]),
                "short_description": row[1],
                "full_vaccine_name": row[2]
            } for row in rows
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def GetAllImmunizations(patient_id: str):
    print(f"[Tool] Retrieving all immunizations for patient {patient_id}")
    query = urlencode({"patient": f"Patient/{patient_id}"})
    url = f"{FHIR_BASE_URL}/Immunization?{query}"
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
        "Prefer": "return=representation"
    }
    response = requests.get(url, headers=headers, auth=FHIR_AUTH)
    if response.status_code != 200:
        print("FHIR Immunization lookup failed:", response.status_code)
        return []

    data = response.json()
    entries = data.get("entry", [])
    immunizations = []
    for e in entries:
        resource = e.get("resource", {})
        status = resource.get("status", "unknown")
        date = resource.get("occurrenceDateTime", "unknown")
        code = None
        code_display = resource.get("vaccineCode", {}).get("text")
        codings = resource.get("vaccineCode", {}).get("coding", [])
        for c in codings:
            if c.get("system") == "http://hl7.org/fhir/sid/cvx":
                code = c.get("code")
                if not code_display:
                    code_display = c.get("display")
        immunizations.append({
            "cvx_code": code,
            "status": status,
            "date": date,
            "description": code_display or "Unknown"
        })

    return immunizations

# === Helper ===
def call_mistral(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    response = requests.post(f"{LMSTUDIO_API_BASE}/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("Error:", response.text)
        return ""

def extract_json(text: str) -> dict:
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end])
    except Exception as e:
        print("Failed to parse JSON:", e)
        return {}
    


   

# === Main Flow ===
def main():
    print("\nWelcome to the Vaccine Status Checker (manual steps with Mistral)")

    while True:
        user_question = input("\nAsk your question (or type 'exit'): ")
        if user_question.lower() in ("exit", "quit"): break

        # Step 1: Extract patient name and disease
        extract_prompt = f"""
Extract the patient name and the infectious disease name from the question below.
Return them as JSON with keys 'patient_name' and 'disease'.

Question: {user_question}
"""
        parsed = extract_json(call_mistral(extract_prompt))
        print("\n[Step 1] Extracted:", parsed)
        if not parsed.get("patient_name") or not parsed.get("disease"):
            print("Could not extract required fields. Try again.")
            continue

        # Step 2: Get patient
        matches = GetPatientByName(parsed["patient_name"])
        if not matches:
            print("No patient found.")
            continue

        # Step 3: Choose patient if multiple
        if len(matches) > 1:
            print("\nMultiple patients found:")
            for idx, p in enumerate(matches):
                print(f"{idx + 1}. {p['name']} (ID: {p['id']}, Gender: {p['gender']}, DOB: {p['birthDate']})")
            choice = int(input("Choose patient number: ")) - 1
        else:
            choice = 0
        patient = matches[choice]

        # Step 4: Get all relevant CVX codes
        vaccine_codes = GetVaccineCodes(parsed["disease"])
        target_cvxs = {v["cvx_code"] for v in vaccine_codes if "cvx_code" in v}

        # Step 5: Get all immunizations
        immunizations = GetAllImmunizations(patient["id"])
        print(f"[Immunization Records for {patient['name']}]")
        for imm in immunizations:
            print(f"- CVX: {imm['cvx_code']}, Description: {imm['description']}, Date: {imm['date']}")

        # Step 6: Check for match
        match = any(imm["cvx_code"] in target_cvxs for imm in immunizations if imm["cvx_code"])
        print("\n[Step 6] Vaccination Status:")
        if match:
            print("✅ The patient has been vaccinated for:", parsed["disease"])
        else:
            print("❌ No evidence found of vaccination for:", parsed["disease"])
        print("\n[Step 7] Recommendation:\n")
        # Step 7: Ask LLM for follow-up vaccination recommendations
        vaccination_summary = json.dumps(immunizations, indent=2)
        prompt_recommend = f"""
        Given the patient's current vaccination record shown below, are there any other vaccinations they should consider getting based on typical clinical guidelines?

        Vaccination Record:
        {vaccination_summary}
     """
        recommendations = call_mistral(prompt_recommend)
        print("[Recommendation]", recommendations)

if __name__ == "__main__":
    main()

