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
    """Ensure all required directories exist with proper permissions"""
    required_dirs = {
        "chat_data": os.environ.get("RAG_PATH_CHAT_DATA", "chat_data"),
        "chat_data/logs": os.environ.get("RAG_PATH_CHAT_DATA_LOGS", "chat_data/logs"),
        "chat_data/knowledge_base": os.environ.get("RAG_PATH_CHAT_DATA_KNOWLEDGE_BASE", "chat_data/knowledge_base")
    }
    
    for name, path in required_dirs.items():
        try:
            print(f"Ensuring directory exists: {path}")
            os.makedirs(path, exist_ok=True)
            # Test write access
            test_file = os.path.join(path, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print(f"✅ Directory {path} is writable")
        except (PermissionError, OSError) as e:
            # If we can't write to the specified path, try using /tmp
            tmp_path = os.path.join("/tmp", name)
            print(f"⚠️ Cannot write to {path}: {e}")
            print(f"Using alternative path: {tmp_path}")
            
            try:
                # Create the alternative directory
                os.makedirs(tmp_path, exist_ok=True)
                
                # Set environment variables to use this path
                env_var_name = f"RAG_PATH_{name.upper().replace('/', '_')}"
                os.environ[env_var_name] = tmp_path
                print(f"✅ Set {env_var_name}={tmp_path}")
            except Exception as e2:
                print(f"❌ ERROR: Failed to create alternative directory: {e2}")
                return False
    
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
    
    # Create necessary directories with permission handling
    if not ensure_directories():
        print("\n❌ Application launch aborted due to directory permission issues.")
        sys.exit(1)
    
    # Check for dependencies and API key
    if not check_dependencies() or not check_gemini_api_key():
        print("\n❌ Application launch aborted due to missing requirements.")
        sys.exit(1)
    
    # Run Streamlit application with specific arguments to avoid PyTorch issues
    print("\n🚀 Starting RAG Chatbot...")
    print("Press Ctrl+C to stop the application")
    
    try:
        # Use a more direct command with specific flags to avoid PyTorch issues
        port = os.environ.get("PORT", "7860")
        command = [
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            "rag_app/main.py",
            "--browser.serverAddress", "0.0.0.0",  # Listen on all interfaces
            "--server.headless", "true",
            "--server.runOnSave", "false",  # Disable auto-rerun on save
            "--server.enableCORS", "false",
            "--server.port", port,
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