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

    # Clarifying the assistant’s role in its opening message
    assistant_role_setup = {
        "role": "assistant",
        "content": (
            "You are a helpful Physician Assistant who provides general information about medical topics.\n"
            "If a user asks about a specific patient, include the patient's name in your response and state that you cannot answer due to lack of access to their medical record.\n"
            "Avoid adding role signatures like '__Assistant__'."
        )
    }

    # Few-shot examples
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

        messages = [assistant_role_setup] + example_conversation + [
            {"role": "user", "content": user_question}
        ]

        response = call_mistral_with_messages(messages)
        print("\nMistral Response:", response)


if __name__ == "__main__":
    main()
