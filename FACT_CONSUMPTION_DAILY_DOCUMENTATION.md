# FACT_CONSUMPTION_DAILY_NEW_VER_TEMP - Complete Documentation

**Table Name**: `fact_consumption_daily_new_ver_temp`  
**Purpose**: Documents credits inflow and outflow by source  
**Granularity**: `date`, `distinct_id`, `source` (mp_event_name)  
**Update Frequency**: Daily (processes last 7 days)  
**Partitioning**: By `date`  
**Source Tables**: 
- `vmp_master_event_normalized` (raw events)
- `agg_player_daily` (player daily aggregations)
- `dim_player` (player dimensions)

---

## Table of Contents

1. [Overview](#overview)
2. [Schema](#schema)
3. [Business Logic](#business-logic)
4. [SQL Implementation](#sql-implementation)
5. [Key Fields Explained](#key-fields-explained)
6. [Data Flow](#data-flow)
7. [Business Rules](#business-rules)

---

## Overview

This table tracks **credits inflow and outflow** at a daily granularity, broken down by:
- **Date**: The day of the transaction
- **Player**: `distinct_id`
- **Source**: The event name (`mp_event_name`) that generated the inflow/outflow
- **Direction**: Whether it's an `inflow` (credits gained) or `outflow` (credits spent)

### Key Characteristics

- **Tracks both directions**: Inflow (rewards) and Outflow (spending)
- **Source-level granularity**: Each row represents one source of inflow/outflow
- **Daily aggregation**: One row per player per day per source
- **Enriched with dimensions**: Includes player attributes from aggregated tables
- **Fraud filtering**: Excludes fraudsters and specific countries

---

## Schema

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `date` | DATE | Date of the transaction (partition key) |
| `distinct_id` | STRING | Player identifier |
| `inflow_outflow` | STRING | Direction: 'inflow' or 'outflow' |
| `source` | STRING | Event name that generated the flow (mp_event_name) |
| `sum_value` | FLOAT64 | Total credits amount (positive for inflow, negative for outflow) |
| `cnt` | INT64 | Count of events/transactions |

### Calculated Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_outflow_per_player_per_day` | FLOAT64 | Total outflow for player on this day (window function) |

### Dimension Fields (from player_dimensions)

| Field | Type | Description |
|-------|------|-------------|
| `first_chapter_of_day` | INT64 | Player's first chapter reached on this day |
| `paid_today_flag` | INT64 | 1 if player made a purchase today, 0 otherwise |
| `paid_ever_flag` | INT64 | 1 if player has ever made a purchase, 0 otherwise |
| `is_us_player` | INT64 | 1 if player's first country is US, 0 otherwise |
| `last_version_of_day` | STRING | Last app version used on this day |
| `last_balance_of_day` | FLOAT64 | Player's credit balance at end of day |

---

## Business Logic

### Inflow (Credits Gained)

**Source Events**: All events where `mp_event_name LIKE '%rewards%'`

**Logic**:
- Sum of `item_quantity_1` where `item_id_1_name` contains 'credits'
- Represents credits gained from rewards

**Example Sources**:
- `rewards_race` - Credits from race rewards
- `rewards_daily` - Daily rewards
- `rewards_level_up` - Level up rewards
- Any other reward events

### Outflow (Credits Spent)

**Source Events**: 
- `generation` - Credits spent on generating items
- `click_bubble_purchase` - Credits spent on bubble purchases

**Logic**:
```sql
sum_value = (SUM(delta_credits) * -1) + SUM(bubble_cost)
```

**Count Calculation**:
- For `generation`: Uses `number_of_events` if available
- If `number_of_events` is NULL: Calculates as `delta_credits / (mode_status + 1)` (or 6 if mode_status = 3)
- For `click_bubble_purchase`: Adds 1 per event
- Final count = generation count + bubble purchase count

**Special Logic**:
- `delta_credits` is negated (multiplied by -1) to represent outflow
- `bubble_cost` is added directly (already represents cost)
- `mode_status` affects the count calculation for generation events

---

## SQL Implementation

### Step 1: Inflow CTE

Captures all credits gained from reward events:

```sql
inflow AS (
    SELECT
        date,
        distinct_id,
        'inflow' AS inflow_outflow,
        mp_event_name AS source,
        SUM(item_quantity_1) AS sum_value,
        COUNT(*) AS cnt
    FROM vmp_master_event_normalized
    WHERE date >= CURRENT_DATE - 7
      AND mp_event_name LIKE '%rewards%'
      AND LOWER(item_id_1_name) LIKE '%credits%'
      -- Filters: fraudsters, countries
    GROUP BY date, distinct_id, mp_event_name
)
```

### Step 2: Outflow CTE

Captures all credits spent on generation and bubble purchases:

```sql
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
    FROM vmp_master_event_normalized
    WHERE date >= CURRENT_DATE - 7
      AND mp_event_name IN ('generation', 'click_bubble_purchase')
      -- Filters: fraudsters, countries
    GROUP BY date, distinct_id, mp_event_name
)
```

### Step 3: Combine CTE

Unions inflow and outflow:

```sql
combine AS (
    SELECT * FROM inflow
    UNION ALL
    SELECT * FROM outflow
)
```

### Step 4: Player Dimensions CTE

Enriches data with player attributes from aggregated tables:

```sql
player_dimensions AS (
    SELECT
        apd.date,
        apd.distinct_id,
        apd.first_chapter AS first_chapter_of_day,
        CASE WHEN apd.total_purchase_revenue > 0 THEN 1 ELSE 0 END AS paid_today_flag,
        apd.last_platform AS last_platform_of_day,
        CASE WHEN dp.ltv_purchases > 0 THEN 1 ELSE 0 END AS paid_ever_flag,
        CASE WHEN dp.first_country = 'US' THEN 1 ELSE 0 END AS is_us_player,
        apd.last_credit_balance AS last_balance_of_day,
        apd.last_app_version AS last_version_of_day
    FROM agg_player_daily apd
    LEFT JOIN dim_player dp ON apd.distinct_id = dp.distinct_id
    WHERE apd.date >= CURRENT_DATE - 7
      -- Filters: fraudsters, countries
)
```

### Step 5: Final SELECT

Combines everything and adds window function for total outflow:

```sql
SELECT
    c.*,
    SUM(CASE WHEN c.inflow_outflow = 'outflow' THEN c.sum_value ELSE 0 END) 
        OVER (PARTITION BY c.date, c.distinct_id) AS total_outflow_per_player_per_day,
    pd.first_chapter_of_day,
    pd.paid_today_flag,
    pd.paid_ever_flag,
    pd.is_us_player,
    COALESCE(pd.last_version_of_day, 0) AS last_version_of_day,
    pd.last_balance_of_day
FROM combine c
LEFT JOIN player_dimensions pd
    ON c.date = pd.date AND c.distinct_id = pd.distinct_id
WHERE c.date >= CURRENT_DATE - 7
```

---

## Key Fields Explained

### sum_value

- **Inflow**: Positive value representing credits gained
- **Outflow**: Negative value representing credits spent
- **Calculation**:
  - Inflow: `SUM(item_quantity_1)` from reward events
  - Outflow: `(SUM(delta_credits) * -1) + SUM(bubble_cost)`

### cnt

- **Inflow**: Count of reward events
- **Outflow**: Count of spending events (with special logic for generation)

### total_outflow_per_player_per_day

- **Window function** that calculates total outflow per player per day
- Sums all outflow `sum_value` for a player on a given day
- Same value repeated for each source row (for that player/day)

### first_chapter_of_day

- Player's first chapter reached on this day
- From `agg_player_daily.first_chapter`

### paid_today_flag

- Binary flag: 1 if player made any purchase today
- Based on `agg_player_daily.total_purchase_revenue > 0`

### paid_ever_flag

- Binary flag: 1 if player has ever made a purchase (lifetime)
- Based on `dim_player.ltv_purchases > 0`

### is_us_player

- Binary flag: 1 if player's first country is US
- Based on `dim_player.first_country = 'US'`

### last_balance_of_day

- Player's credit balance at the end of the day
- From `agg_player_daily.last_credit_balance`

### last_version_of_day

- Last app version used on this day
- From `agg_player_daily.last_app_version`

---

## Data Flow

```
vmp_master_event_normalized (Raw Events)
    ↓
    [Filter: date >= CURRENT_DATE - 7, fraudsters, countries]
    ↓
┌─────────────────┐         ┌─────────────────┐
│   inflow CTE    │         │   outflow CTE   │
│ (rewards events)│         │(generation/bubbles)│
└─────────────────┘         └─────────────────┘
    ↓                           ↓
    └───────────┬───────────────┘
                ↓
        combine CTE (UNION ALL)
                ↓
    ┌───────────────────────────┐
    │  player_dimensions CTE   │
    │ (from agg_player_daily + │
    │      dim_player)         │
    └───────────────────────────┘
                ↓
        Final SELECT
        (with window function)
                ↓
    fact_consumption_daily_new_ver_temp
```

---

## Business Rules

### Filtering Rules

1. **Date Range**: Only processes last 7 days (`date >= CURRENT_DATE - 7`)
2. **Fraudsters**: Excludes `distinct_id` in `potential_fraudsters` table
3. **Countries**: Excludes `UA`, `IL`, `AM` from both events and player dimensions
4. **Null Timestamps**: Excludes events where `res_timestamp IS NULL`

### Inflow Rules

1. **Event Pattern**: `mp_event_name LIKE '%rewards%'`
2. **Item Type**: `LOWER(item_id_1_name) LIKE '%credits%'`
3. **Value**: Sum of `item_quantity_1`
4. **Count**: Simple `COUNT(*)` of events

### Outflow Rules

1. **Event Types**: Only `generation` and `click_bubble_purchase`
2. **Value Calculation**:
   - Negate `delta_credits` (multiply by -1)
   - Add `bubble_cost` directly
3. **Count Calculation**:
   - If `number_of_events` exists: use it
   - If `number_of_events` is NULL: calculate as `delta_credits / (mode_status + 1)` (or 6 if mode_status = 3)
   - Add 1 for each `click_bubble_purchase` event

### Dimension Rules

1. **Player Dimensions**: Joined from `agg_player_daily` and `dim_player`
2. **Flags**: Binary (0/1) based on conditions
3. **Null Handling**: Uses `COALESCE` for version field

### Window Function

- `total_outflow_per_player_per_day`: Calculated per player per day
- Partitions by `date` and `distinct_id`
- Only sums outflow values (filters with CASE statement)

---

## Example Data

### Sample Row (Inflow)

```
date: 2025-01-15
distinct_id: "abc123"
inflow_outflow: "inflow"
source: "rewards_race"
sum_value: 500.0
cnt: 1
total_outflow_per_player_per_day: -1200.0
first_chapter_of_day: 25
paid_today_flag: 1
paid_ever_flag: 1
is_us_player: 1
last_version_of_day: "1.2.3"
last_balance_of_day: 3500.0
```

### Sample Row (Outflow)

```
date: 2025-01-15
distinct_id: "abc123"
inflow_outflow: "outflow"
source: "generation"
sum_value: -800.0
cnt: 4
total_outflow_per_player_per_day: -1200.0  (same for all sources on this day)
first_chapter_of_day: 25
paid_today_flag: 1
paid_ever_flag: 1
is_us_player: 1
last_version_of_day: "1.2.3"
last_balance_of_day: 3500.0
```

---

## Key Differences from Race Project

1. **Granularity**: Daily + source level (vs event-level or level/cycle-level)
2. **Direction Tracking**: Explicit inflow/outflow (vs aggregated metrics)
3. **Source Breakdown**: Each source is a separate row (vs aggregated totals)
4. **Window Functions**: Uses window function for daily totals
5. **Dimension Enrichment**: Joins with aggregated player tables (vs calculating from raw events)

---

## Usage Examples

### Query: Total Inflow vs Outflow by Source

```sql
SELECT
    source,
    inflow_outflow,
    SUM(sum_value) AS total_value,
    SUM(cnt) AS total_count
FROM `yotam-395120.peerplay.fact_consumption_daily_new_ver_temp`
WHERE date >= CURRENT_DATE - 7
GROUP BY source, inflow_outflow
ORDER BY source, inflow_outflow
```

### Query: Player Daily Net Flow

```sql
SELECT
    date,
    distinct_id,
    SUM(CASE WHEN inflow_outflow = 'inflow' THEN sum_value ELSE 0 END) AS total_inflow,
    SUM(CASE WHEN inflow_outflow = 'outflow' THEN sum_value ELSE 0 END) AS total_outflow,
    SUM(sum_value) AS net_flow
FROM `yotam-395120.peerplay.fact_consumption_daily_new_ver_temp`
WHERE date >= CURRENT_DATE - 7
GROUP BY date, distinct_id
```

### Query: Outflow by Player Segment

```sql
SELECT
    paid_ever_flag,
    is_us_player,
    source,
    SUM(sum_value) AS total_outflow,
    COUNT(DISTINCT distinct_id) AS distinct_players
FROM `yotam-395120.peerplay.fact_consumption_daily_new_ver_temp`
WHERE inflow_outflow = 'outflow'
  AND date >= CURRENT_DATE - 7
GROUP BY paid_ever_flag, is_us_player, source
```

---

## Notes

- **Table Name**: Contains `_temp` suffix - may be temporary or in testing
- **7-Day Window**: Only processes last 7 days (rolling window)
- **Mode Status Logic**: Special calculation for generation count when `number_of_events` is NULL
- **Country Filtering**: Excludes Ukraine (UA), Israel (IL), Armenia (AM)
- **Fraud Filtering**: Consistent with Race project pattern

---

**Last Updated**: January 2025  
**Table Version**: New Version (temp)

