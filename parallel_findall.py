"""
Parallel FindAll functionality using Parallel.ai FindAll API
"""
import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuration
PARALLEL_BASE_URL = "https://api.parallel.ai"


# Note: Parallel.ai API does not provide an endpoint to list previous runs
# We use Google Sheets to store search history for future reference


def save_search_to_gsheets(query, run_id, results, columns, timestamp):
    """
    Save search results to Google Sheets using run_id as worksheet name

    Args:
        query (str): Search query
        run_id (str): FindAll run ID (will be used as worksheet name)
        results (list): FindAll results
        columns (list): Column definitions
        timestamp (str): Search timestamp
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)

        # Use readable date/time as worksheet name
        worksheet_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Create results dataframe
        df = create_results_dataframe(results, columns)

        # Create a metadata row as the first row
        metadata_row = pd.DataFrame([{
            'Name': f'SEARCH QUERY: {query}',
            'Score': '',
            'URL': f'Run ID: {run_id}',
            'Description': f'Search executed on {timestamp}',
            **{col: '' for col in df.columns if col not in ['Name', 'Score', 'URL', 'Description']}
        }])

        # Combine metadata row with results
        df = pd.concat([metadata_row, df], ignore_index=True)

        # Save to new worksheet
        conn.create(worksheet=worksheet_name, data=df)

        # Also update the main index sheet
        update_search_index(query, run_id, len(results), timestamp, worksheet_name)

        return True

    except Exception as e:
        st.error(f"Could not save to Google Sheets: {e}")
        return False


def update_search_index(query, run_id, result_count, timestamp, worksheet_name):
    """
    Update the main search index worksheet

    Args:
        query (str): Search query
        run_id (str): FindAll run ID
        result_count (int): Number of results found
        timestamp (str): Search timestamp
        worksheet_name (str): Name of the worksheet containing the results
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)

        # Read existing index data
        try:
            df = conn.read(worksheet="Searches")
        except Exception:
            # Create new index structure if it doesn't exist
            df = pd.DataFrame(columns=['Timestamp', 'Query', 'Run_ID', 'Result_Count', 'Worksheet'])

        # Use the worksheet name passed from the main function
        new_row = {
            'Timestamp': timestamp,
            'Query': query,
            'Run_ID': run_id,
            'Result_Count': result_count,
            'Worksheet': worksheet_name
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Write back to index sheet
        try:
            # Try to update existing worksheet first
            conn.update(worksheet="Searches", data=df)
        except Exception:
            # If update fails, create new worksheet
            conn.create(worksheet="Searches", data=df)
        return True

    except Exception as e:
        st.warning(f"Could not update search index: {e}")
        return False


def load_search_history():
    """
    Load search history from Google Sheets Searches worksheet

    Returns:
        pd.DataFrame: Search history or empty DataFrame if error
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Searches", ttl="1m")
        return df.sort_values('Timestamp', ascending=False) if not df.empty else pd.DataFrame()
    except Exception as e:
        st.warning(f"Could not load search history: {e}")
        return pd.DataFrame()


def load_search_results_from_worksheet(worksheet_name):
    """
    Load specific search results from a worksheet

    Args:
        worksheet_name (str): Name of the worksheet to load

    Returns:
        pd.DataFrame: Search results or empty DataFrame if error
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=worksheet_name, ttl="1m")
        return df
    except Exception as e:
        st.error(f"Could not load results from worksheet {worksheet_name}: {e}")
        return pd.DataFrame()


def get_findall_run_by_id(run_id):
    """
    Fetch a specific FindAll run by ID
    
    Args:
        run_id (str): The FindAll run ID
        
    Returns:
        dict: Run data with results or None if error
    """
    try:
        parallel_api_key = st.secrets["parallel_api_key"]
    except (KeyError, AttributeError):
        return None
    
    try:
        response = requests.get(
            f"{PARALLEL_BASE_URL}/v1beta/findall/runs/{run_id}",
            headers={"x-api-key": parallel_api_key}
        )
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"API Error fetching run {run_id}: {e}")
        return None
    except Exception as e:
        st.error(f"Error fetching run {run_id}: {e}")
        return None


