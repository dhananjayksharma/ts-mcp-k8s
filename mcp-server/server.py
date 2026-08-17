from mcp.server import MCPServer
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = MCPServer("local-demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@mcp.tool()
def disk_usage() -> str:
    """Show local disk usage."""
    result = subprocess.run(
        ["df", "-h"],
        capture_output=True,
        text=True,
    )
    return result.stdout


@mcp.tool()
def memory_usage() -> str:
    """Show Linux memory usage."""
    result = subprocess.run(
        ["free", "-h"],
        capture_output=True,
        text=True,
    )
    return result.stdout


@mcp.tool()
def uptime() -> str:
    """Show system uptime."""
    result = subprocess.run(
        ["uptime"],
        capture_output=True,
        text=True,
    )
    return result.stdout

@mcp.tool()
def system_info() -> str:
    """Return basic information about this MCP server."""
    return "Ubuntu local MCP server is running"


@mcp.tool()
def get_nodes_status() -> str:
    """Return Kubernetes node status."""
    return kubectl("get", "nodes", "-o", "wide")

@mcp.tool()
def get_nodes() -> str:
    """Get Kubernetes cluster nodes."""

    result = subprocess.run(
        ["kubectl", "get", "nodes", "-o", "wide"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return result.stderr

    return result.stdout

@mcp.tool()
def get_all_namespaces() -> str:
    """Show all Kubernetes namespaces."""

    result = subprocess.run(
        [
            "kubectl",
            "get",
            "namespaces",
            "-o",
            "wide",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "kubectl get namespaces failed"
        )

    return result.stdout.strip()

def kubectl(*args: str) -> str:
    result = subprocess.run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return f"ERROR:\n{result.stderr}"

    return result.stdout


@mcp.tool()
def get_all_pods() -> str:
    """List pods from all Kubernetes namespaces."""

    return run_kubectl([
        "get",
        "pods",
        "-A",
        "-o",
        "wide",
    ])

@mcp.tool()
def get_pods(namespace: str = "default") -> str:
    """Return pods in a Kubernetes namespace."""
    return kubectl(
        "get",
        "pods",
        "-n",
        namespace,
        "-o",
        "wide",
    )


@mcp.tool()
def describe_pod(namespace: str, pod: str) -> str:
    """Describe a Kubernetes pod."""
    return kubectl(
        "describe",
        "pod",
        pod,
        "-n",
        namespace,
    )


@mcp.tool()
def pod_logs(
    namespace: str,
    pod: str,
    tail: int = 100,
) -> str:
    """Return recent logs for a Kubernetes pod."""

    return kubectl(
        "logs",
        pod,
        "-n",
        namespace,
        "--tail",
        str(tail),
    )

def run_kubectl(args: list[str]) -> str:

    try:
        result = subprocess.run(
            ["kubectl", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )

    except subprocess.TimeoutExpired:
        return "ERROR: kubectl command timed out"

    except FileNotFoundError:
        return "ERROR: kubectl command not found"

    if result.returncode != 0:
        return f"ERROR:\n{result.stderr}"

    return result.stdout

@mcp.tool()
def get_events(namespace: str = "default") -> str:
    """Get Kubernetes events for a namespace."""

    return run_kubectl([
        "get",
        "events",
        "-n",
        namespace,
        "--sort-by=.metadata.creationTimestamp",
    ])

if __name__ == "__main__":
    logger.info("Starting local demo MCP server... Done!")
    mcp.run() 