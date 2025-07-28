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



def call_mistral_with_messages(messages: List[dict]) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False
    }
    response = requests.post(f"{LMSTUDIO_API_BASE}/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("Error:", response.text)
        return ""


# === Main Flow ===
def main():
    print("\nWelcome to the Physician Assistant Agent!")

    # Shared context message defining the assistant's role
    system_message = {
        "role": "assistant",
        "content": (
            "You are a helpful Physician Assistant who provides the doctor with general information about medical topics.\n"
            "If no patient is specified, give general information concisely without warnings or disclaimers.\n"
            "If a question is about a specific patient, respond that you cannot answer it because you do not have access to the patient's medical records."
        )
    }


    while True:
        user_question = input("\nAsk your question (or type 'exit'): ")
        if user_question.lower() in ("exit", "quit"):
            break

        # Build the full message history for this question
        messages = [system_message]  + [
            {"role": "user", "content": user_question}
        ]

        response = call_mistral_with_messages(messages)
        print("\nMistral Response:", response)




if __name__ == "__main__":
    main()
