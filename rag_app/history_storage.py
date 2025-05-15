# rag_chatbot/history_storage.py
import sqlite3
import os
from datetime import datetime
from rag_app.logging_config import logger

# Use environment variables for paths if available (for permission handling)
def get_db_path():
    """Get database path with fallback for permission issues"""
    # Check environment variable first (set by run_app.py if permission issues)
    if "RAG_PATH_CHAT_DATA" in os.environ:
        DB_DIR = os.environ["RAG_PATH_CHAT_DATA"]
    else:
        DB_DIR = "chat_data"
    
    # Try to use the default path
    DB_PATH = os.path.join(DB_DIR, "chat_history.db")
    
    # If we can't write to the default path, use /tmp
    if not os.access(DB_DIR, os.W_OK):
        tmp_dir = os.path.join("/tmp", "chat_data")
        os.makedirs(tmp_dir, exist_ok=True)
        DB_PATH = os.path.join(tmp_dir, "chat_history.db")
        logger.warning(f"Using alternative database path: {DB_PATH}")
    
    return DB_PATH

def init_db():
    """Initialize the SQLite database for chat history"""
    try:
        # Get the database path with permission handling
        DB_PATH = get_db_path()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        logger.info(f"Using database path: {DB_PATH}")

        # Connect and initialize the table
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                question TEXT,
                answer TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise

def save_interaction(question, answer):
    """Save a Q&A interaction to the database
    
    Args:
        question: The user's question
        answer: The system's answer
    """
    try:
        DB_PATH = get_db_path()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO history (timestamp, question, answer)
            VALUES (?, ?, ?)
        ''', (timestamp, question, answer))
        conn.commit()
        conn.close()
        logger.info(f"Saved interaction at {timestamp}")
    except Exception as e:
        logger.error(f"Error saving interaction: {str(e)}")

def format_timestamp(timestamp_str):
    """Convert ISO timestamp to a human-readable format
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        Formatted timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%b %d, %Y at %I:%M %p")  # e.g. "Jan 01, 2023 at 10:30 AM"
    except Exception as e:
        logger.error(f"Error formatting timestamp: {str(e)}")
        return timestamp_str

def get_chat_history(limit=10):
    """Retrieve the most recent chat interactions
    
    Args:
        limit: Maximum number of records to retrieve
        
    Returns:
        List of (timestamp, question, answer) tuples with formatted timestamp
    """
    try:
        DB_PATH = get_db_path()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, question, answer 
            FROM history 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        history = cursor.fetchall()
        conn.close()
        
        # Format timestamps to be more readable
        formatted_history = [(format_timestamp(ts), q, a) for ts, q, a in history]
        
        logger.info(f"Retrieved {len(history)} history items")
        return formatted_history
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return []

def clear_history():
    """Clear all chat history from the database"""
    try:
        DB_PATH = get_db_path()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history')
        conn.commit()
        conn.close()
        logger.info("Chat history cleared")
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")