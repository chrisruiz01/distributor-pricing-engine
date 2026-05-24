from pathlib import Path

import pandas as pd

from app.config import get_engine


DATA_DIR = Path("data")


def load_csv_to_postgres(file_name: str, table_name: str) -> None:
    file_path = DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Missing file: {file_path}")

    df = pd.read_csv(file_path)
    engine = get_engine()

    df.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=5_000,
    )

    print(f"Loaded {len(df):,} rows into table: {table_name}")


def main() -> None:
    load_csv_to_postgres("customers.csv", "customers")
    load_csv_to_postgres("products.csv", "products")
    load_csv_to_postgres("transactions.csv", "transactions")

    print("All CSV files loaded into PostgreSQL.")


if __name__ == "__main__":
    main()