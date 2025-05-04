#!/usr/bin/env python
"""
Fix script for RAG Chatbot project structure
This script reorganizes the project files to match the imports
"""
import os
import shutil
import sys

def ensure_directory(path):
    """Ensure directory exists"""
    if not os.path.exists(path):
        print(f"Creating directory: {path}")
        os.makedirs(path, exist_ok=True)

def main():
    print("\n" + "="*60)
    print(" RAG Chatbot Structure Fix ".center(60, "="))
    print("="*60 + "\n")
    
    # Get current directory
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    
    # Check if we're in the project root
    if not os.path.exists("run_app.py") or not os.path.exists("requirements.txt"):
        print("⚠️ This script must be run from the project root directory!")
        print("Please navigate to the directory containing run_app.py and try again.")
        return False
    
    # Create rag_app directory if it doesn't exist
    ensure_directory("rag_app")
    
    # Files to move into rag_app directory
    files_to_move = [
        "rag_engine.py",
        "document_loader.py",
        "history_storage.py",
        "logging_config.py",
        "main.py"
    ]
    
    # Create __init__.py if it doesn't exist
    with open(os.path.join("rag_app", "__init__.py"), "w") as f:
        f.write("# Package initialization file\n")
    
    # Move files if they're in the root directory
    for filename in files_to_move:
        if os.path.exists(filename) and not os.path.exists(os.path.join("rag_app", filename)):
            print(f"Moving {filename} to rag_app directory")
            shutil.move(filename, os.path.join("rag_app", filename))
    
    # Fix imports in moved files
    files_to_fix = [
        os.path.join("rag_app", "main.py"),
        os.path.join("rag_app", "rag_engine.py"),
        os.path.join("rag_app", "document_loader.py"),
        os.path.join("rag_app", "history_storage.py")
    ]
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            print(f"Fixing imports in {filepath}")
            with open(filepath, "r") as file:
                content = file.read()
            
            # Fix imports
            content = content.replace("from logging_config import", "from rag_app.logging_config import")
            content = content.replace("from rag_engine import", "from rag_app.rag_engine import")
            content = content.replace("from document_loader import", "from rag_app.document_loader import")
            content = content.replace("from history_storage import", "from rag_app.history_storage import")
            
            # Write back
            with open(filepath, "w") as file:
                file.write(content)
    
    # Ensure chat_data directory exists
    ensure_directory("chat_data")
    ensure_directory("chat_data/logs")
    ensure_directory("chat_data/knowledge_base")
    
    print("\n✅ Project structure fixed successfully!")
    print("\nYou can now run the application with:")
    print("  python run_app.py")
    
    return True

if __name__ == "__main__":
    main()