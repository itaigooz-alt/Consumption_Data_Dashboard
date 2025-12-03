-- ================================================================
-- FACT_CONSUMPTION_DAILY_AGGREGATED TABLE
-- ================================================================
-- Purpose: Aggregated credits inflow and outflow by source and dimensions
-- Granularity: date, source, dimension buckets (NOT by distinct_id)
-- Update Frequency: Daily (processes last 30 days)
-- Partition: By date
-- ================================================================
-- OPTIMIZATION: Aggregated at dimension level instead of player level
-- This reduces table size significantly while maintaining all dashboard functionality
-- ================================================================

CREATE OR REPLACE TABLE `yotam-395120.peerplay.fact_consumption_daily_dashboard`
    PARTITION BY date
AS 

WITH inflow AS (
    SELECT
        e.date,
        e.distinct_id,
        mp_event_name AS source,
        'inflow' AS inflow_outflow,
        -- Aggregate dimensions
        CASE
            WHEN apd.first_chapter BETWEEN 0 AND 10 THEN '0-10'
            WHEN apd.first_chapter BETWEEN 11 AND 20 THEN '11-20'
            WHEN apd.first_chapter BETWEEN 21 AND 50 THEN '21-50'
            ELSE '50+'
        END AS first_chapter_bucket,
        CASE
            WHEN dp.first_country = 'US' THEN 1
            ELSE 0
        END AS is_us_player,
        CASE
            WHEN apd.last_credit_balance BETWEEN 0 AND 100 THEN '0-100'
            WHEN apd.last_credit_balance BETWEEN 101 AND 300 THEN '101-300'
            WHEN apd.last_credit_balance BETWEEN 301 AND 500 THEN '301-500'
            WHEN apd.last_credit_balance BETWEEN 501 AND 1000 THEN '501-1000'
            WHEN apd.last_credit_balance BETWEEN 1001 AND 3000 THEN '1001-3000'
            WHEN apd.last_credit_balance BETWEEN 3001 AND 5000 THEN '3001-5000'
            ELSE '5000+'
        END AS last_balance_bucket,
        COALESCE(apd.last_app_version, 0) AS last_version_of_day,
        CASE WHEN apd.total_purchase_revenue > 0 THEN 1 ELSE 0 END AS paid_today_flag,
        CASE WHEN dp.ltv_purchases > 0 THEN 1 ELSE 0 END AS paid_ever_flag,
        -- Metrics
        SUM(item_quantity_1) AS sum_value,
        COUNT(DISTINCT e.distinct_id) AS distinct_players,
        COUNT(*) AS cnt
    FROM `yotam-395120.peerplay.vmp_master_event_normalized` e
    INNER JOIN `yotam-395120.peerplay.agg_player_daily` apd
        ON e.date = apd.date
        AND e.distinct_id = apd.distinct_id
    LEFT JOIN `yotam-395120.peerplay.dim_player` dp
        ON e.distinct_id = dp.distinct_id
    WHERE e.date >= CURRENT_DATE - 14 AND e.date < CURRENT_DATE
      AND e.res_timestamp IS NOT NULL
      AND e.mp_event_name LIKE '%rewards%'
      AND LOWER(e.item_id_1_name) LIKE '%credits%'
      AND e.mp_country_code NOT IN ('UA', 'IL', 'AM')
      AND e.distinct_id NOT IN (SELECT distinct_id FROM `yotam-395120.peerplay.potential_fraudsters`)
      AND dp.first_country NOT IN ('UA', 'IL', 'AM')
    GROUP BY all
),

