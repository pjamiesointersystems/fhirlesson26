# AGENT 5 (Fixed): Improved Autonomous Agent with Strict Step-by-Step Tool Execution

import os
import json
import requests
import re
from typing import List, Dict, Any
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode

# === Config ===
LMSTUDIO_API_BASE = "http://localhost:1234/v1"
MODEL = "mistral-7b-instruct-v0.3"
FHIR_BASE_URL = "http://127.0.0.1:8080/csp/healthshare/demo/fhir/r4"
FHIR_AUTH = HTTPBasicAuth("_SYSTEM", "ISCDEMO")

# === Tools ===
def GetPatientByName(name: str) -> Any:
    print(f"[Tool] GetPatientByName: {name}")
    name_parts = name.strip().split()
    last_name_fragment = re.sub(r"[^A-Za-z0-9]", "", name_parts[-1])[:4] if name_parts else ""
    query_params = urlencode({"family:contains": last_name_fragment})
    url = f"{FHIR_BASE_URL}/Patient?{query_params}"
    headers = {"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"}
    response = requests.get(url, headers=headers, auth=FHIR_AUTH)
    if response.status_code != 200:
        return f"Error fetching patient: {response.status_code}"
    bundle = response.json()
    patients = []
    for e in bundle.get("entry", []):
        r = e["resource"]
        name = r.get("name", [{}])[0]
        display = f"{' '.join(name.get('given', []))} {name.get('family', '')}"
        patients.append({"id": r.get("id"), "name": display.strip(), "dob": r.get("birthDate"), "gender": r.get("gender")})
    return patients

def GetAllImmunizations(patient_id: str) -> Any:
    print(f"[Tool] GetAllImmunizations: {patient_id}")
    query = urlencode({"patient": f"Patient/{patient_id}"})
    url = f"{FHIR_BASE_URL}/Immunization?{query}"
    headers = {"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"}
    response = requests.get(url, headers=headers, auth=FHIR_AUTH)
    if response.status_code != 200:
        return f"Error fetching immunizations: {response.status_code}"
    results = []
    for e in response.json().get("entry", []):
        r = e["resource"]
        code = next((c["code"] for c in r.get("vaccineCode", {}).get("coding", []) if c["system"] == "http://hl7.org/fhir/sid/cvx"), None)
        results.append({
            "cvx_code": code,
            "description": r.get("vaccineCode", {}).get("text", ""),
            "date": r.get("occurrenceDateTime", ""),
            "status": r.get("status")
        })
    return results

# === Tool registry ===
TOOLS = {
    "GetPatientByName": GetPatientByName,
    "GetAllImmunizations": GetAllImmunizations
}

# === Flattened prompt-style LLM call ===
def call_mistral(messages: List[Dict[str, str]]) -> str:
    prompt_lines = []
    for m in messages:
        prefix = "Instructions:" if m["role"] == "system" else m["role"].upper() + ":"
        prompt_lines.append(f"{prefix} {m['content']}")
    prompt_text = "\n\n".join(prompt_lines)
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt_text}],
        "stream": False
    }
    response = requests.post(f"{LMSTUDIO_API_BASE}/chat/completions", headers={"Content-Type": "application/json"}, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("[Error] LLM call failed:", response.text)
        return ""

# === ReAct-style agent loop with enforced observation-wait ===
def run_agent(user_question: str):
    devprompt = [{
        "role": "system",
        "content": (
            "You are an autonomous clinical assistant agent."
            " You are able to reason step-by-step and use available tools to answer the user's question."
            " At each step, follow this format:\n\n"
            "Thought: [what you need to do next]\n"
            "Action: [tool name from the list below]\n"
            "Action Input: [input to pass to the tool]\n\n"
            "When you receive the result, use it in your next Thought."
            " When you have enough information to answer, reply with:\n"
            "Final Answer: [your response to the user]\n\n"
            "Do not assume tool results. Wait for an Observation before continuing your reasoning."
            " Available tools:\n"
            "- GetPatientByName: find patients in the FHIR server by name (string)\n"
            "- GetAllImmunizations: get immunizations for a patient by FHIR ID (string)"
        )
    }]

    few_shot = [
        {"role": "user", "content": "Has John Smith been vaccinated for COVID?"},
        {"role": "assistant", "content": "Thought: I need to find John Smith in the patient records.\nAction: GetPatientByName\nAction Input: John Smith"},
        {"role": "user", "content": "Observation: [{\"id\": \"123\", \"name\": \"John Smith\"}]"},
        {"role": "assistant", "content": "Thought: I should now check immunizations.\nAction: GetAllImmunizations\nAction Input: 123"},
        {"role": "user", "content": "Observation: [{\"cvx_code\": \"208\", \"description\": \"COVID-19 mRNA\", \"date\": \"2022-02-01\"}]"},
        {"role": "assistant", "content": "Final Answer: Yes, John Smith has been vaccinated for COVID-19."}
    ]

    userprompt = {"role": "user", "content": user_question.strip()}
    full_history = devprompt + few_shot + [userprompt]

    for _ in range(6):
        print("\n======== Full Prompt to Mistral ========")
        for msg in full_history:
            print(f"{msg['role'].upper()}: {msg['content']}\n")

        response = call_mistral(full_history)
        print("\n[Agent]", response)

        action_match = re.search(r"Action\s*:\s*(\w+)", response)
        input_match = re.search(r"Action Input\s*:\s*(.*)\n?", response)

        if action_match and input_match:
            tool = action_match.group(1).strip()
            arg = input_match.group(1).strip()
            tool_fn = TOOLS.get(tool)
            if not tool_fn:
                print(f"[Error] Unknown tool: {tool}")
                break
            result = tool_fn(arg)
            full_history.append({"role": "assistant", "content": response})
            full_history.append({"role": "user", "content": f"Observation: {json.dumps(result, indent=2)}"})
        else:
            if not response.strip():
                print("\n[Final Answer] (No response from model)")
            else:
                print("\n[Final Answer]", response)
            break

# === Run ===
def main():
    print("\nAutonomous FHIR Agent – ReAct Style (Agent 5)")
    while True:
        user_question = input("\nAsk your question (or type 'exit'): ")
        if user_question.lower() in ("exit", "quit"): break
        run_agent(user_question)

if __name__ == "__main__":
    main()