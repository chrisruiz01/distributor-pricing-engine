# app/agent_tools.py
"""
Constrained tool functions for the pricing agent.

GOVERNANCE CONTRACT:
- These are the ONLY operations the agent can perform on the dataframe.
- Every argument is validated against an allowlist before execution.
- No free-form eval, no arbitrary column access, no SQL passthrough.
- Each function returns {"data": <DataFrame or dict>, "metadata": <dict>}
  so the UI can display both the result and a trace of what was called.
"""

from __future__ import annotations

import pandas as pd
from typing import Optional


# ---------------------------------------------------------------------------
# Allowlists — validated before any function executes
# These are the only values the agent is permitted to use.
# ---------------------------------------------------------------------------

ALLOWED_REGIONS = {
    "Midwest", "Northeast", "Southwest", "Southeast", "West"
}

ALLOWED_INDUSTRIES = {
    "HVAC Contractor", "Appliance Repair", "Plumbing Contractor",
    "Pool/Spa Service", "Commercial Kitchen Repair"
}

ALLOWED_CUSTOMER_TYPES = {
    "Local Independent", "Regional Chain", "National Account"
}

ALLOWED_PRODUCT_CATEGORIES = {
    "Heavy Equipment", "Consumable", "Commodity Part",
    "OEM Specialty Part", "Accessory"
}

ALLOWED_GROUP_BY_FIELDS = {
    "region", "industry", "customer_type",
    "product_category", "service_model"
}

ALLOWED_SERVICE_MODELS = {
    "Mixed", "Routine Replenishment", "Emergency Repair"
}

ALLOWED_METRICS = {
    "pocket_margin_pct",
    "pocket_margin_dollars",
    "gross_margin_dollars",
    "exception_rate",
    "override_discount_pct",
    "estimated_margin_leakage",
    "revenue",
}

MAX_N = 50  # cap on top_n results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_filters(
    df: pd.DataFrame,
    region: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    product_category: Optional[str] = None,
) -> pd.DataFrame:
    """Apply validated dimension filters to the dataframe."""
    filtered = df.copy()
    if region:
        filtered = filtered[filtered["region"] == region]
    if industry:
        filtered = filtered[filtered["industry"] == industry]
    if customer_type:
        filtered = filtered[filtered["customer_type"] == customer_type]
    if product_category:
        filtered = filtered[filtered["product_category"] == product_category]
    return filtered


def _validate_filter_args(
    region: Optional[str],
    industry: Optional[str],
    customer_type: Optional[str],
    product_category: Optional[str],
) -> None:
    """Raise ValueError if any filter value is not in its allowlist."""
    if region and region not in ALLOWED_REGIONS:
        raise ValueError(
            f"Invalid region '{region}'. Allowed: {sorted(ALLOWED_REGIONS)}"
        )
    if industry and industry not in ALLOWED_INDUSTRIES:
        raise ValueError(
            f"Invalid industry '{industry}'. Allowed: {sorted(ALLOWED_INDUSTRIES)}"
        )
    if customer_type and customer_type not in ALLOWED_CUSTOMER_TYPES:
        raise ValueError(
            f"Invalid customer_type '{customer_type}'. "
            f"Allowed: {sorted(ALLOWED_CUSTOMER_TYPES)}"
        )
    if product_category and product_category not in ALLOWED_PRODUCT_CATEGORIES:
        raise ValueError(
            f"Invalid product_category '{product_category}'. "
            f"Allowed: {sorted(ALLOWED_PRODUCT_CATEGORIES)}"
        )


# ---------------------------------------------------------------------------
# Tool 1: filter_accounts
# "Show me accounts in HVAC with revenue above $50k"
# ---------------------------------------------------------------------------

