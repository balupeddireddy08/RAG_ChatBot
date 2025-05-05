# rag_chatbot/logging_config.py
import logging
import os
import sys
from datetime import datetime

def get_log_path():
    """Get log directory path with fallback for permission issues"""
    # Check environment variable first (set by run_app.py if permission issues)
    if "RAG_PATH_CHAT_DATA_LOGS" in os.environ:
        return os.environ["RAG_PATH_CHAT_DATA_LOGS"]
    
    # Default path
    log_dir = os.path.join("chat_data", "logs")
    
    # If we can't write to the default path, use /tmp
    if not os.access("chat_data", os.W_OK):
        tmp_dir = os.path.join("/tmp", "chat_data", "logs")
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir
        
    return log_dir

def setup_logging():
    """Configure logging for the application"""
    # Get log directory with permission handling
    log_dir = get_log_path()
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/rag_chatbot_{timestamp}.log"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create a logger for this application
    app_logger = logging.getLogger("rag_chatbot")
    app_logger.setLevel(logging.INFO)
    app_logger.info(f"Using log directory: {log_dir}")
    
    # Suppress specific warnings from libraries we use
    logging.getLogger("torch._dynamo.utils").setLevel(logging.ERROR)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("streamlit").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    
    # Set warning filters for known issues
    import warnings
    warnings.filterwarnings("ignore", message=".*gpu is not available.*")
    warnings.filterwarnings("ignore", message=".*Trying to initialize with empty weights*")
    warnings.filterwarnings("ignore", category=UserWarning, module="torch")
    warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
    
    # Log startup message
    app_logger.info(f"Logging initialized. Log file: {log_file}")
    
    return app_logger

# Create a logger instance that can be imported elsewhere
logger = setup_logging()