"""Helpers for working with PostgreSQL fraud detection outputs."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extensions import connection as PgConnection

# Load backend environment variables if present
backend_env = Path(__file__).parent.parent / "backend" / ".env"
if backend_env.exists():
    load_dotenv(backend_env)
else:
    load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "agri_subsidy")
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    def __post_init__(self):
        # Override with DATABASE_URL values if available
        db_url = os.getenv("DATABASE_URL")
        if db_url and db_url.startswith("postgresql"):
            try:
                parsed = urlparse(db_url)
                # Use object.__setattr__ to modify frozen dataclass fields
                object.__setattr__(self, "user", parsed.username or self.user)
                if parsed.password:
                    object.__setattr__(self, "password", unquote(parsed.password))
                object.__setattr__(self, "host", parsed.hostname or self.host)
                if parsed.port:
                    object.__setattr__(self, "port", int(parsed.port))
                if parsed.path:
                    object.__setattr__(self, "database", parsed.path.lstrip("/"))
            except Exception as e:
                print(f"[DB] Error parsing DATABASE_URL: {e}")


def get_connection(config: DatabaseConfig | None = None) -> PgConnection:
    settings = config or DatabaseConfig()
    return psycopg2.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.database,
        user=settings.user,
        password=settings.password,
    )


def run_dealer_anomaly_refresh(config: DatabaseConfig | None = None) -> int:
    """Refresh dealer fraud flags inside PostgreSQL and return inserted rows."""

    with get_connection(config) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT refresh_dealer_fraud_flags();")
            return int(cursor.fetchone()[0])


def load_flagged_dealers(config: DatabaseConfig | None = None) -> pd.DataFrame:
    query = """
        SELECT
            entity_id AS dealer_id,
            reason,
            anomaly_score,
            flagged_on
        FROM fraud_flags
        WHERE entity_type = 'dealer'
        ORDER BY flagged_on DESC, anomaly_score DESC;
    """

    with get_connection(config) as conn:
        return pd.read_sql_query(query, conn)


def load_anomaly_view(config: DatabaseConfig | None = None) -> pd.DataFrame:
    query = "SELECT * FROM dealer_anomaly_scores ORDER BY anomaly_score DESC, total_transactions DESC;"

    with get_connection(config) as conn:
        return pd.read_sql_query(query, conn)
