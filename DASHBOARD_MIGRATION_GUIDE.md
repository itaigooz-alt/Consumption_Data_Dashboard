# Dashboard Migration Guide: Player-Level to Aggregated Table

## Overview

This guide explains how to update the dashboard to use the new aggregated table `fact_consumption_daily_aggregated` instead of `fact_consumption_daily_new_ver_temp`.

## Key Changes

### 1. Table Name Change

**Old**: `fact_consumption_daily_new_ver_temp`  
**New**: `fact_consumption_daily_aggregated`

### 2. Granularity Change

**Old**: `date`, `distinct_id`, `source`, `inflow_outflow`  
**New**: `date`, `source`, `inflow_outflow`, `first_chapter_bucket`, `is_us_player`, `last_balance_bucket`, `last_version_of_day`, `paid_today_flag`, `paid_ever_flag`

### 3. Column Changes

**Removed**:
- `distinct_id` (no longer in table)
- `first_chapter_of_day` (replaced by `first_chapter_bucket`)
- `last_balance_of_day` (replaced by `last_balance_bucket`)
- `total_outflow_per_player_per_day` (replaced by `total_outflow_per_dimension_per_day`)

**Added**:
- `first_chapter_bucket` (already bucketed: '0-10', '11-20', '21-50', '50+')
- `last_balance_bucket` (already bucketed: '0-100', '101-300', etc.)
- `distinct_players` (count of unique players in this bucket)
- `total_outflow_per_dimension_per_day` (outflow per dimension combination)

## Code Changes Required

### Step 1: Update Table Name

**File**: `consumption_dashboard.py`

```python
# OLD:
FULL_TABLE = "yotam-395120.peerplay.fact_consumption_daily_new_ver_temp"

# NEW:
FULL_TABLE = "yotam-395120.peerplay.fact_consumption_daily_aggregated"
```

### Step 2: Update Column References

**File**: `consumption_dashboard.py`

**Remove `distinct_id` from queries** (if any):
- The new table doesn't have `distinct_id`, so remove any references

**Update column names**:
- `first_chapter_of_day` → `first_chapter_bucket` (already bucketed)
- `last_balance_of_day` → `last_balance_bucket` (already bucketed)
- `total_outflow_per_player_per_day` → `total_outflow_per_dimension_per_day`

### Step 3: Remove Bucketing Functions (No Longer Needed)

**File**: `consumption_dashboard.py`

The new table already has bucketed values, so you can remove:
- `bucket_first_chapter()` function
- `bucket_last_balance()` function
- The bucketing logic in the main function

**Change**:
```python
# OLD:
df['first_chapter_bucket'] = df['first_chapter_of_day'].apply(bucket_first_chapter)
df['last_balance_bucket'] = df['last_balance_of_day'].apply(bucket_last_balance)

# NEW:
# Columns already exist as buckets in the table
# Just use: df['first_chapter_bucket'] and df['last_balance_bucket']
```

### Step 4: Update RTP Calculation

**File**: `consumption_dashboard.py` - `create_rtp_by_source_chart()`

**OLD Logic** (player-day level):
```python
player_day_outflow = outflow_df.groupby(['date', 'distinct_id'])['sum_value'].sum()
daily_outflow = player_day_outflow.groupby('date')['outflow'].sum()
```

**NEW Logic** (dimension level):
```python
# Outflow is already aggregated by dimension, just sum by date
daily_outflow = outflow_df.groupby('date')['sum_value'].sum().reset_index()
daily_outflow['outflow'] = abs(daily_outflow['sum_value'])  # Make positive
```

Or use the pre-calculated column:
```python
# Use total_outflow_per_dimension_per_day, but need to aggregate by date
# Since outflow is the same for all sources in a dimension combination,
# we can use the window function result
```

Actually, since the table is already aggregated, we can simplify:
```python
# Get outflow by date (sum across all dimension combinations)
outflow_by_date = df[df['inflow_outflow'] == 'outflow'].groupby('date')['sum_value'].sum().reset_index()
outflow_by_date['outflow'] = abs(outflow_by_date['sum_value'])
```

### Step 5: Update Load Data Function

**File**: `consumption_dashboard.py` - `load_data()`

**Remove columns that don't exist**:
- `distinct_id`
- `first_chapter_of_day` (use `first_chapter_bucket`)
- `last_balance_of_day` (use `last_balance_bucket`)
- `total_outflow_per_player_per_day` (use `total_outflow_per_dimension_per_day`)

**Update SELECT statement**:
```python
query = f"""
    SELECT 
        date,
        source,
        inflow_outflow,
        sum_value,
        cnt,
        first_chapter_bucket,
        is_us_player,
        last_balance_bucket,
        last_version_of_day,
        paid_today_flag,
        paid_ever_flag,
        total_outflow_per_dimension_per_day,
        distinct_players
    FROM `{FULL_TABLE}`
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {date_limit_days} DAY)
    LIMIT 1000000
"""
```

### Step 6: Update Data Type Handling

**File**: `consumption_dashboard.py` - `load_data()`

**Update numeric fields**:
```python
numeric_fields = ['sum_value', 'cnt', 'total_outflow_per_dimension_per_day', 
                 'last_version_of_day', 'distinct_players']
```

**Update flag fields** (same):
```python
flag_fields = ['paid_today_flag', 'paid_ever_flag', 'is_us_player']
```

**Remove**:
- `first_chapter_of_day` (no longer exists)
- `last_balance_of_day` (no longer exists)

## Benefits

✅ **99%+ size reduction** - From millions of rows to thousands  
✅ **Faster loading** - Much smaller table to query  
✅ **Same functionality** - All views and filters work the same  
✅ **No bucketing needed** - Already done in SQL  

## Testing Checklist

- [ ] Update table name
- [ ] Update column references
- [ ] Remove bucketing functions
- [ ] Update RTP calculation
- [ ] Test all filters
- [ ] Test all views
- [ ] Test dimension selectors
- [ ] Verify date range works
- [ ] Check performance improvement

## Rollback Plan

If issues occur, you can:
1. Revert to old table by changing `FULL_TABLE` back
2. Keep both tables and switch between them
3. Use feature flag to toggle between tables

---

**Next**: Review the SQL in `sql/create_fact_consumption_daily_aggregated.sql` and apply the dashboard changes above.

