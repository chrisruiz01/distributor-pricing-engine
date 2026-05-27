from pathlib import Path

import pandas as pd
from sqlalchemy import text

from config import get_engine


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TRANSACTIONS_CSV = DATA_DIR / "transactions.csv"


def load_transactions_from_csv() -> pd.DataFrame:
    """Load synthetic transaction data from the local CSV file."""
    return pd.read_csv(TRANSACTIONS_CSV, parse_dates=["invoice_date"])


def load_transactions_from_db() -> pd.DataFrame:
    """Load transaction data from PostgreSQL."""
    engine = get_engine()

    query = text("""
        SELECT
            t.transaction_id,
            t.invoice_date,
            t.customer_id,
            c.industry,
            c.region,
            c.customer_type,
            t.product_id,
            p.product_category,
            p.product_name,
            t.quantity,
            t.list_price,
            t.invoice_price,
            t.unit_cost,
            t.standard_discount_pct,
            t.override_discount_pct,
            t.rebate_pct,
            t.freight_cost,
            t.service_cost,
            t.exception_flag,
            t.order_channel,
            t.service_model,
            t.freight_terms,
            t.contract_flag
        FROM transactions t
        LEFT JOIN customers c
            ON t.customer_id = c.customer_id
        LEFT JOIN products p
            ON t.product_id = p.product_id
    """)

    return pd.read_sql(query, engine)


def load_transactions() -> pd.DataFrame:
    """
    Load synthetic transaction data from CSV.

    The portfolio app uses repo-contained synthetic data so it can run locally
    and on Streamlit Cloud without database credentials.
    """
    return load_transactions_from_csv()