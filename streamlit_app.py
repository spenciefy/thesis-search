"""
Thesis Extraction & Company Search
Main Streamlit application for thesis extraction and company search
"""
import streamlit as st
from parallel_findall import render_parallel_findall_tab
from thesis_extraction import render_thesis_extraction_tab


def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Thesis Extraction & Company Search",
        page_icon="🔍",
    )
    
    st.title("Thesis Extraction & Company Search")
    st.info("""💡 Imagine if after Climate Weekly or Thesis Thursday, you got a list of companies (and people) to talk to that are aligned on the ideas, themes, and potential theses discussed. 
   
   **📝 Instructions:**
   1. Extract theses from content and generate thesis based search queries
   2. Copy and paste a search query into "New Search" to get a list of companies, powered by parallel.ai's FindAll api (or I recommend using Parallel's interface directly: https://platform.parallel.ai/find-all)
    """)

    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["📝 Thesis Extraction", "🔍 New Search", "📚 Search History"])

    with tab1:
        render_thesis_extraction_tab()

    with tab2:
        render_parallel_findall_tab(tab_type="new_search")

    with tab3:
        render_parallel_findall_tab(tab_type="search_history")
  


if __name__ == "__main__":
    main()