def search_findall(query, result_limit=10):
    """
    Search using Parallel.ai FindAll API

    Args:
        query (str): Search query
        result_limit (int): Maximum number of results to return

    Returns:
        tuple: (results, columns, run_id) or (None, None, None) if error
    """
    # Get API key from secrets
    try:
        parallel_api_key = st.secrets["parallel_api_key"]
    except (KeyError, AttributeError):
        st.error("Parallel API key not found in secrets. Please configure parallel_api_key in .streamlit/secrets.toml")
        return None, None, None

    try:
        progress_bar = st.progress(0)
        
        # Create a container for logs that will stack
        log_container = st.container()
        
        with log_container:
            st.write("🔄 **Step 1:** Ingesting query...")
        progress_bar.progress(25)

        ingest_response = requests.post(
            f"{PARALLEL_BASE_URL}/v1beta/findall/ingest",
            headers={"x-api-key": parallel_api_key},
            json={"query": query}
        )
        ingest_response.raise_for_status()

        findall_spec = ingest_response.json()

        # Show detailed column information
        column_names = [col.get('name', 'Unknown') for col in findall_spec.get('columns', [])]
        with log_container:
            st.write(f"🚀 **Step 2:** Starting FindAll run with {len(findall_spec['columns'])} columns: {', '.join(column_names)}")
        progress_bar.progress(50)

        run_response = requests.post(
            f"{PARALLEL_BASE_URL}/v1beta/findall/runs",
            headers={"x-api-key": parallel_api_key},
            json={
                "findall_spec": findall_spec,
                "processor": "base",
                "result_limit": result_limit
            }
        )
        run_response.raise_for_status()

        findall_id = run_response.json()["findall_id"]

        with log_container:
            st.write(f"⏳ **Step 3:** Compiling company results for run id: `{findall_id}`")
            st.info("🕒 This process typically takes 3-5 minutes as Parallel.ai gathers comprehensive company data. This tool was cobbled together, so unfortunately you will have to leave this page open to make sure search results get saved.")
        progress_bar.progress(75)

        # Poll for results without additional spinner
        polling_count = 0
        while True:
            poll_response = requests.get(
                f"{PARALLEL_BASE_URL}/v1beta/findall/runs/{findall_id}",
                headers={"x-api-key": parallel_api_key}
            )
            poll_response.raise_for_status()

            result = poll_response.json()
            polling_count += 1

            if not result["is_active"] and not result["are_enrichments_active"]:
                break

            time.sleep(5)

        progress_bar.progress(100)
        with log_container:
            st.write(f"✅ **Search completed!** Found {len(result.get('results', []))} results")

        # Debug: Show result structure
        if result.get('results'):
            with log_container:
                st.success(f"📊 Retrieved {len(result['results'])} results with columns: {', '.join(column_names)}")
        else:
            with log_container:
                st.warning("⚠️ No results found in the response. The query may be too specific or no matching companies exist.")
            
        return result.get('results', []), findall_spec['columns'], findall_id

    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None, None, None
    except KeyError as e:
        st.error(f"Unexpected response format: missing key {e}")
        return None, None, None
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None, None


def create_results_dataframe(results, columns):
    """
    Create a pandas DataFrame from search results
    
    Args:
        results (list): Search results from FindAll API
        columns (list): Column definitions from FindAll API
        
    Returns:
        pd.DataFrame: Formatted results dataframe
    """
    if not results:
        return pd.DataFrame()
    
    df_data = []
    for entity in results:
        row = {}
        
        # Always include basic fields
        row['Name'] = entity.get('name', '')
        row['Score'] = entity.get('score', 0)
        row['URL'] = entity.get('url', '')
        row['Description'] = entity.get('description', '')
        
        # Add enrichment results if available
        if 'enrichment_results' in entity:
            for enrichment in entity['enrichment_results']:
                key = enrichment.get('key', '')
                value = enrichment.get('value', '')
                
                if key and value:
                    # Create readable column name
                    display_name = key.replace('_', ' ').replace('evidence', '').title().strip()
                    row[display_name] = value
        
        # Add filter results if available  
        if 'filter_results' in entity:
            for filter_result in entity['filter_results']:
                key = filter_result.get('key', '')
                value = filter_result.get('value', '')
                reasoning = filter_result.get('reasoning', '')
                
                if key:
                    # Create readable column name
                    display_name = key.replace('_', ' ').replace('check', '').title().strip()
                    
                    # Combine value and reasoning for richer display (keep full text)
                    if value and reasoning:
                        combined_value = f"{value.upper()}: {reasoning}"
                        row[display_name] = combined_value
                    elif value:
                        row[display_name] = value.upper()

        df_data.append(row)

    return pd.DataFrame(df_data)




