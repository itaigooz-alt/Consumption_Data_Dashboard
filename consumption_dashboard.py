#!/usr/bin/env python3
"""
Consumption Dashboard
Connects to BigQuery fact_consumption_daily_new_ver_temp table and displays consumption analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.cloud import bigquery
from google.auth import default
from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
import json
import time
from datetime import datetime, timedelta
import numpy as np
import os
from urllib.parse import urlparse

# Page configuration
st.set_page_config(
    page_title="Consumption Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# GOOGLE OAUTH AUTHENTICATION
# ============================================================================

ALLOWED_DOMAINS = ['peerplay.com', 'peerplay.io']
ALLOWED_EMAILS = []

def check_authorization(email):
    """Check if user's email is authorized"""
    if not email:
        return False
    if ALLOWED_EMAILS and email.lower() in [e.lower() for e in ALLOWED_EMAILS]:
        return True
    email_domain = email.split('@')[-1].lower() if '@' in email else ''
    return email_domain in [d.lower() for d in ALLOWED_DOMAINS]

def get_google_oauth_url():
    """Get Google OAuth URL for authentication"""
    client_id = None
    client_secret = None
    
    # Try to access secrets, but handle missing secrets gracefully
    try:
        if hasattr(st, 'secrets'):
            try:
                if 'GOOGLE_OAUTH_CLIENT_ID' in st.secrets:
                    client_id = st.secrets['GOOGLE_OAUTH_CLIENT_ID']
                elif hasattr(st.secrets, 'get'):
                    client_id = st.secrets.get('GOOGLE_OAUTH_CLIENT_ID')
                if not client_id and 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                    creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                    try:
                        if hasattr(creds_json, 'get'):
                            client_id = creds_json.get('GOOGLE_OAUTH_CLIENT_ID')
                        elif hasattr(creds_json, '__getitem__'):
                            if 'GOOGLE_OAUTH_CLIENT_ID' in creds_json:
                                client_id = creds_json['GOOGLE_OAUTH_CLIENT_ID']
                    except:
                        pass
            except (KeyError, AttributeError, TypeError, Exception):
                pass
    except Exception:
        # Secrets not configured - this is OK for local development
        pass
    
    # Try to get client_secret
    try:
        if hasattr(st, 'secrets'):
            try:
                if 'GOOGLE_OAUTH_CLIENT_SECRET' in st.secrets:
                    client_secret = st.secrets['GOOGLE_OAUTH_CLIENT_SECRET']
                elif hasattr(st.secrets, 'get'):
                    client_secret = st.secrets.get('GOOGLE_OAUTH_CLIENT_SECRET')
                if not client_secret and 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                    creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                    try:
                        if hasattr(creds_json, 'get'):
                            client_secret = creds_json.get('GOOGLE_OAUTH_CLIENT_SECRET')
                        elif hasattr(creds_json, '__getitem__'):
                            if 'GOOGLE_OAUTH_CLIENT_SECRET' in creds_json:
                                client_secret = creds_json['GOOGLE_OAUTH_CLIENT_SECRET']
                    except:
                        pass
            except (KeyError, AttributeError, TypeError, Exception):
                pass
    except Exception:
        # Secrets not configured - this is OK for local development
        pass
    
    if not client_id:
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    if not client_secret:
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return None
    
    redirect_uri = None
    try:
        if hasattr(st, 'secrets'):
            try:
                if 'STREAMLIT_REDIRECT_URI' in st.secrets:
                    redirect_uri = st.secrets['STREAMLIT_REDIRECT_URI']
                elif hasattr(st.secrets, 'get'):
                    redirect_uri = st.secrets.get('STREAMLIT_REDIRECT_URI')
                if not redirect_uri and 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                    creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                    try:
                        if hasattr(creds_json, 'get'):
                            redirect_uri = creds_json.get('STREAMLIT_REDIRECT_URI')
                        elif hasattr(creds_json, '__getitem__'):
                            if 'STREAMLIT_REDIRECT_URI' in creds_json:
                                redirect_uri = creds_json['STREAMLIT_REDIRECT_URI']
                    except:
                        pass
            except (KeyError, AttributeError, TypeError, Exception):
                pass
    except Exception:
        # Secrets not configured - this is OK for local development
        pass
    
    if not redirect_uri:
        redirect_uri = os.environ.get('STREAMLIT_REDIRECT_URI')
    
    if not redirect_uri:
        redirect_uri = "https://consumption-dashboard.streamlit.app/"
    
    try:
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
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
            redirect_uri=redirect_uri
        )
        authorization_url, _ = flow.authorization_url(prompt="consent")
        return authorization_url
    except Exception as e:
        st.error(f"Error creating OAuth flow: {e}")
        return None

