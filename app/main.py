import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_access import load_transactions
from utils import format_currency, format_pct
from pricing_logic import recommend_action, product_action, infer_wtp_signal


st.set_page_config(
    page_title="Distributor Pricing Engine",
    page_icon="📊",
    layout="wide",
)

@st.cache_data
def get_data() -> pd.DataFrame:
    return load_transactions()

df = get_data()

min_date = df["invoice_date"].min().date()
max_date = df["invoice_date"].max().date()

st.title("Distributor Price Realization & Margin Leakage Engine")
st.caption("Synthetic B2B distributor pricing analytics MVP")

with st.expander("MVP Project Scope"):
    st.markdown(
        """
        This app simulates strategic pricing work for a B2B distributor.

        It uses synthetic invoice-level data to analyze:
        - price realization
        - margin leakage
        - discount exceptions
        - customer peer benchmarks
        - pricing scenario impact 
        - buyer context / WTP signals

        The goal is to mimic the kind of pricing analytics used to improve margin performance, 
        pricing consistency, discount discipline, and commercial decision-making.
        """
    )

with st.sidebar:
    st.header("Filters")

    selected_date_range = st.date_input(
        "Invoice Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    selected_regions = st.multiselect(
        "Region",
        sorted(df["region"].unique()),
        default=sorted(df["region"].unique()),
    )

    selected_categories = st.multiselect(
        "Product Category",
        sorted(df["product_category"].unique()),
        default=sorted(df["product_category"].unique()),
    )

    selected_customer_types = st.multiselect(
        "Customer Type",
        sorted(df["customer_type"].unique()),
        default=sorted(df["customer_type"].unique()),
    )

if len(selected_date_range) == 2:
    start_date, end_date = selected_date_range
else:
    start_date, end_date = min_date, max_date

filtered = df[
    (df["invoice_date"].dt.date >= start_date)
    & (df["invoice_date"].dt.date <= end_date)
    & df["region"].isin(selected_regions)
    & df["product_category"].isin(selected_categories)
    & df["customer_type"].isin(selected_customer_types)
].copy()

total_revenue = filtered["gross_revenue"].sum()
gross_margin = filtered["gross_margin_dollars"].sum()
pocket_margin = filtered["pocket_margin_dollars"].sum()
avg_pocket_margin_pct = pocket_margin / total_revenue if total_revenue else 0
exception_rate = filtered["exception_flag"].mean()
avg_override_discount = filtered["override_discount_pct"].mean()

st.subheader("Executive Summary")
st.caption(f"Period: {start_date} to {end_date}")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

kpi1.metric("Revenue", format_currency(total_revenue))
kpi2.metric("Gross Margin", format_currency(gross_margin))
kpi3.metric("Pocket Margin", format_currency(pocket_margin))
kpi4.metric("Pocket Margin %", format_pct(avg_pocket_margin_pct))
kpi5.metric("Exception Rate", format_pct(exception_rate))

st.markdown("#### Executive Findings")

if avg_pocket_margin_pct < 0.18:
    margin_finding = (
        "Pocket margin is below the initial 18% management threshold."
        "Prioritize underpriced customers, weak product categories, and exception-heavy segments."
    )
else:
    margin_finding = (
        "Pocket margin is above the initial 18% management threshold."
        "Focus on maintaining discipline and selectively improving low-performing pockets."
    )

if exception_rate > 0.18:
    exception_finding = (
        "Exception activity is elevated. Review override patterns by rep, region, customer type, and product category."
    )
else:
    exception_finding = (
        "Exception activity is within the initial tolerance range. Monitor for pockets of excessive override behavior."
    )

if avg_override_discount > 0.02:
    override_finding = (
        "Average override discount is meaningful enough to warrant governance review."
    )
else:
    override_finding = (
        "Average override discount appears controlled overall, but customer-level leakage may still exist."
    )

st.info(
    f"""
    **Margin:** {margin_finding}

    **Exceptions:** {exception_finding}

    **Override Discounts:** {override_finding}
    """
)

st.markdown("#### Suggested Pricing Priorities")

priority_items = []

if exception_rate > 0.18:
    priority_items.append(
        "1. Investigate high-exception regions, reps, and customer groups before tightening policy."
    )

if avg_pocket_margin_pct < 0.18:
    priority_items.append(
        "2. Prioritize customers below peer margin where the dollar opportunity is material."
    )

