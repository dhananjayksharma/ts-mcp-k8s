import asyncio
from typing import Any

import ollama

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MODEL = "llama3.1:8b"

FAILURE_STATUSES = {
    "CrashLoopBackOff",
    "Error",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerConfigError",
    "CreateContainerError",
    "Pending",
    "Failed",
    "ContainerCreating",
    "RunContainerError",
}

def extract_text(result: Any) -> str:
    """
    Convert MCP CallToolResult content into plain text.
    """
    output = []

    for item in result.content:
        if hasattr(item, "text"):
            output.append(item.text)

    return "\n".join(output)


async def call_tool(
    session,
    name: str,
    arguments: dict | None = None,
) -> str:

    print(f"\n[MCP] Calling tool: {name}")

    result = await session.call_tool(
        name,
        arguments or {},
    )

    if getattr(result, "isError", False):
        text = extract_text(result)
        raise RuntimeError(
            f"MCP tool {name} failed:\n{text}"
        )

    return extract_text(result)


def discover_problem_pod(pods_output: str):
    """
    Parse:
    kubectl get pods -A -o wide

    Expected columns begin with:

    NAMESPACE NAME READY STATUS RESTARTS AGE ...
    """

    lines = pods_output.strip().splitlines()

    if len(lines) <= 1:
        return None

    for line in lines[1:]:

        fields = line.split()

        if len(fields) < 5:
            continue

        namespace = fields[0]
        pod = fields[1]
        ready = fields[2]
        status = fields[3]

        # Explicit failure
        if status in FAILURE_STATUSES:

            return {
                "namespace": namespace,
                "pod": pod,
                "ready": ready,
                "status": status,
            }

        # Example:
        # READY = 0/1
        if ready.startswith("0/"):

            return {
                "namespace": namespace,
                "pod": pod,
                "ready": ready,
                "status": status,
            }

    return None


def generate_rca(
    question: str,
    pod: dict,
    describe: str,
    events: str,
    logs: str,
) -> str:

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


async def troubleshoot(question: str):

    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (
        read,
        write,
    ):

        async with ClientSession(
            read,
            write,
        ) as session:

            print("\nConnecting to MCP server...")

            await session.initialize()

            print("MCP server connected.")

            # --------------------------------------------------
            # Validate required MCP tools
            # --------------------------------------------------
            
            required_tools = {
                "get_all_pods",
                "describe_pod",
                "get_events",
                "pod_logs",
            }

            tools_result = await session.list_tools()

            available_tools = {
                tool.name
                for tool in tools_result.tools
            }

            print("\nAvailable MCP tools:")

            for name in sorted(available_tools):
                print(f" - {name}")

            missing = required_tools - available_tools

            if missing:
                raise RuntimeError(
                    f"MCP server missing required tools: "
                    f"{', '.join(sorted(missing))}"
                )

            # --------------------------------------------------
            # STEP 1
            # Discover pods
            # --------------------------------------------------

            pods = await call_tool(
                session,
                "get_all_pods",
            )

            print("\n========== PODS ==========")
            print(pods)

            problem = discover_problem_pod(pods)

            if not problem:

                print(
                    "\nNo obviously unhealthy pod "
                    "was discovered."
                )

                return

            print("\n========== FAILURE FOUND ==========")

            print(
                f"""
Namespace : {problem["namespace"]}
Pod       : {problem["pod"]}
Ready     : {problem["ready"]}
Status    : {problem["status"]}
"""
            )

            namespace = problem["namespace"]
            pod = problem["pod"]

            # --------------------------------------------------
            # STEP 2
            # Describe pod
            # --------------------------------------------------

            describe = await call_tool(
                session,
                "describe_pod",
                {
                    "namespace": namespace,
                    "pod": pod,
                },
            )

            # --------------------------------------------------
            # STEP 3
            # Kubernetes events
            # --------------------------------------------------

            events = await call_tool(
                session,
                "get_events",
                {
                    "namespace": namespace,
                },
            )

            # --------------------------------------------------
            # STEP 4
            # Application logs
            # --------------------------------------------------

            logs = await call_tool(
                session,
                "pod_logs",
                {
                    "namespace": namespace,
                    "pod": pod,
                    "tail": 200,
                },
            )

            # --------------------------------------------------
            # STEP 5
            # LLM RCA
            # --------------------------------------------------

            print("\n[AI] Sending evidence to Ollama...")

            rca = generate_rca(
                question,
                problem,
                describe,
                events,
                logs,
            )

            print("\n")
            print("=" * 70)
            print("AI KUBERNETES ROOT CAUSE ANALYSIS")
            print("=" * 70)

            print(rca)


async def main():

    question = input(
        "\nWhat Kubernetes problem should I investigate?\n> "
    )

    await troubleshoot(question)


if __name__ == "__main__":
    asyncio.run(main())