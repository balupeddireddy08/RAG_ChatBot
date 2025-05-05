#!/usr/bin/env python
"""
Run script for the RAG Chatbot application
This handles common errors and sets necessary environment variables
"""
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set environment variables to avoid common errors
os.environ["USER_AGENT"] = "RAG-Chatbot/1.0"
os.environ["STREAMLIT_SERVER_WATCHDOG_TIMEOUT"] = "100" # Increased timeout
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"  # Avoids protobuf issues
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"  # Run in headless mode
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"  # Disable usage stats
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # Enable PyTorch fallbacks

# Disable PyTorch JIT to avoid issues with Streamlit's watchdog
os.environ["PYTORCH_JIT"] = "0"

def check_gemini_api_key():
    """Check if Gemini API key is set in environment"""
    if not os.environ.get("GEMINI_API_KEY"):
        print("\n❌ ERROR: GEMINI_API_KEY environment variable not set.")
        print("The application requires a Google Gemini API key to function.")
        print("\nPlease set your Gemini API key using one of these methods:")
        print("  1. Create a .env file with: GEMINI_API_KEY=your_key_here")
        print("  2. Or set it in your environment before running this script:")
        print("     - Windows: set GEMINI_API_KEY=your_key_here")
        print("     - Linux/Mac: export GEMINI_API_KEY=your_key_here")
        print("\nGet your API key at: https://ai.google.dev/")
        return False
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import streamlit
        import sentence_transformers
        import lancedb
        return True
    except ImportError as e:
        print(f"\n❌ ERROR: Missing required dependency: {str(e)}")
        print("Please install all required dependencies:")
        print("  pip install -r requirements.txt")
        return False

def ensure_directories():
    """Ensure all required directories exist"""
    dirs = ["chat_data", "chat_data/logs", "chat_data/knowledge_base"]
    for directory in dirs:
        if not os.path.exists(directory):
            print(f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)
    return True

def check_project_structure():
    """Check if project structure is correct"""
    if not os.path.exists("rag_app") or not os.path.isdir("rag_app"):
        print("\n❌ ERROR: rag_app directory not found.")
        print("Please run fix_project_structure.py first or check your project structure.")
        return False
        
    required_files = [
        "rag_app/__init__.py",
        "rag_app/main.py",
        "rag_app/rag_engine.py",
        "rag_app/document_loader.py",
        "rag_app/history_storage.py",
        "rag_app/logging_config.py"
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"\n❌ ERROR: Required file {file} not found.")
            print("Please run fix_project_structure.py first or check your project structure.")
            return False
            
    return True

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print(" RAG Chatbot Launcher ".center(60, "="))
    print("="*60 + "\n")
    
    # Check project structure
    if not check_project_structure():
        print("\n❌ Application launch aborted due to project structure issues.")
        sys.exit(1)
    
    # Check for dependencies and API key
    if not check_dependencies() or not check_gemini_api_key():
        print("\n❌ Application launch aborted due to missing requirements.")
        sys.exit(1)
    
    # Ensure directories exist
    ensure_directories()
    
    # Run Streamlit application with specific arguments to avoid PyTorch issues
    print("\n🚀 Starting RAG Chatbot...")
    print("Press Ctrl+C to stop the application")
    
    try:
        # Use a more direct command with specific flags to avoid PyTorch issues
        command = [
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            "rag_app/main.py",
            "--browser.serverAddress", "localhost",
            "--server.headless", "true",
            "--server.runOnSave", "false",  # Disable auto-rerun on save
            "--server.enableCORS", "false",
            "--server.port", "7860",
            "--server.enableXsrfProtection", "false",
            "--server.maxUploadSize", "200",
            "--theme.base", "light"
        ]
        subprocess.run(command, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running Streamlit: {e}")
        print("\nCheck the logs in chat_data/logs/ for more details.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()