if avg_override_discount > 0.02:
    priority_items.append(
        "3. Review override discount guidance and approval thresholds."
    )

priority_items.append(
    "4. Use the scenario simulator to size margin upside before recommending price actions."
)

priority_items.append(
    "5. Validate whether low-margin pockets reflect strategic intent, competitive pressure, or accidental leakage."
)

st.success("\n\n".join(priority_items))

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Pocket Margin by Product Category")

    category_summary = (
        filtered.groupby("product_category", as_index=False)
        .agg(
            revenue=("gross_revenue", "sum"),
            pocket_margin=("pocket_margin_dollars", "sum"),
        )
    )
    category_summary["pocket_margin_pct"] = (
        category_summary["pocket_margin"] / category_summary["revenue"]
    )

    category_summary = category_summary.sort_values("pocket_margin_pct").copy()
    category_summary["pocket_margin_label"] = category_summary["pocket_margin_pct"].map(
        lambda x: f"{x:.1%}"
    )

    fig = px.bar(
        category_summary,
        x="product_category",
        y="pocket_margin_pct",
        text="pocket_margin_label",
        labels={
            "product_category": "Product Category",
            "pocket_margin_pct": "Pocket Margin %",
        },
    )
    fig.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Exception Rate by Region")

    region_summary = (
        filtered.groupby("region", as_index=False)
        .agg(
            transactions=("transaction_id", "count"),
            exception_rate=("exception_flag", "mean"),
            avg_override_discount=("override_discount_pct", "mean"),
        )
    )

    region_summary = region_summary.sort_values("exception_rate", ascending=False).copy()
    region_summary["exception_rate_label"] = region_summary["exception_rate"].map(
        lambda x: f"{x:.1%}"
    )

    fig = px.bar(
        region_summary,
        x="region",
        y="exception_rate",
        text="exception_rate_label",
        labels={
            "region": "Region",
            "exception_rate": "Exception Rate",
        },
    )
    fig.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Top Customer Margin Leakage Candidates")

with st.expander("Definitions for leakage table"):
    st.markdown(
        """
        **Peer Margin %**   
        Median pocket margin percentage for customers in the same peer group.  
        Current peer group = `industry + customer_type`.

        **Gap to Peer**  
        Difference between peer margin and the customer's actual pocket margin.  
        Formula: `Peer Margin % - Pocket Margin %`.

        **Est. Leakage**  
        Estimated margin opportunity if the customer moved up to the peer benchmark.  
        Formula: `Positive Gap to Peer × Revenue`.

        **Exception Rate**  
        Share of transactions where an override discount was applied.  
        Formula: `Exception Transactions / Total Transactions`.

        **Avg Override Discount**  
        Average override discount across all transactions, including transactions with no override.

        **Transactions**  
        Number of invoice lines for the customer in the filtered period.
        """
    )

customer_summary = (
    filtered.groupby(
        ["customer_id", "industry", "region", "customer_type"],
        as_index=False,
    )
    .agg(
        revenue=("gross_revenue", "sum"),
        pocket_margin=("pocket_margin_dollars", "sum"),
        transactions=("transaction_id", "count"),
        exception_rate=("exception_flag", "mean"),
        avg_override_discount=("override_discount_pct", "mean"),
    )
)

customer_summary["pocket_margin_pct"] = (
    customer_summary["pocket_margin"] / customer_summary["revenue"]
)

peer_benchmark = (
    customer_summary.groupby(["industry", "customer_type"], as_index=False)
    .agg(peer_pocket_margin_pct=("pocket_margin_pct", "median"))
)

customer_summary = customer_summary.merge(
    peer_benchmark,
    on=["industry", "customer_type"],
    how="left",
)

customer_summary["margin_gap_to_peer"] = (
     customer_summary["peer_pocket_margin_pct"]
    - customer_summary["pocket_margin_pct"]
)

customer_summary["estimated_margin_leakage"] = (
    customer_summary["margin_gap_to_peer"].clip(lower=0)
    * customer_summary["revenue"]
)

leakage_candidates = customer_summary.sort_values(
    "estimated_margin_leakage",
    ascending=False,
).head(25)

