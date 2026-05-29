CREATE OR REPLACE VIEW dealer_anomaly_scores AS
WITH dealer_stats AS (
    SELECT
        d.dealer_id,
        d.dealer_name,
        d.district,
        COUNT(t.txn_id) AS total_transactions,
        COUNT(DISTINCT t.farmer_id) AS unique_farmers,
        AVG(t.subsidy_amount) AS avg_subsidy_amount,
        STDDEV_POP(t.subsidy_amount) AS subsidy_amount_stddev,
        MAX(t.date) AS last_transaction_date
    FROM dealers d
    LEFT JOIN transactions t ON t.dealer_id = d.dealer_id
    GROUP BY d.dealer_id, d.dealer_name, d.district
),
district_stats AS (
    SELECT
        district,
        AVG(total_transactions) AS district_avg_transactions,
        AVG(unique_farmers) AS district_avg_unique_farmers
    FROM dealer_stats
    GROUP BY district
),
scored AS (
    SELECT
        ds.dealer_id,
        ds.dealer_name,
        ds.district,
        ds.total_transactions,
        ds.unique_farmers,
        dtx.district_avg_transactions,
        dtx.district_avg_unique_farmers,
        ds.avg_subsidy_amount,
        ds.subsidy_amount_stddev,
        CASE
            WHEN dtx.district_avg_transactions IS NULL OR dtx.district_avg_transactions = 0 THEN 0
            ELSE ROUND((ds.total_transactions / dtx.district_avg_transactions)::numeric, 2)
        END AS transaction_ratio,
        CASE
            WHEN ds.total_transactions = 0 THEN 0
            ELSE ROUND((ds.unique_farmers::numeric / ds.total_transactions)::numeric, 2)
        END AS farmer_diversity_ratio
    FROM dealer_stats ds
    JOIN district_stats dtx USING (district)
)
SELECT
    dealer_id,
    dealer_name,
    district,
    total_transactions,
    unique_farmers,
    district_avg_transactions,
    district_avg_unique_farmers,
    avg_subsidy_amount,
    subsidy_amount_stddev,
    transaction_ratio,
    farmer_diversity_ratio,
    LEAST(
        100,
        ROUND(
            (
                CASE WHEN transaction_ratio > 2 THEN 45 ELSE 0 END +
                CASE WHEN farmer_diversity_ratio < 0.5 THEN 25 ELSE 0 END +
                CASE WHEN total_transactions >= 20 AND total_transactions > 3 * COALESCE(district_avg_transactions, 0) THEN 20 ELSE 0 END +
                CASE WHEN subsidy_amount_stddev IS NOT NULL AND subsidy_amount_stddev > avg_subsidy_amount THEN 10 ELSE 0 END
            )::numeric,
            2
        )
    ) AS anomaly_score,
    CASE
        WHEN total_transactions = 0 THEN 'No transactions recorded'
        WHEN transaction_ratio > 2 AND farmer_diversity_ratio < 0.5 THEN 'Dealer serves unusually many transactions with low farmer diversity'
        WHEN transaction_ratio > 2 THEN 'Dealer transaction volume is above district average'
        WHEN farmer_diversity_ratio < 0.5 THEN 'Dealer repeatedly serves the same farmers'
        WHEN subsidy_amount_stddev IS NOT NULL AND subsidy_amount_stddev > avg_subsidy_amount THEN 'Unusually volatile subsidy amounts'
        ELSE 'Normal'
    END AS reason,
    NOW() AS flagged_on
FROM scored;

CREATE OR REPLACE FUNCTION refresh_dealer_fraud_flags()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    inserted_rows INTEGER;
BEGIN
    DELETE FROM fraud_flags
    WHERE entity_type = 'dealer';

    INSERT INTO fraud_flags (entity_type, entity_id, reason, anomaly_score, flagged_on)
    SELECT
        'dealer' AS entity_type,
        dealer_id AS entity_id,
        reason,
        anomaly_score,
        flagged_on
    FROM dealer_anomaly_scores
    WHERE anomaly_score >= 50
      AND reason <> 'Normal';

    GET DIAGNOSTICS inserted_rows = ROW_COUNT;
    RETURN inserted_rows;
END;
$$;

CREATE OR REPLACE VIEW suspicious_dealers_basic AS
WITH dealer_counts AS (
    SELECT
        dealer_id,
        COUNT(farmer_id) AS total_farmers
    FROM transactions
    GROUP BY dealer_id
),
avg_counts AS (
    SELECT AVG(total_farmers) AS avg_farmers_per_dealer
    FROM dealer_counts
)
SELECT
    dc.dealer_id,
    dc.total_farmers,
    ac.avg_farmers_per_dealer,
    ROUND((dc.total_farmers - ac.avg_farmers_per_dealer)::numeric, 2) AS excess_volume,
    NOW() AS flagged_on
FROM dealer_counts dc
CROSS JOIN avg_counts ac
WHERE dc.total_farmers > 2 * ac.avg_farmers_per_dealer;
