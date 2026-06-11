# app/pages/1_AI_Agent.py
"""
AI Pricing Query Agent — Streamlit chat page.

Architecture:
- Loads the same dataframe as main.py (cached, no double load)
- Instantiates the Anthropic client once per session
- Maintains chat history in st.session_state
- Calls run_agent() on each new message
- Displays answer + tool call trace under each response
"""

import streamlit as st
import anthropic
import pandas as pd
import sys
from pathlib import Path

# Make app/ importable when running as a page
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_access import load_transactions
from agent import run_agent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Pricing Agent",
    page_icon="🤖",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data + client — cached so they don't reload on every interaction
# ---------------------------------------------------------------------------

@st.cache_data
def get_data() -> pd.DataFrame:
    return load_transactions()

@st.cache_resource
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

df = get_data()
client = get_client()

# ---------------------------------------------------------------------------
# Tool trace renderer
# Defined after the chat loop so it can be called from both
# history rendering and new message rendering above.
# ---------------------------------------------------------------------------

def _render_tool_trace(tool_calls: list):
    """Display the tool call trace in a collapsed expander."""
    with st.expander(f"🔍 Tool calls ({len(tool_calls)} step{'s' if len(tool_calls) > 1 else ''})"):
        for i, call in enumerate(tool_calls, 1):
            tool_name = call["tool"]
            args = call["args"]
            rows = call.get("rows_returned", 0)
            err = call.get("error")

            if err:
                st.error(f"**Step {i}: `{tool_name}`** — ❌ {err}")
            else:
                st.success(f"**Step {i}: `{tool_name}`** — {rows} rows returned")

            # Show args as a clean key: value list
            arg_lines = [f"- **{k}**: `{v}`" for k, v in args.items() if v is not None]
            if arg_lines:
                st.markdown("\n".join(arg_lines))

            if i < len(tool_calls):
                st.divider()
                
# ---------------------------------------------------------------------------
# Session state — persists chat history across reruns
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {role, content, tool_calls, error}

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("🤖 AI Pricing Query Agent")
st.caption(
    "Ask natural-language questions about margin performance, exceptions, "
    "and customer pricing behavior. The agent uses constrained tool functions — "
    "no free-form code execution."
)

with st.expander("Example questions to try"):
    st.markdown(
        """
        - Which accounts have the worst pocket margin in the Midwest?
        - What is the exception rate by product category?
        - Show me the top 10 accounts with the highest estimated margin leakage
        - What does the price waterfall look like for customer C0007?
        - Which industries have the lowest pocket margin percentage?
        - Where are exceptions most concentrated by region?
        - Show me HVAC Contractor accounts with revenue above $50,000
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Render existing chat history
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show tool call trace under assistant messages
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            _render_tool_trace(msg["tool_calls"])

        if msg["role"] == "assistant" and msg.get("error"):
            st.error(f"⚠️ {msg['error']}")

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask a pricing question..."):

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "tool_calls": None,
        "error": None,
    })

    # Run agent and display response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = run_agent(prompt, df, client)

        answer = result["answer"]
        tool_calls = result["tool_calls"]
        error = result["error"]

        # Show answer
        if answer:
            st.markdown(answer)
        elif error and not answer:
            st.error(f"⚠️ {error}")

        # Show tool call trace
        if tool_calls:
            _render_tool_trace(tool_calls)

        # Show non-fatal error alongside answer
        if error and answer:
            st.warning(f"Note: {error}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer or "",
        "tool_calls": tool_calls,
        "error": error,
    })