outflow AS (
    SELECT
        e.date,
        e.distinct_id,
        mp_event_name AS source,
        'outflow' AS inflow_outflow,
        -- Aggregate dimensions
        CASE
            WHEN apd.first_chapter BETWEEN 0 AND 10 THEN '0-10'
            WHEN apd.first_chapter BETWEEN 11 AND 20 THEN '11-20'
            WHEN apd.first_chapter BETWEEN 21 AND 50 THEN '21-50'
            ELSE '50+'
        END AS first_chapter_bucket,
        CASE
            WHEN dp.first_country = 'US' THEN 1
            ELSE 0
        END AS is_us_player,
        CASE
            WHEN apd.last_credit_balance BETWEEN 0 AND 100 THEN '0-100'
            WHEN apd.last_credit_balance BETWEEN 101 AND 300 THEN '101-300'
            WHEN apd.last_credit_balance BETWEEN 301 AND 500 THEN '301-500'
            WHEN apd.last_credit_balance BETWEEN 501 AND 1000 THEN '501-1000'
            WHEN apd.last_credit_balance BETWEEN 1001 AND 3000 THEN '1001-3000'
            WHEN apd.last_credit_balance BETWEEN 3001 AND 5000 THEN '3001-5000'
            ELSE '5000+'
        END AS last_balance_bucket,
        COALESCE(apd.last_app_version, 0) AS last_version_of_day,
        CASE WHEN apd.total_purchase_revenue > 0 THEN 1 ELSE 0 END AS paid_today_flag,
        CASE WHEN dp.ltv_purchases > 0 THEN 1 ELSE 0 END AS paid_ever_flag,
        -- Metrics
        (SUM(IFNULL(e.delta_credits, 0)) * -1) + SUM(IFNULL(e.bubble_cost, 0)) AS sum_value,
        COUNT(DISTINCT e.distinct_id) AS distinct_players,
        SUM(
            CASE
                WHEN e.number_of_events IS NULL AND e.delta_credits IS NOT NULL
                    THEN (e.delta_credits / CASE WHEN e.mode_status = 3 THEN 6 ELSE (e.mode_status + 1) END) * -1
                ELSE IFNULL(e.number_of_events, 0)
            END
        ) + SUM(CASE WHEN e.mp_event_name = 'click_bubble_purchase' THEN 1 ELSE 0 END) AS cnt
    FROM `yotam-395120.peerplay.vmp_master_event_normalized` e
    INNER JOIN `yotam-395120.peerplay.agg_player_daily` apd
        ON e.date = apd.date
        AND e.distinct_id = apd.distinct_id
    LEFT JOIN `yotam-395120.peerplay.dim_player` dp
        ON e.distinct_id = dp.distinct_id
    WHERE e.date >= CURRENT_DATE - 14 AND e.date < CURRENT_DATE
      AND e.res_timestamp IS NOT NULL
      AND e.mp_event_name IN ('generation', 'click_bubble_purchase')
      AND e.mp_country_code NOT IN ('UA', 'IL', 'AM')
      AND e.distinct_id NOT IN (SELECT distinct_id FROM `yotam-395120.peerplay.potential_fraudsters`)
      AND dp.first_country NOT IN ('UA', 'IL', 'AM')
    GROUP BY all 
),

combine AS (
    SELECT * FROM inflow
    UNION ALL
    SELECT * FROM outflow
), 

