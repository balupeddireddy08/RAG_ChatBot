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

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """Print a stylish banner for the application"""
    banner = f"""
{Colors.BLUE}{Colors.BOLD}
██████╗  █████╗  ██████╗     ██████╗██╗  ██╗ █████╗ ████████╗██████╗  ██████╗ ████████╗
██╔══██╗██╔══██╗██╔════╝    ██╔════╝██║  ██║██╔══██╗╚══██╔══╝██╔══██╗██╔═══██╗╚══██╔══╝
██████╔╝███████║██║  ███╗   ██║     ███████║███████║   ██║   ██████╔╝██║   ██║   ██║   
██╔══██╗██╔══██║██║   ██║   ██║     ██╔══██║██╔══██║   ██║   ██╔══██╗██║   ██║   ██║   
██║  ██║██║  ██║╚██████╔╝   ╚██████╗██║  ██║██║  ██║   ██║   ██████╔╝╚██████╔╝   ██║   
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═════╝  ╚═════╝    ╚═╝   
{Colors.ENDC}
{Colors.GREEN}Retrieval-Augmented Generation Chatbot{Colors.ENDC}
"""
    print(banner)

def check_gemini_api_key():
    """Check if Gemini API key is set in environment"""
    if not os.environ.get("GEMINI_API_KEY"):
        print(f"\n{Colors.FAIL}❌ ERROR: GEMINI_API_KEY environment variable not set.{Colors.ENDC}")
        print("The application requires a Google Gemini API key to function.")
        print("\nPlease set your Gemini API key using one of these methods:")
        print(f"  1. Create a {Colors.BOLD}.env{Colors.ENDC} file with: GEMINI_API_KEY=your_key_here")
        print("  2. Or set it in your environment before running this script:")
        print("     - Windows: set GEMINI_API_KEY=your_key_here")
        print("     - Linux/Mac: export GEMINI_API_KEY=your_key_here")
        print(f"\nGet your API key at: {Colors.UNDERLINE}https://ai.google.dev/{Colors.ENDC}")
        return False
    return True

def ensure_directories():
    """Ensure all required directories exist with proper permissions"""
    required_dirs = {
        "chat_data": os.environ.get("RAG_PATH_CHAT_DATA", "chat_data"),
        "chat_data/logs": os.environ.get("RAG_PATH_CHAT_DATA_LOGS", "chat_data/logs"),
        "chat_data/knowledge_base": os.environ.get("RAG_PATH_CHAT_DATA_KNOWLEDGE_BASE", "chat_data/knowledge_base")
    }
    
    print(f"\n{Colors.BLUE}Setting up directory structure...{Colors.ENDC}")
    
    for name, path in required_dirs.items():
        try:
            print(f"  Creating directory: {path}")
            os.makedirs(path, exist_ok=True)
            # Test write access
            test_file = os.path.join(path, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print(f"  {Colors.GREEN}✅ Directory {path} is writable{Colors.ENDC}")
        except (PermissionError, OSError) as e:
            # If we can't write to the specified path, try using /tmp
            tmp_path = os.path.join("/tmp", name)
            print(f"  {Colors.WARNING}⚠️ Cannot write to {path}: {e}{Colors.ENDC}")
            print(f"  {Colors.WARNING}Using alternative path: {tmp_path}{Colors.ENDC}")
            
            try:
                # Create the alternative directory
                os.makedirs(tmp_path, exist_ok=True)
                
                # Set environment variables to use this path
                env_var_name = f"RAG_PATH_{name.upper().replace('/', '_')}"
                os.environ[env_var_name] = tmp_path
                print(f"  {Colors.GREEN}✅ Set {env_var_name}={tmp_path}{Colors.ENDC}")
            except Exception as e2:
                print(f"  {Colors.FAIL}❌ ERROR: Failed to create alternative directory: {e2}{Colors.ENDC}")
                return False
    
    return True

def check_project_structure():
    """Check if project structure is correct"""
    print(f"\n{Colors.BLUE}Verifying project structure...{Colors.ENDC}")
    
    if not os.path.exists("rag_app") or not os.path.isdir("rag_app"):
        print(f"\n{Colors.FAIL}❌ ERROR: rag_app directory not found.{Colors.ENDC}")
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
    
    all_files_found = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  {Colors.FAIL}❌ {file} (missing){Colors.ENDC}")
            all_files_found = False
            
    if not all_files_found:
        print(f"\n{Colors.FAIL}❌ ERROR: Required files missing.{Colors.ENDC}")
        print("Please run fix_project_structure.py first or check your project structure.")
        return False
    
    print(f"\n{Colors.GREEN}✅ Project structure looks good!{Colors.ENDC}")
    return True

def main():
    """Main entry point"""
    print_banner()
    
    # Check project structure
    if not check_project_structure():
        print(f"\n{Colors.FAIL}❌ Application launch aborted due to project structure issues.{Colors.ENDC}")
        sys.exit(1)
    
    # Create necessary directories with permission handling
    if not ensure_directories():
        print(f"\n{Colors.FAIL}❌ Application launch aborted due to directory permission issues.{Colors.ENDC}")
        sys.exit(1)
    
    # Run Streamlit application with specific arguments to avoid PyTorch issues
    print(f"\n{Colors.GREEN}🚀 Starting RAG Chatbot...{Colors.ENDC}")
    print(f"{Colors.BOLD}Press Ctrl+C to stop the application{Colors.ENDC}")
    
    try:
        # Use a more direct command with specific flags to avoid PyTorch issues
        port = os.environ.get("PORT", "7860")
        print(f"\n{Colors.BLUE}Starting web server on port {port}...{Colors.ENDC}")
        print(f"Once started, you can access the application at: {Colors.UNDERLINE}http://localhost:{port}{Colors.ENDC}")
        
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
        print(f"\n\n{Colors.GREEN}👋 Application stopped by user.{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}❌ Error running Streamlit: {e}{Colors.ENDC}")
        print("\nCheck the logs in chat_data/logs/ for more details.")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Unexpected error: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()