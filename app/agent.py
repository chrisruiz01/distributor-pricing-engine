# app/agent.py
"""
Agent loop for the pricing query agent.

ARCHITECTURE:
- Sends user query + tool definitions to Claude
- Handles tool_use -> execute -> tool_result cycle
- Returns final answer text + a trace of every tool call made
- The caller (Streamlit page) owns display; this module owns the loop logic

GOVERNANCE:
- Only functions in TOOL_REGISTRY can be called
- Arguments are validated inside each tool function before execution
- Max 10 iterations prevents infinite loops
- All tool errors are caught and returned as tool_result errors,
  not raised — Claude sees the error and can respond gracefully
"""

from __future__ import annotations

import json
from typing import Any

import anthropic
import pandas as pd

from agent_tools import (
    filter_accounts,
    aggregate_margin,
    top_n_by_metric,
    get_price_waterfall,
    get_exception_summary,
    ALLOWED_REGIONS,
    ALLOWED_INDUSTRIES,
    ALLOWED_CUSTOMER_TYPES,
    ALLOWED_PRODUCT_CATEGORIES,
    ALLOWED_GROUP_BY_FIELDS,
    ALLOWED_METRICS,
    ALLOWED_SERVICE_MODELS,
)

# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
MAX_ITERATIONS = 10

# ---------------------------------------------------------------------------
# Tool registry
# Maps tool name (string Claude uses) -> callable
# This is the ONLY place tool dispatch happens.
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, Any] = {
    "filter_accounts": filter_accounts,
    "aggregate_margin": aggregate_margin,
    "top_n_by_metric": top_n_by_metric,
    "get_price_waterfall": get_price_waterfall,
    "get_exception_summary": get_exception_summary,
}

