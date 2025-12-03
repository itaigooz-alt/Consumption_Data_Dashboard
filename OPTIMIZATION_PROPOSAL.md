# Consumption Table Optimization Proposal

## Problem
The current `fact_consumption_daily_new_ver_temp` table has granularity of `date`, `distinct_id`, `source`, `inflow_outflow`, which creates a very large table (millions of rows) that is too heavy to load in Streamlit.

## Solution
Create a new aggregated table `fact_consumption_daily_aggregated` that:
- **Removes player-level granularity** (`distinct_id`)
- **Aggregates at dimension bucket level** instead
- **Maintains all dashboard functionality**

## New Granularity

**Old**: `date`, `distinct_id`, `source`, `inflow_outflow`  
**New**: `date`, `source`, `inflow_outflow`, `first_chapter_bucket`, `is_us_player`, `last_balance_bucket`, `last_version_of_day`, `paid_today_flag`, `paid_ever_flag`

## Size Reduction Estimate

**Example Calculation:**
- **Old table**: If you have 100,000 players × 10 sources × 2 types (inflow/outflow) × 30 days = **60 million rows**
- **New table**: 10 sources × 2 types × 4 chapter buckets × 2 US flags × 7 balance buckets × 5 versions × 2 paid flags × 30 days = **~168,000 rows**

**Reduction**: ~99.7% smaller! 🎉

## What Changes in the Dashboard

### ✅ **No Changes Needed** (Works the Same):
1. **Daily Consumption** - Already aggregates by date
2. **Credits Components** - Already aggregates by date
3. **Daily Free vs Paid Inflow** - Already aggregates by date
4. **Daily Free Share by Source** - Already aggregates by date and source
5. **Daily RTP by Source** - Already aggregates by date and source

### ✅ **Filters Still Work**:
- All filters work the same (they filter on dimension buckets)
- Dimension selectors work the same (they split by dimension buckets)

### ⚠️ **Minor Code Changes Needed**:
1. Update table name in `consumption_dashboard.py`
2. Remove `distinct_id` from any groupby operations (if any)
3. Update `total_outflow_per_player_per_day` calculation (now `total_outflow_per_dimension_per_day`)

## New Table Structure

```sql
CREATE OR REPLACE TABLE `yotam-395120.peerplay.fact_consumption_daily_aggregated`
    PARTITION BY date
AS 
-- Aggregated by date, source, and dimension buckets
-- No distinct_id granularity
```

**Columns:**
- `date`
- `source` (mp_event_name)
- `inflow_outflow` ('inflow' or 'outflow')
- `first_chapter_bucket` ('0-10', '11-20', '21-50', '50+')
- `is_us_player` (0 or 1)
- `last_balance_bucket` ('0-100', '101-300', etc.)
- `last_version_of_day`
- `paid_today_flag` (0 or 1)
- `paid_ever_flag` (0 or 1)
- `sum_value` (aggregated credits)
- `distinct_players` (count of unique players in this bucket)
- `cnt` (count of events)
- `total_outflow_per_dimension_per_day` (for RTP calculation)

## Migration Steps

1. **Create new aggregated table** (see `sql/create_fact_consumption_daily_aggregated.sql`)
2. **Update dashboard code**:
   - Change table name from `fact_consumption_daily_new_ver_temp` to `fact_consumption_daily_aggregated`
   - Remove any `distinct_id` references
   - Update `total_outflow_per_player_per_day` to `total_outflow_per_dimension_per_day`
3. **Test dashboard** - All views should work the same
4. **Deploy**

## Benefits

✅ **99%+ size reduction**  
✅ **Faster dashboard loading**  
✅ **Same functionality**  
✅ **All filters and views work**  
✅ **Easier to maintain**

## Trade-offs

⚠️ **Lost**: Player-level detail (can't drill down to individual players)  
✅ **Gained**: Much faster performance, all dashboard views still work

---

**Next Steps**: Review the SQL code in `sql/create_fact_consumption_daily_aggregated.sql` and update the dashboard accordingly.