display_cols = [
    "customer_id",
    "industry",
    "region",
    "customer_type",
    "revenue",
    "pocket_margin_pct",
    "peer_pocket_margin_pct",
    "margin_gap_to_peer",
    "estimated_margin_leakage",
    "exception_rate",
    "avg_override_discount",
    "transactions",
]

table_display = leakage_candidates[display_cols].copy()

pct_cols = [
    "pocket_margin_pct",
    "peer_pocket_margin_pct",
    "margin_gap_to_peer",
    "exception_rate",
    "avg_override_discount",
]

for col in pct_cols:
    table_display[col] = table_display[col] * 100

st.dataframe(
    table_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "revenue": st.column_config.NumberColumn("Revenue", format="$%,.0f"),
        "pocket_margin_pct": st.column_config.NumberColumn("Pocket Margin %", format="%.1f%%"),
        "peer_pocket_margin_pct": st.column_config.NumberColumn("Peer Margin %", format="%.1f%%"),
        "margin_gap_to_peer": st.column_config.NumberColumn("Gap to Peer", format="%.1f%%"),
        "estimated_margin_leakage": st.column_config.NumberColumn("Est. Leakage", format="$%,.0f"),
        "exception_rate": st.column_config.NumberColumn("Exception Rate", format="%.1f%%"),
        "avg_override_discount": st.column_config.NumberColumn("Avg Override Discount", format="%.1f%%"),
    },
)

st.divider()

st.subheader("Scenario Simulator: Move Underpriced Customers Toward Peer Margin")

st.caption(
    "Estimate the margin impact of improving below-peer customers by closing a portion of their gap to peer benchmark."
)

scenario_col1, scenario_col2, scenario_col3 = st.columns(3)

with scenario_col1:
    gap_capture_pct = st.slider(
        "Percent of Gap Captured",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        help="If a customer is 6 margin points below peer, capturing 50% means improving by 3 points.",
    )

with scenario_col2:
    min_revenue_threshold = st.number_input(
        "Minimum Customer Revenue",
        min_value=0,
        value=10_000,
        step=5_000,
        help="Only include customers with revenue at or above this threshold.",
    )

with scenario_col3:
    min_gap_threshold = st.slider(
        "Minimum Gap to Peer",
        min_value=0.0,
        max_value=20.0,
        value=2.0,
        step=0.5,
        help="Only include customers at least this many margin points below peer.",
    )

scenario_df = customer_summary.copy()

scenario_df["positive_gap_to_peer"] = scenario_df["margin_gap_to_peer"].clip(lower=0)

eligible = scenario_df[
    (scenario_df["revenue"] >= min_revenue_threshold)
    & (scenario_df["positive_gap_to_peer"] >= min_gap_threshold / 100)
].copy()

eligible["captured_gap"] = eligible["positive_gap_to_peer"] * (gap_capture_pct / 100)
eligible["estimated_incremental_margin"] = eligible["captured_gap"] * eligible["revenue"]

total_incremental_margin = eligible["estimated_incremental_margin"].sum()
affected_customers = eligible["customer_id"].nunique()
affected_revenue = eligible["revenue"].sum()

sim_kpi1, sim_kpi2, sim_kpi3 = st.columns(3)

sim_kpi1.metric("Estimated Incremental Margin", format_currency(total_incremental_margin))
sim_kpi2.metric("Affected Customers", f"{affected_customers:,}")
sim_kpi3.metric("Affected Revenue", format_currency(affected_revenue))

with st.expander("Scenario interpretation and risk note"):
    st.markdown(
        """
        This scenario estimates **potential margin improvement**, not guaranteed profit capture.

        The estimate assumes selected customers can be moved partway toward their peer margin benchmark.
        Before taking action, pricing teams should validate:

        - whether the customer is strategically important
        - whether low margin reflects a deliberate contract or competitive position
        - whether the peer group is truly comparable
        - whether recent cost changes, rebates, freight, or product mix explain the gap
        - whether Sales has a credible value message to support the change

        Use this as a prioritization tool, then investigate before recommending a price action.
        """
    )

st.markdown("#### Top Scenario Opportunities")

eligible["recommended_action"] = eligible.apply(recommend_action, axis=1)

scenario_display = eligible.sort_values(
    "estimated_incremental_margin",
    ascending=False,
).head(25)

