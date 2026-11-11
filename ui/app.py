"""A small local web gateway for trying MCP-TDO with Ollama.

This app is meant for local development and demos. It keeps the MCP servers
inside the process, so the browser can submit a prompt without exposing a
general-purpose remote tool runner.
"""

import asyncio
from typing import Any

import streamlit as st
from mcp_tdo.agents import AgentRunner
from mcp_tdo.agents.providers import OllamaProvider
from mcp_tdo.mcp_client import InMemoryMCPClient
from mcp_tdo.mcp_servers import SERVER_FACTORIES

st.set_page_config(page_title="MCP-TDO Gateway", page_icon="🔧", layout="wide")


def run_prompt(prompt: str, model: str, server_name: str, max_steps: int) -> Any:
    """Run the existing agent pipeline from Streamlit's synchronous callback."""
    server = SERVER_FACTORIES[server_name]()
    client = InMemoryMCPClient(server, server_name)
    runner = AgentRunner(
        OllamaProvider(model=model),
        client,
        max_steps=max_steps,
    )
    result = asyncio.run(runner.run(prompt))
    return result, client


st.title("MCP-TDO Gateway")
st.caption("Send a prompt to a local Ollama model and watch it use an MCP tool.")

with st.sidebar:
    st.header("Gateway settings")
    model = st.text_input("Ollama model", value="qwen3:8b")
    server_name = st.selectbox("MCP server", options=sorted(SERVER_FACTORIES))
    max_steps = st.slider("Maximum agent steps", min_value=1, max_value=10, value=5)
    st.info(
        "This demo uses local Ollama and in-memory fixture servers. "
        "It does not call paid APIs or touch your real filesystem."
    )

st.subheader("Ask the gateway")
with st.form("prompt_form"):
    prompt = st.text_area(
        "What should the agent do?",
        value="Find Dana at Acme.",
        height=100,
        placeholder="For example: Find Dana at Acme.",
    )
    submitted = st.form_submit_button("Run prompt", type="primary")

if submitted:
    if not prompt.strip():
        st.error("Enter a prompt before running the gateway.")
    else:
        with st.spinner("The model is choosing and calling an MCP tool..."):
            try:
                result, client = run_prompt(prompt, model, server_name, max_steps)
            except Exception as error:
                message = str(error)
                if "connection" in message.lower() or "connect" in message.lower():
                    st.error(
                        "Ollama is not reachable. Start Ollama with `ollama serve`, "
                        "wait a few seconds, then submit the prompt again."
                    )
                else:
                    st.error(f"Gateway request failed: {message}")
            else:
                st.success(f"Finished: {result.stopped_reason}")
                left, right = st.columns(2)
                with left:
                    st.metric("Steps", result.steps)
                    st.metric("Latency", f"{result.latency_ms:.0f} ms")
                with right:
                    st.metric("Tool calls", len(result.tool_calls))
                    st.metric("Estimated cost", f"${result.estimated_cost:.4f}")

                st.subheader("Agent answer")
                st.write(result.final_text or "The agent did not return a final answer.")

                st.subheader("Selected tools")
                if result.tool_calls:
                    st.json([call.model_dump() for call in result.tool_calls])
                else:
                    st.write("The agent did not call a tool.")

                st.subheader("MCP trace")
                if client.traces:
                    st.json([trace.model_dump(mode="json") for trace in client.traces])
                else:
                    st.write("No MCP calls were recorded.")

                with st.expander("Raw agent result"):
                    st.json(result.model_dump())