def filter_accounts(
    df: pd.DataFrame,
    region: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    product_category: Optional[str] = None,
    min_revenue: float = 0,
) -> dict:
    """
    Return a customer-level summary filtered by dimension values.
    
    Parameters
    ----------
    region : one of ALLOWED_REGIONS or None
    industry : one of ALLOWED_INDUSTRIES or None
    customer_type : one of ALLOWED_CUSTOMER_TYPES or None
    product_category : one of ALLOWED_PRODUCT_CATEGORIES or None
    min_revenue : minimum gross revenue threshold (default 0)
    """
    _validate_filter_args(region, industry, customer_type, product_category)

    if min_revenue < 0:
        raise ValueError("min_revenue must be >= 0")

    filtered = _apply_filters(df, region, industry, customer_type, product_category)

    # Summarize to customer level
    summary = (
        filtered.groupby(
            ["customer_id", "industry", "region", "customer_type"],
            as_index=False,
        )
        .agg(
            revenue=("gross_revenue", "sum"),
            pocket_margin_dollars=("pocket_margin_dollars", "sum"),
            transactions=("transaction_id", "count"),
            exception_rate=("exception_flag", "mean"),
            avg_override_discount=("override_discount_pct", "mean"),
        )
    )

    summary["pocket_margin_pct"] = (
        summary["pocket_margin_dollars"] / summary["revenue"]
    )

    summary = summary[summary["revenue"] >= min_revenue]
    summary = summary.sort_values("revenue", ascending=False).reset_index(drop=True)

    return {
        "data": summary,
        "metadata": {
            "tool": "filter_accounts",
            "filters_applied": {
                "region": region,
                "industry": industry,
                "customer_type": customer_type,
                "product_category": product_category,
                "min_revenue": min_revenue,
            },
            "rows_returned": len(summary),
        },
    }


# ---------------------------------------------------------------------------
# Tool 2: aggregate_margin
# "What's the average pocket margin by product category?"
# ---------------------------------------------------------------------------

def aggregate_margin(
    df: pd.DataFrame,
    group_by: str,
    metric: str = "pocket_margin_pct",
    region: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    product_category: Optional[str] = None,
) -> dict:
    """
    Aggregate a margin or discount metric grouped by one dimension.

    Parameters
    ----------
    group_by : one of ALLOWED_GROUP_BY_FIELDS
    metric : one of ALLOWED_METRICS
    region, industry, customer_type, product_category : optional filters
    """
    if group_by not in ALLOWED_GROUP_BY_FIELDS:
        raise ValueError(
            f"Invalid group_by '{group_by}'. "
            f"Allowed: {sorted(ALLOWED_GROUP_BY_FIELDS)}"
        )
    if metric not in ALLOWED_METRICS:
        raise ValueError(
            f"Invalid metric '{metric}'. Allowed: {sorted(ALLOWED_METRICS)}"
        )

    _validate_filter_args(region, industry, customer_type, product_category)
    filtered = _apply_filters(df, region, industry, customer_type, product_category)

    # For rate/pct metrics, compute weighted average via sum of components.
    # For dollar metrics, just sum.
    if metric == "pocket_margin_pct":
        agg = (
            filtered.groupby(group_by, as_index=False)
            .agg(
                pocket_margin_dollars=("pocket_margin_dollars", "sum"),
                revenue=("gross_revenue", "sum"),
                transactions=("transaction_id", "count"),
            )
        )
        agg[metric] = agg["pocket_margin_dollars"] / agg["revenue"]
        agg = agg[[group_by, metric, "revenue", "transactions"]]

    elif metric == "exception_rate":
        agg = (
            filtered.groupby(group_by, as_index=False)
            .agg(
                exception_rate=("exception_flag", "mean"),
                transactions=("transaction_id", "count"),
                revenue=("gross_revenue", "sum"),
            )
        )

    elif metric == "override_discount_pct":
        agg = (
            filtered.groupby(group_by, as_index=False)
            .agg(
                override_discount_pct=("override_discount_pct", "mean"),
                transactions=("transaction_id", "count"),
                revenue=("gross_revenue", "sum"),
            )
        )

    else:
        # Dollar metrics: sum
        agg = (
            filtered.groupby(group_by, as_index=False)
            .agg(
                value=(metric, "sum"),
                transactions=("transaction_id", "count"),
                revenue=("gross_revenue", "sum"),
            )
        )
        agg = agg.rename(columns={"value": metric})

    agg = agg.sort_values(metric, ascending=False).reset_index(drop=True)

    return {
        "data": agg,
        "metadata": {
            "tool": "aggregate_margin",
            "group_by": group_by,
            "metric": metric,
            "filters_applied": {
                "region": region,
                "industry": industry,
                "customer_type": customer_type,
                "product_category": product_category,
            },
            "rows_returned": len(agg),
        },
    }