scenario_display = scenario_display[
    [
        "customer_id",
        "industry",
        "region",
        "customer_type",
        "revenue",
        "pocket_margin_pct",
        "peer_pocket_margin_pct",
        "positive_gap_to_peer",
        "captured_gap",
        "estimated_incremental_margin",
        "exception_rate",
        "transactions",
        "recommended_action",
    ]
].copy()

scenario_pct_cols = [
    "pocket_margin_pct",
    "peer_pocket_margin_pct",
    "positive_gap_to_peer",
    "captured_gap",
    "exception_rate",
]

for col in scenario_pct_cols:
    scenario_display[col] = scenario_display[col] * 100

st.dataframe(
    scenario_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "revenue": st.column_config.NumberColumn("Revenue", format="$%,.0f"),
        "pocket_margin_pct": st.column_config.NumberColumn("Pocket Margin %", format="%.1f%%"),
        "peer_pocket_margin_pct": st.column_config.NumberColumn("Peer Margin %", format="%.1f%%"),
        "positive_gap_to_peer": st.column_config.NumberColumn("Gap to Peer", format="%.1f%%"),
        "captured_gap": st.column_config.NumberColumn("Captured Gap", format="%.1f%%"),
        "estimated_incremental_margin": st.column_config.NumberColumn(
            "Est. Incremental Margin",
            format="$%,.0f",
        ),
        "exception_rate": st.column_config.NumberColumn("Exception Rate", format="%.1f%%"),
    },
)

scenario_export = scenario_display.copy()

csv = scenario_export.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download scenario recommendations as CSV",
    data=csv,
    file_name="scenario_recommendations.csv",
    mime="text/csv",
)

st.divider()

st.subheader("Price Realization Waterfall")

st.caption(
    "Shows how list revenue is reduced by discounts, rebates, freight, and product cost to arrive at pocket margin."
)

with st.expander("How to read this waterfall"):
    st.markdown(
        """
        This waterfall starts with **List Revenue**, then steps down through each source of price or margin reduction.

        - **Standard Discounts**: expected discounts from customer/product pricing logic.
        - **Override Discounts**: manual or exception-based discounts beyond standard guidance.
        - **Product Cost**: cost of goods sold.
        - **Rebates**: customer rebates or incentives.
        - **Freight**: delivery or fulfillment cost absorbed by the business.
        - **Pocket Margin**: remaining margin after discounts, cost, rebates, and freight.

        In distributor pricing, the key question is not only “what price did we invoice?”  
        It is “how much value did we actually keep after all leakage points?”
        """
    )

waterfall = filtered.copy()

waterfall["list_revenue"] = waterfall["list_price"] * waterfall["quantity"]
waterfall["standard_discount_dollars"] = (
    waterfall["list_price"]
    * waterfall["standard_discount_pct"]
    * waterfall["quantity"]
)
waterfall["override_discount_dollars"] = (
    waterfall["list_price"]
    * waterfall["override_discount_pct"]
    * waterfall["quantity"]
)
waterfall["net_invoice_revenue"] = waterfall["gross_revenue"]
waterfall["product_cost_dollars"] = waterfall["unit_cost"] * waterfall["quantity"]

list_revenue = waterfall["list_revenue"].sum()
standard_discounts = -waterfall["standard_discount_dollars"].sum()
override_discounts = -waterfall["override_discount_dollars"].sum()
product_cost = -waterfall["product_cost_dollars"].sum()
rebates = -waterfall["rebate_dollars"].sum()
freight = -waterfall["freight_cost"].sum()
pocket_margin = waterfall["pocket_margin_dollars"].sum()

waterfall_df = pd.DataFrame(
    {
        "component": [
            "List Revenue",
            "Standard Discounts",
            "Override Discounts",
            "Product Cost",
            "Rebates",
            "Freight",
            "Pocket Margin",
        ],
        "amount": [
            list_revenue,
            standard_discounts,
            override_discounts,
            product_cost,
            rebates,
            freight,
            pocket_margin,
        ],
        "measure": [
            "absolute",
            "relative",
            "relative",
            "relative",
            "relative",
            "relative",
            "total",
        ],
    }
)

