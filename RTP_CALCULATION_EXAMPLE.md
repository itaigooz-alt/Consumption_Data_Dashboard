# RTP Calculation Example for One Player

## Understanding the Data Granularity

The `fact_consumption_daily_new_ver_temp` table has this structure:
- **One row per**: `date`, `distinct_id` (player), `source`, `inflow_outflow`
- **Key point**: Outflow is stored **once per player per day**, but it appears in **multiple rows** (one for each source)

## Example: Player "player123" on 2025-11-12

### Raw Data Structure

```
date        | distinct_id | source                    | inflow_outflow | sum_value
------------|-------------|---------------------------|----------------|----------
2025-11-12  | player123   | rewards_timed_task        | inflow         | 1000
2025-11-12  | player123   | rewards_harvest_collect   | inflow         | 500
2025-11-12  | player123   | rewards_board_task        | inflow         | 300
2025-11-12  | player123   | rewards_timed_task        | outflow        | -2000  ← Same outflow value
2025-11-12  | player123   | rewards_harvest_collect   | outflow        | -2000  ← repeats for each source
2025-11-12  | player123   | rewards_board_task        | outflow        | -2000  ← repeats for each source
```

**Important**: The outflow value (-2000) is the **same** for all sources because it represents the player's total daily outflow.

### Step-by-Step RTP Calculation

#### Step 1: Get Player's Daily Outflow (Once)

```python
# Outflow is the same for all sources, so we get it once per player-day
player_outflow = abs(-2000) = 2000  # Make it positive
```

#### Step 2: Calculate Free Inflow by Source

```python
# Filter for free inflow only (exclude rewards_store and rewards_rolling_offer_collect)
# All sources in this example are free, so:

Free Inflow by source:
- rewards_timed_task:     1000 credits
- rewards_harvest_collect: 500 credits  
- rewards_board_task:     300 credits
```

#### Step 3: Calculate RTP for Each Source

```python
RTP = (Free Inflow by Source / Total Outflow) × 100

For rewards_timed_task:
  RTP = (1000 / 2000) × 100 = 50%

For rewards_harvest_collect:
  RTP = (500 / 2000) × 100 = 25%

For rewards_board_task:
  RTP = (300 / 2000) × 100 = 15%
```

### Why This Approach?

**The Problem**: If we didn't handle the granularity correctly, we might do:
```python
# WRONG APPROACH:
# Sum outflow across all rows (would count 2000 three times = 6000)
total_outflow_wrong = 2000 + 2000 + 2000 = 6000  # ❌ Wrong!

# Then RTP would be:
RTP_wrong = (1000 / 6000) × 100 = 16.67%  # ❌ Incorrect!
```

**The Correct Approach** (what the code does):
```python
# CORRECT APPROACH:
# Get outflow once per player-day (group by date + distinct_id)
player_day_outflow = groupby(['date', 'distinct_id'])['sum_value'].sum()
# Result: -2000 (only counted once)

# Then aggregate across all players for the day
daily_outflow = sum of all player-day outflows

# Calculate RTP per source
RTP = (Free Inflow by Source / Daily Total Outflow) × 100
```

## Current Code Logic (Aggregated View)

The dashboard currently shows **aggregated RTP across all players**:

```python
# Step 1: Get outflow at player-day level (avoid double counting)
player_day_outflow = outflow_df.groupby(['date', 'distinct_id'])['sum_value'].sum()
# This gives: {('2025-11-12', 'player123'): -2000, ('2025-11-12', 'player456'): -1500, ...}

# Step 2: Aggregate outflow by date (sum across all players)
daily_outflow = player_day_outflow.groupby('date')['outflow'].sum()
# For 2025-11-12: 2000 + 1500 + ... = Total daily outflow across all players

# Step 3: Get free inflow by source (aggregated across all players)
free_inflow_by_source = free_inflow_df.groupby(['date', 'source'])['sum_value'].sum()
# For 2025-11-12, rewards_timed_task: sum of all players' rewards_timed_task inflow

# Step 4: Calculate RTP
RTP = (Free Inflow by Source / Daily Total Outflow) × 100
```

## Example: Multiple Players

Let's say we have 2 players on 2025-11-12:

**Player 123:**
- Outflow: 2000
- Free Inflow: rewards_timed_task = 1000, rewards_harvest_collect = 500

**Player 456:**
- Outflow: 1500
- Free Inflow: rewards_timed_task = 800, rewards_harvest_collect = 400

**Calculation:**
```python
# Step 1: Daily total outflow (across all players)
daily_outflow = 2000 + 1500 = 3500

# Step 2: Free inflow by source (across all players)
rewards_timed_task_inflow = 1000 + 800 = 1800
rewards_harvest_collect_inflow = 500 + 400 = 900

# Step 3: RTP by source
RTP_rewards_timed_task = (1800 / 3500) × 100 = 51.43%
RTP_rewards_harvest_collect = (900 / 3500) × 100 = 25.71%
```

## Key Takeaway

**RTP is calculated as:**
```
RTP (by source) = (Total Free Inflow from that source / Total Daily Outflow) × 100
```

Where:
- **Total Free Inflow by source**: Sum of all free inflow from that source across all players for the day
- **Total Daily Outflow**: Sum of all players' daily outflows (each player's outflow counted once)

This ensures we don't double-count outflow, which would happen if we summed outflow across all source rows.

---

**Formula Summary:**
```
RTP_source = (Σ Free Inflow_source / Σ Player Daily Outflow) × 100
```

Where:
- Σ Free Inflow_source = Sum of free inflow from this source across all players
- Σ Player Daily Outflow = Sum of each player's daily outflow (each player counted once)

