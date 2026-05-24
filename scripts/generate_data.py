from pathlib import Path
import numpy as np
import pandas as pd 


RANDOM_SEED = 42
N_CUSTOMERS = 500
N_PRODUCTS = 300
N_TRANSACTIONS = 50_000

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def generate_customers() -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)

    industries = [
        "HVAC Contractor",
        "Appliance Repair",
        "Plumbing Contractor",
        "Commercial Kitchen Repair",
        "Pool/Spa Service",
    ]

    regions = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
    customer_types = ["Local Independent", "Regional Chain", "National Account"]
    service_models = ["Emergency Repair", "Routine Replenishment", "Mixed"]

    customers = pd.DataFrame({
        "customer_id": [f"C{str(i).zfill(4)}" for i in range(1, N_CUSTOMERS + 1)],
        "industry": rng.choice(industries, N_CUSTOMERS),
        "region": rng.choice(regions, N_CUSTOMERS),
        "customer_type": rng.choice(customer_types, N_CUSTOMERS, p=[0.72, 0.22, 0.06]),
        "service_model": rng.choice(service_models, N_CUSTOMERS, p=[0.30, 0.35, 0.35])
    })

    customers["annual_revenue_band"] = np.select(
        [
            customers["customer_type"].eq("National Account"),
            customers["customer_type"].eq("Regional Chain"),
        ],
        ["Large", "Mid-Market"],
        default="Small",
    )

    return customers


def generate_products() -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 1)

    categories = [
        "OEM Specialty Part",
        "Commodity Part",
        "Heavy Equipment",
        "Accessory",
        "Consumable",
    ]

    products = pd.DataFrame({
        "sku": [f"SKU{str(i).zfill(5)}" for i in range(1, N_PRODUCTS + 1)],
        "product_category": rng.choice(categories, N_PRODUCTS, p=[0.30, 0.30, 0.10, 0.15, 0.15]),
    })

    base_cost = {
        "OEM Specialty Part": (35, 250),
        "Commodity Part": (5, 75),
        "Heavy Equipment": (500, 3500),
        "Accessory": (10, 150),
        "Consumable": (2, 40),
    }

    costs = []
    for category in products["product_category"]:
        low, high = base_cost[category]
        costs.append(round(rng.uniform(low, high), 2))

    products["unit_cost"] = costs

    markup_by_category = {
        "OEM Specialty Part": 1.85,
        "Commodity Part": 1.35,
        "Heavy Equipment": 1.28,
        "Accessory": 1.70,
        "Consumable": 1.55,
    }

    products["list_price"] = products.apply(
        lambda row: round(row["unit_cost"] * markup_by_category[row["product_category"]], 2),
        axis=1,
    )

    products["criticality"] = np.select(
        [
            products["product_category"].eq("OEM Specialty Part"),
            products["product_category"].eq("Heavy Equipment"),
            products["product_category"].eq("Commodity Part"),
        ],
        ["High", "Medium", "Low"],
        default="Medium",
    )

    return products


def generate_transactions(customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 2)

    tx = pd.DataFrame({
        "transaction_id": [f"T{str(i).zfill(7)}" for i in range(1, N_TRANSACTIONS + 1)],
        "invoice_date": pd.to_datetime(
            rng.choice(pd.date_range("2025-01-01", "2025-12-31"), N_TRANSACTIONS)
        ),
        "customer_id": rng.choice(customers["customer_id"], N_TRANSACTIONS),
        "sku": rng.choice(products["sku"], N_TRANSACTIONS),
        "branch_id": rng.choice([f"B{str(i).zfill(3)}" for i in range(1, 31)], N_TRANSACTIONS),
        "sales_rep_id": rng.choice([f"R{str(i).zfill(3)}" for i in range(1, 76)], N_TRANSACTIONS),
    })

    tx = tx.merge(customers, on="customer_id", how="left")
    tx = tx.merge(products, on="sku", how="left")

    tx["quantity"] = rng.integers(1, 12, N_TRANSACTIONS)

    base_discount = np.select(
        [
            tx["customer_type"].eq("National Account"),
            tx["customer_type"].eq("Regional Chain"),
            tx["customer_type"].eq("Local Independent"),
        ],
        [0.18, 0.12, 0.06],
        default=0.06,
    )

    category_discount_adjustment = np.select(
        [
            tx["product_category"].eq("Commodity Part"),
            tx["product_category"].eq("OEM Specialty Part"),
            tx["product_category"].eq("Heavy Equipment"),
        ],
        [0.04, -0.02, 0.02],
        default=0.00,
    )

    random_noise = rng.normal(0, 0.025, N_TRANSACTIONS)

    tx["standard_discount_pct"] = np.clip(
        base_discount + category_discount_adjustment + random_noise,
        0,
        0.35,
    )

    tx["exception_flag"] = rng.choice([0, 1], N_TRANSACTIONS, p=[0.82, 0.18])

    tx["override_discount_pct"] = np.where(
        tx["exception_flag"].eq(1),
        rng.uniform(0.02, 0.18, N_TRANSACTIONS),
        0,
    )

    tx["invoice_price"] = tx["list_price"] * (
        1 - tx["standard_discount_pct"] - tx["override_discount_pct"]
    )

    tx["rebate_pct"] = np.where(
        tx["customer_type"].eq("National Account"),
        rng.uniform(0.01, 0.04, N_TRANSACTIONS),
        rng.uniform(0.00, 0.015, N_TRANSACTIONS),
    )

    tx["freight_cost"] = np.where(
        tx["product_category"].eq("Heavy Equipment"),
        rng.uniform(35, 180, N_TRANSACTIONS),
        rng.uniform(1, 18, N_TRANSACTIONS),
    )

    tx["gross_revenue"] = tx["invoice_price"] * tx["quantity"]
    tx["gross_margin_dollars"] = (tx["invoice_price"] - tx["unit_cost"]) * tx["quantity"]

    tx["rebate_dollars"] = tx["gross_revenue"] * tx["rebate_pct"]
    tx["pocket_margin_dollars"] = (
        tx["gross_margin_dollars"] - tx["rebate_dollars"] - tx["freight_cost"]
    )

    tx["pocket_margin_pct"] = tx["pocket_margin_dollars"] / tx["gross_revenue"]

    money_cols = [
        "unit_cost",
        "list_price",
        "invoice_price",
        "freight_cost",
        "gross_revenue",
        "gross_margin_dollars",
        "rebate_dollars",
        "pocket_margin_dollars",
        "pocket_margin_pct",
    ]

    for col in money_cols:
        tx[col] = tx[col].round(4)

    return tx


def main() -> None:
    customers = generate_customers()
    products = generate_products()
    transactions = generate_transactions(customers, products)

    customers.to_csv(DATA_DIR / "customers.csv", index=False)
    products.to_csv(DATA_DIR / "products.csv", index=False)
    transactions.to_csv(DATA_DIR / "transactions.csv", index=False)

    print("Synthetic distributor pricing data generated.")
    print(f"Customers: {len(customers):,}")
    print(f"Products: {len(products):,}")
    print(f"Transactions: {len(transactions):,}")


if __name__ == "__main__":
    main()