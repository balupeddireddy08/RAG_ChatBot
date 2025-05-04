import streamlit as st
import os
import sys

# Disable watchdog to prevent PyTorch class inspection errors
os.environ["STREAMLIT_SERVER_WATCHDOG_TIMEOUT"] = "0"

# Set a user agent to avoid warnings
os.environ["USER_AGENT"] = "RAG-Chatbot/1.0"

# Import after setting environment variables
from rag_app.rag_engine import process_documents, answer_question, check_knowledge_base_exists
from rag_app.document_loader import get_input_data
from rag_app.history_storage import save_interaction, init_db, get_chat_history
from rag_app.logging_config import logger

# Configure page settings
st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize the database
logger.info("Initializing database")
init_db()

# App title and description
st.title("RAG Chatbot")
st.markdown("""
This application uses Retrieval-Augmented Generation (RAG) to answer questions based on your documents.
1. Select an input type and provide your content
2. Process the input to build a knowledge base
3. Ask questions about your content
""")

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "knowledge_base_exists" not in st.session_state:
    st.session_state.knowledge_base_exists = check_knowledge_base_exists()
if "input_processed" not in st.session_state:
    st.session_state.input_processed = False
if "query_text" not in st.session_state:
    st.session_state.query_text = ""
if "current_input_data" not in st.session_state:
    st.session_state.current_input_data = ""

# Function to handle query submission
def handle_query_submit():
    if st.session_state.query_input and st.session_state.knowledge_base_exists:
        query = st.session_state.query_input
        logger.info(f"User query: {query}")
        
        # Add user question to history
        st.session_state.chat_history.append({"role": "user", "content": query})
        
        # Get answer
        with st.spinner("Thinking..."):
            response = answer_question(query)
            if response:
                # Add response to history
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                # Save to database
                save_interaction(query, response)
                logger.info("Query answered and saved to history")
                
                # Clear input
                st.session_state.query_text = ""
            else:
                st.error("Failed to get a response. Please try again.")

# Sidebar for input processing
with st.sidebar:
    st.header("Document Processing")
    input_type = st.selectbox(
        "Choose input type", 
        ["Text", "Link", "PDF", "DOCX", "TXT"],
        help="Select the type of content you want to process"
    )
    
    # Get input data based on type and store it in session state
    input_data = get_input_data(input_type)
    if input_data:
        # Store the current input data in session state
        st.session_state.current_input_data = input_data
        
        # Show content length for debugging
        st.info(f"Content loaded: {len(input_data)} characters")
        
        # Log for debugging
        logger.info(f"Input data received for {input_type}: {len(input_data)} characters")
    
    # Add a process button that will use the stored input data
    if st.button("Process Input", type="primary"):
        # Get the data from session state
        data_to_process = st.session_state.current_input_data
        
        if data_to_process and len(data_to_process) > 0:
            logger.info(f"Processing input of type: {input_type}, length: {len(data_to_process)} chars")
            
            with st.spinner("Processing documents..."):
                success, message = process_documents(data_to_process)
                if success:
                    st.session_state.knowledge_base_exists = True
                    st.session_state.input_processed = True
                    st.success(message)
                    logger.info("Knowledge base successfully created")
                else:
                    st.error(message)
                    logger.error(f"Failed to process input: {message}")
        else:
            st.error("No content to process. Please provide input first.")
            logger.error("No content to process")
    
    # Display current knowledge base status
    st.divider()
    if st.session_state.knowledge_base_exists:
        st.success("Knowledge base is ready!")
    else:
        st.warning("No knowledge base available. Please process input first.")

# Main area for chat
st.divider()

# Chat interface
st.header("Ask Questions")

# Chat input - use the session state value for default value, but don't modify widget state directly
query = st.text_input(
    "Ask a question about your documents", 
    key="query_input", 
    value=st.session_state.query_text,
    on_change=handle_query_submit
)

# Submit button
col1, col2 = st.columns([1, 5])
with col1:
    submit = st.button("Submit", type="primary", disabled=not st.session_state.knowledge_base_exists)

if submit and st.session_state.query_input:
    handle_query_submit()

# Display chat history
st.divider()
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"**You:** {message['content']}")
    else:
        st.markdown(f"**RAG Bot:** {message['content']}")
    st.divider()

# Option to view past chat history from database
if st.checkbox("Show chat history from database"):
    logger.info("Retrieving chat history from database")
    history = get_chat_history(10)
    if history:
        st.subheader("Recent Chat History")
        for timestamp, question, answer in history:
            with st.expander(f"Q: {question[:50]}... ({timestamp})"):
                st.markdown(f"**Question:** {question}")
                st.markdown(f"**Answer:** {answer}")
    else:
        st.info("No chat history found in database.")