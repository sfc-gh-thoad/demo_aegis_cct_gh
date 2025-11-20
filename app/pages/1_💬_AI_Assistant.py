"""
Project Aegis: Clinical Control Tower (CCT)
AI Assistant Page - Natural language interface for clinical trial data
"""

import streamlit as st
from shared_components import (
    get_snowflake_session,
    load_trial_summary,
    apply_custom_css,
    render_portfolio_sidebar,
    render_ai_sidebar_additions
)
from cortex_agent_chat import CortexAgentChat

# Page configuration
st.set_page_config(
    page_title="AI Assistant - Clinical Control Tower",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply shared styling
apply_custom_css()


def _ai_assistant_fragment():
    """
    Render AI Assistant chat interface.
    """
    st.header("💬 Clinical Trials AI Assistant")
    st.caption("Ask questions about trial enrollment, delays, and site performance")
    
    try:
        # Try to create chat instance using Streamlit secrets
        if "cortex_agent" in st.secrets:
            agent_config = st.secrets["cortex_agent"]
            
            chat = CortexAgentChat(
                pat=agent_config.get("pat") or st.secrets["snowflake"]["password"],
                host=agent_config.get("host") or f"{st.secrets['snowflake']['account']}.snowflakecomputing.com",
                database=agent_config.get("database", "AEGIS_CCT"),
                schema=agent_config.get("schema", "AGENTS"),
                agent=agent_config.get("agent", "CCT_CLINICAL_AGENT"),
                model=agent_config.get("model", "claude-4-sonnet"),
                session_key="cct_agent_chat",
                title="",  # Empty string to hide title
                chat_input_placeholder="Ask about trials, enrollment, delays, or site performance...",
                verify_ssl=False
            )
        else:
            # Fallback: use main Snowflake connection
            chat = CortexAgentChat(
                pat=st.secrets["snowflake"]["password"],
                host=f"{st.secrets['snowflake']['account']}.snowflakecomputing.com",
                database="AEGIS_CCT",
                schema="AGENTS",
                agent="CCT_CLINICAL_AGENT",
                model="claude-4-sonnet",
                session_key="cct_agent_chat",
                title="",  # Empty string to hide title
                chat_input_placeholder="Ask about trials, enrollment, delays, or site performance...",
                verify_ssl=False
            )
        
        # Store in session state for sidebar access
        st.session_state.cct_chat_instance = chat
        
        # Render debug panel if debug mode is enabled
        chat.render_debug_panel()
        
        # Render chat interface (natural rendering without container)
        chat.render()
            
    except Exception as e:
        st.error(f"""
        **Unable to initialize AI Assistant**
        
        Error: {str(e)}
        
        Please configure the Cortex Agent in `.streamlit/secrets.toml`:
        
        ```toml
        [cortex_agent]
        database = "AEGIS_CCT"
        schema = "AGENTS"
        agent = "CCT_CLINICAL_AGENT"
        model = "claude-4-sonnet"
        ```
        
        Or ensure your main Snowflake connection has access to the agent.
        """)


def main():
    """Main entry point for AI Assistant page"""
    
    # Load trial data for sidebar
    trial_df = load_trial_summary()
    
    if not trial_df.empty:
        # Render standard portfolio sidebar
        render_portfolio_sidebar(trial_df)
        
        # Render AI-specific sidebar additions (includes settings)
        chat_instance = st.session_state.get('cct_chat_instance')
        render_ai_sidebar_additions(chat_instance)
    
    # Render chat interface
    _ai_assistant_fragment()


if __name__ == "__main__":
    main()

