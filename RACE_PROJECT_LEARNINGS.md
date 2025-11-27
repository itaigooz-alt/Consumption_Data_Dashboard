# Race Project - Key Learnings & Best Practices

**Purpose**: Comprehensive documentation of patterns, solutions, and best practices from the Race project to guide the Consumption project development.

**Date**: January 2025

---

## Table of Contents

1. [Project Architecture Patterns](#project-architecture-patterns)
2. [BigQuery Integration Patterns](#bigquery-integration-patterns)
3. [Streamlit Dashboard Patterns](#streamlit-dashboard-patterns)
4. [SQL Optimization Techniques](#sql-optimization-techniques)
5. [Authentication & Security](#authentication--security)
6. [Deployment Patterns](#deployment-patterns)
7. [Code Organization](#code-organization)
8. [Data Modeling Patterns](#data-modeling-patterns)
9. [Common Solutions & Patterns](#common-solutions--patterns)
10. [Troubleshooting Patterns](#troubleshooting-patterns)

---

## Project Architecture Patterns

### Directory Structure

```
project/
├── sql/                          # SQL queries and table definitions
│   ├── create_table_*.sql       # DDL for table creation
│   ├── create_fact_*.sql        # Complete SQL with CTEs
│   └── *_migration.sql          # Schema migration scripts
├── python/                       # Python scripts for data updates
│   ├── update_fact_*.py         # Daily update scripts
│   └── create_table.py          # Table creation utilities
├── mcp-server/                  # MCP server (if using MCP)
│   ├── bigquery-server.js
│   └── package.json
├── *_dashboard.py               # Main Streamlit dashboard
├── run_dashboard.sh            # Dashboard launcher
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version for deployment
├── .streamlit/                 # Streamlit config
│   ├── config.toml
│   └── secrets.toml.example
├── .gitignore                  # Git ignore rules
└── Documentation/              # Comprehensive docs
    ├── README.md
    ├── *_DOCUMENTATION.md
    └── *_SETUP.md
```

### Key Principles

1. **Separation of Concerns**: SQL, Python, and dashboard code are separated
2. **Documentation First**: Comprehensive documentation for every component
3. **Version Control**: All code tracked in Git with meaningful commits
4. **Incremental Updates**: Daily update scripts that process only latest data
5. **Multiple Granularities**: Event-level and detailed progression-level tables

---

## BigQuery Integration Patterns

### Client Initialization Pattern

**Multi-Method Authentication** (Priority Order):

1. **Streamlit Cloud Secrets** (`st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']`)
   - Primary method for production deployment
   - Handles both dict (TOML table) and string (JSON string) formats
   - Robust JSON parsing with error handling

2. **Environment Variable** (`GOOGLE_APPLICATION_CREDENTIALS_JSON`)
   - Fallback for local development
   - Can be set as JSON string

3. **File Path** (`GOOGLE_APPLICATION_CREDENTIALS` env var)
   - Points to service account JSON file
   - Traditional method

4. **Application Default Credentials (ADC)**
   - `gcloud auth application-default login`
   - Last resort fallback

### Code Pattern

```python
@st.cache_resource
def get_bigquery_client():
    """Initialize BigQuery client with multiple auth methods"""
    try:
        # Method 1: Streamlit secrets (production)
        if hasattr(st, 'secrets'):
            if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                secret_value = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                # Handle both dict and string formats
                if isinstance(secret_value, dict):
                    creds_dict = secret_value
                else:
                    creds_dict = json.loads(secret_value)
                
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                return bigquery.Client(credentials=credentials, project=PROJECT_ID)
        
        # Method 2: Environment variable
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
            creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            creds_dict = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            return bigquery.Client(credentials=credentials, project=PROJECT_ID)
        
        # Method 3: File path
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            credentials = service_account.Credentials.from_service_account_file(
                os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'),
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            return bigquery.Client(credentials=credentials, project=PROJECT_ID)
        
        # Method 4: ADC
        credentials, project = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        return bigquery.Client(credentials=credentials, project=PROJECT_ID)
        
    except Exception as e:
        st.error(f"Failed to initialize BigQuery client: {e}")
        raise
```

### Data Loading Pattern

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(_client, table_name, filters=None):
    """Load data from BigQuery with caching"""
    query = f"""
    SELECT *
    FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}`
    WHERE 1=1
    """
    
    # Add filters dynamically
    if filters:
        for key, value in filters.items():
            if value:
                if isinstance(value, list):
                    query += f" AND {key} IN ({','.join(map(str, value))})"
                else:
                    query += f" AND {key} = {value}"
    
    df = _client.query(query).to_dataframe()
    
    # Handle data types (important for BigQuery)
    # Use db-dtypes for proper type conversion
    return df
```

### Key Points

- **Use `@st.cache_resource`** for BigQuery client (persists across reruns)
- **Use `@st.cache_data`** for query results (with TTL for freshness)
- **Prefix cache function parameters with `_`** if they shouldn't affect cache key
- **Handle data types**: Use `db-dtypes` package for proper BigQuery type conversion
- **Error handling**: Provide clear error messages for authentication failures

---

## Streamlit Dashboard Patterns

### Page Configuration

```python
st.set_page_config(
    page_title="Dashboard Name",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

### Authentication Pattern

```python
def authenticate_user():
    """Handle Google OAuth authentication"""
    # Check if already authenticated
    if st.session_state.get('authenticated'):
        return st.session_state.get('user_email')
    
    # Check for OAuth callback
    query_params = st.query_params
    if 'code' in query_params:
        # Process OAuth callback
        # Exchange code for token
        # Get user info
        # Check authorization
        # Set session state
        pass
    
    # Show login page or redirect
    # Auto-redirect to Google OAuth
    pass
```

### Filter Pattern with Apply Button

```python
# Initialize session state
if 'filter_temp' not in st.session_state:
    st.session_state.filter_temp = {
        'field1': [],
        'field2': None
    }

if 'filter_applied' not in st.session_state:
    st.session_state.filter_applied = {
        'field1': [],
        'field2': None
    }

# Filter widgets (use temporary values)
selected_field1 = st.sidebar.multiselect(
    "Field 1",
    options=options,
    default=st.session_state.filter_temp['field1']
)
st.session_state.filter_temp['field1'] = selected_field1

# Apply button
if st.sidebar.button("✅ Apply Filters", type="primary"):
    st.session_state.filter_applied = st.session_state.filter_temp.copy()
    st.rerun()

# Use applied filters for actual filtering
filters = st.session_state.filter_applied.copy()
```

### Tabbed Navigation Pattern

```python
tab1, tab2 = st.tabs(["Tab 1 Name", "Tab 2 Name"])

with tab1:
    # Tab 1 content
    if len(filtered_df) == 0:
        st.warning("No data matches filters.")
    else:
        # Views and charts
        pass

with tab2:
    # Tab 2 content
    pass
```

### Chart Creation Pattern

```python
def create_chart_function(df, dimension):
    """Create chart with optional dimension splitting"""
    if len(df) == 0:
        return None
    
    if dimension:
        # Create subplots for each dimension value
        unique_values = sorted(df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values],
            vertical_spacing=0.1
        )
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = df[df[dimension] == dim_value]
            # Create trace for this dimension value
            fig.add_trace(..., row=i, col=1)
        
        fig.update_layout(...)
    else:
        # Single chart without dimension splitting
        fig = px.bar(df, ...)
        fig.update_layout(...)
    
    return fig
```

### KPI Display Pattern

```python
# Calculate metrics
total_players = len(df)
total_revenue = df['revenue'].sum()
rate = (metric / total_players * 100) if total_players > 0 else 0

# Display in columns
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Players", f"{total_players:,}")
with col2:
    st.metric("Total Revenue", f"${total_revenue:,.2f}")
with col3:
    st.metric("Rate", f"{rate:.1f}%")
```

### Summary Table Pattern

```python
def create_summary_table(df, group_by_field):
    """Create summary table grouped by field"""
    summary_data = []
    
    for group_value in sorted(df[group_by_field].unique()):
        subset = df[df[group_by_field] == group_value]
        
        # Calculate KPIs
        metric1 = subset['field1'].sum()
        metric2 = len(subset)
        rate = (metric1 / metric2) if metric2 > 0 else 0
        
        summary_data.append({
            'Group Field': group_value,
            'Metric 1': metric1,
            'Metric 2': metric2,
            'Rate': rate
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Format for display
    display_df = summary_df.copy()
    display_df['Metric 1'] = summary_df['Metric 1'].apply(lambda x: f"${x:,.2f}")
    display_df['Rate'] = summary_df['Rate'].apply(lambda x: f"{x:.2f}%")
    
    return display_df
```

---

## SQL Optimization Techniques

### CTE Combination Pattern

**Problem**: Multiple CTEs scanning the same table for different metrics

**Solution**: Combine related CTEs to reduce table scans

**Example**:
```sql
-- BEFORE: Two separate CTEs
total_revenue_event AS (
    SELECT distinct_id, race_live_ops_id,
           SUM(price_usd) AS total_revenue
    FROM table WHERE mp_event_name = 'purchase_successful'
    GROUP BY all
),
total_purchases_event AS (
    SELECT distinct_id, race_live_ops_id,
           COUNT(*) AS total_purchases
    FROM table WHERE mp_event_name = 'purchase_successful'
    GROUP BY all
)

-- AFTER: Combined CTE
revenue_and_purchases_event AS (
    SELECT distinct_id, race_live_ops_id,
           SUM(price_usd) AS total_revenue,
           COUNT(*) AS total_purchases
    FROM table WHERE mp_event_name = 'purchase_successful'
    GROUP BY all
)
```

### Conditional Aggregation Pattern

**Problem**: Need to calculate different metrics based on conditions

**Solution**: Use CASE statements in aggregations

**Example**:
```sql
race_results AS (
    SELECT distinct_id, race_live_ops_id,
           COUNT(CASE WHEN race_rank <= 3 THEN 1 END) AS races_won,
           COUNT(CASE WHEN race_rank > 3 THEN 1 END) AS races_lost
    FROM table WHERE mp_event_name = 'race_end'
    GROUP BY all
)
```

### Version-Specific Logic Pattern

**Problem**: Different calculation logic for different app versions

**Solution**: Use CASE statements with version checks

**Example**:
```sql
SUM(CASE WHEN mp_event_name = 'generation'
     THEN
         CASE
             WHEN CAST(version_float AS FLOAT64) >= 0.357
                  AND CAST(version_float AS FLOAT64) < 0.3593
                  AND number_of_events IS NOT NULL
             THEN ABS(CAST(COALESCE(delta_credits, 0) AS INT64)) * CAST(number_of_events AS INT64)
             ELSE ABS(CAST(COALESCE(delta_credits, 0) AS INT64))
         END
     ELSE 0
END) AS generation_credits_spent
```

### Optimization Checklist

- ✅ Combine CTEs that scan the same table
- ✅ Use conditional aggregation instead of separate CTEs
- ✅ Minimize table scans (one scan per unique filter combination)
- ✅ Use appropriate JOIN types (INNER vs LEFT)
- ✅ Filter early in CTEs (WHERE clauses)
- ✅ Use GROUP BY ALL for cleaner code
- ✅ Partition and cluster tables appropriately

---

## Authentication & Security

### Google OAuth 2.0 Pattern

**Purpose**: Restrict dashboard access to authorized users

**Implementation**:

1. **OAuth Configuration** (in secrets):
```toml
GOOGLE_OAUTH_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET = "your-client-secret"
STREAMLIT_REDIRECT_URI = "https://your-app.streamlit.app/"
```

2. **OAuth Flow**:
```python
def get_google_oauth_url():
    """Generate Google OAuth URL"""
    client_id = st.secrets.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = st.secrets.get('GOOGLE_OAUTH_CLIENT_SECRET')
    redirect_uri = st.secrets.get('STREAMLIT_REDIRECT_URI')
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
    )
    
    flow.redirect_uri = redirect_uri
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return authorization_url

def authenticate_user():
    """Handle OAuth authentication"""
    # Check session state
    if st.session_state.get('authenticated'):
        return st.session_state.get('user_email')
    
    # Check for OAuth callback
    query_params = st.query_params
    if 'code' in query_params:
        # Exchange code for token
        # Get user info
        # Check authorization
        # Set session state
        pass
    
    # Auto-redirect to Google OAuth
    auth_url = get_google_oauth_url()
    # Use JavaScript redirect
    st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
    st.markdown(f'<script>window.location.replace("{auth_url}");</script>', unsafe_allow_html=True)
    st.stop()
```

3. **Authorization Check**:
```python
ALLOWED_DOMAINS = ['company.com', 'company.io']
ALLOWED_EMAILS = []

def check_authorization(email):
    """Check if user email is authorized"""
    if not email:
        return False
    
    if ALLOWED_EMAILS and email.lower() in [e.lower() for e in ALLOWED_EMAILS]:
        return True
    
    email_domain = email.split('@')[-1].lower() if '@' in email else ''
    return email_domain in [d.lower() for d in ALLOWED_DOMAINS]
```

### Secrets Management Pattern

**Streamlit Cloud Secrets Format** (TOML):

```toml
# Top-level keys (not nested)
GOOGLE_OAUTH_CLIENT_ID = "your-client-id"
GOOGLE_OAUTH_CLIENT_SECRET = "your-client-secret"
STREAMLIT_REDIRECT_URI = "https://your-app.streamlit.app/"

# BigQuery credentials (can be table or string)
[GOOGLE_APPLICATION_CREDENTIALS_JSON]
type = "service_account"
project_id = "your-project-id"
private_key_id = "key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "service-account@project.iam.gserviceaccount.com"
# ... other fields
```

**Reading Secrets Pattern**:

```python
# Handle both dict (TOML table) and string formats
if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
    secret_value = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
    
    # Check if it's already a dict (TOML table format)
    if isinstance(secret_value, dict):
        creds_dict = secret_value
    # Or if it's a string (JSON string)
    elif isinstance(secret_value, str):
        creds_dict = json.loads(secret_value)
    
    # Use credentials
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
```

---

## Deployment Patterns

### Streamlit Cloud Deployment

**Requirements**:
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version (e.g., `python-3.11`)
- `.streamlit/config.toml` - Streamlit configuration
- Secrets configured in Streamlit Cloud dashboard

**Configuration Files**:

`requirements.txt`:
```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
google-cloud-bigquery>=3.11.0
google-auth>=2.23.0
google-auth-oauthlib>=1.0.0
requests>=2.31.0
db-dtypes>=1.2.0
numpy>=1.24.0
```

`runtime.txt`:
```
python-3.11
```

`.streamlit/config.toml`:
```toml
[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false
```

### Environment Variables Pattern

```python
# Configuration with environment variable overrides
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'default-project-id')
DATASET_ID = os.environ.get('BQ_DATASET_ID', 'default-dataset')
TABLE_ID = os.environ.get('TABLE_ID', 'default-table')
FULL_TABLE = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}'
```

### Git Configuration Pattern

```bash
# Initialize repository
git init

# Configure GitHub CLI as credential helper
git config --global credential.helper '!'/opt/homebrew/bin/gh auth git-credential

# Add and commit
git add .
git commit -m "Descriptive commit message"

# Push to GitHub
git remote add origin https://github.com/username/repo.git
git push -u origin main
```

---

## Code Organization

### Function Naming Conventions

- **Chart functions**: `create_*_chart` or `create_*_view`
- **Data loading**: `load_*_data`
- **Utility functions**: `get_*`, `calculate_*`, `format_*`
- **Authentication**: `authenticate_*`, `check_*`

### Code Structure Pattern

```python
# 1. Imports
import streamlit as st
import pandas as pd
# ...

# 2. Page configuration
st.set_page_config(...)

# 3. Authentication (if required)
authenticate_user()

# 4. Configuration constants
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'default')
# ...

# 5. Cached resources
@st.cache_resource
def get_bigquery_client():
    pass

# 6. Cached data loading
@st.cache_data(ttl=3600)
def load_data(_client, table_name):
    pass

# 7. Chart creation functions
def create_chart_1(df, dimension):
    pass

def create_chart_2(df, dimension):
    pass

# 8. Main dashboard logic
def main():
    # Sidebar filters
    # Data loading
    # Tab navigation
    # Chart rendering
    pass

if __name__ == "__main__":
    main()
```

### Documentation Pattern

- **README.md**: Project overview, quick start, structure
- **PROJECT_DOCUMENTATION.md**: Comprehensive project documentation
- **SQL_CODE_DOCUMENTATION.md**: Complete SQL code with explanations
- ***_SETUP.md**: Setup guides for specific components
- ***_TROUBLESHOOTING.md**: Common issues and solutions

---

## Data Modeling Patterns

### Fact Table Design

**Granularity Definition**:
- Clearly define the grain (one row per what?)
- Document all dimensions that define uniqueness

**Field Categories**:
- **Event timing**: `start_timestamp`, `end_timestamp`
- **Identifiers**: Primary keys, foreign keys
- **Metrics**: Aggregated values (sums, counts, averages)
- **Flags**: Binary indicators (0/1)
- **Context**: User attributes, segment IDs

**Naming Conventions**:
- `total_*`: Sum across entire event
- `*_during_*`: Sum during specific time window
- `*_per_*`: Average or ratio
- `number_of_*`: Count
- `is_*` or `*_flag`: Binary indicator

### Incremental Update Pattern

```sql
-- Step 1: Identify latest data to update
WITH latest_data AS (
    SELECT MAX(data_id) AS latest_id
    FROM source_table
    WHERE date BETWEEN 'start_date' AND 'end_date'
),

-- Step 2-N: Calculate metrics for latest data only
metric_cte AS (
    SELECT ...
    FROM source_table
    WHERE data_id = (SELECT latest_id FROM latest_data)
    AND date BETWEEN 'start_date' AND 'end_date'
    GROUP BY all
)

-- Final: Insert or replace
INSERT INTO fact_table
SELECT ... FROM metric_cte
```

### Time Window Pattern

```sql
-- Event-level: All time during event
total_metric_event AS (
    SELECT distinct_id, SUM(metric) AS total_metric
    FROM events
    WHERE event_timestamp BETWEEN start_timestamp AND end_timestamp
    GROUP BY all
),

-- Activity-level: Only during active competition
metric_during_activity AS (
    SELECT e.distinct_id, SUM(e.metric) AS metric_during_activity
    FROM events e
    INNER JOIN activity_windows w
        ON e.distinct_id = w.distinct_id
        AND e.event_timestamp BETWEEN w.activity_start AND w.activity_end
    GROUP BY all
)
```

---

## Common Solutions & Patterns

### Handling Missing Data

```python
# Use COALESCE in SQL
COALESCE(metric, 0) AS metric

# Use fillna in Python
df['field'].fillna(0)

# Check for empty dataframes
if len(df) == 0:
    st.warning("No data available")
    return None
```

### Formatting Numbers

```python
# Currency
f"${value:,.2f}"  # $1,234.56

# Percentage
f"{value:.2f}%"  # 75.50%

# Integer with commas
f"{value:,}"  # 1,234

# Float with commas
f"{value:,.2f}"  # 1,234.56
```

### Dimension Splitting Pattern

```python
def create_chart_with_dimension(df, dimension, chart_func):
    """Create chart with optional dimension splitting"""
    if dimension:
        # Use subplots (rows) for dimension values
        unique_values = sorted(df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values]
        )
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = df[df[dimension] == dim_value]
            trace = chart_func(subset)  # Get trace from chart function
            fig.add_trace(trace, row=i, col=1)
        
        fig.update_layout(...)
    else:
        # Single chart
        fig = chart_func(df)
    
    return fig
```

### Filter Application Pattern

```python
# Build filter dictionary
filters = {}

if selected_field1:
    filters['field1'] = selected_field1

if selected_field2:
    filters['field2'] = selected_field2

# Apply filters to dataframe
filtered_df = df.copy()
for key, value in filters.items():
    if isinstance(value, list):
        filtered_df = filtered_df[filtered_df[key].isin(value)]
    elif value is not None:
        filtered_df = filtered_df[filtered_df[key] == value]
```

---

## Troubleshooting Patterns

### BigQuery Authentication Issues

**Problem**: "Failed to initialize BigQuery client"

**Solutions**:
1. Check secrets format in Streamlit Cloud
2. Verify JSON is valid (use JSON validator)
3. Try TOML table format vs JSON string format
4. Check service account permissions
5. Verify project ID matches

### Streamlit Caching Issues

**Problem**: Data not refreshing

**Solutions**:
1. Use `@st.cache_data(ttl=3600)` with appropriate TTL
2. Prefix function parameters with `_` if they shouldn't affect cache
3. Use "Refresh Now" button to clear cache
4. Check if data actually changed in BigQuery

### SQL Performance Issues

**Problem**: Slow queries

**Solutions**:
1. Combine related CTEs
2. Add appropriate WHERE filters early
3. Use partitioning and clustering
4. Limit date ranges in queries
5. Use appropriate JOIN types

### OAuth Issues

**Problem**: "OAuth configuration not found"

**Solutions**:
1. Verify secrets are at top level (not nested)
2. Check redirect URI matches exactly
3. Verify OAuth credentials in Google Cloud Console
4. Check secret names are exact (case-sensitive)

---

## Key Takeaways for Consumption Project

### Must-Have Components

1. **Multi-method BigQuery authentication** (secrets → env var → file → ADC)
2. **Robust error handling** with clear user messages
3. **Comprehensive documentation** for every component
4. **Optimized SQL** with combined CTEs
5. **Apply button pattern** for filters
6. **Tabbed navigation** for different views
7. **Summary tables** for comparison views
8. **Proper data type handling** (db-dtypes)

### Best Practices

1. **Documentation First**: Write docs as you build
2. **Incremental Development**: Build and test one feature at a time
3. **Error Handling**: Always handle edge cases (empty data, missing values)
4. **User Experience**: Clear labels, helpful messages, loading indicators
5. **Code Reusability**: Create reusable chart functions
6. **Version Control**: Meaningful commit messages
7. **Testing**: Test with real data before deployment

### Common Pitfalls to Avoid

1. ❌ Not handling empty dataframes
2. ❌ Forgetting to format numbers/percentages
3. ❌ Not using caching appropriately
4. ❌ Creating too many separate CTEs
5. ❌ Not documenting business rules
6. ❌ Hardcoding values instead of using config
7. ❌ Not handling authentication errors gracefully

---

## Next Steps for Consumption Project

1. **Define data model**: What tables? What granularity?
2. **Set up project structure**: Create directories, files
3. **Configure BigQuery**: Set up authentication, test connection
4. **Create SQL queries**: Start with basic queries, optimize later
5. **Build dashboard**: Start simple, add features incrementally
6. **Add documentation**: Document as you go
7. **Deploy**: Set up Streamlit Cloud, configure secrets
8. **Iterate**: Add features based on feedback

---

**Last Updated**: January 2025  
**Source Project**: Race Event Analytics  
**Target Project**: Consumption Analytics



