# Lesson 26 – Using AI Workflows and Agents with FHIR Data

## 🧠 Overview

This repository accompanies **Lesson 26** of the AI + FHIR curriculum. The lesson introduces students to the difference between **LLM Prompt Chat**, **LLM Workflows**, and **Autonomous AI Agents**, through a sequence of progressively enhanced agents that interact with real **FHIR data**.

The goal is to show how to apply modern language models to clinical use cases using structured EHR data, with a specific focus on **immunization history** and patient queries.

---

## 🎯 Learning Objectives

- Understand the difference between LLM workflows and AI agents
- Design a basic FHIR-aware workflow using a local LLM (via LM Studio)
- Build increasingly autonomous agents using FHIR tooling and reasoning loops
- Apply few-shot prompting to control behavior and response safety
- Observe tradeoffs between manual control and LLM autonomy

---

## 📦 Repository Contents

| Folder / File        | Description |
|----------------------|-------------|
| `agent1.py`          | Basic prompt chat – answers simple immunization questions (no tools) |
| `agent2.py`          | Adds few-shot prompting and basic PHI guardrails |
| `agent3.py`          | Introduces FHIR tool usage (`GetPatientByName`), patient selection |
| `agent4.py`          | Adds immunization queries via `GetAllImmunizations`, logic is scripted |
| `agent5.py`          | Enables autonomous agent reasoning (ReAct: Thought → Action → Observation) |
| `agent6.py`          | Adds prompt guardrails to prevent tool hallucination and constrain scope |
| `slides/`            | Supporting slides from PowerPoint presentation |
| `README.md`          | You’re reading it now |

---

## 🧪 System Requirements

- Python 3.9+
- LM Studio (for local LLM inference)
- InterSystems IRIS for Health (FHIR sandbox)
- Tested with `mistral-7b-instruct-v0.3.gguf` (quantized model)

---

## 🚀 Getting Started

1. Clone the repo:
   ```bash
   git clone https://github.com/pjamiesointersystems/fhirlesson26.git
   cd fhirlesson26
