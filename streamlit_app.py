"""
Streamlit Web Interface for Conversational Database Agent
Provides a user-friendly chat interface for interacting with the database
"""

import streamlit as st
import time
import json
from datetime import datetime
from typing import Dict, List, Any


st.set_page_config(
    page_title="Conversational Database Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    from database_agent import ConversationalDatabaseAgent
    from config import config, SAMPLE_ANALYTICS_SCHEMA
except ImportError:
    st.error("Please make sure all required modules are installed. Run: pip install -r requirements.txt")
    st.stop()

@st.cache_resource
def get_agent():
    """Initialize and cache the database agent"""
    agent = ConversationalDatabaseAgent()

    if agent.connect_database():
        return agent
    else:
        return None

def initialize_session_state():
    """Initialize Streamlit session state variables"""

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent" not in st.session_state:
        st.session_state.agent = get_agent()

    if "query_count" not in st.session_state:
        st.session_state.query_count = 0

    if "session_start_time" not in st.session_state:
        st.session_state.session_start_time = datetime.now()

def render_sidebar():
    """Render the sidebar with app information and controls"""

    with st.sidebar:
        st.title("🤖 Database Agent")

        ##
        if st.session_state.agent:
            st.success("✅ Connected to MongoDB")
            st.info(f"Database: {config.database.database_name}")
        else:
            st.error("❌ Database connection failed")
            st.warning("Check your .env configuration")

        st.divider()

        ##
        st.subheader("📊 Session Stats")
        session_duration = datetime.now() - st.session_state.session_start_time
        st.metric("Duration", f"{session_duration.total_seconds():.0f}s")
        st.metric("Queries", st.session_state.query_count)
        st.metric("Messages", len(st.session_state.messages))

        st.divider()

        # Some examples taken from AI to test
        st.subheader(" Example Queries")
        example_queries = [
            "What is the accounts collection?",
            "How many customers do we have?",
            "Show me customer information",
            "What's the average account limit?",
            "Find accounts with InvestmentStock",
            "What products are available?"
        ]

        for query in example_queries:
            if st.button(query, key=f"example_{query}", use_container_width=True):
                st.session_state.pending_query = query
                st.rerun()

        st.divider()

        # Controls
        st.subheader(" Controls")

        if st.button(" Clear Chat", use_container_width=True):
            st.session_state.messages = []
            if st.session_state.agent:
                st.session_state.agent.reset_conversation()
            st.rerun()

        if st.button(" Show Insights", use_container_width=True):
            st.session_state.show_insights = True
            st.rerun()

        if st.button(" Show Schema", use_container_width=True):
            st.session_state.show_schema = True
            st.rerun()

def render_schema_info():
    """Render database schema information"""

    st.subheader("📋 Database Schema")

    if not st.session_state.agent:
        st.error("Agent not connected")
        return

   
    if not st.session_state.agent.schema_manager.schema_cache:
        with st.spinner("Discovering schema..."):
            st.session_state.agent.schema_manager.discover_schema()

    schema = st.session_state.agent.schema_manager.schema_cache


    if schema:
        tabs = st.tabs(list(schema.keys()))

        for i, (collection_name, info) in enumerate(schema.items()):
            with tabs[i]:
                st.write(f"**Collection:** {collection_name}")
                st.write(f"**Documents:** {info.get('document_count', 'Unknown')}")

                fields = info.get('fields', {})
                if fields:
                    st.write("**Fields:**")
                    field_data = []
                    for field_name, field_info in fields.items():
                        field_data.append({
                            "Field": field_name,
                            "Type": field_info.get('type', 'unknown'),
                            "Sample": str(field_info.get('sample_value', ''))[:50]
                        })

                    st.dataframe(field_data, use_container_width=True)
    else:
        st.warning("No schema information available")

def render_insights():
    """Render conversation insights"""

    st.subheader("Conversation Insights")

    if not st.session_state.agent or not st.session_state.agent.memory_manager.conversation_log:
        st.info("No conversation history available yet.")
        return

    try:
        with st.spinner("Analyzing conversation..."):
            insights = st.session_state.agent.get_insights()

        col1, col2 = st.columns(2)

        with col1:
            st.metric("User Intent", insights.user_intent)
            st.metric("Emotional Tone", insights.emotional_tone)

        with col2:
            if insights.data_gaps:
                st.write("**Data Gaps:**")
                for gap in insights.data_gaps:
                    st.write(f"• {gap}")

        if insights.suggested_queries:
            st.write("**Suggested Questions:**")
            for suggestion in insights.suggested_queries:
                if st.button(f"💡 {suggestion}", key=f"suggestion_{suggestion}"):
                    st.session_state.pending_query = suggestion
                    st.rerun()

    except Exception as e:
        st.error(f"Error generating insights: {e}")

def render_chat_message(role: str, content: str, extra_info: Dict = None):
    """Render a chat message"""

    with st.chat_message(role):
        st.markdown(content)

        if extra_info and config.agent.debug_mode:
            with st.expander("Debug Info"):
                st.json(extra_info)

def process_user_query(query: str):
    """Process user query and display response"""

    if not st.session_state.agent:
        st.error("Database agent is not connected. Please check your configuration.")
        return

  
    st.session_state.messages.append({"role": "user", "content": query})
    render_chat_message("user", query)

    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                start_time = time.time()
                response, result = st.session_state.agent.process_query(query)
                execution_time = time.time() - start_time

                
                st.markdown(response)

                # Show additional info if debug mode
                if config.agent.debug_mode:
                    with st.expander("Query Details"):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Query Type", result.query_type)
                        with col2:
                            st.metric("Success", "✅" if result.success else "❌")
                        with col3:
                            st.metric("Results", result.count)
                        with col4:
                            st.metric("Time (ms)", f"{result.execution_time_ms:.2f}")


                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "execution_time": execution_time,
                    "result_count": result.count
                })

                st.session_state.query_count += 1

            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

def render_main_chat():
    """Render the main chat interface"""

    st.title("Conversational Database Agent")
    st.markdown("Chat with your MongoDB database using natural language!")

    
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        extra_info = {k: v for k, v in message.items() if k not in ["role", "content"]}
        render_chat_message(role, content, extra_info if extra_info else None)

    
    query = st.chat_input("Ask me anything about your database...")

    #This part here handles pending query from sidebar buttons
    if "pending_query" in st.session_state:
        query = st.session_state.pending_query
        del st.session_state.pending_query

    if query:
        process_user_query(query)
        st.rerun()

def main():
    """Main Streamlit application"""

    
    initialize_session_state()

    render_sidebar()


    if "show_schema" in st.session_state and st.session_state.show_schema:
        render_schema_info()
        del st.session_state.show_schema
        if st.button("← Back to Chat"):
            st.rerun()
        return

    if "show_insights" in st.session_state and st.session_state.show_insights:
        render_insights()
        del st.session_state.show_insights
        if st.button("← Back to Chat"):
            st.rerun()
        return

    
    render_main_chat()

    # This shows welcome message if no messages at the starting
    if not st.session_state.messages:
        st.info("👋 Welcome! Ask me anything about your database. Try queries like 'How many customers do we have?' or 'What is the accounts collection?'")

if __name__ == "__main__":
    main()
