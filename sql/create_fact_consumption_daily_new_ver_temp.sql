-- ================================================================
-- FACT_CONSUMPTION_DAILY_NEW_VER_TEMP TABLE
-- ================================================================
-- Purpose: Documents credits inflow and outflow by source
-- Granularity: date, distinct_id, source (mp_event_name)
-- Update Frequency: Daily (processes last 7 days)
-- Partition: By date
-- ================================================================

CREATE OR REPLACE TABLE `yotam-395120.peerplay.fact_consumption_daily_new_ver_temp`
    PARTITION BY date
AS 

WITH inflow AS (
    SELECT
        date,
        distinct_id,
        'inflow' AS inflow_outflow,
        mp_event_name AS source,
        SUM(item_quantity_1) AS sum_value,
        COUNT(*) AS cnt
    FROM `yotam-395120.peerplay.vmp_master_event_normalized`
    WHERE date >= CURRENT_DATE - 7
      AND res_timestamp IS NOT NULL
      AND mp_event_name LIKE '%rewards%'
      AND LOWER(item_id_1_name) LIKE '%credits%'
      AND mp_country_code NOT IN ('UA', 'IL', 'AM')
      AND distinct_id NOT IN (SELECT distinct_id FROM `yotam-395120.peerplay.potential_fraudsters`)
    GROUP BY date, distinct_id, mp_event_name
),

outflow AS (
    SELECT
        date,
        distinct_id,
        'outflow' AS inflow_outflow,
        mp_event_name AS source,
        (SUM(IFNULL(delta_credits, 0)) * -1) + SUM(IFNULL(bubble_cost, 0)) AS sum_value,
        SUM(
            CASE
                WHEN number_of_events IS NULL AND delta_credits IS NOT NULL
                    THEN (delta_credits / CASE WHEN mode_status = 3 THEN 6 ELSE (mode_status + 1) END) * -1
                ELSE IFNULL(number_of_events, 0)
            END
        ) + SUM(CASE WHEN mp_event_name = 'click_bubble_purchase' THEN 1 ELSE 0 END) AS cnt
    FROM `yotam-395120.peerplay.vmp_master_event_normalized`
    WHERE date >= CURRENT_DATE - 7
      AND res_timestamp IS NOT NULL
      AND mp_event_name IN ('generation', 'click_bubble_purchase')
      AND mp_country_code NOT IN ('UA', 'IL', 'AM')
      AND distinct_id NOT IN (SELECT distinct_id FROM `yotam-395120.peerplay.potential_fraudsters`)
    GROUP BY date, distinct_id, mp_event_name
),

combine AS (
    SELECT * FROM inflow
    UNION ALL
    SELECT * FROM outflow
),

-- Get dimensions from aggregated tables
player_dimensions AS (
    SELECT
        apd.date,
        apd.distinct_id,
        -- New Dimension: Player's first chapter of the day
        apd.first_chapter AS first_chapter_of_day,
        -- New Dimension: Flag if player paid today
        CASE
            WHEN apd.total_purchase_revenue > 0 THEN 1
            ELSE 0
        END AS paid_today_flag,
        -- New Dimension: Last version of the day
        apd.last_platform AS last_platform_of_day,
        -- Note: Using last_platform as proxy. If you need version_float specifically,
        -- you may need to get it from the raw events table
        -- New Dimension: Flag if player paid ever (from dim_player)
        CASE
            WHEN dp.ltv_purchases > 0 THEN 1
            ELSE 0
        END AS paid_ever_flag,
        -- New Dimension: Is US player
        CASE
            WHEN dp.first_country = 'US' THEN 1
            ELSE 0
        END AS is_us_player,
        -- New KPI: Last balance of the day
        apd.last_credit_balance AS last_balance_of_day,
        apd.last_app_version as last_version_of_day
    FROM `yotam-395120.peerplay.agg_player_daily` apd
    LEFT JOIN `yotam-395120.peerplay.dim_player` dp
        ON apd.distinct_id = dp.distinct_id
    WHERE apd.date >= CURRENT_DATE - 7
      AND dp.first_country NOT IN ('UA', 'IL', 'AM')
      AND apd.distinct_id NOT IN (SELECT distinct_id FROM `yotam-395120.peerplay.potential_fraudsters`)
)

-- Final output with all dimensions and KPIs
SELECT
    c.*,
    -- Original metric
    SUM(CASE
        WHEN c.inflow_outflow = 'outflow' THEN c.sum_value
        ELSE 0
    END) OVER (PARTITION BY c.date, c.distinct_id) AS total_outflow_per_player_per_day,
    -- New Dimensions
    pd.first_chapter_of_day,
    pd.paid_today_flag,
    pd.paid_ever_flag,
    pd.is_us_player,
    COALESCE(pd.last_version_of_day, 0) AS last_version_of_day,
    -- New KPI
    pd.last_balance_of_day
FROM combine c
LEFT JOIN player_dimensions pd
    ON c.date = pd.date
    AND c.distinct_id = pd.distinct_id
WHERE c.date >= CURRENT_DATE - 7;