fig = go.Figure(
    go.Waterfall(
        name="Price Realization",
        orientation="v",
        measure=waterfall_df["measure"],
        x=waterfall_df["component"],
        y=waterfall_df["amount"],
        text=[f"${x:,.0f}" for x in waterfall_df["amount"]],
        textposition="outside",
        connector={"line": {"color": "rgba(180,180,180,0.5)"}},
        increasing={"marker": {"color": "#7EC8F5"}},
        decreasing={"marker": {"color": "#F87171"}},
        totals={"marker": {"color": "#60A5FA"}},
    )
)

fig.update_layout(
    yaxis_title="Dollars",
    xaxis_title="Component",
    yaxis_tickprefix="$",
    yaxis_tickformat=",.0f",
    showlegend=False,
)

st.plotly_chart(fig, use_container_width=True)

waterfall_table = waterfall_df[["component", "amount"]].copy()

waterfall_table["amount_type"] = waterfall_table["amount"].apply(
    lambda x: "Add / Starting Value" if x >= 0 else "Reduction"
)

st.dataframe(
    waterfall_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "component": st.column_config.TextColumn("Component"),
        "amount": st.column_config.NumberColumn("Amount", format="$%,.0f"),
        "amount_type": st.column_config.TextColumn("Type"),
    },
)

st.divider()

st.subheader("Product Category Pricing Opportunity")

st.caption(
    "Identifies product categories with lower pocket margin, higher override discounting, or high exception activity."
)

product_opportunity = (
    filtered.groupby("product_category", as_index=False)
    .agg(
        revenue=("gross_revenue", "sum"),
        pocket_margin=("pocket_margin_dollars", "sum"),
        gross_margin=("gross_margin_dollars", "sum"),
        transactions=("transaction_id", "count"),
        exception_rate=("exception_flag", "mean"),
        avg_standard_discount=("standard_discount_pct", "mean"),
        avg_override_discount=("override_discount_pct", "mean"),
    )
)

product_opportunity["pocket_margin_pct"] = (
    product_opportunity["pocket_margin"] / product_opportunity["revenue"]
)

product_opportunity["gross_margin_pct"] = (
    product_opportunity["gross_margin"] / product_opportunity["revenue"]
)

product_opportunity["discount_drag_pct"] = (
    product_opportunity["avg_standard_discount"]
    + product_opportunity["avg_override_discount"]
)

product_opportunity["recommended_action"] = product_opportunity.apply(product_action, axis=1)

product_display = product_opportunity.sort_values(
    ["pocket_margin_pct", "exception_rate"],
    ascending=[True, False],
).copy()

product_pct_cols = [
    "pocket_margin_pct",
    "gross_margin_pct",
    "exception_rate",
    "avg_standard_discount",
    "avg_override_discount",
    "discount_drag_pct",
]

for col in product_pct_cols:
    product_display[col] = product_display[col] * 100

st.dataframe(
    product_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "revenue": st.column_config.NumberColumn("Revenue", format="$%,.0f"),
        "pocket_margin": st.column_config.NumberColumn("Pocket Margin", format="$%,.0f"),
        "gross_margin": st.column_config.NumberColumn("Gross Margin", format="$%,.0f"),
        "pocket_margin_pct": st.column_config.NumberColumn("Pocket Margin %", format="%.1f%%"),
        "gross_margin_pct": st.column_config.NumberColumn("Gross Margin %", format="%.1f%%"),
        "exception_rate": st.column_config.NumberColumn("Exception Rate", format="%.1f%%"),
        "avg_standard_discount": st.column_config.NumberColumn("Avg Standard Discount", format="%.1f%%"),
        "avg_override_discount": st.column_config.NumberColumn("Avg Override Discount", format="%.1f%%"),
        "discount_drag_pct": st.column_config.NumberColumn("Total Discount Drag", format="%.1f%%"),
        "recommended_action": st.column_config.TextColumn("Recommended Action"),
    },
)

st.divider()

st.subheader("Buyer Context & WTP Signals")

st.caption(
    "Compares pricing outcomes by buyer context. Higher urgency or specialized needs may support stronger price realization."
)

context_summary = (
    filtered.groupby(["industry", "customer_type", "service_model"], as_index=False)
    .agg(
        revenue=("gross_revenue", "sum"),
        pocket_margin=("pocket_margin_dollars", "sum"),
        transactions=("transaction_id", "count"),
        exception_rate=("exception_flag", "mean"),
        avg_override_discount=("override_discount_pct", "mean"),
    )
)

