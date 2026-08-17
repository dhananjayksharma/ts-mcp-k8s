import asyncio
from collections.abc import Callable

try:
    from .llm import generate_rca
    from .mcp_client import call_tool, get_mcp_session, validate_required_tools
except ImportError:
    # Allows: python agent/agent.py
    from llm import generate_rca
    from mcp_client import call_tool, get_mcp_session, validate_required_tools


ProgressCallback = Callable[[str], None]

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

RCA_REQUIRED_TOOLS = {
    "get_all_pods",
    "describe_pod",
    "get_events",
    "pod_logs",
}


def notify(progress: ProgressCallback | None, message: str) -> None:
    """Send a user-visible progress update when a UI callback is supplied."""
    if progress is not None:
        progress(message)


def is_namespace_list_question(question: str) -> bool:
    """Detect simple requests asking to list/show Kubernetes namespaces."""
    q = " ".join(question.lower().strip().split())

    namespace_words = ("namespace", "namespaces", "ns")
    list_words = ("show", "list", "get", "display", "all", "what")

    return any(word in q.split() for word in namespace_words) and any(
        word in q.split() for word in list_words
    )


def discover_problem_pod(pods_output: str) -> dict | None:
    """
    Parse output shaped like: kubectl get pods -A -o wide.

    Expected first columns:
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

        if status in FAILURE_STATUSES or ready.startswith("0/"):
            return {
                "namespace": namespace,
                "pod": pod,
                "ready": ready,
                "status": status,
            }

    return None


async def show_all_namespaces(
    progress: ProgressCallback | None = None,
) -> str:
    """Return all Kubernetes namespaces through the MCP server."""
    notify(progress, "🔌 Connecting to MCP server...")

    async with get_mcp_session() as session:
        notify(progress, "✅ MCP server connected")
        notify(progress, "🧰 Checking `get_all_namespaces` MCP tool...")

        await validate_required_tools(
            session,
            required_tools={"get_all_namespaces"},
        )

        notify(progress, "🔧 MCP tool: `get_all_namespaces()`")
        notify(progress, "📂 Reading Kubernetes namespaces...")

        namespaces = await call_tool(
            session,
            "get_all_namespaces",
        )

        notify(progress, "✅ Kubernetes namespaces loaded")

        return (
            "## Kubernetes Namespaces\n\n"
            "```text\n"
            f"{namespaces.strip()}\n"
            "```"
        )


async def troubleshoot(
    question: str,
    progress: ProgressCallback | None = None,
) -> str:
    """
    Main agent workflow used by the ChatGPT-style UI.

    Simple namespace-list questions are routed directly to the namespace MCP
    tool. Other questions continue through the existing Kubernetes RCA flow.
    """
    if is_namespace_list_question(question):
        return await show_all_namespaces(progress=progress)

    notify(progress, "🔌 Connecting to MCP server...")

    async with get_mcp_session() as session:
        notify(progress, "✅ MCP server connected")

        notify(progress, "🧰 Discovering and validating MCP tools...")
        available_tools = await validate_required_tools(
            session,
            required_tools=RCA_REQUIRED_TOOLS,
        )
        notify(
            progress,
            "✅ Required tools available: " + ", ".join(sorted(available_tools)),
        )

        # STEP 1: discover unhealthy pod
        notify(progress, "🔧 MCP tool: `get_all_pods()`")
        notify(progress, "📦 Checking Kubernetes pods for unhealthy workloads...")
        pods = await call_tool(session, "get_all_pods")

        problem = discover_problem_pod(pods)

        if not problem:
            notify(progress, "✅ No obviously unhealthy pod was discovered")
            return (
                "## Kubernetes Analysis\n\n"
                "I checked the pods through the MCP server and did not find an "
                "obviously unhealthy pod based on the configured failure statuses "
                "or a `READY=0/x` condition."
            )

        namespace = problem["namespace"]
        pod = problem["pod"]

        notify(
            progress,
            f"⚠️ Found unhealthy pod: `{namespace}/{pod}` "
            f"(status: `{problem['status']}`, ready: `{problem['ready']}`)",
        )

        # STEP 2: describe pod
        notify(
            progress,
            f"🔧 MCP tool: `describe_pod(namespace='{namespace}', pod='{pod}')`",
        )
        notify(progress, "🔍 Reading pod configuration and container state...")
        describe = await call_tool(
            session,
            "describe_pod",
            {
                "namespace": namespace,
                "pod": pod,
            },
        )

        # STEP 3: namespace events
        notify(
            progress,
            f"🔧 MCP tool: `get_events(namespace='{namespace}')`",
        )
        notify(progress, "⚠️ Reading Kubernetes events...")
        events = await call_tool(
            session,
            "get_events",
            {
                "namespace": namespace,
            },
        )

        # STEP 4: application logs
        notify(
            progress,
            f"🔧 MCP tool: `pod_logs(namespace='{namespace}', pod='{pod}', tail=200)`",
        )
        notify(progress, "📜 Reading recent application logs...")
        logs = await call_tool(
            session,
            "pod_logs",
            {
                "namespace": namespace,
                "pod": pod,
                "tail": 200,
            },
        )

        # STEP 5: local Ollama RCA
        notify(progress, "🧠 Sending collected evidence to Ollama...")
        notify(progress, "🔎 Generating Kubernetes root cause analysis...")

        rca = generate_rca(
            question=question,
            pod=problem,
            describe=describe,
            events=events,
            logs=logs,
        )

        notify(progress, "✅ Root cause analysis generated")
        return rca


async def main() -> None:
    """Optional CLI mode; the same agent.py can still be tested without UI."""
    question = input("\nWhat Kubernetes problem should I investigate?\n> ")

    def console_progress(message: str) -> None:
        print(message)

    answer = await troubleshoot(question, progress=console_progress)

    print("\n" + "=" * 70)
    print("MCP KUBERNETES AGENT RESPONSE")
    print("=" * 70)
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