# ---------------------------------------------------------------------------
# Tool 3: top_n_by_metric
# "Which 10 accounts have the worst list-to-pocket leakage in HVAC?"
# ---------------------------------------------------------------------------

def top_n_by_metric(
    df: pd.DataFrame,
    metric: str,
    n: int = 10,
    ascending: bool = True,
    region: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    product_category: Optional[str] = None,
    min_revenue: float = 0,
) -> dict:
    """
    Return the top N customers ranked by a metric.

    Parameters
    ----------
    metric : one of ALLOWED_METRICS
    n : number of results, max 50
    ascending : True = worst first (lowest margin), False = best first
    """
    if metric not in ALLOWED_METRICS:
        raise ValueError(
            f"Invalid metric '{metric}'. Allowed: {sorted(ALLOWED_METRICS)}"
        )
    if not (1 <= n <= MAX_N):
        raise ValueError(f"n must be between 1 and {MAX_N}, got {n}")
    if min_revenue < 0:
        raise ValueError("min_revenue must be >= 0")

    _validate_filter_args(region, industry, customer_type, product_category)
    filtered = _apply_filters(df, region, industry, customer_type, product_category)

    # Build customer-level summary with all metrics available
    summary = (
        filtered.groupby(
            ["customer_id", "industry", "region", "customer_type"],
            as_index=False,
        )
        .agg(
            revenue=("gross_revenue", "sum"),
            pocket_margin_dollars=("pocket_margin_dollars", "sum"),
            gross_margin_dollars=("gross_margin_dollars", "sum"),
            exception_rate=("exception_flag", "mean"),
            override_discount_pct=("override_discount_pct", "mean"),
            transactions=("transaction_id", "count"),
        )
    )

    summary["pocket_margin_pct"] = (
        summary["pocket_margin_dollars"] / summary["revenue"]
    )

    # Compute estimated_margin_leakage if requested
    if metric == "estimated_margin_leakage":
        peer_benchmark = (
            summary.groupby(["industry", "customer_type"], as_index=False)
            .agg(peer_pocket_margin_pct=("pocket_margin_pct", "median"))
        )
        summary = summary.merge(peer_benchmark, on=["industry", "customer_type"], how="left")
        summary["margin_gap_to_peer"] = (
            summary["peer_pocket_margin_pct"] - summary["pocket_margin_pct"]
        )
        summary["estimated_margin_leakage"] = (
            summary["margin_gap_to_peer"].clip(lower=0) * summary["revenue"]
        )

    summary = summary[summary["revenue"] >= min_revenue]

    result = (
        summary.sort_values(metric, ascending=ascending)
        .head(n)
        .reset_index(drop=True)
    )

    return {
        "data": result,
        "metadata": {
            "tool": "top_n_by_metric",
            "metric": metric,
            "n": n,
            "ascending": ascending,
            "filters_applied": {
                "region": region,
                "industry": industry,
                "customer_type": customer_type,
                "product_category": product_category,
                "min_revenue": min_revenue,
            },
            "rows_returned": len(result),
        },
    }


# ---------------------------------------------------------------------------
# Tool 4: get_price_waterfall
# "Show me the price waterfall for customer C0007"
# ---------------------------------------------------------------------------

