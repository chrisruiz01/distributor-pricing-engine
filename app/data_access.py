import pandas as pd
from sqlalchemy import text

from config import get_engine


def load_transactions() -> pd.DataFrame:
    query = text("""
        SELECT
            transaction_id,
            invoice_date,
            customer_id,
            sku,
            branch_id,
            sales_rep_id,
            industry,
            region,
            customer_type,
            service_model,
            annual_revenue_band,
            product_category,
            unit_cost,
            list_price,
            criticality,
            quantity,
            standard_discount_pct,
            exception_flag,
            override_discount_pct,
            invoice_price,
            rebate_pct,
            freight_cost,
            gross_revenue,
            gross_margin_dollars,
            rebate_dollars,
            pocket_margin_dollars,
            pocket_margin_pct
        FROM transactions
    """)

    engine = get_engine()

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    df["invoice_date"] = pd.to_datetime(df["invoice_date"])

    return df