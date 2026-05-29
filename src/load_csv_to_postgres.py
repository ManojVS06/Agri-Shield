from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values

from database import DatabaseConfig, get_connection


def _read_source_frames(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    farmers = pd.read_csv(data_dir / "farmers.csv")
    dealers = pd.read_csv(data_dir / "dealers.csv")
    transactions = pd.read_csv(data_dir / "transactions.csv")
    return farmers, dealers, transactions


def _transform_frames(
    farmers: pd.DataFrame,
    dealers: pd.DataFrame,
    transactions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    farmers_t = farmers.loc[
        :,
        [
            "farmer_id",
            "name",
            "district",
            "village",
            "land_size_acres",
            "crop_type",
            "income_category",
            "farmer_location_lat",
            "farmer_location_long",
        ],
    ].copy()

    dealers_t = dealers.loc[
        :,
        [
            "dealer_id",
            "dealer_name",
            "district",
            "license_number",
            "shop_size",
            "years_active",
            "gst_number",
            "avg_daily_sales",
            "dealer_location_lat",
            "dealer_location_long",
        ],
    ].copy()

    transactions_t = transactions.loc[
        :,
        [
            "txn_id",
            "farmer_id",
            "dealer_id",
            "subsidy_type",
            "product_type",
            "quantity",
            "subsidy_amount",
            "actual_price",
            "date",
            "season",
            "crop_type",
            "payment_mode",
            "district",
            "land_size_acres",
            "distance_farmer_dealer",
            "transaction_hour",
            "day_of_week",
            "transaction_month",
            "is_fraud",
            "fraud_type",
            "fraud_reason",
            "risk_score",
        ],
    ].copy()
    transactions_t["date"] = pd.to_datetime(transactions_t["date"], errors="raise")

    return farmers_t, dealers_t, transactions_t


def _insert_dataframe(cursor, table_name: str, df: pd.DataFrame) -> None:
    if df.empty:
        return

    columns = list(df.columns)
    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]
    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES %s"
    execute_values(cursor, sql, rows, page_size=1000)


def load_csv_to_postgres(
    data_dir: Path,
    config: DatabaseConfig | None = None,
    truncate: bool = True,
) -> dict[str, int]:
    farmers, dealers, transactions = _read_source_frames(data_dir)
    farmers_t, dealers_t, transactions_t = _transform_frames(farmers, dealers, transactions)

    with get_connection(config) as conn:
        with conn.cursor() as cursor:
            if truncate:
                cursor.execute("TRUNCATE TABLE transactions, fraud_flags, farmers, dealers RESTART IDENTITY CASCADE;")

            _insert_dataframe(cursor, "farmers", farmers_t)
            _insert_dataframe(cursor, "dealers", dealers_t)
            _insert_dataframe(cursor, "transactions", transactions_t)

    return {
        "farmers": len(farmers_t),
        "dealers": len(dealers_t),
        "transactions": len(transactions_t),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load generated CSV files into PostgreSQL core tables.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Directory containing farmers.csv, dealers.csv, transactions.csv")
    parser.add_argument("--no-truncate", action="store_true", help="Do not truncate target tables before inserting rows")
    args = parser.parse_args()

    counts = load_csv_to_postgres(data_dir=args.data_dir, truncate=not args.no_truncate)
    print(f"Loaded farmers: {counts['farmers']}")
    print(f"Loaded dealers: {counts['dealers']}")
    print(f"Loaded transactions: {counts['transactions']}")


if __name__ == "__main__":
    main()