-- Pivot sources into columns: per dimension combination, get sum_value and cnt for each source
source_pivoted AS (
    SELECT
        date,
        distinct_id,
        first_chapter_bucket,
        is_us_player,
        last_balance_bucket,
        last_version_of_day,
        paid_today_flag,
        paid_ever_flag,
        -- Pivot sum_value by source (inflow sources - all 18 sources)
        SUM(CASE WHEN source = 'rewards_race' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_race_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_store' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_store_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_rolling_offer_collect' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_rolling_offer_collect_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_board_task' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_board_task_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_harvest_collect' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_harvest_collect_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_missions_total' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_missions_total_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_recipes' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_recipes_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_flowers' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_flowers_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_rewarded_video' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_rewarded_video_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_disco' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_disco_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_timed_task' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_timed_task_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_sell_board_item' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_sell_board_item_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_mass_compensation' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_mass_compensation_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_missions_task' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_missions_task_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_album_set_completion' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_album_set_completion_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_self_collectable' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_self_collectable_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_eoc' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_eoc_inflow_sum_value,
        SUM(CASE WHEN source = 'rewards_frenzy_non_jackpot' AND inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS rewards_frenzy_non_jackpot_inflow_sum_value,
        -- Pivot cnt by source (inflow sources - all 18 sources)
        SUM(CASE WHEN source = 'rewards_race' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_race_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_store' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_store_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_rolling_offer_collect' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_rolling_offer_collect_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_board_task' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_board_task_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_harvest_collect' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_harvest_collect_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_missions_total' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_missions_total_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_recipes' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_recipes_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_flowers' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_flowers_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_rewarded_video' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_rewarded_video_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_disco' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_disco_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_timed_task' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_timed_task_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_sell_board_item' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_sell_board_item_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_mass_compensation' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_mass_compensation_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_missions_task' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_missions_task_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_album_set_completion' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_album_set_completion_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_self_collectable' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_self_collectable_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_eoc' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_eoc_inflow_cnt,
        SUM(CASE WHEN source = 'rewards_frenzy_non_jackpot' AND inflow_outflow = 'inflow' THEN cnt ELSE 0 END) AS rewards_frenzy_non_jackpot_inflow_cnt,
        -- Pivot sum_value by source (outflow sources - 2 sources)
        SUM(CASE WHEN source = 'generation' AND inflow_outflow = 'outflow' THEN sum_value ELSE 0 END) AS generation_outflow_sum_value,
        SUM(CASE WHEN source = 'click_bubble_purchase' AND inflow_outflow = 'outflow' THEN sum_value ELSE 0 END) AS click_bubble_purchase_outflow_sum_value,
        -- Pivot cnt by source (outflow sources - 2 sources)
        SUM(CASE WHEN source = 'generation' AND inflow_outflow = 'outflow' THEN cnt ELSE 0 END) AS generation_outflow_cnt,
        SUM(CASE WHEN source = 'click_bubble_purchase' AND inflow_outflow = 'outflow' THEN cnt ELSE 0 END) AS click_bubble_purchase_outflow_cnt
    FROM combine
    WHERE date >= CURRENT_DATE - 14 AND date < CURRENT_DATE
    GROUP BY ALL 
)

-- Final output: Pivoted by source (sources as columns instead of rows)
SELECT
    date,
    first_chapter_bucket,
    is_us_player,
    last_balance_bucket,
    last_version_of_day,
    paid_today_flag,
    paid_ever_flag,
    count(distinct distinct_id) as players,
    -- Inflow sources (as columns) - all 18 sources
    sum(rewards_race_inflow_sum_value) as rewards_race_inflow_sum_value,
    sum(rewards_race_inflow_cnt) as rewards_race_inflow_cnt,
    sum(rewards_store_inflow_sum_value) as rewards_store_inflow_sum_value,
    sum(rewards_store_inflow_cnt) as rewards_store_inflow_cnt,
    sum(rewards_rolling_offer_collect_inflow_sum_value) as rewards_rolling_offer_collect_inflow_sum_value,
    sum(rewards_rolling_offer_collect_inflow_cnt) as rewards_rolling_offer_collect_inflow_cnt,
    sum(rewards_board_task_inflow_sum_value) as rewards_board_task_inflow_sum_value,
    sum(rewards_board_task_inflow_cnt) as rewards_board_task_inflow_cnt,
    sum(rewards_harvest_collect_inflow_sum_value) as rewards_harvest_collect_inflow_sum_value,
    sum(rewards_harvest_collect_inflow_cnt) as rewards_harvest_collect_inflow_cnt,
    sum(rewards_missions_total_inflow_sum_value) as rewards_missions_total_inflow_sum_value,
    sum(rewards_missions_total_inflow_cnt) as rewards_missions_total_inflow_cnt,
    sum(rewards_recipes_inflow_sum_value) as rewards_recipes_inflow_sum_value,
    sum(rewards_recipes_inflow_cnt) as rewards_recipes_inflow_cnt,
    sum(rewards_flowers_inflow_sum_value) as rewards_flowers_inflow_sum_value,
    sum(rewards_flowers_inflow_cnt) as rewards_flowers_inflow_cnt,
    sum(rewards_rewarded_video_inflow_sum_value) as rewards_rewarded_video_inflow_sum_value,
    sum(rewards_rewarded_video_inflow_cnt) as rewards_rewarded_video_inflow_cnt,
    sum(rewards_disco_inflow_sum_value) as rewards_disco_inflow_sum_value,
    sum(rewards_disco_inflow_cnt) as rewards_disco_inflow_cnt,
    sum(rewards_timed_task_inflow_sum_value) as rewards_timed_task_inflow_sum_value,
    sum(rewards_timed_task_inflow_cnt) as rewards_timed_task_inflow_cnt,
    sum(rewards_sell_board_item_inflow_sum_value) as rewards_sell_board_item_inflow_sum_value,
    sum(rewards_sell_board_item_inflow_cnt) as rewards_sell_board_item_inflow_cnt,
    sum(rewards_mass_compensation_inflow_sum_value) as rewards_mass_compensation_inflow_sum_value,
    sum(rewards_mass_compensation_inflow_cnt) as rewards_mass_compensation_inflow_cnt,
    sum(rewards_missions_task_inflow_sum_value) as rewards_missions_task_inflow_sum_value,
    sum(rewards_missions_task_inflow_cnt) as rewards_missions_task_inflow_cnt,
    sum(rewards_album_set_completion_inflow_sum_value) as rewards_album_set_completion_inflow_sum_value,
    sum(rewards_album_set_completion_inflow_cnt) as rewards_album_set_completion_inflow_cnt,
    sum(rewards_self_collectable_inflow_sum_value) as rewards_self_collectable_inflow_sum_value,
    sum(rewards_self_collectable_inflow_cnt) as rewards_self_collectable_inflow_cnt,
    sum(rewards_eoc_inflow_sum_value) as rewards_eoc_inflow_sum_value,
    sum(rewards_eoc_inflow_cnt) as rewards_eoc_inflow_cnt,
    sum(rewards_frenzy_non_jackpot_inflow_sum_value) as rewards_frenzy_non_jackpot_inflow_sum_value,
    sum(rewards_frenzy_non_jackpot_inflow_cnt) as rewards_frenzy_non_jackpot_inflow_cnt,
    -- Outflow sources (as columns) - 2 sources
    sum(generation_outflow_sum_value) as generation_outflow_sum_value,
    sum(generation_outflow_cnt) as generation_outflow_cnt,
    sum(click_bubble_purchase_outflow_sum_value) as click_bubble_purchase_outflow_sum_value,
    sum(click_bubble_purchase_outflow_cnt) as click_bubble_purchase_outflow_cnt,
    -- Calculated totals
    -- Total inflow: sum of all inflow sources
    (rewards_race_inflow_sum_value +
     rewards_store_inflow_sum_value +
     rewards_rolling_offer_collect_inflow_sum_value +
     rewards_board_task_inflow_sum_value +
     rewards_harvest_collect_inflow_sum_value +
     rewards_missions_total_inflow_sum_value +
     rewards_recipes_inflow_sum_value +
     rewards_flowers_inflow_sum_value +
     rewards_rewarded_video_inflow_sum_value +
     rewards_disco_inflow_sum_value +
     rewards_timed_task_inflow_sum_value +
     rewards_sell_board_item_inflow_sum_value +
     rewards_mass_compensation_inflow_sum_value +
     rewards_missions_task_inflow_sum_value +
     rewards_album_set_completion_inflow_sum_value +
     rewards_self_collectable_inflow_sum_value +
     rewards_eoc_inflow_sum_value +
     rewards_frenzy_non_jackpot_inflow_sum_value) AS total_inflow,
    -- Total free inflow: all inflow sources EXCEPT rewards_store and rewards_rolling_offer_collect
    (rewards_race_inflow_sum_value +
     rewards_board_task_inflow_sum_value +
     rewards_harvest_collect_inflow_sum_value +
     rewards_missions_total_inflow_sum_value +
     rewards_recipes_inflow_sum_value +
     rewards_flowers_inflow_sum_value +
     rewards_rewarded_video_inflow_sum_value +
     rewards_timed_task_inflow_sum_value +
     rewards_sell_board_item_inflow_sum_value +
     rewards_mass_compensation_inflow_sum_value +
     rewards_missions_task_inflow_sum_value +
     rewards_album_set_completion_inflow_sum_value +
     rewards_self_collectable_inflow_sum_value +
     rewards_eoc_inflow_sum_value +
     rewards_frenzy_non_jackpot_inflow_sum_value) AS total_free_inflow,
    -- Total paid inflow: rewards_store and rewards_rolling_offer_collect only
    (rewards_store_inflow_sum_value +
     rewards_rolling_offer_collect_inflow_sum_value+rewards_disco_inflow_sum_value) AS total_paid_inflow,
    -- Total outflow: sum of all outflow sources (already calculated as total_outflow_per_dimension_per_day, but adding explicit calculation)
    (generation_outflow_sum_value +
     click_bubble_purchase_outflow_sum_value) AS total_outflow
FROM source_pivoted
WHERE date >= CURRENT_DATE - 14 AND date < CURRENT_DATE
GROUP BY ALL ;
