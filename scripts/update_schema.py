"""Migration script to add missing tables to PostgreSQL for AgriShield."""
import sys
from pathlib import Path
import psycopg2

sys.path.append(str(Path(__file__).parent.parent / "src"))
from database import get_connection

def main():
    print("Creating investigations and audit_logs tables...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Create investigations table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS investigations (
                    investigation_id BIGSERIAL PRIMARY KEY,
                    dealer_id BIGINT NOT NULL,
                    txn_id BIGINT,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    assigned_to TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            # Create audit_logs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id BIGSERIAL PRIMARY KEY,
                    user_id TEXT,
                    user_email TEXT,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id BIGINT NOT NULL,
                    details JSONB,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            # Create indices
            cur.execute("CREATE INDEX IF NOT EXISTS idx_investigations_dealer_id ON investigations(dealer_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);")
        
        conn.commit()
        print("Successfully created tables!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