def render_parallel_findall_tab(tab_type="new_search"):
    """
    Render the Parallel FindAll tab UI

    Args:
        tab_type (str): Either "new_search" or "search_history"
    """
    if tab_type == "new_search":
        st.header("New Company Search")
        st.info("💡 Search using Parallel.ai FindAll API, which transforms natural language queries into enriched datasets with verified information")
        with st.form("search_form"):
            query = st.text_area(
                "Enter your search query:", 
                value="Find all seed or pre-seed startups that have raised less than $10M, founded after 2020, that are developing novel insurance or risk management solutions for climate-related physical assets (e.g., property, infrastructure) that are experiencing increasing climate impact.",
                height=150,
                help="You can enter multi-line queries for complex searches"
            )
            result_limit = st.number_input("Result limit:", min_value=5, max_value=30, value=10)
            submit_button = st.form_submit_button("Search")

        if submit_button and query:
            with st.spinner("Searching..."):
                results, columns, run_id = search_findall(query, result_limit)

            if results is not None:
                if len(results) > 0:
                    st.success(f"Found {len(results)} results")

                    # Save to Google Sheets
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if save_search_to_gsheets(query, run_id, results, columns, timestamp):
                        st.success("✅ Results saved to Google Sheets")

                    df = create_results_dataframe(results, columns)
                    if not df.empty:
                        # Show column info for debugging
                        st.info(f"📊 Displaying results with columns: {list(df.columns)}")
                        st.dataframe(df, use_container_width=True)

                        # Show run ID for future reference
                        if run_id:
                            st.info(f"🔗 **Run ID for future reference**: `{run_id}`")
                    else:
                        st.warning("Results were found but DataFrame is empty. Check data structure.")
                        # Debug: Show raw results structure
                        with st.expander("🔍 Debug: Raw Results Structure"):
                            st.json(results[:2] if len(results) > 2 else results)
                else:
                    st.info("Search completed but no results were returned.")
            elif query:
                st.error("Search failed. Please try again.")

    elif tab_type == "search_history":
        st.header("Search History")
        st.info("📋 Browse company search history (all results saved to this Google Sheet: https://docs.google.com/spreadsheets/d/1bYVZHEKaQu5mkLqbsH0tvFnylIteai-YvuuJzSftFTE/edit?gid=944934347#gid=944934347)")

        # Load search history
        history_df = load_search_history()

        if not history_df.empty:
            st.write(f"**{len(history_df)} previous searches found**")

            # Display each search as an expandable section
            for idx, row in history_df.iterrows():
                query_text = row.get('Query', 'Unknown Query')
                timestamp = row.get('Timestamp', 'Unknown Time')
                run_id = row.get('Run_ID', 'Unknown ID')
                result_count = row.get('Result_Count', 0)
                worksheet_name = row.get('Worksheet', run_id[:31] if len(run_id) > 31 else run_id)

                # Create expandable section for each search
                with st.expander(f"{query_text} ({result_count} results)"):
                    # Auto-load and display results
                    with st.spinner(f"Loading results from {worksheet_name}..."):
                        results_df = load_search_results_from_worksheet(worksheet_name)

                        if not results_df.empty:
                            # Skip the metadata row (first row) when displaying
                            display_df = results_df.iloc[1:] if len(results_df) > 1 else results_df

                            st.markdown(f"**Found {len(display_df)} companies:**")

                            # Display results as a Streamlit table first
                            st.dataframe(display_df, use_container_width=True)

                            st.markdown("---")
                            st.markdown("### Company Details")

                            # Create compact company list
                            for _, company_row in display_df.iterrows():
                                company_name = company_row.get('Name', 'Unknown Company')
                                company_url = company_row.get('URL', '')

                                # Add company name with hyperlink - make it bigger
                                if company_url and company_url.strip() and company_url != '':
                                    # Ensure URL has proper protocol
                                    if not company_url.startswith(('http://', 'https://')):
                                        if '.' in company_url:  # Looks like a domain
                                            company_url = f"https://{company_url}"
                                        else:
                                            # If it's not a URL, just show company name
                                            st.markdown(f"### {company_name}")
                                            continue
                                    st.markdown(f"### [{company_name}]({company_url})")
                                else:
                                    st.markdown(f"### {company_name}")

                                # Collect all relevant data points
                                details = []
                                for col in display_df.columns:
                                    if col not in ['Name', 'URL']:
                                        value = company_row.get(col, '')
                                        if value and str(value).strip() and str(value).lower() not in ['skipped', 'nan']:
                                            clean_col = col.replace('_', ' ').title()
                                            # Keep full values, no truncation
                                            details.append(f"**{clean_col}:** {value}")

                                # Display details with line breaks
                                if details:
                                    for detail in details:
                                        st.markdown(f"• {detail}")

                                st.markdown("")  # Add spacing between companies
                        else:
                            st.error("❌ Could not load results from this search")
        else:
            st.info("📭 No previous searches found. Run a search to build your history!")
