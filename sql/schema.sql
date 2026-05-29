CREATE TABLE IF NOT EXISTS farmers (
    farmer_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    aadhaar TEXT UNIQUE NOT NULL,
    land_size_acres NUMERIC(10, 2) NOT NULL CHECK (land_size_acres >= 0),
    district TEXT NOT NULL,
    village TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dealers (
    dealer_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    district TEXT NOT NULL,
    license_number TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id BIGINT PRIMARY KEY,
    farmer_id BIGINT NOT NULL REFERENCES farmers(farmer_id),
    dealer_id BIGINT NOT NULL REFERENCES dealers(dealer_id),
    subsidy_type TEXT NOT NULL,
    quantity NUMERIC(12, 2) NOT NULL CHECK (quantity > 0),
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    date TIMESTAMP NOT NULL,
    season TEXT NOT NULL,
    crop_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fraud_flags (
    flag_id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('farmer', 'dealer')),
    entity_id BIGINT NOT NULL,
    reason TEXT NOT NULL,
    anomaly_score NUMERIC(5, 2) NOT NULL CHECK (anomaly_score >= 0),
    flagged_on TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_dealer_id ON transactions (dealer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_farmer_id ON transactions (farmer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (date);
CREATE INDEX IF NOT EXISTS idx_dealers_district ON dealers (district);