context_summary["pocket_margin_pct"] = (
    context_summary["pocket_margin"] / context_summary["revenue"]
)

context_summary["wtp_signal"] = context_summary.apply(infer_wtp_signal, axis=1)

context_display = context_summary.sort_values(
    ["pocket_margin_pct", "exception_rate"],
    ascending=[True, False],
).copy()

for col in ["pocket_margin_pct", "exception_rate", "avg_override_discount"]:
    context_display[col] = context_display[col] * 100

st.dataframe(
    context_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "revenue": st.column_config.NumberColumn("Revenue", format="$%,.0f"),
        "pocket_margin": st.column_config.NumberColumn("Pocket Margin", format="$%,.0f"),
        "pocket_margin_pct": st.column_config.NumberColumn("Pocket Margin %", format="%.1f%%"),
        "exception_rate": st.column_config.NumberColumn("Exception Rate", format="%.1f%%"),
        "avg_override_discount": st.column_config.NumberColumn("Avg Override Discount", format="%.1f%%"),
        "wtp_signal": st.column_config.TextColumn("WTP Signal", width="large",),
    },
) 

st.markdown("#### Pocket Margin by Service Model")

service_model_summary = (
    filtered.groupby("service_model", as_index=False)
    .agg(
        revenue=("gross_revenue", "sum"),
        pocket_margin=("pocket_margin_dollars", "sum"),
        exception_rate=("exception_flag", "mean"),
    )
)

service_model_summary["pocket_margin_pct"] = (
    service_model_summary["pocket_margin"] / service_model_summary["revenue"]
)

service_model_summary = service_model_summary.sort_values("pocket_margin_pct").copy()

service_model_summary["pocket_margin_label"] = service_model_summary[
    "pocket_margin_pct"
].map(lambda x: f"{x:.1%}")

fig = px.bar(
    service_model_summary,
    x="service_model",
    y="pocket_margin_pct",
    text="pocket_margin_label",
    color="service_model",
    labels={
        "service_model": "Service Model",
        "pocket_margin_pct": "Pocket Margin %",
    },
)

fig.update_layout(
    yaxis_tickformat=".0%",
    showlegend=False,
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Data Quality Checks")

st.caption(
    "Basic validation checks to confirm the pricing dataset is usable before making recommendations."
)

with st.expander("How to interpret these checks"):
    st.markdown(
        """
        These checks are not all errors. Some are investigation prompts.

        - **Negative pocket margin rows** may reflect real margin leakage, high freight, rebates, heavy discounting, or intentional strategic pricing.
        - **Invoice price below unit cost rows** require deeper review because the business is selling below product cost before freight and rebates.
        - **Discounts above 50% rows** may indicate pricing errors, extreme exceptions, or unusual contract terms.
        - Clean data does not mean good pricing. It only means the dataset is usable enough to support analysis.

        Use this section to decide where recommendations need more validation before action.
        """
    )

dq = filtered.copy()

dq_checks = {
    "Transactions": len(dq),
    "Missing invoice prices": dq["invoice_price"].isna().sum(),
    "Missing unit costs": dq["unit_cost"].isna().sum(),
    "Negative revenue rows": (dq["gross_revenue"] < 0).sum(),
    "Negative pocket margin rows": (dq["pocket_margin_dollars"] < 0).sum(),
    "Invoice price below unit cost rows": (dq["invoice_price"] < dq["unit_cost"]).sum(),
    "Discounts above 50% rows": (
        (dq["standard_discount_pct"] + dq["override_discount_pct"]) > 0.50
    ).sum(),
}

dq_table = pd.DataFrame(
    {
        "check": list(dq_checks.keys()),
        "result": list(dq_checks.values()),
    }
)

dq_table["status"] = dq_table["result"].apply(
    lambda x: "Review" if x > 0 else "OK"
)

# Transaction count should always be OK unless the filtered data is empty
dq_table.loc[dq_table["check"].eq("Transactions"), "status"] = dq_table.loc[
    dq_table["check"].eq("Transactions"), "result"
].apply(lambda x: "OK" if x > 0 else "Review")

st.dataframe(
    dq_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "check": st.column_config.TextColumn("Check"),
        "result": st.column_config.NumberColumn("Result", format="%d"),
        "status": st.column_config.TextColumn("Status"),
    },
)

st.markdown("#### Waterfall Reconciliation")