def authenticate_user():
    """Handle Google OAuth authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    
    if st.session_state.authenticated:
        return True
    
    query_params = st.query_params
    code = query_params.get('code', None)
    
    if code:
        try:
            redirect_uri = None
            try:
                if hasattr(st, 'secrets'):
                    try:
                        if 'STREAMLIT_REDIRECT_URI' in st.secrets:
                            redirect_uri = st.secrets['STREAMLIT_REDIRECT_URI']
                        elif hasattr(st.secrets, 'get'):
                            redirect_uri = st.secrets.get('STREAMLIT_REDIRECT_URI')
                        if not redirect_uri and 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                            creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                            try:
                                if hasattr(creds_json, 'get'):
                                    redirect_uri = creds_json.get('STREAMLIT_REDIRECT_URI')
                                elif hasattr(creds_json, '__getitem__'):
                                    if 'STREAMLIT_REDIRECT_URI' in creds_json:
                                        redirect_uri = creds_json['STREAMLIT_REDIRECT_URI']
                            except:
                                pass
                    except (KeyError, AttributeError, TypeError, Exception):
                        pass
            except Exception:
                pass
            
            if not redirect_uri:
                redirect_uri = os.environ.get('STREAMLIT_REDIRECT_URI', "https://consumption-dashboard.streamlit.app/")
            
            client_id = None
            client_secret = None
            try:
                if hasattr(st, 'secrets'):
                    try:
                        if 'GOOGLE_OAUTH_CLIENT_ID' in st.secrets:
                            client_id = st.secrets['GOOGLE_OAUTH_CLIENT_ID']
                        elif hasattr(st.secrets, 'get'):
                            client_id = st.secrets.get('GOOGLE_OAUTH_CLIENT_ID')
                        if not client_id and 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                            creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                            try:
                                if hasattr(creds_json, 'get'):
                                    client_id = creds_json.get('GOOGLE_OAUTH_CLIENT_ID')
                                elif hasattr(creds_json, '__getitem__'):
                                    if 'GOOGLE_OAUTH_CLIENT_ID' in creds_json:
                                        client_id = creds_json['GOOGLE_OAUTH_CLIENT_ID']
                            except:
                                pass
                    except (KeyError, AttributeError, TypeError, Exception):
                        pass
                    
                    try:
                        if 'GOOGLE_OAUTH_CLIENT_SECRET' in st.secrets:
                            client_secret = st.secrets['GOOGLE_OAUTH_CLIENT_SECRET']
                        elif hasattr(st.secrets, 'get'):
                            client_secret = st.secrets.get('GOOGLE_OAUTH_CLIENT_SECRET')
                        if not client_secret and 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                            creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                            try:
                                if hasattr(creds_json, 'get'):
                                    client_secret = creds_json.get('GOOGLE_OAUTH_CLIENT_SECRET')
                                elif hasattr(creds_json, '__getitem__'):
                                    if 'GOOGLE_OAUTH_CLIENT_SECRET' in creds_json:
                                        client_secret = creds_json['GOOGLE_OAUTH_CLIENT_SECRET']
                            except:
                                pass
                    except (KeyError, AttributeError, TypeError, Exception):
                        pass
            except Exception:
                # Secrets not configured - this is OK for local development
                pass
            
            if not client_id:
                client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
            if not client_secret:
                client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
            
            if client_id and client_secret:
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
                    scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
                    redirect_uri=redirect_uri
                )
                flow.fetch_token(code=code)
                credentials = flow.credentials
                import requests
                user_info = requests.get(
                    f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={credentials.token}"
                ).json()
                email = user_info.get('email', '')
                
                if check_authorization(email):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_name = user_info.get('name', '')
                    # Clear the code from URL
                    st.query_params.clear()
                    st.rerun()
                    return email
                else:
                    st.error(f"❌ Access Denied: {email} is not authorized to access this dashboard.")
                    st.info("This dashboard is restricted to Peerplay employees only.")
                    return None
        except Exception as e:
            error_msg = str(e)
            # Handle scope change errors specifically
            if "Scope has changed" in error_msg or "scope" in error_msg.lower():
                st.error("🔐 **Authentication Error: Scope Mismatch**")
                st.warning("""
                **What happened:**
                The OAuth scopes have changed. You need to re-authorize the application.
                
                **Solution:**
                1. Clear your browser cookies/cache for this site
                2. Or use an incognito/private browsing window
                3. Click the login button again to re-authorize
                
                **Note:** This is a one-time re-authorization. After this, you should be able to access the dashboard normally.
                """)
                # Clear session state to force re-authentication
                if 'authenticated' in st.session_state:
                    del st.session_state['authenticated']
                if 'user_email' in st.session_state:
                    del st.session_state['user_email']
            else:
                st.error(f"Authentication error: {error_msg}")
            return None
    # Check for auth URL first - if it exists, redirect immediately without showing debug
    try:
        auth_url = get_google_oauth_url()
        if auth_url:
            # Show minimal content and redirect using JavaScript
            st.markdown("### 🔐 Redirecting to Google Authentication...")
            st.markdown("Please wait while we redirect you to sign in with your Google account.")
            
            # Use JavaScript to redirect - simplified approach
            redirect_js = f"""
            <script type="text/javascript">
                (function() {{
                    try {{
                        window.location.href = "{auth_url}";
                    }} catch(e) {{
                        console.error("Redirect error:", e);
                        // Fallback: create a link and click it
                        var link = document.createElement('a');
                        link.href = "{auth_url}";
                        link.click();
                    }}
                }})();
            </script>
            """
            
            st.markdown(redirect_js, unsafe_allow_html=True)
            
            # Also provide a clickable link as fallback
            st.markdown("---")
            st.markdown("If you are not redirected automatically, click here:")
            st.markdown(f"[**🔵 Sign in with Google**]({auth_url})")
            
            # Stop execution to prevent dashboard from loading
            st.stop()
    except Exception as e:
        # If there's an error getting the auth URL, show it and continue to error page
        st.error(f"Error setting up authentication: {str(e)}")
        auth_url = None
    
    # Only show login page and debug if OAuth is not configured
    st.title("🔐 Authentication Required")
    st.markdown("### Consumption Dashboard")
    st.markdown("This dashboard is restricted to **Peerplay employees only**.")
    
    # Debug: Show what secrets are available (only if OAuth not configured)
    if hasattr(st, 'secrets'):
        try:
            available_secrets = list(st.secrets.keys()) if hasattr(st.secrets, 'keys') else []
            with st.expander("🔍 Debug: Available Secrets", expanded=False):
                st.write(f"Found {len(available_secrets)} secrets:")
                for key in available_secrets:
                    # Don't show sensitive values, just keys
                    if 'SECRET' in key.upper() or 'KEY' in key.upper():
                        st.write(f"- `{key}`: ✅ (hidden)")
                    else:
                        try:
                            value = st.secrets.get(key)
                            if isinstance(value, str) and len(value) > 50:
                                st.write(f"- `{key}`: ✅ (value too long to display)")
                            else:
                                st.write(f"- `{key}`: `{value}`")
                        except:
                            st.write(f"- `{key}`: ✅ (exists)")
        except Exception:
            pass
    
    # If OAuth is not configured, proceed without authentication for local development
    st.warning("⚠️ OAuth not configured. Proceeding without authentication.")
    st.info("For production deployment, configure OAuth credentials in Streamlit Cloud secrets.")
    st.session_state.authenticated = True
    return True

# ============================================================================
# BIGQUERY CONNECTION
# ============================================================================

PROJECT_ID = "yotam-395120"
FULL_TABLE = "yotam-395120.peerplay.fact_consumption_daily_new_ver_temp"

@st.cache_resource
def init_bigquery_client():
    """Initialize BigQuery client with multiple authentication methods"""
    try:
        # Method 1: Service account JSON from Streamlit secrets (for Streamlit Cloud)
        try:
            if hasattr(st, 'secrets') and 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
                creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
                
                # Handle different formats
                if isinstance(creds_json, dict):
                    credentials = service_account.Credentials.from_service_account_info(creds_json)
                    client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
                    return client
                elif isinstance(creds_json, str):
                    # Try parsing as JSON string
                    try:
                        creds_dict = json.loads(creds_json)
                        credentials = service_account.Credentials.from_service_account_info(creds_dict)
                        client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
                        return client
                    except json.JSONDecodeError:
                        # Try stripping and unescaping
                        creds_str = creds_json.strip().strip('"').replace('\\n', '\n').replace('\\"', '"')
                        try:
                            creds_dict = json.loads(creds_str)
                            credentials = service_account.Credentials.from_service_account_info(creds_dict)
                            client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
                            return client
                        except:
                            pass
                
                # Handle AttrDict (Streamlit's dict-like type)
                if hasattr(creds_json, 'get'):
                    try:
                        creds_dict = dict(creds_json)
                        credentials = service_account.Credentials.from_service_account_info(creds_dict)
                        client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
                        return client
                    except:
                        pass
        except Exception:
            # Secrets not configured - continue to next method
            pass
        
        # Method 2: Service account JSON file path (for local development)
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and os.path.exists(creds_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(creds_path)
                client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
                return client
            except Exception:
                pass
        
        # Method 3: Application Default Credentials (for local development)
        # This is the standard way to authenticate locally
        try:
            credentials, project = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
            return client
        except Exception as adc_error:
            # If ADC fails, provide helpful error message
            st.error("❌ Failed to initialize BigQuery client")
            st.error("**Authentication Error:** No valid credentials found.")
            st.markdown("""
            **For local development:**
            1. Run: `gcloud auth application-default login`
            2. Or set `GOOGLE_APPLICATION_CREDENTIALS` environment variable to your service account JSON file path
            
            **For Streamlit Cloud deployment:**
            Add `GOOGLE_APPLICATION_CREDENTIALS_JSON` to your Streamlit Cloud secrets
            """)
            return None
            
    except Exception as e:
        st.error(f"❌ Failed to initialize BigQuery client: {e}")
        st.markdown("""
        **Troubleshooting:**
        - For local: Run `gcloud auth application-default login`
        - Check that service account has BigQuery permissions
        - Verify credentials are correctly set
        """)
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes instead of 1 minute
def load_data(_client, date_limit_days=30):
    """Load data from BigQuery with optimized query"""
    try:
        # Only load recent data by default (last 30 days)
        # Use partition pruning and limit columns for faster query
        # The table is partitioned by date, so this should be fast
        query = f"""
        SELECT 
            date,
            distinct_id,
            source,
            inflow_outflow,
            sum_value,
            cnt,
            total_outflow_per_player_per_day,
            first_chapter_of_day,
            paid_today_flag,
            paid_ever_flag,
            is_us_player,
            last_version_of_day,
            last_balance_of_day
        FROM `{FULL_TABLE}`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {date_limit_days} DAY)
        ORDER BY date DESC, distinct_id, source
        LIMIT 1000000
        """
        
        # Use job_config for faster queries with caching
        from google.cloud.bigquery import QueryJobConfig
        job_config = QueryJobConfig(
            use_query_cache=True,
            use_legacy_sql=False,
            maximum_bytes_billed=10**10  # 10GB limit
        )
        
        df = _client.query(query, job_config=job_config).to_dataframe()
        
        # Ensure proper data types
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Handle numeric fields
        numeric_fields = ['sum_value', 'cnt', 'total_outflow_per_player_per_day', 
                         'first_chapter_of_day', 'last_balance_of_day', 'last_version_of_day']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)
        
        # Handle flag fields
        flag_fields = ['paid_today_flag', 'paid_ever_flag', 'is_us_player']
        for field in flag_fields:
            if field in df.columns:
                df[field] = df[field].fillna(0).astype(int)
        
        # Handle string fields
        if 'source' in df.columns:
            df['source'] = df['source'].astype(str)
        if 'inflow_outflow' in df.columns:
            df['inflow_outflow'] = df['inflow_outflow'].astype(str)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_bucket_label(value, buckets):
    """Create bucket label for a value"""
    for i, (min_val, max_val, label) in enumerate(buckets):
        if i == len(buckets) - 1:  # Last bucket (no upper limit)
            if value >= min_val:
                return label
        else:
            if min_val <= value < max_val:
                return label
    return buckets[-1][2]  # Default to last bucket

def bucket_first_chapter(value):
    """Bucket first_chapter_of_day"""
    buckets = [
        (0, 11, "0-10"),
        (11, 21, "11-20"),
        (21, 51, "21-50"),
        (51, float('inf'), "50+")
    ]
    return create_bucket_label(value, buckets)

def bucket_last_balance(value):
    """Bucket last_balance_of_day"""
    buckets = [
        (0, 101, "0-100"),
        (101, 301, "101-300"),
        (301, 501, "301-500"),
        (501, 1001, "501-1000"),
        (1001, 3001, "1001-3000"),
        (3001, 5001, "3001-5000"),
        (5001, float('inf'), "5000+")
    ]
    return create_bucket_label(value, buckets)

def calculate_daily_aggregates(df, dimension=None):
    """Helper function to calculate daily aggregates"""
    if len(df) == 0:
        return pd.DataFrame()
    
    # Aggregate data by date (and dimension if provided)
    if dimension:
        group_cols = ['date', dimension]
    else:
        group_cols = ['date']
    
    # Calculate daily aggregates
    daily_data = []
    for date_group, group_df in df.groupby(group_cols):
        if dimension:
            # date_group is a tuple (date, dimension_value)
            date_val, dim_val = date_group
        else:
            # date_group is just the date
            date_val = date_group
            dim_val = None
        
        # Ensure date_val is a proper date object, not a tuple
        if isinstance(date_val, tuple):
            date_val = date_val[0]
        if isinstance(date_val, pd.Timestamp):
            date_val = date_val.date()
        
        # Calculate total inflow and outflow
        # Note: Since we have multiple rows per player per day (one per source),
        # we need to aggregate by distinct_id first, then sum across all players
        # For inflow: sum all positive values
        # For outflow: sum all negative values (they're already negative in the data)
        
        inflow_df = group_df[group_df['inflow_outflow'] == 'inflow']
        outflow_df = group_df[group_df['inflow_outflow'] == 'outflow']
        
        # Sum all inflow values (they're positive)
        total_inflow = inflow_df['sum_value'].sum()
        
        # Sum all outflow values (they're already negative, so we keep them negative)
        total_outflow_negative = outflow_df['sum_value'].sum()
        total_outflow_positive = abs(total_outflow_negative)  # For display as positive bar
        
        # Calculate free inflow (source not in rewards_store, rewards_rolling_offer_collect)
        free_inflow = inflow_df[
            ~inflow_df['source'].isin(['rewards_store', 'rewards_rolling_offer_collect'])
        ]['sum_value'].sum()
        
        # Calculate paid inflow (source in rewards_store, rewards_rolling_offer_collect)
        paid_inflow = inflow_df[
            inflow_df['source'].isin(['rewards_store', 'rewards_rolling_offer_collect'])
        ]['sum_value'].sum()
        
        # Calculate consumption ratio (outflow / inflow)
        consumption = (total_outflow_positive / total_inflow * 100) if total_inflow > 0 else 0
        
        row = {
            'date': date_val,
            'total_outflow': -total_outflow_positive,  # Keep negative for display (below zero)
            'total_free_inflow': free_inflow,
            'total_paid_inflow': paid_inflow,
            'consumption': consumption
        }
        if dimension:
            row[dimension] = dim_val
        
        daily_data.append(row)
    
    chart_df = pd.DataFrame(daily_data)
    
    # Ensure we have all dates in the range, even if no data
    if len(chart_df) > 0:
        min_date = chart_df['date'].min()
        max_date = chart_df['date'].max()
        
        # Ensure dates are proper date objects, not tuples
        if isinstance(min_date, tuple):
            min_date = min_date[0]
        if isinstance(max_date, tuple):
            max_date = max_date[0]
        
        # Convert to pandas Timestamp if needed
        if isinstance(min_date, pd.Timestamp):
            min_date = min_date.date()
        if isinstance(max_date, pd.Timestamp):
            max_date = max_date.date()
        
        # Create a complete date range
        all_dates = pd.date_range(start=min_date, end=max_date, freq='D').date.tolist()
        
        # Add missing dates with zero values
        existing_dates = set(chart_df['date'].tolist())
        for date_val in all_dates:
            if date_val not in existing_dates:
                row = {
                    'date': date_val,
                    'total_outflow': 0,
                    'total_free_inflow': 0,
                    'total_paid_inflow': 0,
                    'consumption': 0
                }
                if dimension:
                    # For missing dates, we need to add rows for each dimension value
                    # But for now, let's just add one row and handle dimensions separately
                    pass
                daily_data.append(row)
        
        chart_df = pd.DataFrame(daily_data)
    
    chart_df = chart_df.sort_values('date')
    return chart_df

def create_consumption_trend_chart(df, dimension=None):
    """Create daily consumption trend line chart only"""
    if len(df) == 0:
        return None
    
    chart_df = calculate_daily_aggregates(df, dimension)
    
    if len(chart_df) == 0:
        return None
    
    if dimension:
        # Create subplots for each dimension value
        unique_values = sorted(chart_df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values],
            vertical_spacing=0.1
        )
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = chart_df[chart_df[dimension] == dim_value]
            
            # Add consumption line
            fig.add_trace(
                go.Scatter(
                    x=subset['date'],
                    y=subset['consumption'],
                    mode='lines+markers',
                    name='Consumption %',
                    line=dict(color='darkblue', width=2),
                    marker=dict(size=8),
                    showlegend=(i == 1)
                ),
                row=i, col=1
            )
        
        fig.update_xaxes(title_text="Date", row=n_rows, col=1)
        fig.update_yaxes(title_text="Consumption %", row=n_rows, col=1)
        
    else:
        # Single chart
        fig = go.Figure()
        
        # Add consumption line
        fig.add_trace(
            go.Scatter(
                x=chart_df['date'],
                y=chart_df['consumption'],
                mode='lines+markers',
                name='Consumption %',
                line=dict(color='darkblue', width=2),
                marker=dict(size=8)
            )
        )
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Consumption %")
    
    fig.update_layout(
        title="Daily Consumption Trend",
        height=600 if not dimension else 200 * n_rows,
        hovermode='x unified'
    )
    
    return fig

def create_credits_components_chart(df, dimension=None):
    """Create bar chart showing credits components on single axis (outflow below zero, inflow above zero)"""
    if len(df) == 0:
        return None
    
    chart_df = calculate_daily_aggregates(df, dimension)
    
    if len(chart_df) == 0:
        return None
    
    if dimension:
        # Create subplots for each dimension value
        unique_values = sorted(chart_df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values],
            vertical_spacing=0.1
        )
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = chart_df[chart_df[dimension] == dim_value]
            
            # Add outflow (negative values, extends downward from zero)
            fig.add_trace(
                go.Bar(
                    x=subset['date'],
                    y=subset['total_outflow'],
                    name='Total Outflow',
                    marker_color='orange',
                    showlegend=(i == 1)
                ),
                row=i, col=1
            )
            
            # Add total inflow (free + paid combined, positive values, extends upward from zero)
            total_inflow = subset['total_free_inflow'] + subset['total_paid_inflow']
            fig.add_trace(
                go.Bar(
                    x=subset['date'],
                    y=total_inflow,
                    name='Total Inflow',
                    marker_color='darkblue',
                    showlegend=(i == 1)
                ),
                row=i, col=1
            )
        
        fig.update_xaxes(title_text="Date", row=n_rows, col=1)
        # Set Y-axis to show both negative and positive ranges properly
        fig.update_yaxes(
            title_text="Credits", 
            row=n_rows, col=1,
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='black'
        )
        
    else:
        # Single chart with single axis
        fig = go.Figure()
        
        # Add outflow (negative values, extends downward from zero)
        fig.add_trace(
            go.Bar(
                x=chart_df['date'],
                y=chart_df['total_outflow'],
                name='Total Outflow',
                marker_color='orange'
            )
        )
        
        # Add total inflow (free + paid combined, positive values, extends upward from zero)
        total_inflow = chart_df['total_free_inflow'] + chart_df['total_paid_inflow']
        fig.add_trace(
            go.Bar(
                x=chart_df['date'],
                y=total_inflow,
                name='Total Inflow',
                marker_color='darkblue'
            )
        )
        
        fig.update_xaxes(title_text="Date")
        # Set Y-axis to show both negative and positive ranges properly
        fig.update_yaxes(
            title_text="Credits",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='black'
        )
    
    fig.update_layout(
        title="Credits Components",
        height=600 if not dimension else 200 * n_rows,
        barmode='group',  # Group bars: outflow (negative) and inflow (positive) side by side
        hovermode='x unified'
    )
    
    return fig

def create_free_vs_paid_inflow_chart(df, dimension=None):
    """Create stacked bar chart showing Free vs Paid Inflow share as percentages"""
    if len(df) == 0:
        return None
    
    # Filter for inflow only
    inflow_df = df[df['inflow_outflow'] == 'inflow'].copy()
    if len(inflow_df) == 0:
        return None
    
    # Aggregate by date (and dimension if provided)
    if dimension:
        group_cols = ['date', dimension]
    else:
        group_cols = ['date']
    
    daily_data = []
    for date_group, group_df in inflow_df.groupby(group_cols):
        if dimension:
            date_val, dim_val = date_group
        else:
            date_val = date_group
            dim_val = None
        
        # Ensure date_val is a proper date object
        if isinstance(date_val, tuple):
            date_val = date_val[0]
        if isinstance(date_val, pd.Timestamp):
            date_val = date_val.date()
        
        # Calculate free inflow (source not in rewards_store, rewards_rolling_offer_collect)
        free_inflow = group_df[
            ~group_df['source'].isin(['rewards_store', 'rewards_rolling_offer_collect'])
        ]['sum_value'].sum()
        
        # Calculate paid inflow (source in rewards_store, rewards_rolling_offer_collect)
        paid_inflow = group_df[
            group_df['source'].isin(['rewards_store', 'rewards_rolling_offer_collect'])
        ]['sum_value'].sum()
        
        total_inflow = free_inflow + paid_inflow
        
        # Calculate percentages
        free_share = (free_inflow / total_inflow * 100) if total_inflow > 0 else 0
        paid_share = (paid_inflow / total_inflow * 100) if total_inflow > 0 else 0
        
        row = {
            'date': date_val,
            'Free Inflow': free_inflow,  # Keep absolute for tooltip
            'Paid Inflow': paid_inflow,  # Keep absolute for tooltip
            'Free Share %': free_share,
            'Paid Share %': paid_share
        }
        if dimension:
            row[dimension] = dim_val
        
        daily_data.append(row)
    
    chart_df = pd.DataFrame(daily_data)
    chart_df = chart_df.sort_values('date')
    
    if dimension:
        unique_values = sorted(chart_df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values],
            vertical_spacing=0.1
        )
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = chart_df[chart_df[dimension] == dim_value]
            
            fig.add_trace(
                go.Bar(
                    x=subset['date'],
                    y=subset['Free Share %'],
                    name='Free Inflow',
                    marker_color='green',
                    showlegend=(i == 1),
                    customdata=subset[['Free Inflow']].values,
                    hovertemplate='<b>Free Inflow</b><br>' +
                                'Date: %{x}<br>' +
                                'Share: %{y:.2f}%<br>' +
                                'Credits: %{customdata[0]:,.0f}<extra></extra>'
                ),
                row=i, col=1
            )
            
            fig.add_trace(
                go.Bar(
                    x=subset['date'],
                    y=subset['Paid Share %'],
                    name='Paid Inflow',
                    marker_color='blue',
                    showlegend=(i == 1),
                    customdata=subset[['Paid Inflow']].values,
                    hovertemplate='<b>Paid Inflow</b><br>' +
                                'Date: %{x}<br>' +
                                'Share: %{y:.2f}%<br>' +
                                'Credits: %{customdata[0]:,.0f}<extra></extra>'
                ),
                row=i, col=1
            )
        
        fig.update_xaxes(title_text="Date", row=n_rows, col=1)
        fig.update_yaxes(title_text="Share (%)", row=n_rows, col=1, range=[0, 100])
    else:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=chart_df['date'],
            y=chart_df['Free Share %'],
            name='Free Inflow',
            marker_color='green',
            customdata=chart_df[['Free Inflow']].values,
            hovertemplate='<b>Free Inflow</b><br>' +
                        'Date: %{x}<br>' +
                        'Share: %{y:.2f}%<br>' +
                        'Credits: %{customdata[0]:,.0f}<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            x=chart_df['date'],
            y=chart_df['Paid Share %'],
            name='Paid Inflow',
            marker_color='blue',
            customdata=chart_df[['Paid Inflow']].values,
            hovertemplate='<b>Paid Inflow</b><br>' +
                        'Date: %{x}<br>' +
                        'Share: %{y:.2f}%<br>' +
                        'Credits: %{customdata[0]:,.0f}<extra></extra>'
        ))
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Share (%)", range=[0, 100])
    
    fig.update_layout(
        title="Daily Free vs Paid Inflow",
        height=600 if not dimension else 200 * n_rows,
        barmode='stack',
        hovermode='x unified'
    )
    
    return fig

def create_free_share_by_source_chart(df, dimension=None):
    """Create stacked bar chart showing Free Inflow share by source"""
    if len(df) == 0:
        return None
    
    # Filter for free inflow only
    free_inflow_df = df[
        (df['inflow_outflow'] == 'inflow') &
        (~df['source'].isin(['rewards_store', 'rewards_rolling_offer_collect']))
    ].copy()
    
    if len(free_inflow_df) == 0:
        return None
    
    # Aggregate by date and source (and dimension if provided)
    if dimension:
        group_cols = ['date', 'source', dimension]
    else:
        group_cols = ['date', 'source']
    
    daily_data = []
    for date_group, group_df in free_inflow_df.groupby(group_cols):
        if dimension:
            date_val, source_val, dim_val = date_group
        else:
            date_val, source_val = date_group
            dim_val = None
        
        # Ensure date_val is a proper date object
        if isinstance(date_val, tuple):
            date_val = date_val[0]
        if isinstance(date_val, pd.Timestamp):
            date_val = date_val.date()
        
        total_free_inflow = group_df['sum_value'].sum()
        
        row = {
            'date': date_val,
            'source': source_val,
            'Free Inflow': total_free_inflow
        }
        if dimension:
            row[dimension] = dim_val
        
        daily_data.append(row)
    
    chart_df = pd.DataFrame(daily_data)
    chart_df = chart_df.sort_values('date')
    
    # Calculate shares per date
    if dimension:
        for dim_val in chart_df[dimension].unique():
            for date_val in chart_df[chart_df[dimension] == dim_val]['date'].unique():
                subset = chart_df[(chart_df['date'] == date_val) & (chart_df[dimension] == dim_val)]
                total = subset['Free Inflow'].sum()
                chart_df.loc[(chart_df['date'] == date_val) & (chart_df[dimension] == dim_val), 'Share'] = (
                    chart_df.loc[(chart_df['date'] == date_val) & (chart_df[dimension] == dim_val), 'Free Inflow'] / total * 100
                ) if total > 0 else 0
    else:
        for date_val in chart_df['date'].unique():
            subset = chart_df[chart_df['date'] == date_val]
            total = subset['Free Inflow'].sum()
            chart_df.loc[chart_df['date'] == date_val, 'Share'] = (
                chart_df.loc[chart_df['date'] == date_val, 'Free Inflow'] / total * 100
            ) if total > 0 else 0
    
    if dimension:
        unique_values = sorted(chart_df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values],
            vertical_spacing=0.1
        )
        
        sources = sorted(chart_df['source'].unique())
        colors = px.colors.qualitative.Set3[:len(sources)]
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = chart_df[chart_df[dimension] == dim_value]
            
            for j, source_val in enumerate(sources):
                source_data = subset[subset['source'] == source_val]
                if len(source_data) > 0:
                    fig.add_trace(
                        go.Bar(
                            x=source_data['date'],
                            y=source_data['Share'],
                            name=source_val,
                            marker_color=colors[j % len(colors)],
                            showlegend=(i == 1),
                            customdata=source_data[['Free Inflow']].values,
                            hovertemplate='<b>%{fullData.name}</b><br>' +
                                        'Date: %{x}<br>' +
                                        'Share: %{y:.2f}%<br>' +
                                        'Credits: %{customdata[0]:,.0f}<extra></extra>'
                        ),
                        row=i, col=1
                    )
        
        fig.update_xaxes(title_text="Date", row=n_rows, col=1)
        fig.update_yaxes(title_text="Share (%)", row=n_rows, col=1)
    else:
        sources = sorted(chart_df['source'].unique())
        colors = px.colors.qualitative.Set3[:len(sources)]
        
        fig = go.Figure()
        
        for j, source_val in enumerate(sources):
            source_data = chart_df[chart_df['source'] == source_val]
            if len(source_data) > 0:
                fig.add_trace(go.Bar(
                    x=source_data['date'],
                    y=source_data['Share'],
                    name=source_val,
                    marker_color=colors[j % len(colors)],
                    customdata=source_data[['Free Inflow']].values,
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                'Date: %{x}<br>' +
                                'Share: %{y:.2f}%<br>' +
                                'Credits: %{customdata[0]:,.0f}<extra></extra>'
                ))
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Share (%)")
    
    fig.update_layout(
        title="Daily Free Share by Source",
        height=600 if not dimension else 200 * n_rows,
        barmode='stack',
        hovermode='closest'  # Show only the hovered source, not all sources
    )
    
    return fig

def create_rtp_by_source_chart(df, dimension=None):
    """Create line chart showing RTP by source (Free Inflow / Outflow)"""
    if len(df) == 0:
        return None
    
    # First, get outflow at player-day level (to avoid double counting)
    # Outflow is stored per player per day, so we need to get unique player-day combinations
    outflow_df = df[df['inflow_outflow'] == 'outflow'].copy()
    
    if len(outflow_df) == 0:
        return None
    
    # Get unique player-day outflow totals
    # Note: total_outflow_per_player_per_day already exists in the data, but we'll calculate it to be safe
    player_day_outflow = outflow_df.groupby(['date', 'distinct_id'])['sum_value'].sum().reset_index()
    player_day_outflow['outflow'] = abs(player_day_outflow['sum_value'])  # Make positive
    
    # Ensure date is proper date type
    if 'date' in player_day_outflow.columns:
        player_day_outflow['date'] = pd.to_datetime(player_day_outflow['date']).dt.date
    
    # Aggregate outflow by date (sum across all players)
    daily_outflow = player_day_outflow.groupby('date')['outflow'].sum().reset_index()
    
    # Get free inflow by source
    free_inflow_df = df[
        (df['inflow_outflow'] == 'inflow') &
        (~df['source'].isin(['rewards_store', 'rewards_rolling_offer_collect']))
    ].copy()
    
    if len(free_inflow_df) == 0:
        return None
    
    # Aggregate free inflow by date and source (and dimension if provided)
    if dimension:
        group_cols = ['date', 'source', dimension]
    else:
        group_cols = ['date', 'source']
    
    daily_data = []
    for date_group, group_df in free_inflow_df.groupby(group_cols):
        if dimension:
            date_val, source_val, dim_val = date_group
        else:
            date_val, source_val = date_group
            dim_val = None
        
        # Ensure date_val is a proper date object
        if isinstance(date_val, tuple):
            date_val = date_val[0]
        if isinstance(date_val, pd.Timestamp):
            date_val = date_val.date()
        
        free_inflow = group_df['sum_value'].sum()
        
        # Get outflow for this date (ensure date types match)
        date_val_for_lookup = date_val
        if isinstance(date_val_for_lookup, pd.Timestamp):
            date_val_for_lookup = date_val_for_lookup.date()
        
        date_outflow = daily_outflow[daily_outflow['date'] == date_val_for_lookup]['outflow'].values
        total_outflow = date_outflow[0] if len(date_outflow) > 0 else 0
        
        # Calculate RTP
        rtp = (free_inflow / total_outflow * 100) if total_outflow > 0 else 0
        
        row = {
            'date': date_val,
            'source': source_val,
            'Free Inflow': free_inflow,
            'Total Outflow': total_outflow,
            'RTP': rtp
        }
        if dimension:
            row[dimension] = dim_val
        
        daily_data.append(row)
    
    chart_df = pd.DataFrame(daily_data)
    chart_df = chart_df.sort_values('date')
    
    if dimension:
        unique_values = sorted(chart_df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values],
            vertical_spacing=0.1
        )
        
        sources = sorted(chart_df['source'].unique())
        colors = px.colors.qualitative.Set1[:len(sources)]
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = chart_df[chart_df[dimension] == dim_value]
            
            for j, source_val in enumerate(sources):
                source_data = subset[subset['source'] == source_val].sort_values('date')
                if len(source_data) > 0:
                    fig.add_trace(
                        go.Scatter(
                            x=source_data['date'],
                            y=source_data['RTP'],
                            mode='lines+markers',
                            name=source_val,
                            line=dict(color=colors[j % len(colors)], width=2),
                            marker=dict(size=6),
                            showlegend=(i == 1)
                        ),
                        row=i, col=1
                    )
        
        fig.update_xaxes(title_text="Date", row=n_rows, col=1)
        fig.update_yaxes(title_text="RTP (%)", row=n_rows, col=1)
    else:
        sources = sorted(chart_df['source'].unique())
        colors = px.colors.qualitative.Set1[:len(sources)]
        
        fig = go.Figure()
        
        for j, source_val in enumerate(sources):
            source_data = chart_df[chart_df['source'] == source_val].sort_values('date')
            if len(source_data) > 0:
                fig.add_trace(go.Scatter(
                    x=source_data['date'],
                    y=source_data['RTP'],
                    mode='lines+markers',
                    name=source_val,
                    line=dict(color=colors[j % len(colors)], width=2),
                    marker=dict(size=6)
                ))
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="RTP (%)")
    
    fig.update_layout(
        title="Daily RTP by Source",
        height=600 if not dimension else 200 * n_rows,
        hovermode='x unified'
    )
    
    return fig

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

def main():
    # Authentication
    if not authenticate_user():
        return
    
    st.title("📊 Consumption Dashboard")
    
    # Initialize BigQuery client
    client = init_bigquery_client()
    if client is None:
        st.stop()
    
    # Load data with loading indicator and progress
    with st.spinner("Loading data from BigQuery (this may take 10-30 seconds)..."):
        # Load last 30 days by default for faster initial load
        # User can expand date range using the filter
        try:
            df = load_data(client, date_limit_days=30)
        except Exception as e:
            st.error(f"Error loading data: {e}")
            st.info("💡 Tip: The query might be taking too long. Try reducing the date range or check your BigQuery connection.")
            return
    
    if len(df) == 0:
        st.warning("No data available for the last 30 days.")
        st.info("💡 Tip: The dashboard loads the last 30 days by default for faster performance. Use the date filter to expand the range.")
        return
    
    # Show data info
    st.caption(f"📊 Loaded {len(df):,} rows from last 30 days. Use date filter to expand range.")
    
    # ============================================================================
    # FILTERS WITH APPLY BUTTON
    # ============================================================================
    
    st.sidebar.header("Filters")
    
    # Initialize filter state
    if 'filter_temp' not in st.session_state:
        # Initialize date_range to None - will be set to full range below
        st.session_state.filter_temp = {
            'date_range': None,
            'first_chapter_of_day': [],
            'inflow_outflow': [],
            'is_us_player': [],
            'last_balance_of_day': [],
            'last_version_of_day': [],
            'paid_ever_flag': [],
            'paid_today_flag': [],
            'source': []
        }
    
    if 'filter_applied' not in st.session_state:
        st.session_state.filter_applied = st.session_state.filter_temp.copy()
    
    # Initialize date_range to full available range if not set
    if st.session_state.filter_applied.get('date_range') is None:
        if 'date' in df.columns and len(df) > 0:
            min_date = df['date'].min()
            max_date = df['date'].max()
            st.session_state.filter_applied['date_range'] = (min_date, max_date)
            st.session_state.filter_temp['date_range'] = (min_date, max_date)
    
    # Prepare filter options
    # Get date range from loaded data for the slider
    if 'date' in df.columns and len(df) > 0:
        min_date = df['date'].min()
        max_date = df['date'].max()
        date_range = (min_date, max_date)
    else:
        date_range = (None, None)
    
    # Query actual min/max dates from table for slider range (lightweight query)
    try:
        range_query = f"""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM `{FULL_TABLE}`
        """
        range_df = client.query(range_query).to_dataframe()
        if len(range_df) > 0 and pd.notna(range_df['min_date'].iloc[0]) and pd.notna(range_df['max_date'].iloc[0]):
            actual_min_date = pd.to_datetime(range_df['min_date'].iloc[0]).date()
            actual_max_date = pd.to_datetime(range_df['max_date'].iloc[0]).date()
            # Use actual range for slider, but keep loaded data range as default
            if date_range[0] is None:
                date_range = (actual_min_date, actual_max_date)
            else:
                # Extend slider range to show full available range
                date_range = (actual_min_date, actual_max_date)
    except Exception as e:
        # Fallback to loaded data range if query fails
        pass
    
    # Add bucketed columns for filtering
    df['first_chapter_bucket'] = df['first_chapter_of_day'].apply(bucket_first_chapter)
    df['last_balance_bucket'] = df['last_balance_of_day'].apply(bucket_last_balance)
    
    # Date range filter (using slider with date conversion)
    if date_range[0] and date_range[1]:
        # Convert dates to days since min_date for slider
        min_date = date_range[0]
        max_date = date_range[1]
        date_list = pd.date_range(start=min_date, end=max_date, freq='D').date.tolist()
        
        # Get current date range from state or use full range
        current_range = st.session_state.filter_temp.get('date_range')
        if current_range is None:
            current_range = (min_date, max_date)
        
        # Convert current range to indices
        try:
            start_idx = date_list.index(current_range[0]) if current_range[0] in date_list else 0
            end_idx = date_list.index(current_range[1]) if current_range[1] in date_list else len(date_list) - 1
        except:
            start_idx = 0
            end_idx = len(date_list) - 1
        
        st.sidebar.write("**Date Range**")
        selected_indices = st.sidebar.slider(
            "Select Date Range",
            min_value=0,
            max_value=len(date_list) - 1,
            value=(start_idx, end_idx),
            format="Day {}"
        )
        
        # Convert indices back to dates
        selected_start_date = date_list[selected_indices[0]]
        selected_end_date = date_list[selected_indices[1]]
        selected_date_range = (selected_start_date, selected_end_date)
        st.session_state.filter_temp['date_range'] = selected_date_range
        
        # Display selected range
        st.sidebar.caption(f"From: {selected_start_date} to {selected_end_date}")
    
    # First chapter filter
    chapter_options = sorted(df['first_chapter_bucket'].dropna().unique())
    selected_chapter = st.sidebar.multiselect(
        "First Chapter of Day",
        options=chapter_options,
        default=st.session_state.filter_temp.get('first_chapter_of_day', [])
    )
    st.session_state.filter_temp['first_chapter_of_day'] = selected_chapter
    
    # Inflow/Outflow filter
    inflow_outflow_options = sorted(df['inflow_outflow'].dropna().unique())
    selected_inflow_outflow = st.sidebar.multiselect(
        "Inflow/Outflow",
        options=inflow_outflow_options,
        default=st.session_state.filter_temp.get('inflow_outflow', [])
    )
    st.session_state.filter_temp['inflow_outflow'] = selected_inflow_outflow
    
    # Is US Player filter
    us_player_options = sorted(df['is_us_player'].dropna().unique())
    selected_us_player = st.sidebar.multiselect(
        "Is US Player",
        options=us_player_options,
        default=st.session_state.filter_temp.get('is_us_player', [])
    )
    st.session_state.filter_temp['is_us_player'] = selected_us_player
    
    # Last balance filter
    balance_options = sorted(df['last_balance_bucket'].dropna().unique())
    selected_balance = st.sidebar.multiselect(
        "Last Balance of Day",
        options=balance_options,
        default=st.session_state.filter_temp.get('last_balance_of_day', [])
    )
    st.session_state.filter_temp['last_balance_of_day'] = selected_balance
    
    # Last version filter
    version_options = sorted(df['last_version_of_day'].dropna().unique())
    selected_version = st.sidebar.multiselect(
        "Last Version of Day",
        options=version_options,
        default=st.session_state.filter_temp.get('last_version_of_day', [])
    )
    st.session_state.filter_temp['last_version_of_day'] = selected_version
    
    # Paid ever flag filter
    paid_ever_options = sorted(df['paid_ever_flag'].dropna().unique())
    selected_paid_ever = st.sidebar.multiselect(
        "Paid Ever Flag",
        options=paid_ever_options,
        default=st.session_state.filter_temp.get('paid_ever_flag', [])
    )
    st.session_state.filter_temp['paid_ever_flag'] = selected_paid_ever
    
    # Paid today flag filter
    paid_today_options = sorted(df['paid_today_flag'].dropna().unique())
    selected_paid_today = st.sidebar.multiselect(
        "Paid Today Flag",
        options=paid_today_options,
        default=st.session_state.filter_temp.get('paid_today_flag', [])
    )
    st.session_state.filter_temp['paid_today_flag'] = selected_paid_today
    
    # Source filter
    source_options = sorted(df['source'].dropna().unique())
    selected_source = st.sidebar.multiselect(
        "Source",
        options=source_options,
        default=st.session_state.filter_temp.get('source', [])
    )
    st.session_state.filter_temp['source'] = selected_source
    
    # Apply button
    if st.sidebar.button("✅ Apply Filters", type="primary"):
        st.session_state.filter_applied = st.session_state.filter_temp.copy()
        st.rerun()
    
    # Apply filters
    filters = st.session_state.filter_applied
    
    # Check if we need to reload data based on date range
    # Only reload if user selected a date range outside currently loaded data
    if filters.get('date_range'):
        date_min, date_max = filters['date_range']
        # Check if the requested range is outside loaded data
        if len(df) > 0:
            loaded_min = df['date'].min()
            loaded_max = df['date'].max()
            if date_min < loaded_min or date_max > loaded_max:
                # Need to reload with expanded range
                # Calculate days needed from today
                from datetime import date
                today = date.today()
                days_needed = max(
                    (today - date_min).days + 1,
                    30  # Minimum 30 days
                )
                with st.spinner(f"Loading data for selected date range ({date_min} to {date_max})..."):
                    # Clear cache and reload
                    load_data.clear()
                    df = load_data(client, date_limit_days=days_needed)
    
    filtered_df = df.copy()
    
    # Apply date range filter
    # If no date range is set, show all available data
    if filters.get('date_range'):
        date_min, date_max = filters['date_range']
        filtered_df = filtered_df[
            (filtered_df['date'] >= date_min) & 
            (filtered_df['date'] <= date_max)
        ]
    # If no date range filter is applied, show all loaded data (no filtering)
    if filters.get('first_chapter_of_day'):
        filtered_df = filtered_df[filtered_df['first_chapter_bucket'].isin(filters['first_chapter_of_day'])]
    if filters.get('inflow_outflow'):
        filtered_df = filtered_df[filtered_df['inflow_outflow'].isin(filters['inflow_outflow'])]
    if filters.get('is_us_player'):
        filtered_df = filtered_df[filtered_df['is_us_player'].isin(filters['is_us_player'])]
    if filters.get('last_balance_of_day'):
        filtered_df = filtered_df[filtered_df['last_balance_bucket'].isin(filters['last_balance_of_day'])]
    if filters.get('last_version_of_day'):
        filtered_df = filtered_df[filtered_df['last_version_of_day'].isin(filters['last_version_of_day'])]
    if filters.get('paid_ever_flag'):
        filtered_df = filtered_df[filtered_df['paid_ever_flag'].isin(filters['paid_ever_flag'])]
    if filters.get('paid_today_flag'):
        filtered_df = filtered_df[filtered_df['paid_today_flag'].isin(filters['paid_today_flag'])]
    if filters.get('source'):
        filtered_df = filtered_df[filtered_df['source'].isin(filters['source'])]
    
    # ============================================================================
    # DIMENSION SELECTOR
    # ============================================================================
    
    st.sidebar.header("Dimension Selector")
    
    dimension_options = {
        'None': None,
        'First Chapter of Day': 'first_chapter_bucket',
        'Is US Player': 'is_us_player',
        'Last Balance of Day': 'last_balance_bucket',
        'Last Version of Day': 'last_version_of_day',
        'Paid Ever Flag': 'paid_ever_flag',
        'Paid Today Flag': 'paid_today_flag'
    }
    
    selected_dimension_label = st.sidebar.selectbox(
        "Split by Dimension",
        options=list(dimension_options.keys()),
        index=0
    )
    selected_dimension = dimension_options[selected_dimension_label]
    
    # ============================================================================
    # MAIN CONTENT
    # ============================================================================
    
    if len(filtered_df) == 0:
        st.warning("No data matches the selected filters.")
        return
    
    # View 1: Daily Consumption (Trend Line Only)
    st.header("Daily Consumption")
    st.markdown("**Consumption = Total Outflow / Total Inflow** (line trend)")
    
    # Debug info (can be removed later)
    if filters.get('date_range'):
        date_min, date_max = filters['date_range']
        unique_dates = sorted(filtered_df['date'].unique()) if len(filtered_df) > 0 else []
        st.caption(f"📅 Date range: {date_min} to {date_max} | 📊 Days with data: {len(unique_dates)} ({', '.join(str(d) for d in unique_dates[:5])}{'...' if len(unique_dates) > 5 else ''})")
    
    consumption_trend_chart = create_consumption_trend_chart(filtered_df, selected_dimension)
    if consumption_trend_chart:
        st.plotly_chart(consumption_trend_chart, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")
    
    # View 2: Credits Components (Bar Chart)
    st.header("Credits Components")
    st.markdown("**Bars show:** Total Outflow (negative), Total Free Inflow, Total Paid Inflow")
    
    credits_components_chart = create_credits_components_chart(filtered_df, selected_dimension)
    if credits_components_chart:
        st.plotly_chart(credits_components_chart, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")
    
    # New View 1: Daily Free vs Paid Inflow
    st.header("Daily Free vs Paid Inflow")
    st.markdown("**Stacked bars showing share of Free Inflow vs Paid Inflow**")
    
    free_vs_paid_chart = create_free_vs_paid_inflow_chart(filtered_df, selected_dimension)
    if free_vs_paid_chart:
        st.plotly_chart(free_vs_paid_chart, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")
    
    # New View 2: Daily Free Share by Source
    st.header("Daily Free Share by Source")
    st.markdown("**Stacked bars showing share of Free Inflow by source (hover for absolute values)**")
    
    free_share_by_source_chart = create_free_share_by_source_chart(filtered_df, selected_dimension)
    if free_share_by_source_chart:
        st.plotly_chart(free_share_by_source_chart, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")
    
    # New View 3: Daily RTP by Source
    st.header("Daily RTP by Source")
    st.markdown("**RTP = Total Free Inflow (by source) / Total Outflow** (line chart per source)")
    st.caption("Note: Outflow is calculated at player-day level to avoid double counting")
    
    rtp_by_source_chart = create_rtp_by_source_chart(filtered_df, selected_dimension)
    if rtp_by_source_chart:
        st.plotly_chart(rtp_by_source_chart, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

if __name__ == "__main__":
    main()

