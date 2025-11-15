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
        except (KeyError, AttributeError, TypeError):
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
        except (KeyError, AttributeError, TypeError):
            pass
    
    if not client_id:
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    if not client_secret:
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return None
    
    redirect_uri = None
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
        except (KeyError, AttributeError, TypeError):
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
                except (KeyError, AttributeError, TypeError):
                    pass
            
            if not redirect_uri:
                redirect_uri = os.environ.get('STREAMLIT_REDIRECT_URI', "https://consumption-dashboard.streamlit.app/")
            
            client_id = None
            client_secret = None
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
                except (KeyError, AttributeError, TypeError):
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
                except (KeyError, AttributeError, TypeError):
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
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(f"Access denied. Email {email} is not authorized.")
                    return False
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return False
    else:
        auth_url = get_google_oauth_url()
        if auth_url:
            st.markdown("""
            <script>
            window.location.replace("""" + auth_url + """");
            </script>
            """, unsafe_allow_html=True)
            return False
        else:
            st.warning("OAuth not configured. Proceeding without authentication.")
            st.session_state.authenticated = True
            return True
    
    return st.session_state.authenticated

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
        
        # Method 2: Service account JSON file path (for local development)
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
            return client
        
        # Method 3: Application Default Credentials (for local development)
        try:
            credentials, project = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
            return client
        except Exception as adc_error:
            st.error("❌ Failed to initialize BigQuery client")
            st.error("**Authentication Error:** No valid credentials found.")
            return None
            
    except Exception as e:
        st.error(f"❌ Failed to initialize BigQuery client: {e}")
        return None

@st.cache_data(ttl=60)
def load_data(_client):
    """Load data from BigQuery"""
    try:
        query = f"""
        SELECT *
        FROM `{FULL_TABLE}`
        ORDER BY date DESC, distinct_id, source
        """
        
        df = _client.query(query).to_dataframe()
        
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

def create_daily_consumption_chart(df, dimension=None):
    """Create daily consumption chart with line and stacked bars"""
    if len(df) == 0:
        return None
    
    # Aggregate data by date (and dimension if provided)
    if dimension:
        group_cols = ['date', dimension]
    else:
        group_cols = ['date']
    
    # Calculate daily aggregates
    daily_data = []
    for date_group, group_df in df.groupby(group_cols):
        if dimension:
            date_val, dim_val = date_group
        else:
            date_val = date_group
            dim_val = None
        
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
    chart_df = chart_df.sort_values('date')
    
    if dimension:
        # Create subplots for each dimension value
        unique_values = sorted(chart_df[dimension].dropna().unique())
        n_rows = len(unique_values)
        
        fig = make_subplots(
            rows=n_rows, cols=1,
            subplot_titles=[f"{dimension}: {val}" for val in unique_values],
            vertical_spacing=0.1,
            specs=[[{"secondary_y": True}] for _ in range(n_rows)]
        )
        
        for i, dim_value in enumerate(unique_values, 1):
            subset = chart_df[chart_df[dimension] == dim_value]
            
            # Add stacked bars
            fig.add_trace(
                go.Bar(
                    x=subset['date'],
                    y=subset['total_outflow'],
                    name='Total Outflow',
                    marker_color='red',
                    showlegend=(i == 1)
                ),
                row=i, col=1, secondary_y=False
            )
            
            fig.add_trace(
                go.Bar(
                    x=subset['date'],
                    y=subset['total_free_inflow'],
                    name='Total Free Inflow',
                    marker_color='orange',
                    showlegend=(i == 1)
                ),
                row=i, col=1, secondary_y=False
            )
            
            fig.add_trace(
                go.Bar(
                    x=subset['date'],
                    y=subset['total_paid_inflow'],
                    name='Total Paid Inflow',
                    marker_color='blue',
                    showlegend=(i == 1)
                ),
                row=i, col=1, secondary_y=False
            )
            
            # Add consumption line
            fig.add_trace(
                go.Scatter(
                    x=subset['date'],
                    y=subset['consumption'],
                    mode='lines+markers',
                    name='Consumption %',
                    line=dict(color='darkblue', width=2),
                    showlegend=(i == 1)
                ),
                row=i, col=1, secondary_y=True
            )
        
        fig.update_xaxes(title_text="Date", row=n_rows, col=1)
        fig.update_yaxes(title_text="Credits", row=n_rows, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Consumption %", row=n_rows, col=1, secondary_y=True)
        
    else:
        # Single chart
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add stacked bars
        fig.add_trace(
            go.Bar(
                x=chart_df['date'],
                y=chart_df['total_outflow'],
                name='Total Outflow',
                marker_color='red'
            ),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Bar(
                x=chart_df['date'],
                y=chart_df['total_free_inflow'],
                name='Total Free Inflow',
                marker_color='orange'
            ),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Bar(
                x=chart_df['date'],
                y=chart_df['total_paid_inflow'],
                name='Total Paid Inflow',
                marker_color='blue'
            ),
            secondary_y=False
        )
        
        # Add consumption line
        fig.add_trace(
            go.Scatter(
                x=chart_df['date'],
                y=chart_df['consumption'],
                mode='lines+markers',
                name='Consumption %',
                line=dict(color='darkblue', width=2)
            ),
            secondary_y=True
        )
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Credits", secondary_y=False)
        fig.update_yaxes(title_text="Consumption %", secondary_y=True)
    
    fig.update_layout(
        title="Daily Consumption",
        height=600 if not dimension else 200 * n_rows,
        barmode='stack',
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
    
    # Load data
    df = load_data(client)
    
    if len(df) == 0:
        st.warning("No data available.")
        return
    
    # ============================================================================
    # FILTERS WITH APPLY BUTTON
    # ============================================================================
    
    st.sidebar.header("Filters")
    
    # Initialize filter state
    if 'filter_temp' not in st.session_state:
        st.session_state.filter_temp = {
            'date': None,
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
    
    # Prepare filter options
    date_range = (df['date'].min(), df['date'].max()) if 'date' in df.columns else (None, None)
    
    # Add bucketed columns for filtering
    df['first_chapter_bucket'] = df['first_chapter_of_day'].apply(bucket_first_chapter)
    df['last_balance_bucket'] = df['last_balance_of_day'].apply(bucket_last_balance)
    
    # Date filter
    if date_range[0] and date_range[1]:
        selected_date = st.sidebar.date_input(
            "Date",
            value=st.session_state.filter_temp.get('date') or date_range[1],
            min_value=date_range[0],
            max_value=date_range[1]
        )
        st.session_state.filter_temp['date'] = selected_date
    
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
    filtered_df = df.copy()
    filters = st.session_state.filter_applied
    
    if filters.get('date'):
        filtered_df = filtered_df[filtered_df['date'] == filters['date']]
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
    
    # Daily Consumption View
    st.header("Daily Consumption")
    st.markdown("**Consumption = Total Outflow / Total Inflow** (line trend)")
    st.markdown("**Bars show:** Total Outflow (negative), Total Free Inflow, Total Paid Inflow")
    
    consumption_chart = create_daily_consumption_chart(filtered_df, selected_dimension)
    if consumption_chart:
        st.plotly_chart(consumption_chart, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

if __name__ == "__main__":
    main()

