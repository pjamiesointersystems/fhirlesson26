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

def RetrievePatientData(patient_id: str):
    # === STUB for now ===
    print(f"[Stub] Retrieving data for patient ID: {patient_id}")
    return f"(Simulated response for patient ID {patient_id}: allergies, conditions, immunizations...)"


# === Secondary Flow ===
# === New: Ask Mistral to extract a patient name ===
def detect_patient_name(user_question: str) -> str:
    system_prompt = (
        "You are a helpful assistant. Determine if the following question refers to a specific patient. "
        "If it does, return only the full name of the patient (e.g., 'Susann Mann'). "
        "If no patient is mentioned, return: 'No patient mentioned'."
    )
    messages = [
        {"role": "user", "content": system_prompt},
        {"role": "user", "content": user_question}
    ]
    result = call_mistral_with_messages(messages)
    name = result.strip()
    if name.lower() == "no patient mentioned":
        return ""
    return name


def call_mistral_with_messages(messages: List[dict]) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False
    }
    response = requests.post(f"{LMSTUDIO_API_BASE}/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        raw = response.json()["choices"][0]["message"]["content"]
        return clean_mistral_response(raw)
    else:
        print("Error:", response.text)
        return ""


def clean_mistral_response(text: str) -> str:
    # Remove any trailing assistant markers like "__(Assistant)__" or similar
    cleaned = re.sub(r"__\s*\(*assistant\)*\s*__.*$", "", text, flags=re.IGNORECASE).strip()
    return cleaned


# === Main Flow ===
def main():
    print("\nWelcome to the Physician Assistant Agent!")

    assistant_role_setup = {
        "role": "assistant",
        "content": (
            "You are a helpful Physician Assistant who provides general information about medical topics.\n"
            "If a user asks about a specific patient, include the patient's name in your response and state that you cannot answer due to lack of access to their medical record.\n"
            "Avoid adding role signatures like '__Assistant__'."
        )
    }

    example_conversation = [
        {"role": "user", "content": "What is the difference between a cold and flu?"},
        {"role": "assistant", "content": "A cold is caused by rhinoviruses and usually has milder symptoms. Flu, caused by influenza viruses, tends to be more severe and may require antiviral treatment."},
        {"role": "user", "content": "What is the treatment for bacterial skin infections?"},
        {"role": "assistant", "content": "Bacterial skin infections like impetigo or cellulitis are treated with antibiotics. The specific choice depends on the bacteria and the patient's medical history."},
        {"role": "user", "content": "What is John Smith's blood glucose level?"},
        {"role": "assistant", "content": "I do not have access to John Smith's medical record, so I cannot provide that information."}
    ]

    while True:
        user_question = input("\nAsk your question (or type 'exit'): ")
        if user_question.lower() in ("exit", "quit"):
            break

        # Check for name-based patient question
        patient_name = detect_patient_name(user_question)

        if patient_name:
            candidates = GetPatientByName(patient_name)
            if not candidates:
                print(f"{patient_name}")
            else:
                print(f"\nMultiple patients found for '{patient_name}':")
                for idx, p in enumerate(candidates):
                    print(f"{idx + 1}. {p['name']} (Gender: {p['gender']}, DOB: {p['birthDate']}, ID: {p['id']})")

                try:
                    selection = int(input("Select a patient (1-N): ").strip())
                    selected_patient = candidates[selection - 1]
                    print("\n[Patient Selected]", selected_patient["name"])
                    print(RetrievePatientData(selected_patient["id"]))
                    continue  # Skip LLM for patient data stub
                except (ValueError, IndexError):
                    print("Invalid selection. Skipping patient data retrieval.")

        # General question fallback using LLM
        messages = [assistant_role_setup] + example_conversation + [
            {"role": "user", "content": user_question}
        ]
        response = call_mistral_with_messages(messages)
        print("\nMistral Response:", response)


if __name__ == "__main__":
    main()
