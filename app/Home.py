"""
Project Aegis: Clinical Control Tower (CCT) Dashboard
Main dashboard page for monitoring clinical trial performance
"""

import streamlit as st
import pandas as pd
import altair as alt
from shared_components import (
    get_snowflake_session,
    load_trial_summary,
    load_trial_enrollment_timeseries,
    apply_custom_css,
    render_portfolio_sidebar
)

# Page configuration
st.set_page_config(
    page_title="Enrollment",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply shared styling
apply_custom_css()

# Initialize session
session = get_snowflake_session()

# =====================================================
# Main Dashboard
# =====================================================

def main():
    """Main application entry point"""
    
    st.title("🏥 Clinical Control Tower")
    st.caption("Real-time monitoring of clinical trial enrollment performance")
    
    if session is None:
        st.error("Cannot connect to Snowflake. Please check your configuration.")
        return
    
    # Load trial data with spinner
    with st.spinner("Loading trial data..."):
        trial_df = load_trial_summary()
    
    if trial_df.empty:
        st.warning("No trial data available.")
        return
    
    # Render sidebar with portfolio metrics
    render_portfolio_sidebar(trial_df)
    
    # Add About section and connection status to sidebar
    with st.sidebar:
        with st.expander("ℹ️ About This Dashboard"):
            st.markdown("""
            **Project Aegis**  
            Clinical Control Tower
            
            This dashboard provides real-time monitoring of clinical trial enrollment 
            performance across your portfolio.
            
            **Features:**
            - Portfolio-level metrics
            - Trial-by-trial status tracking
            - Interactive enrollment timelines
            - Filtering by status and phase
        """)
        
        st.divider()
        
        # Refresh button
        if st.button("🔄 Refresh Data", type="primary", use_container_width=True, help="Reconnect to Snowflake and refresh all data"):
            # Clear all caches
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success("Data refreshed successfully!")
            st.rerun()
        
        # Connection status at bottom
        if session:
            st.info("✓ Connected to Snowflake")
        else:
            st.error("✗ Not connected to Snowflake")
    
    # Render dashboard content
    render_dashboard_content(trial_df)


def render_dashboard_content(trial_df):
    """Render the main dashboard content with trial metrics and charts"""
    
    # =====================================================
    # Alert for Off-Track Trials
    # =====================================================
    
    off_track_count = len(trial_df[trial_df['TRIAL_STATUS'] == 'Off Track'])
    at_risk_count = len(trial_df[trial_df['TRIAL_STATUS'] == 'At Risk'])
    
    if off_track_count > 0:
        st.warning(f"⚠️ **Alert:** {off_track_count} {'trial is' if off_track_count == 1 else 'trials are'} currently **Off Track** for **Enrollment vs. Plan**")
    
    if at_risk_count > 0:
        st.info(f"ℹ️ {at_risk_count} {'trial is' if at_risk_count == 1 else 'trials are'} currently **At Risk** and should be monitored closely.")
    
    # =====================================================
    # Filters
    # =====================================================
    
    st.header("Trial Enrollment Overview")
    
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
    
    with filter_col1:
        status_options = ['All'] + sorted(trial_df['TRIAL_STATUS'].unique().tolist())
        status_filter = st.selectbox(
            "Filter by Status",
            options=status_options,
            help="Filter trials by their current status"
        )
    
    with filter_col2:
        phase_options = ['All'] + sorted(trial_df['PHASE'].unique().tolist())
        phase_filter = st.selectbox(
            "Filter by Phase",
            options=phase_options,
            help="Filter trials by clinical phase"
        )
    
    with filter_col3:
        st.write("")  # Spacer
    
    # Apply filters
    filtered_df = trial_df.copy()
    if status_filter != 'All':
        filtered_df = filtered_df[filtered_df['TRIAL_STATUS'] == status_filter]
    if phase_filter != 'All':
        filtered_df = filtered_df[filtered_df['PHASE'] == phase_filter]
    
    st.caption(f"Showing {len(filtered_df)} of {len(trial_df)} trials")

    # =====================================================
    # Trial Summary Table
    # =====================================================
    
    display_df = filtered_df.copy()
    
    # Format dates
    if 'START_DATE' in display_df.columns:
        display_df['START_DATE'] = pd.to_datetime(display_df['START_DATE']).dt.strftime('%Y-%m-%d')
    if 'FORECAST_COMPLETION_DATE' in display_df.columns:
        display_df['FORECAST_COMPLETION_DATE'] = pd.to_datetime(display_df['FORECAST_COMPLETION_DATE']).dt.strftime('%Y-%m-%d')
    
    # Select and rename columns
    display_columns = {
        'STUDY_ID': 'Trial ID',
        'DRUG_NAME': 'Drug Name',
        'TRIAL_STATUS': 'Status',
        'PHASE': 'Phase',
        'START_DATE': 'Start Date',
        'FORECAST_COMPLETION_DATE': 'Target Completion',
        'TRIAL_PROJECTED_DELAY_WEEKS': 'Projected Delay (Weeks)',
        'CURRENT_ENROLLMENT_ATTAINMENT': 'Enrollment vs. Plan',
        'ACTUAL_ENROLLMENT': 'Enrolled',
        'PLANNED_ENROLLMENT': 'Target (to date)'
    }
    
    display_df_filtered = display_df[list(display_columns.keys())].copy()
    display_df_filtered.columns = list(display_columns.values())
    
    # Add status indicator with emojis
    def get_status_indicator(status):
        if status == 'Off Track':
            return '🟠 Off Track'
        elif status == 'At Risk':
            return '🟡 At Risk'
        else:
            return 'On Track'
    
    display_df_filtered['Status'] = display_df_filtered['Status'].apply(get_status_indicator)
    
    # Column configuration
    column_config = {
        'Trial ID': st.column_config.TextColumn(
            'Trial ID',
            help='Clinical trial identifier',
            width='small'
        ),
        'Drug Name': st.column_config.TextColumn(
            'Drug Name',
            help='Investigational product name',
            width='medium'
        ),
        'Status': st.column_config.TextColumn(
            'Status',
            help='Current trial status',
            width='small'
        ),
        'Phase': st.column_config.TextColumn(
            'Phase',
            width='small'
        ),
        'Start Date': st.column_config.DateColumn(
            'Start Date',
            format='YYYY-MM-DD',
            width='small'
        ),
        'Target Completion': st.column_config.DateColumn(
            'Target Completion',
            help='Forecast enrollment completion date',
            format='YYYY-MM-DD',
            width='small'
        ),
        'Projected Delay (Weeks)': st.column_config.NumberColumn(
            'Projected Delay (Weeks)',
            help='Number of weeks this trial is projected to extend beyond its target completion date',
            format='%d',
            width='small'
        ),
        'Enrollment vs. Plan': st.column_config.ProgressColumn(
            'Enrollment vs. Plan',
            help='Percentage of planned enrollment achieved as of today compared to the enrollment target for this date',
            format='%.1f%%',
            min_value=0,
            max_value=100,
            width='medium'
        ),
        'Enrolled': st.column_config.NumberColumn(
            'Enrolled',
            help='Actual subjects enrolled to date',
            format='%d',
            width='small'
        ),
        'Target (to date)': st.column_config.NumberColumn(
            'Target (to date)',
            help='Number of subjects that should have been enrolled by today according to the enrollment plan',
            format='%d',
            width='small'
        )
    }
    
    with st.container(border=True):
        event = st.dataframe(
            display_df_filtered,
            column_config=column_config,
            width='stretch',
            hide_index=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row"
        )
    
    selected_rows = event.selection.rows

    # =====================================================
    # Enrollment Timeline
    # =====================================================

    st.divider()
    st.header("Enrollment Timeline")
    
    if len(selected_rows) > 0:
        selected_idx = selected_rows[0]
        selected_study = filtered_df.iloc[selected_idx]['STUDY_ID']
        trial_info = filtered_df.iloc[selected_idx]
        
        with st.container(border=True):
            info_col1, info_col2, info_col3, info_col4 = st.columns(4)
            
            with info_col1:
                st.metric(
                    "Selected Trial", 
                    selected_study,
                    help=f"{trial_info['DRUG_NAME']} - {trial_info['STUDY_NAME']}"
                )
            
            with info_col2:
                st.metric("Phase", trial_info['PHASE'])
            
            with info_col3:
                status = trial_info['TRIAL_STATUS']
                status_emoji = {'Off Track': '🟠', 'At Risk': '🟡', 'On Track': '🟢'}.get(status, '⚪')
                st.metric("Status", f"{status_emoji} {status}")
            
            with info_col4:
                st.metric(
                    "Enrollment vs. Plan",
                    f"{trial_info['CURRENT_ENROLLMENT_ATTAINMENT']:.1f}%"
                )
        
        with st.spinner("Loading enrollment timeline..."):
            ts_data = load_trial_enrollment_timeseries(selected_study)
        
        if not ts_data.empty:
            ts_data['DATE'] = pd.to_datetime(ts_data['DATE'])
            ts_data = ts_data.sort_values('DATE')
            ts_data['cumulative_planned'] = ts_data['PLANNED_ENROLLMENT'].cumsum()
            ts_data['cumulative_actual'] = ts_data['ACTUAL_ENROLLMENT'].cumsum()
            
            current_date = pd.Timestamp.now()
            actual_data = ts_data[ts_data['DATE'] <= current_date].copy()
            planned_data = ts_data.copy()
            
            # Area chart for planned enrollment
            area_chart = alt.Chart(planned_data).mark_area(
                opacity=0.3,
                color='#F7A078'
            ).encode(
                x=alt.X('DATE:T', 
                       title='Date', 
                       axis=alt.Axis(format='%b %Y', labelAngle=-45)),
                y=alt.Y('cumulative_planned:Q', 
                       title='Cumulative Subjects Enrolled',
                       scale=alt.Scale(zero=True)),
                tooltip=[
                    alt.Tooltip('DATE:T', title='Date', format='%Y-%m-%d'),
                    alt.Tooltip('cumulative_planned:Q', title='Planned Cumulative', format=',d')
                ]
            )
            
            # Line chart for actual enrollment
            line_chart = alt.Chart(actual_data).mark_line(
                strokeWidth=3,
                color='#F25D18'
            ).encode(
                x=alt.X('DATE:T', title='Date'),
                y=alt.Y('cumulative_actual:Q', title='Cumulative Subjects Enrolled'),
                tooltip=[
                    alt.Tooltip('DATE:T', title='Date', format='%Y-%m-%d'),
                    alt.Tooltip('cumulative_actual:Q', title='Actual Cumulative', format=',d')
                ]
            )
            
            # Points for actual enrollment
            points = alt.Chart(actual_data).mark_circle(
                size=60,
                color='#F25D18'
            ).encode(
                x='DATE:T',
                y='cumulative_actual:Q',
                tooltip=[
                    alt.Tooltip('DATE:T', title='Date', format='%Y-%m-%d'),
                    alt.Tooltip('cumulative_actual:Q', title='Actual Enrollment', format=',d')
                ]
            )
            
            combined_chart = (area_chart + line_chart + points).properties(
                width='container',
                height=500,
                title={
                    "text": f"Cumulative Enrollment: {selected_study} ({trial_info['DRUG_NAME']})",
                    "subtitle": ["Area: Planned enrollment trajectory", 
                                "Line: Actual enrollment to date"],
                    "fontSize": 18,
                    "subtitleFontSize": 12
                }
            ).configure_axis(
                labelFontSize=12,
                titleFontSize=14
            )
            
            st.altair_chart(combined_chart, width='stretch')
            
            # Key Enrollment Metrics
            st.subheader("Key Enrollment Metrics")
            
            with st.container(border=True):
                metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
                
                with metric_col1:
                    st.metric(
                        "Planned to Date", 
                        f"{int(trial_info['PLANNED_ENROLLMENT']):,}",
                        help="Expected enrollment as of today based on enrollment plan"
                    )
                
                with metric_col2:
                    actual_vs_plan = int(trial_info['ACTUAL_ENROLLMENT']) - int(trial_info['PLANNED_ENROLLMENT'])
                    st.metric(
                        "Actual Enrolled", 
                        f"{int(trial_info['ACTUAL_ENROLLMENT']):,}",
                        delta=f"{actual_vs_plan:+,} vs plan",
                        delta_color="normal"
                    )
                
                with metric_col3:
                    st.metric(
                        "Total Target", 
                        f"{int(trial_info['PLANNED_ENROLLMENT_TOTAL']):,}",
                        help="Ultimate enrollment target"
                    )
                
                with metric_col4:
                    remaining = int(trial_info['PLANNED_ENROLLMENT_TOTAL']) - int(trial_info['ACTUAL_ENROLLMENT'])
                    st.metric(
                        "Remaining to Target", 
                        f"{remaining:,}"
                    )
                
                with metric_col5:
                    completion_pct = (int(trial_info['ACTUAL_ENROLLMENT']) / int(trial_info['PLANNED_ENROLLMENT_TOTAL'])) * 100
                    st.metric(
                        "Overall Completion", 
                        f"{completion_pct:.1f}%",
                        help="Percent of ultimate target achieved"
                    )
            
            # Detailed statistics in expander
            with st.expander("📊 View Detailed Enrollment Statistics"):
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    st.markdown("**Trial Information**")
                    st.write(f"**Protocol:** {trial_info['STUDY_NAME']}")
                    st.write(f"**Start Date:** {trial_info['START_DATE']}")
                    st.write(f"**Target Completion:** {trial_info['FORECAST_COMPLETION_DATE']}")
                
                with detail_col2:
                    st.markdown("**Enrollment Velocity**")
                    if not actual_data.empty and len(actual_data) > 1:
                        recent_months = min(3, len(actual_data))
                        recent_enrollment = actual_data.tail(recent_months)['ACTUAL_ENROLLMENT'].sum()
                        avg_monthly = recent_enrollment / recent_months
                        st.write(f"**Avg Monthly (Last {recent_months} months):** {avg_monthly:.1f} subjects/month")
                        
                        if avg_monthly > 0:
                            months_to_complete = remaining / avg_monthly
                            st.write(f"**Est. Months to Complete:** {months_to_complete:.1f} months")
        
        else:
            st.info("No enrollment data available for this trial.")
    
    else:
        st.info("👆 **Select a trial** from the table above to view its enrollment timeline and detailed metrics.")


if __name__ == "__main__":
    main()

