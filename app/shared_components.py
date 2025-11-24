"""
Shared components for Clinical Control Tower (CCT) Dashboard

This module provides reusable functions and styling that are used
across multiple pages of the CCT multipage Streamlit application.
"""

import streamlit as st
import pandas as pd
from snowflake.snowpark import Session


# =====================================================
# CSS Styling - Applied to all pages
# =====================================================

def apply_custom_css():
    """Apply CCT theme colors and styling across all pages"""
    st.markdown("""
    <style>
        /* Primary color for progress bars and interactive elements */
        .stProgress > div > div > div > div {
            background-color: #F25D18;
        }
        
        /* Progress column styling */
        [data-testid="stMetricValue"] {
            color: #F25D18;
        }
        
        /* Button primary color */
        .stButton > button[kind="primary"] {
            background-color: #F25D18;
            border-color: #F25D18;
        }
        
        .stButton > button[kind="primary"]:hover {
            background-color: #D94D10;
            border-color: #D94D10;
        }
        
        /* Selection highlights */
        [data-testid="stDataFrame"] [data-selected="true"] {
            background-color: rgba(242, 93, 24, 0.1) !important;
        }
        
        /* Checkbox and radio button accent color */
        .stCheckbox > label > span:first-child,
        .stRadio > label > span:first-child {
            background-color: #F25D18;
        }
        
        /* Chat input styling */
        .stChatInput > div > div {
            border-color: #F25D18;
        }
        
        /* Chat message styling */
        .stChatMessage {
            border-left: 3px solid #F25D18;
        }
        
        /* Style Off Track cells with peach background */
        [data-testid="stDataFrame"] [role="gridcell"]:has(> div > div:contains("🟠 Off Track")) {
            background-color: #F7A078 !important;
            font-weight: 600;
        }
        
        /* Style At Risk cells with light orange background */
        [data-testid="stDataFrame"] [role="gridcell"]:has(> div > div:contains("🟡 At Risk")) {
            background-color: #FFE6CC !important;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)


# =====================================================
# Snowflake Connection
# =====================================================

@st.cache_resource
def get_snowflake_session():
    """Create and cache Snowflake session"""
    try:
        connection_parameters = {
            "account": st.secrets["snowflake"]["account"],
            "user": st.secrets["snowflake"]["user"],
            "password": st.secrets["snowflake"]["password"],
            "role": st.secrets["snowflake"]["role"],
            "warehouse": st.secrets["snowflake"]["warehouse"],
            "database": st.secrets["snowflake"]["database"],
            "schema": st.secrets["snowflake"]["schema"]
        }
        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        st.info("Please configure your Snowflake credentials in .streamlit/secrets.toml")
        return None


# =====================================================
# Data Loading Functions
# =====================================================

@st.cache_data(ttl=300)
def load_trial_summary():
    """Load trial summary metrics for the main dataframe"""
    session = get_snowflake_session()
    if session is None:
        return pd.DataFrame()

    query = """
    SELECT 
        study_id,
        product_name as drug_name,
        enrollment_start_date as start_date,
        target_enrollment_end_date as forecast_completion_date,
        enrollment_percent_complete as current_enrollment_attainment,
        actual_enrollment_total as actual_enrollment,
        planned_enrollment_to_date as planned_enrollment,
        planned_enrollment_total,
        trial_status,
        phase,
        study_name,
        trial_projected_delay_weeks
    FROM AEGIS_CCT.COMBINED.vw_trial_performance
    ORDER BY study_id
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=300)
def load_trial_enrollment_timeseries(study_id):
    """Load enrollment time series for a specific trial (including future projections)"""
    session = get_snowflake_session()
    if session is None:
        return pd.DataFrame()
    
    query = f"""
    SELECT 
        date,
        SUM(planned_enrollment) as planned_enrollment,
        SUM(actual_enrollment) as actual_enrollment
    FROM AEGIS_CCT.COMBINED.fct_enrollment
    WHERE study_id = '{study_id}'
    GROUP BY date
    ORDER BY date
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=3600)
def load_agent_info():
    """Load agent tools and example questions from the agent spec"""
    session = get_snowflake_session()
    if session is None:
        return {'tools': [], 'examples': []}
    
    try:
        # Query the agent spec to get agent information
        query = "DESCRIBE AGENT cct_agent"
        result = session.sql(query).collect()
        
        if result and len(result) > 0:
            import json
            # DESCRIBE AGENT returns lowercase column names
            agent_spec = json.loads(result[0]['agent_spec'])
            
            # Extract tool names and descriptions from the agent spec
            tools = []
            if 'tools' in agent_spec:
                for tool in agent_spec['tools']:
                    # Tool info is nested in tool_spec
                    if 'tool_spec' in tool:
                        tool_spec = tool['tool_spec']
                        tool_info = {
                            'name': tool_spec.get('name', ''),
                            'description': tool_spec.get('description', '')
                        }
                        if tool_info['name']:  # Only add if we have a name
                            tools.append(tool_info)
            
            # Extract example questions from instructions.sample_questions
            examples = []
            if 'instructions' in agent_spec and 'sample_questions' in agent_spec['instructions']:
                sample_questions = agent_spec['instructions']['sample_questions']
                for sq in sample_questions:
                    if isinstance(sq, dict) and 'question' in sq:
                        examples.append(sq['question'])
                    elif isinstance(sq, str):
                        examples.append(sq)
            
            return {'tools': tools, 'examples': examples}
    except Exception as e:
        # Log error for debugging but don't crash the app
        import traceback
        print(f"Error loading agent info: {str(e)}")
        print(traceback.format_exc())
        return {'tools': [], 'examples': []}
    
    return {'tools': [], 'examples': []}


# =====================================================
# Sidebar Rendering - Portfolio metrics for all pages
# =====================================================

def render_portfolio_sidebar(trial_df):
    """Render portfolio metrics sidebar - visible across all pages"""
    with st.sidebar:
       
        # Portfolio Summary - 2 columns in one container
        st.subheader("Portfolio Summary")
        
        with st.container(border=True):
            total_trials = len(trial_df)
            total_actual = trial_df['ACTUAL_ENROLLMENT'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Active Trials", total_trials)
            with col2:
                st.metric("Total Subjects Enrolled", f"{int(total_actual):,}")
        
        # Trial Status
        st.subheader("Trial Status")
        
        with st.container(border=True):
            status_counts = trial_df['TRIAL_STATUS'].value_counts()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                off_track_count = status_counts.get('Off Track', 0)
                st.metric("🟠 Off Track", off_track_count)
            
            with col2:
                at_risk_count = status_counts.get('At Risk', 0)
                st.metric("🟡 At Risk", at_risk_count)
            
            with col3:
                on_track_count = status_counts.get('On Track', 0)
                st.metric("On Track", on_track_count)


def render_ai_sidebar_additions(chat_instance=None):
    """Render AI-specific sidebar additions (clear history, examples, capabilities)"""
    with st.sidebar:
        st.divider()
        
        # Example questions
        st.subheader("💬 Assistant Info")
        
        agent_info = load_agent_info()
        
        with st.expander("💡 Example Questions", expanded=True):
            if agent_info['examples']:
                for example in agent_info['examples']:
                    st.markdown(f"- {example}")
            else:
                st.markdown("""
                **Trial Performance:**
                - Which trials are off track and why?
                - Show enrollment trends for Study ABC123
                
                **Site Performance:**
                - Which sites are at risk?
                - Show site performance by geography
                
                **Forecasting:**
                - What is projected delay for off-track trials?
                """)   

        
        with st.expander("🔧 Agent Capabilities", expanded=False):
            if agent_info['tools']:
                st.markdown("**Available Tools:**")
                for tool in agent_info['tools']:
                    st.markdown(f"**`{tool['name']}`**")
                    if tool.get('description'):
                        st.caption(tool['description'])
                    st.markdown("")
            else:
                st.markdown("""
                The AI assistant can:
                - Query trial enrollment data
                - Analyze site performance metrics
                - Generate forecasts and predictions
                """)

        # Settings section (if chat instance provided)
        if chat_instance:
            with st.expander("⚙️ Settings", expanded=False):
                chat_instance.render_thinking_toggle()
                chat_instance.render_debug_toggle()

        # Clear history button (if chat instance provided)
        if chat_instance:
            if st.button("🗑️ Clear Chat History", use_container_width=True):
                chat_instance.clear_history()
                st.rerun()
        
        st.divider()
        # Connection status at very bottom
        session = get_snowflake_session()
        if session:
            st.info("✓ Connected to Snowflake")
        else:
            st.error("✗ Not connected to Snowflake")
