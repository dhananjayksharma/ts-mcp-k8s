import os

import ollama


MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def generate_rca(
    question: str,
    pod: dict,
    describe: str,
    events: str,
    logs: str,
) -> str:
    """Generate Kubernetes RCA using only evidence collected through MCP."""
    prompt = f"""
You are a senior Kubernetes SRE and Platform Engineer.

Diagnose the Kubernetes failure using ONLY the supplied evidence.

USER QUESTION
-------------
{question}

POD
---
Namespace: {pod["namespace"]}
Pod:       {pod["pod"]}
Ready:     {pod["ready"]}
Status:    {pod["status"]}

KUBECTL DESCRIBE POD
--------------------
{describe}

KUBERNETES EVENTS
-----------------
{events}

APPLICATION LOGS
----------------
{logs}

Perform root cause analysis.

Return this exact structure:

# Kubernetes RCA

## Problem
Brief description.

## Evidence
List the important evidence found in pod status, events,
describe output, and logs.

## Root Cause
Explain the most likely root cause.

## Confidence
High / Medium / Low

## Immediate Fix
Provide exact kubectl or application configuration steps.

## Permanent Fix
Explain the production-grade fix.

## Prevention
Explain monitoring, alerting, resource, security, deployment,
or platform improvements that would prevent recurrence.

IMPORTANT:

- Do not invent information.
- Separate observed evidence from assumptions.
- If evidence is insufficient, say so.
- Prefer Kubernetes evidence over speculation.
"""

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response["message"]["content"]
