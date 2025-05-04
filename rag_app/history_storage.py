# rag_chatbot/history_storage.py
import sqlite3
import os
from datetime import datetime
from rag_app.logging_config import logger

# Use relative path that works regardless of where the script is run from
DB_DIR = "chat_data"
DB_PATH = os.path.join(DB_DIR, "chat_history.db")

def init_db():
    """Initialize the SQLite database for chat history"""
    try:
        # Ensure the directory for the DB exists
        os.makedirs(DB_DIR, exist_ok=True)
        logger.info(f"Ensuring database directory exists: {DB_DIR}")

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

def get_chat_history(limit=10):
    """Retrieve the most recent chat interactions
    
    Args:
        limit: Maximum number of records to retrieve
        
    Returns:
        List of (timestamp, question, answer) tuples
    """
    try:
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
        logger.info(f"Retrieved {len(history)} history items")
        return history
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return []

def clear_history():
    """Clear all chat history from the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history')
        conn.commit()
        conn.close()
        logger.info("Chat history cleared")
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")