"""
Standard Operating Procedures (SOPs) Page
Displays clinical operations playbook documentation
"""

import streamlit as st
import os
from pathlib import Path

# Import shared components
import sys
sys.path.append(str(Path(__file__).parent.parent))
from shared_components import (
    apply_custom_css,
    get_snowflake_session,
    load_trial_summary,
    render_portfolio_sidebar
)


def load_sop_content():
    """Load SOP content from the playbook file"""
    # Get the path to the data file
    app_dir = Path(__file__).parent.parent
    data_dir = app_dir.parent / "data"
    sop_file = data_dir / "cct_demo_clinops_playbook.txt"
    
    try:
        with open(sop_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "⚠️ **Error:** SOP file not found at expected location."
    except Exception as e:
        return f"⚠️ **Error loading SOPs:** {str(e)}"


def main():
    """Main entry point for SOPs page"""
    
    # Page configuration
    st.set_page_config(
        page_title="SOPs - Clinical Control Tower",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom CSS
    apply_custom_css()
    
    # Load trial data for sidebar
    trial_df = load_trial_summary()
    
    if not trial_df.empty:
        # Render standard portfolio sidebar
        render_portfolio_sidebar(trial_df)
    
    # Page header
    st.title("📋 Standard Operating Procedures")
    #st.subheader("Clinical Operations Playbook")
    
    #st.markdown("---")
    
    # Load SOP content
    sop_content = load_sop_content()
    
    # Chapter selector
    chapters = {
        "SOP 401: Site Performance & Intervention Playbook": {
            "icon": "📖",
            "doc_id": "CL-SOP-401-v3.0",
            "date": "15-Jan-2024"
        },
        "SOP 701: Pharmacovigilance & Safety Reporting": {
            "icon": "🚨",
            "doc_id": "CL-SOP-701-v3.0",
            "date": "15-Jan-2024"
        }
    }
    
    selected_chapter = st.selectbox(
        "Select Chapter",
        options=list(chapters.keys()),
        format_func=lambda x: f"{chapters[x]['icon']} {x}",
        label_visibility="collapsed"
    )
    
    #st.markdown("---")
    
    # Display selected chapter
    if selected_chapter == "SOP 401: Site Performance & Intervention Playbook":
        st.markdown(f"## {chapters[selected_chapter]['icon']} {selected_chapter}")
        st.info(f"**Document ID:** {chapters[selected_chapter]['doc_id']} | **Effective Date:** {chapters[selected_chapter]['date']}")
        
        # Extract SOP 401 content (up to where SOP 701 starts)
        if "SOP 701:" in sop_content:
            chapter_content = sop_content.split("SOP 701:")[0]
        else:
            chapter_content = sop_content
        
        # Display in a container for better readability
        with st.container():
            st.markdown(chapter_content)
    
    elif selected_chapter == "SOP 701: Pharmacovigilance & Safety Reporting":
        st.markdown(f"## {chapters[selected_chapter]['icon']} {selected_chapter}")
        st.info(f"**Document ID:** {chapters[selected_chapter]['doc_id']} | **Effective Date:** {chapters[selected_chapter]['date']}")
        
        # Extract SOP 701 content
        if "SOP 701:" in sop_content:
            # Get content from SOP 701 onwards, but exclude Document History and Approvals
            sop_701_start = sop_content.find("SOP 701:")
            
            # Find where Document History starts for SOP 401 (this is actually shared)
            if "## 5. Document History" in sop_content:
                chapter_content = sop_content[sop_701_start:sop_content.find("## 5. Document History")]
            else:
                chapter_content = sop_content[sop_701_start:]
        else:
            chapter_content = "⚠️ SOP 701 content not found in playbook file."
        
        # Display in a container for better readability
        with st.container():
            st.markdown(chapter_content)
    
    # Additional information
    with st.expander("📄 Document Information", expanded=False):
        st.markdown("""
        ### Document History
        
        | Version | Effective Date | Author | Summary of Changes |
        |---------|---------------|--------|-------------------|
        | v1.0 | 10-Oct-2022 | J. Smith | Initial Draft |
        | v2.0 | 12-Dec-2023 | A. Chen | Added CCT integration triggers |
        | v3.0 | 15-Jan-2024 | A. Chen | Clarified PI Engagement escalation path (Play 3) |
        
        ### Approvals
        - A. Chen, Head of Clinical Operations
        - B. Davis, Head of Quality Assurance
        - M. Patel, Chief Medical Officer
        """)


if __name__ == "__main__":
    main()