def get_price_waterfall(
    df: pd.DataFrame,
    customer_id: str,
) -> dict:
    """
    Return aggregated price waterfall components for one customer.

    Parameters
    ----------
    customer_id : must exist in the dataframe
    """
    customer_id = str(customer_id).strip()

    valid_ids = set(df["customer_id"].astype(str).unique())
    if customer_id not in valid_ids:
        raise ValueError(
            f"customer_id '{customer_id}' not found. "
            f"Check spelling — IDs are case-sensitive (e.g. 'C0007')."
        )

    cust = df[df["customer_id"].astype(str) == customer_id].copy()

    list_revenue = (cust["list_price"] * cust["quantity"]).sum()
    standard_discounts = -(cust["list_price"] * cust["standard_discount_pct"] * cust["quantity"]).sum()
    override_discounts = -(cust["list_price"] * cust["override_discount_pct"] * cust["quantity"]).sum()
    product_cost = -(cust["unit_cost"] * cust["quantity"]).sum()
    rebates = -cust["rebate_dollars"].sum()
    freight = -cust["freight_cost"].sum()
    pocket_margin = cust["pocket_margin_dollars"].sum()

    waterfall = pd.DataFrame({
        "component": [
            "List Revenue", "Standard Discounts", "Override Discounts",
            "Product Cost", "Rebates", "Freight", "Pocket Margin"
        ],
        "amount": [
            list_revenue, standard_discounts, override_discounts,
            product_cost, rebates, freight, pocket_margin
        ],
        "measure": [
            "absolute", "relative", "relative",
            "relative", "relative", "relative", "total"
        ],
    })

    pocket_margin_pct = pocket_margin / list_revenue if list_revenue else 0

    return {
        "data": waterfall,
        "metadata": {
            "tool": "get_price_waterfall",
            "customer_id": customer_id,
            "list_revenue": list_revenue,
            "pocket_margin": pocket_margin,
            "pocket_margin_pct": pocket_margin_pct,
            "transactions_included": len(cust),
        },
    }


# ---------------------------------------------------------------------------
# Tool 5: get_exception_summary
# "Where are exceptions concentrated by region and product category?"
# ---------------------------------------------------------------------------

def get_exception_summary(
    df: pd.DataFrame,
    group_by: str,
    region: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    product_category: Optional[str] = None,
) -> dict:
    """
    Summarize exception rates and override discount behavior grouped by one dimension.

    Parameters
    ----------
    group_by : one of ALLOWED_GROUP_BY_FIELDS
    """
    if group_by not in ALLOWED_GROUP_BY_FIELDS:
        raise ValueError(
            f"Invalid group_by '{group_by}'. "
            f"Allowed: {sorted(ALLOWED_GROUP_BY_FIELDS)}"
        )

    _validate_filter_args(region, industry, customer_type, product_category)
    filtered = _apply_filters(df, region, industry, customer_type, product_category)

    summary = (
        filtered.groupby(group_by, as_index=False)
        .agg(
            transactions=("transaction_id", "count"),
            exception_count=("exception_flag", "sum"),
            exception_rate=("exception_flag", "mean"),
            avg_override_discount=("override_discount_pct", "mean"),
            revenue=("gross_revenue", "sum"),
            pocket_margin_dollars=("pocket_margin_dollars", "sum"),
        )
    )

    summary["pocket_margin_pct"] = (
        summary["pocket_margin_dollars"] / summary["revenue"]
    )

    summary = summary.sort_values("exception_rate", ascending=False).reset_index(drop=True)

    return {
        "data": summary,
        "metadata": {
            "tool": "get_exception_summary",
            "group_by": group_by,
            "filters_applied": {
                "region": region,
                "industry": industry,
                "customer_type": customer_type,
                "product_category": product_category,
            },
            "rows_returned": len(summary),
        },
    }