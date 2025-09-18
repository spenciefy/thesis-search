"""
Thesis extraction functionality using OpenRouter API
"""
import streamlit as st
import os
from openai import OpenAI
from config import OPENROUTER_API_KEY


def load_meeting_transcripts():
    """
    Load available meeting transcripts for sample inputs

    Returns:
        dict: Dictionary mapping display names to file contents
    """
    transcripts = {}
    transcript_dir = "content"

    # Define the content files and their display names
    transcript_files = {
        "USV Climate Weekly - July 18, 2025": "usv-climate-weekly-7-18-25.md",
        "USV Climate Weekly - August 1, 2025": "usv-climate-weekly-8-1-25.md",
        "USV Climate Weekly - August 15, 2025": "usv-climate-weekly-8-15-25.md",
        "USV Climate Weekly - August 22, 2025": "usv-climate-weekly-8-22-25.md",
        "Healthcare at the Edge": "healthcare-at-the-edge.md",
        "The Fragmentation of Search": "the-fragmentation-of-search.md",
        "Tools vs Truth": "tools-vs-truth.md",
        "You Don't Own Your Memory": "you-dont-own-your-memory.md"
    }

    for display_name, filename in transcript_files.items():
        file_path = os.path.join(transcript_dir, filename)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    transcripts[display_name] = f.read()
        except Exception as e:
            st.warning(f"Could not load {filename}: {e}")

    return transcripts


def extract_thesis_and_queries(content):
    """
    Extract investment theses and generate search queries using OpenRouter.
    
    Args:
        content (str): Content to analyze (meeting notes, blog posts, etc.)
        
    Returns:
        OpenAI stream response or None if error
    """
    if not OPENROUTER_API_KEY:
        st.error("OpenRouter API key not found. Please set the OPENROUTER_API_KEY environment variable.")
        return None
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        
        prompt = """
        You are a thesis-driven investor at Union Square Ventures who is searching for companies that are
        aligned with a specific thesis. The high level thesis of the fund is 'Investing at the Edge of
        Large Markets Under Transformative Pressure'. 
       
        USV looks for companies that:

       - Enable permissionless innovation - platforms that let anyone participate without gatekeepers
       - Create network effects - where value increases as more users join
       - Operate at structural inflection points - markets being fundamentally reshaped by technology, regulation, or societal change
       - Democratize access - to capital, knowledge, tools, or opportunities previously restricted to few
       - Build foundational infrastructure for emerging paradigms (like "picks and shovels" for new ecosystems)

        Your task is to help extract possible theses from given content (notes, blog post, meeting transcript) and turn them into search queries.
    
        Based on the provided content, what are theses and search queries to search for companies
        that are aligned with the thesis? 
        
        Return as many theses as deemed fit for the content.

        The search queries will be used to search for companies and can be open ended.
        The search queries should be in the format of "Find all seed or pre-seed startups that have raised less than $10M, founded after 2020, that... [thesis]". 
        Return maximum 2 search queries, they should capture the essence of the thesis.
        For example: "Find all seed or pre-seed startups that have raised less than $10M, founded after 2020, climate/energy startups that match this thesis: [thesis]"

        Structure your response as:
        
        #### Thesis 1: [Thesis in 1 concise sentence]
        1. Key insight 1 explained in 1-2 concise sentences
        2. Key insight 2 explained in 1-2 concise sentences
        ...
    
       **Search Queries:**
        1. Find all [search query based on the thesis]
        ...
        """
        
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",  #
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
            stream=True
        )
        
        return response
        
    except Exception as e:
        st.error(f"Error calling OpenRouter API: {e}")
        return None




def render_thesis_extraction_tab():
    """
    Render the Thesis Extraction tab UI
    """
    st.header("Thesis Extraction & Company Search")

    if not OPENROUTER_API_KEY:
        st.warning("⚠️ OpenRouter API key not found. Please set the OPENROUTER_API_KEY environment variable to use this feature.")
        st.code("export OPENROUTER_API_KEY=your_api_key_here")

    # Load available meeting transcripts
    transcripts = load_meeting_transcripts()

    # Initialize content input
    content_input_value = ""

    st.info("💡 Turn any content (meeting transcript, notes) into potential investment theses that can be used to search for companies")


    # Sample transcript selector
    if transcripts:
        selected_transcript = st.selectbox(
            "Select a sample meeting transcript or paste any content below:",
            options=["Paste your own content..."] + list(transcripts.keys())
        )

        # Handle sample loading
        if selected_transcript != "Paste your own content...":
            content_input_value = transcripts[selected_transcript]

    content_input = st.text_area(
        "Content to analyze:",
        value=content_input_value,
        placeholder="Paste your meeting notes, blog post, or transcript here...",
        height=200
    )
    
    extract_button = st.button("Extract Theses", type="primary")
    
    if extract_button and content_input and OPENROUTER_API_KEY:
        st.subheader("📋 Generated Theses & Search Queries")
        
        # Create containers for streaming output
        thesis_container = st.empty()
        status_container = st.empty()
        
        # Initialize the streaming
        status_container.info("🤖 Analyzing...")
        response = extract_thesis_and_queries(content_input)
        
        if response:
            # Stream the response with enhanced markdown support
            full_response = ""
            status_container.info("✨ Streaming response...")
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    
                    # Render markdown with enhanced formatting
                    with thesis_container.container():
                        st.markdown(full_response, unsafe_allow_html=True)
            
            # Clear status and show completion
            status_container.success("✅ Analysis complete!")
            
            # Store the full response
            st.session_state.thesis_response = full_response
            
            # Add helpful note about using the queries
            st.markdown("---")
            st.info("💡 You can copy any search queries from above and use them in the **Parallel FindAll** tab to find companies.")
        else:
            status_container.error("❌ Failed to get response from AI. Please try again.")
                
    elif extract_button and not content_input:
        st.warning("Please enter some content to analyze.")
    elif extract_button and not OPENROUTER_API_KEY:
        st.error("OpenRouter API key is required. Please set the OPENROUTER_API_KEY environment variable.")
