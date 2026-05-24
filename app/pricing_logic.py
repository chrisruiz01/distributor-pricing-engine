def recommend_action(row) -> str:
    """Recommend a customer-level pricing action based on peer margin gap and exception behavior."""
    margin_gap = row.get("margin_gap_to_peer", 0)
    exception_rate = row.get("exception_rate", 0)
    revenue = row.get("revenue", 0)

    if margin_gap >= 0.06 and exception_rate >= 0.20:
        return "Review discount behavior; tighten overrides"

    if margin_gap >= 0.05 and revenue >= 25_000:
        return "Targeted price increase candidate"

    if exception_rate >= 0.25:
        return "Audit exception pattern"

    if margin_gap >= 0.03:
        return "Move toward peer floor"

    return "Monitor"


def product_action(row) -> str:
    """Recommend a product-category pricing action based on margin and exception patterns."""
    pocket_margin_pct = row.get("pocket_margin_pct", 0)
    margin_gap = row.get("margin_gap_to_peer", 0)
    exception_rate = row.get("exception_rate", 0)

    if pocket_margin_pct < 0:
        return "Investigate below-cost pricing"

    if margin_gap >= 0.08 and exception_rate >= 0.30:
        return "Review price floors and discount approvals"

    if margin_gap >= 0.05:
        return "Evaluate price increase opportunity"

    if exception_rate >= 0.30:
        return "Tighten exception governance"

    return "Maintain / monitor"


def infer_wtp_signal(row) -> str:
    """Infer buyer willingness-to-pay context from transaction and service-model signals."""
    signals = []

    if row.get("service_model") in ["Emergency", "Special Order"]:
        signals.append("urgent need")

    if row.get("freight_terms") == "Expedited":
        signals.append("speed-sensitive")

    if row.get("order_channel") in ["Rep Assisted", "Sales Rep"]:
        signals.append("relationship-assisted")

    if row.get("contract_flag") == 1:
        signals.append("contracted buyer")

    if row.get("exception_flag") == 1:
        signals.append("discount exception")

    if not signals:
        return "standard context"

    return ", ".join(signals)