recalc_pocket_margin = (
    dq["gross_revenue"]
    - (dq["unit_cost"] * dq["quantity"])
    - dq["rebate_dollars"]
    - dq["freight_cost"]
).sum()

reported_pocket_margin = dq["pocket_margin_dollars"].sum()
waterfall_recon_diff = recalc_pocket_margin - reported_pocket_margin

recon_col1, recon_col2, recon_col3 = st.columns(3)

recon_col1.metric("Recalculated Pocket Margin", format_currency(recalc_pocket_margin))
recon_col2.metric("Reported Pocket Margin", format_currency(reported_pocket_margin))
recon_col3.metric("Difference", format_currency(waterfall_recon_diff))

if abs(waterfall_recon_diff) < 1:
    st.success("Waterfall reconciliation passed. Recalculated and reported pocket margin match.")
else:
    st.warning(
        "Waterfall reconciliation difference detected. Review revenue, cost, rebate, freight, or pocket margin calculations."
    )


st.markdown("#### Below-Cost Transaction Investigation")

below_cost = dq[dq["invoice_price"] < dq["unit_cost"]].copy()

if below_cost.empty:
    st.success("No below-cost invoice rows found in the current filter context.")
else:
    below_cost_summary = (
        below_cost.groupby(["product_category", "customer_type"], as_index=False)
        .agg(
            transactions=("transaction_id", "count"),
            revenue=("gross_revenue", "sum"),
            pocket_margin=("pocket_margin_dollars", "sum"),
            avg_standard_discount=("standard_discount_pct", "mean"),
            avg_override_discount=("override_discount_pct", "mean"),
            exception_rate=("exception_flag", "mean"),
        )
    )

    below_cost_summary["pocket_margin_pct"] = (
        below_cost_summary["pocket_margin"] / below_cost_summary["revenue"]
    )

    below_cost_summary = below_cost_summary.sort_values(
        "transactions",
        ascending=False,
    ).copy()

    for col in [
        "avg_standard_discount",
        "avg_override_discount",
        "exception_rate",
        "pocket_margin_pct",
    ]:
        below_cost_summary[col] = below_cost_summary[col] * 100

    st.dataframe(
        below_cost_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "product_category": st.column_config.TextColumn("Product Category"),
            "customer_type": st.column_config.TextColumn("Customer Type"),
            "transactions": st.column_config.NumberColumn("Transactions", format="%d"),
            "revenue": st.column_config.NumberColumn("Revenue", format="$%,.0f"),
            "pocket_margin": st.column_config.NumberColumn("Pocket Margin", format="$%,.0f"),
            "pocket_margin_pct": st.column_config.NumberColumn("Pocket Margin %", format="%.1f%%"),
            "avg_standard_discount": st.column_config.NumberColumn("Avg Standard Discount", format="%.1f%%"),
            "avg_override_discount": st.column_config.NumberColumn("Avg Override Discount", format="%.1f%%"),
            "exception_rate": st.column_config.NumberColumn("Exception Rate", format="%.1f%%"),
        },
    )


st.divider()

st.subheader("Exception Heatmap: Region vs Product Category")

st.caption(
    "Highlights where override exceptions are concentrated across regions and product categories."
)

heatmap_data = (
    filtered.groupby(["region", "product_category"], as_index=False)
    .agg(
        exception_rate=("exception_flag", "mean"),
        transactions=("transaction_id", "count"),
    )
)

heatmap_pivot = heatmap_data.pivot(
    index="region",
    columns="product_category",
    values="exception_rate",
)

fig = px.imshow(
    heatmap_pivot,
    text_auto=".1%",
    aspect="auto",
    color_continuous_scale="Reds",
    labels={
        "x": "Product Category",
        "y": "Region",
        "color": "Exception Rate",
    },
)

fig.update_layout(
    xaxis_title="Product Category",
    yaxis_title="Region",
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("How to use this heatmap"):
    st.markdown(
        """
        This view helps identify where pricing exceptions may need investigation.

        High exception rates may indicate:
        - competitive pressure
        - weak price guidance
        - sales override habits
        - unrealistic list or floor prices
        - strategic customer concentration
        - unclear discount governance

        The goal is not to eliminate all exceptions. The goal is to determine whether exceptions are intentional, explainable, and profitable.
        """
    )