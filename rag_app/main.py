import streamlit as st
import os
import sys

# Aggressive disabling of Streamlit's file watcher to prevent PyTorch class inspection errors
os.environ["STREAMLIT_SERVER_WATCHDOG_TIMEOUT"] = "0"
os.environ["STREAMLIT_SERVER_ENABLE_STATIC_SERVING"] = "false"
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_WATCH_INPUTS"] = "false" 
os.environ["USER_AGENT"] = "RAG-Chatbot/1.0"

# Import after setting environment variables
from rag_app.rag_engine import process_documents, answer_question, check_knowledge_base_exists
from rag_app.document_loader import get_input_data
from rag_app.history_storage import save_interaction, init_db, get_chat_history, clear_history
from rag_app.logging_config import logger

# Configure page settings
st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom styling
st.markdown("""
<style>
/* Main styling */
.main {
    background-color: #f9f9f9;
}

/* Header styling */
.header {
    padding: 1.5rem;
    background: linear-gradient(90deg, #4285f4, #0f9d58);
    border-radius: 10px;
    margin-bottom: 20px;
    color: white;
    text-align: center;
}

/* Chat container */
.chat-container {
    border-radius: 10px;
    background-color: white;
    padding: 20px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.1);
    margin-bottom: 20px;
    max-height: 400px;
    overflow-y: auto;
}

/* Message styling */
.message {
    padding: 10px 15px;
    margin-bottom: 10px;
    border-radius: 15px;
    width: 80%;
}

.user-message {
    background-color: #e3f2fd;
    margin-left: auto;
    text-align: right;
    border-bottom-right-radius: 4px;
}

.bot-message {
    background-color: #f1f1f1;
    margin-right: auto;
    border-bottom-left-radius: 4px;
}

/* Input area */
.input-area {
    display: flex;
    margin-top: 10px;
}

.input-area .stTextInput {
    flex-grow: 1;
    margin-right: 10px;
}

/* Remove default Streamlit padding */
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

/* Hide hamburger menu */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Welcome screen */
.welcome-screen {
    text-align: center;
    padding: 40px 20px;
    border-radius: 10px;
    background-color: white;
    box-shadow: 0 1px 5px rgba(0,0,0,0.1);
}

.welcome-icon {
    font-size: 80px;
    margin-bottom: 20px;
}

/* History items */
.history-item {
    padding: 10px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-bottom: 10px;
    background-color: white;
    cursor: pointer;
}

.history-item:hover {
    background-color: #f5f5f5;
}

/* Status indicator */
.status-indicator {
    padding: 5px 10px;
    font-size: 14px;
    border-radius: 50px;
    display: inline-block;
    margin-bottom: 10px;
}

.status-ready {
    background-color: #e6f4ea;
    color: #137333;
}

.status-warning {
    background-color: #fef7e0;
    color: #b06000;
}
</style>
""", unsafe_allow_html=True)

# Initialize the database
init_db()

# Function to ensure knowledge base state is correct
def initialize_knowledge_base_state():
    """Check if the knowledge base really exists and update session state accordingly"""
    exists = check_knowledge_base_exists()
    logger.info(f"Knowledge base existence check on startup: {exists}")
    
    # Update session state
    st.session_state.knowledge_base_exists = exists
    
    # Clean up other states if knowledge base doesn't exist
    if not exists:
        # Clear any document content that might be stored
        for content_key in ['pdf_content', 'docx_content', 'txt_content', 'text_content', 'url_content']:
            if content_key in st.session_state:
                del st.session_state[content_key]
        
        # Reset input processed flag
        st.session_state.input_processed = False
        st.session_state.current_input_data = ""

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "knowledge_base_exists" not in st.session_state:
    st.session_state.knowledge_base_exists = False  # Default to False
if "input_processed" not in st.session_state:
    st.session_state.input_processed = False
if "query_text" not in st.session_state:
    st.session_state.query_text = ""
if "current_input_data" not in st.session_state:
    st.session_state.current_input_data = ""
if "show_history" not in st.session_state:
    st.session_state.show_history = False

# Initialize knowledge base state
initialize_knowledge_base_state()

# Function to handle query submission
def handle_query_submit():
    if st.session_state.query_input and st.session_state.knowledge_base_exists:
        query = st.session_state.query_input
        
        # Check for duplicate
        is_duplicate = False
        if st.session_state.chat_history:
            for i in range(len(st.session_state.chat_history)-1, -1, -1):
                if st.session_state.chat_history[i]["role"] == "user" and st.session_state.chat_history[i]["content"] == query:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
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
                    
                    # Clear input
                    st.session_state.query_text = ""
                else:
                    st.error("Failed to get a response. Please try again.")

# Function to clear chat history
def clear_chat_history():
    st.session_state.chat_history = []

