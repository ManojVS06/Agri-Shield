from __future__ import annotations

from database import get_connection, run_dealer_anomaly_refresh


def _single_value(cursor, query: str):
    cursor.execute(query)
    return cursor.fetchone()[0]


def validate_pipeline() -> None:
    inserted = run_dealer_anomaly_refresh()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            farmers_count = int(_single_value(cursor, "SELECT COUNT(*) FROM farmers;"))
            dealers_count = int(_single_value(cursor, "SELECT COUNT(*) FROM dealers;"))
            transactions_count = int(_single_value(cursor, "SELECT COUNT(*) FROM transactions;"))
            anomaly_rows = int(_single_value(cursor, "SELECT COUNT(*) FROM dealer_anomaly_scores;"))
            suspicious_rows = int(_single_value(cursor, "SELECT COUNT(*) FROM suspicious_dealers_basic;"))
            flagged_rows = int(_single_value(cursor, "SELECT COUNT(*) FROM fraud_flags WHERE entity_type = 'dealer';"))
            invalid_flags = int(
                _single_value(
                    cursor,
                    """
                    SELECT COUNT(*)
                    FROM fraud_flags
                    WHERE entity_type = 'dealer'
                      AND (anomaly_score < 50 OR reason = 'Normal');
                    """,
                )
            )

    assert farmers_count > 0, "No farmer rows loaded"
    assert dealers_count > 0, "No dealer rows loaded"
    assert transactions_count > 0, "No transaction rows loaded"
    assert anomaly_rows == dealers_count, "Anomaly view row count should match dealer count"
    assert invalid_flags == 0, "Invalid dealer flags found (score < 50 or reason Normal)"

    print("Pipeline validation passed")
    print(f"Farmers: {farmers_count}")
    print(f"Dealers: {dealers_count}")
    print(f"Transactions: {transactions_count}")
    print(f"Anomaly rows: {anomaly_rows}")
    print(f"Suspicious dealers (basic view): {suspicious_rows}")
    print(f"Flagged dealers inserted by refresh: {inserted}")
    print(f"Flagged dealers currently in fraud_flags: {flagged_rows}")


if __name__ == "__main__":
    validate_pipeline()