# ---------------------------------------------------------------------------
# Tool definitions (sent to Claude so it knows what's available)
# These are JSON Schema descriptions — Claude uses them to decide
# which tool to call and what arguments to pass.
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "filter_accounts",
        "description": (
            "Return a customer-level summary filtered by one or more dimensions. "
            "Use this to find accounts matching specific criteria like industry, region, "
            "or customer type. Optionally filter by minimum revenue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": f"Filter by region. Allowed: {sorted(ALLOWED_REGIONS)}",
                },
                "industry": {
                    "type": "string",
                    "description": f"Filter by industry. Allowed: {sorted(ALLOWED_INDUSTRIES)}",
                },
                "customer_type": {
                    "type": "string",
                    "description": f"Filter by customer type. Allowed: {sorted(ALLOWED_CUSTOMER_TYPES)}",
                },
                "product_category": {
                    "type": "string",
                    "description": f"Filter by product category. Allowed: {sorted(ALLOWED_PRODUCT_CATEGORIES)}",
                },
                "min_revenue": {
                    "type": "number",
                    "description": "Minimum gross revenue threshold. Default 0.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "aggregate_margin",
        "description": (
            "Aggregate a margin or discount metric grouped by one dimension. "
            "Use this for questions like 'what is the average pocket margin by region?' "
            "or 'which product category has the highest exception rate?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "description": f"Dimension to group by. Allowed: {sorted(ALLOWED_GROUP_BY_FIELDS)}",
                },
                "metric": {
                    "type": "string",
                    "description": f"Metric to aggregate. Allowed: {sorted(ALLOWED_METRICS)}",
                },
                "region": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_REGIONS)}"},
                "industry": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_INDUSTRIES)}"},
                "customer_type": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_CUSTOMER_TYPES)}"},
                "product_category": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_PRODUCT_CATEGORIES)}"},
            },
            "required": ["group_by"],
        },
    },
    {
        "name": "top_n_by_metric",
        "description": (
            "Return the top N customers ranked by a metric. "
            "Use this for 'worst', 'best', 'highest', 'lowest' questions. "
            "Set ascending=true for worst (lowest margin) first, false for best first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": f"Metric to rank by. Allowed: {sorted(ALLOWED_METRICS)}",
                },
                "n": {
                    "type": "integer",
                    "description": "Number of results to return. Max 50. Default 10.",
                },
                "ascending": {
                    "type": "boolean",
                    "description": "True = worst first (lowest values). False = best first. Default true.",
                },
                "region": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_REGIONS)}"},
                "industry": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_INDUSTRIES)}"},
                "customer_type": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_CUSTOMER_TYPES)}"},
                "product_category": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_PRODUCT_CATEGORIES)}"},
                "min_revenue": {"type": "number", "description": "Minimum revenue threshold. Default 0."},
            },
            "required": ["metric"],
        },
    },
    {
        "name": "get_price_waterfall",
        "description": (
            "Return the aggregated price waterfall for a single customer: "
            "list revenue → standard discounts → override discounts → "
            "product cost → rebates → freight → pocket margin. "
            "Use when asked about a specific customer's pricing or margin breakdown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID, e.g. 'C0007'. Must exist in the dataset.",
                },
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_exception_summary",
        "description": (
            "Summarize exception rates and override discount behavior grouped by one dimension. "
            "Use for questions about where exceptions are concentrated or which segments "
            "have the most override discount activity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "description": f"Dimension to group by. Allowed: {sorted(ALLOWED_GROUP_BY_FIELDS)}",
                },
                "region": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_REGIONS)}"},
                "industry": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_INDUSTRIES)}"},
                "customer_type": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_CUSTOMER_TYPES)}"},
                "product_category": {"type": "string", "description": f"Optional filter. Allowed: {sorted(ALLOWED_PRODUCT_CATEGORIES)}"},
            },
            "required": ["group_by"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a pricing analytics assistant for a B2B distributor.
You help pricing analysts and commercial leaders answer questions about margin 
performance, discount exceptions, and customer pricing behavior.

You have access to five tools that query a transaction dataset. Use them to 
answer questions accurately. You may call multiple tools in sequence if needed.

Rules:
- Only use the provided tools. Do not attempt to write code or query data directly.
- Always use exact allowed values for filter arguments (regions, industries, etc.)
- If a question cannot be answered with the available tools, say so clearly.
- Be concise. Lead with the direct answer, then support with data.
- When referencing dollar amounts, use $ formatting. When referencing percentages, use % formatting.
- If a tool returns an error, explain what went wrong and what the user could try instead.
"""

# ---------------------------------------------------------------------------
# Core agent loop
# ---------------------------------------------------------------------------

def run_agent(
    query: str,
    df: pd.DataFrame,
    client: anthropic.Anthropic,
) -> dict:
    """
    Run the agent loop for a single user query.

    Parameters
    ----------
    query : natural language question from the user
    df : the full transactions dataframe (passed in, not loaded here)
    client : instantiated Anthropic client

    Returns
    -------
    dict with keys:
        answer : str — final text response from the model
        tool_calls : list — trace of every tool called, args used, row count returned
        error : str or None — surface-level error message if something failed
    """
    messages = [{"role": "user", "content": query}]
    tool_call_trace = []
    iterations = 0

    while iterations < MAX_ITERATIONS:
        iterations += 1

        # --- Call the API ---
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except anthropic.APIError as e:
            return {
                "answer": None,
                "tool_calls": tool_call_trace,
                "error": f"API error: {str(e)}",
            }

        # --- Append assistant response to message history ---
        # This is required — the API needs the full conversation history
        # including the assistant's tool_use blocks on every subsequent call.
        messages.append({"role": "assistant", "content": response.content})

        # --- Check stop reason ---
        if response.stop_reason == "end_turn":
            # Extract the final text answer
            answer_text = _extract_text(response.content)
            return {
                "answer": answer_text,
                "tool_calls": tool_call_trace,
                "error": None,
            }

        if response.stop_reason != "tool_use":
            # Unexpected stop reason
            return {
                "answer": _extract_text(response.content),
                "tool_calls": tool_call_trace,
                "error": f"Unexpected stop reason: {response.stop_reason}",
            }

        # --- Process tool calls ---
        # response.content is a list of blocks; some are text, some are tool_use.
        # We need to execute every tool_use block and collect results.
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_args = block.input
            tool_use_id = block.id

            # Dispatch — only tools in TOOL_REGISTRY can be called
            if tool_name not in TOOL_REGISTRY:
                # Should never happen if tool definitions are correct,
                # but handle it defensively
                result_content = f"Error: unknown tool '{tool_name}'"
                tool_call_trace.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "error": result_content,
                    "rows_returned": 0,
                })
            else:
                try:
                    tool_fn = TOOL_REGISTRY[tool_name]
                    result = tool_fn(df, **tool_args)

                    # Serialize the dataframe to a compact JSON string for the API.
                    # The model gets a text representation, not raw Python objects.
                    data_json = result["data"].to_json(orient="records", date_format="iso")
                    metadata = result["metadata"]

                    result_content = json.dumps({
                        "metadata": metadata,
                        "data": json.loads(data_json),
                    })

                    tool_call_trace.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "rows_returned": metadata.get("rows_returned", len(result["data"])),
                        "error": None,
                    })

                except (ValueError, KeyError) as e:
                    # Validation error or missing column — return as tool error,
                    # not a Python exception. Claude sees this and can self-correct
                    # or explain the issue to the user.
                    result_content = f"Tool error: {str(e)}"
                    tool_call_trace.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "rows_returned": 0,
                        "error": str(e),
                    })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result_content,
            })

        # --- Send tool results back to Claude ---
        messages.append({"role": "user", "content": tool_results})

    # Fell out of the loop — max iterations hit
    return {
        "answer": None,
        "tool_calls": tool_call_trace,
        "error": f"Agent did not complete within {MAX_ITERATIONS} iterations. Try a simpler query.",
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _extract_text(content_blocks) -> str:
    """Pull text out of a response content block list."""
    return " ".join(
        block.text for block in content_blocks if hasattr(block, "text")
    ).strip()