# Function to toggle history view
def toggle_history():
    st.session_state.show_history = not st.session_state.show_history

# Set page structure with a clean header
st.markdown('<div class="header"><h1>RAG Chatbot</h1><p>Retrieval-Augmented Generation for smarter responses</p></div>', unsafe_allow_html=True)

# Use a 2-column layout for upload/chat
col1, col2 = st.columns([1, 2])

# Left column - Knowledge base controls
with col1:
    st.markdown("### 📚 Knowledge Base")
    
    # Status indicator
    if st.session_state.knowledge_base_exists:
        st.markdown('<div class="status-indicator status-ready">Knowledge base ready</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-indicator status-warning">No knowledge base</div>', unsafe_allow_html=True)
    
    # Upload section
    with st.expander("Upload Documents", expanded=not st.session_state.knowledge_base_exists):
        input_type = st.selectbox(
            "Document Type", 
            ["PDF", "DOCX", "TXT", "Text", "Link"],
            help="Select the type of content you want to process"
        )
        
        # Get input data based on type and store it in session state
        input_data = get_input_data(input_type)
        if input_data:
            st.session_state.current_input_data = input_data
            st.success(f"Content loaded: {len(input_data)} characters")
        else:
            # Clear the current_input_data if no data was returned
            st.session_state.current_input_data = ""
        
        # Process button
        process_btn = st.button("Process Documents", type="primary", use_container_width=True)
        
        if process_btn:
            data_to_process = st.session_state.current_input_data
            
            if data_to_process and len(data_to_process) > 0:
                with st.spinner("Processing documents..."):
                    try:
                        success, message = process_documents(data_to_process)
                        if success:
                            st.session_state.knowledge_base_exists = True
                            st.session_state.input_processed = True
                            st.success(f"{message}")
                            st.rerun()
                        else:
                            st.error(message)
                    except Exception as e:
                        st.error(f"Error during document processing: {str(e)}")
                        logger.error(f"Unhandled error in document processing: {str(e)}")
            else:
                st.error("No content to process. Please provide input first.")
    
    # Previous conversations section
    st.markdown("### 📜 Conversation History")
    history_btn = st.button("Toggle History View", use_container_width=True, on_click=toggle_history)
    
    if st.session_state.show_history:
        history = get_chat_history(10)
        if history:
            for timestamp, question, answer in history:
                st.markdown(f"""
                <div class="history-item">
                    <div style="color: #666; font-size: 12px;">{timestamp}</div>
                    <div><strong>Q:</strong> {question[:50] + '...' if len(question) > 50 else question}</div>
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("Clear All History", use_container_width=True):
                clear_history()
                st.success("History cleared")
                st.rerun()
        else:
            st.info("No conversation history found")

# Right column - Chat interface
with col2:
    st.markdown("### 💬 Chat")
    
    # Chat container
    st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
    
    if st.session_state.chat_history:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="message user-message">
                    <strong>You:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="message bot-message">
                    <strong>Bot:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
    else:
        if st.session_state.knowledge_base_exists:
            st.markdown("""
            <div class="welcome-screen">
                <div class="welcome-icon">💬</div>
                <h3>Ready to Chat!</h3>
                <p>Ask a question about your documents below.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="welcome-screen">
                <div class="welcome-icon">👋</div>
                <h3>Welcome to RAG Chatbot!</h3>
                <p>Please upload and process documents in the left panel to create a knowledge base.</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat controls
    if st.session_state.chat_history:
        clear_chat = st.button("Clear Chat", use_container_width=True)
        if clear_chat:
            clear_chat_history()
            st.rerun()
    
    # Input area - only enabled if knowledge base exists
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    
    # Use columns for input and button
    input_cols = st.columns([5, 1])
    
    with input_cols[0]:
        query = st.text_input(
            "Message", 
            key="query_input",
            value=st.session_state.query_text,
            placeholder="Ask a question about your documents...",
            disabled=not st.session_state.knowledge_base_exists,
            label_visibility="collapsed"
        )
    
    with input_cols[1]:
        submit = st.button(
            "Send",
            type="primary", 
            disabled=not st.session_state.knowledge_base_exists,
            use_container_width=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle submit
    if submit and st.session_state.query_input:
        handle_query_submit()
        st.rerun()

# Add JavaScript for auto-scrolling to bottom of chat
st.markdown("""
<script>
    function scrollChatToBottom() {
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    // Scroll on page load
    window.addEventListener('load', scrollChatToBottom);
    
    // Create observer to scroll when new messages appear
    const chatObserver = new MutationObserver(scrollChatToBottom);
    
    // Start observing the chat container
    window.addEventListener('load', function() {
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatObserver.observe(chatContainer, { childList: true, subtree: true });
        }
    });
</script>
""", unsafe_allow_html=True)