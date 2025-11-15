# Quick Reference Guide - Consumption Project

**Quick lookup for common patterns and code snippets**

---

## BigQuery Client Setup

```python
from google.cloud import bigquery
from google.oauth2 import service_account
from google.auth import default
import json
import os
import streamlit as st

@st.cache_resource
def get_bigquery_client():
    """Initialize BigQuery client - use this exact pattern"""
    # Try st.secrets first (production)
    # Then env var, then file, then ADC
    # See RACE_PROJECT_LEARNINGS.md for full implementation
    pass
```

## Data Loading Pattern

```python
@st.cache_data(ttl=3600)
def load_data(_client, table_name):
    """Load data with caching"""
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}`"
    df = _client.query(query).to_dataframe()
    return df
```

## Filter Pattern with Apply Button

```python
# Session state
if 'filter_applied' not in st.session_state:
    st.session_state.filter_applied = {'field': []}

# Widget
selected = st.sidebar.multiselect("Field", options, default=st.session_state.filter_applied['field'])

# Apply button
if st.button("✅ Apply"):
    st.session_state.filter_applied['field'] = selected
    st.rerun()
```

## Chart with Dimension Splitting

```python
def create_chart(df, dimension):
    if dimension:
        # Subplots for each dimension value
        fig = make_subplots(rows=len(unique_values), cols=1)
        # Add traces per dimension
    else:
        # Single chart
        fig = px.bar(df, ...)
    return fig
```

## SQL CTE Combination

```sql
-- Combine related CTEs
combined_metrics AS (
    SELECT 
        SUM(metric1) AS total_metric1,
        COUNT(*) AS total_count
    FROM table
    WHERE condition
    GROUP BY all
)
```

## Summary Table Pattern

```python
def create_summary_table(df, group_by):
    summary = []
    for group_val in df[group_by].unique():
        subset = df[df[group_by] == group_val]
        summary.append({
            'Group': group_val,
            'Metric': subset['field'].sum()
        })
    return pd.DataFrame(summary)
```

---

**See RACE_PROJECT_LEARNINGS.md for detailed explanations**

