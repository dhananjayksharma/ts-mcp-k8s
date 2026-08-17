import asyncio
import sys
from pathlib import Path

import streamlit as st


# Make the project root importable when Streamlit starts ui/app.py directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.agent import troubleshoot  # noqa: E402


st.set_page_config(
    page_title="MCP Kubernetes Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 MCP Kubernetes Agent")
st.caption("Local MCP • Ollama • Kubernetes • Minikube • GPU")


# -----------------------------------------------------------------------------
# Chat history
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -----------------------------------------------------------------------------
# User input
# -----------------------------------------------------------------------------
prompt = st.chat_input(
    "Ask: show all namespaces, pods, failures, events, logs, RCA..."
)

if prompt:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.status(
            "🤔 Thinking...",
            expanded=True,
        )

        def progress_callback(message: str) -> None:
            # These are high-level execution/tool-status messages, not hidden
            # chain-of-thought. They are safe and useful for an agent UI.
            status.write(message)

        try:
            answer = asyncio.run(
                troubleshoot(
                    prompt,
                    progress=progress_callback,
                )
            )

            status.update(
                label="✅ Complete",
                state="complete",
                expanded=False,
            )

            st.markdown(answer)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

        except Exception as exc:
            status.update(
                label="❌ Request failed",
                state="error",
                expanded=True,
            )

            error_message = f"Agent failed: `{exc}`"
            st.error(error_message)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                }
            )


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Agent")
    st.write("**MCP:** stdio server")
    st.write("**LLM:** local Ollama")
    st.write("**Mode:** Kubernetes Q&A + RCA")

    st.divider()
    st.markdown("**Examples**")
    st.code("show all namespaces")
    st.code("why is my pod failing?")

    if st.button("🗑️ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
