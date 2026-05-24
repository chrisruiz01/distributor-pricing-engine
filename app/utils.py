def format_currency(value: float) -> str:
    """Format a number as US currency."""
    return f"${value:,.0f}"


def format_pct(value: float) -> str:
    """Format a decimal as a percentage."""
    return f"{value:.1%}" 