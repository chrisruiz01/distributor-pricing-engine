# Distributor Price Realization & Margin Leakage Engine

Synthetic B2B distributor pricing analytics project built to mimic strategic pricing work in a complex distribution environment. Now includes an AI agent layer for natural-language querying and automated variance commentary.

## Live App

[Open the deployed Streamlit app](https://distributor-pricing-engine.streamlit.app/)

## AI Agent Layer

### Natural-Language Query Agent

[Open the AI Pricing Agent](https://distributor-pricing-engine.streamlit.app/AI_Agent)

Ask natural-language questions about margin performance, exceptions, and customer pricing behavior. The agent uses the Anthropic API (claude-haiku) with constrained tool-use — the model selects and calls predefined functions against the transaction dataframe; it cannot execute arbitrary code or query data directly.

**Example queries:**
- Which accounts have the worst pocket margin in HVAC Contractor?
- Show me the top 10 accounts with the highest estimated margin leakage
- What is the exception rate by product category?
- What does the price waterfall look like for customer C0007?
- Where are exceptions most concentrated by region?

**Agent architecture:**
```text
User query
│
▼
Anthropic Messages API (tool definitions)
│
▼
tool_use response — tool name + arguments
│
▼
agent.py dispatches via TOOL_REGISTRY
│
▼
agent_tools.py executes against dataframe
(argument validation → pandas computation)
│
▼
tool_result returned to API
│
▼
Final answer + visible tool call trace
```

The loop runs until `stop_reason == "end_turn"` or a 10-iteration guard fires. Claude never touches the dataframe — it specifies calls, the application executes them.

### Variance Commentary

Button on the main dashboard. Computed aggregates (portfolio KPIs, lowest-margin categories, highest-exception regions, top leakage accounts) are sent to the model, which returns an executive-ready narrative. Raw transaction data never leaves the application.

### Governance Design

**Constrained tool registry** — the agent can only call five functions defined in `agent_tools.py`. No free-form code execution, no arbitrary SQL, no eval. `TOOL_REGISTRY` in `agent.py` is the single dispatch point.

**Argument validation before execution** — every filter argument is checked against an allowlist (`ALLOWED_REGIONS`, `ALLOWED_INDUSTRIES`, etc.) before any pandas operation runs. Invalid arguments are returned to the model as a `tool_result` error; Claude can self-correct or explain the issue.

**Show-your-work transparency** — every agent response displays the exact tool calls made, arguments used, and rows returned.

**Graceful failure** — API errors and unanswerable questions are caught and surfaced in the UI.

### Tool Functions

| Tool | Purpose |
|---|---|
| `filter_accounts` | Customer-level summary filtered by region, industry, customer type, product category, minimum revenue |
| `aggregate_margin` | Margin or discount metric aggregated by one dimension |
| `top_n_by_metric` | Top N customers ranked by any allowed metric |
| `get_price_waterfall` | Full price waterfall breakdown for a single customer |
| `get_exception_summary` | Exception rate and override discount behavior by dimension |

---

## MVP Scope

This project models invoice-level pricing performance across customers, SKUs, branches, reps, discounts, rebates, freight, and product cost.

The current Streamlit app includes:

- Executive pricing KPIs with date, region, category, and customer-type filters
- AI variance commentary (executive narrative from computed aggregates)
- Product category pocket margin analysis
- Regional exception rate analysis
- Customer margin leakage candidates
- Peer benchmark margin comparison
- Metric definitions for leakage analysis
- Scenario simulator for moving underpriced customers toward peer margin
- Exportable scenario recommendation list
- Price realization waterfall from list revenue to pocket margin
- Waterfall explanation for business users
- Product category pricing opportunity table
- Buyer context and willingness-to-pay signal analysis
- Service model margin visualization
- Natural-language query agent with constrained tool-use and visible tool call trace

---

## Project Summary

A concise business-facing explanation of the pricing problem, app capabilities, pricing logic, buyer context signals, and interview positioning is available here:

[Project Summary](docs/project-summary.md)

## Pricing Questions This Project Answers

- Where are we leaking margin?
- Which customers are priced below similar peers?
- How much margin could be recovered by moving customers toward peer benchmarks?
- How often are price exceptions being used?
- Where do discounts, rebates, freight, and cost reduce realized margin?
- Which accounts have the worst margin in a given segment? *(via AI agent)*
- What does the full price waterfall look like for a specific customer? *(via AI agent)*

## Tech Stack

- Python
- pandas / numpy
- Streamlit
- Plotly
- Anthropic API (claude-haiku, tool use)
- PostgreSQL / SQLAlchemy *(data generation; app runs on CSV)*

## Project Structure
```text
app/
main.py              # Main dashboard + variance commentary
agent.py             # Agent loop — Anthropic API + tool dispatch
agent_tools.py       # Constrained tool functions + argument validation
data_access.py       # Data loading
pages/
1_AI_Agent.py      # Chat UI for the NL query agent
data/
transactions.csv     # Synthetic B2B distributor transaction data
docs/
project-summary.md
```

## Local Setup

```bash
pip install -r requirements.txt
# Add ANTHROPIC_API_KEY to app/.streamlit/secrets.toml
cd app
streamlit run main.py
```

---

## Project Narrative

This project simulates the pricing analytics environment of a complex B2B distributor.

The app starts with executive pricing KPIs, then moves into deeper diagnostic views:

1. **Price Realization**
   - Tracks revenue, gross margin, pocket margin, and exception activity.
   - Uses a waterfall to show how list revenue is reduced by discounts, cost, rebates, and freight.

2. **Margin Leakage**
   - Compares customers against peer groups based on industry and customer type.
   - Estimates margin opportunity for customers performing below peer benchmarks.

3. **Scenario Modeling**
   - Allows users to simulate capturing a portion of the gap between current margin and peer margin.
   - Produces an exportable recommendation list for follow-up action.

4. **Discount Governance**
   - Highlights exception activity by region, product category, customer, and product segment.
   - Helps distinguish intentional discounting from potential leakage.

5. **Buyer Context / WTP Signals**
   - Compares pricing outcomes by industry, customer type, and service model.
   - Flags cases where urgent buyer context may suggest potential under-capture.

6. **Data Quality**
   - Validates core pricing fields before recommendations are trusted.
   - Investigates negative margin and below-cost transactions.

7. **AI Agent Layer**
   - Natural-language query agent with constrained tool-use and governance controls.
   - Variance commentary that generates executive-ready narrative from computed aggregates.
   - Designed for production use: validated arguments, visible tool traces, graceful failure handling.

The goal is not to find a mathematically perfect price. The goal is to create a practical pricing workflow that helps Sales, Finance, and Pricing identify where to investigate, where to tighten guidance, and where margin improvement may be possible.
