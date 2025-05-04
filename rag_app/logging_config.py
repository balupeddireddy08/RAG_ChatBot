# rag_chatbot/logging_config.py
import logging
import os
import sys
from datetime import datetime

def setup_logging():
    """Configure logging for the application"""
    # Ensure log directory exists
    log_dir = "chat_data/logs"
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