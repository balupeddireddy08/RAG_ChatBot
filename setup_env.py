#!/usr/bin/env python
"""
Setup environment for the RAG Chatbot application
This script helps configure API keys and other environment variables
"""
import os
import sys
import getpass

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
{Colors.GREEN}Environment Setup Wizard{Colors.ENDC}
"""
    print(banner)

def check_env_file():
    """Check if .env file exists"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        print(f"{Colors.BLUE}Found existing .env file at {env_path}{Colors.ENDC}")
        overwrite = input("Would you like to overwrite it? (y/n): ").strip().lower()
        if overwrite != 'y':
            print(f"{Colors.WARNING}Setup canceled. Using existing .env file.{Colors.ENDC}")
            return False
    return True

def setup_env_variables():
    """Set up environment variables in .env file"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    print(f"\n{Colors.BOLD}Setting up environment variables for RAG Chatbot{Colors.ENDC}")
    print(f"This will create a .env file at: {env_path}")
    
    print(f"\n{Colors.BOLD}API Key Configuration:{Colors.ENDC}")
    print("The RAG Chatbot requires a Google Gemini API key to function.")
    print(f"You can get your key at: {Colors.UNDERLINE}https://ai.google.dev/{Colors.ENDC}")
    
    # Get API key securely (without echo)
    api_key = getpass.getpass(f"\n{Colors.BLUE}Enter your Gemini API key: {Colors.ENDC}")
    
    if not api_key:
        print(f"{Colors.FAIL}No API key provided. Setup canceled.{Colors.ENDC}")
        return False
    
    # Optional port configuration
    print(f"\n{Colors.BOLD}Web Server Configuration (Optional):{Colors.ENDC}")
    port = input(f"{Colors.BLUE}Enter port number for the web server (default: 7860): {Colors.ENDC}").strip()
    port = port if port.isdigit() else "7860"
    
    # Write to .env file
    try:
        with open(env_path, "w") as f:
            f.write(f"GEMINI_API_KEY={api_key}\n")
            f.write(f"PORT={port}\n")
        
        print(f"\n{Colors.GREEN}✅ .env file created successfully!{Colors.ENDC}")
        print(f"The file contains your API key and will be used when running the application.")
        print(f"If you need to change these settings, you can edit the file or run this setup again.")
        return True
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Error creating .env file: {str(e)}{Colors.ENDC}")
        return False

def main():
    """Main function"""
    print_banner()
    
    if not check_env_file():
        return
    
    if setup_env_variables():
        print(f"\n{Colors.GREEN}✅ Setup completed successfully!{Colors.ENDC}")
        print(f"\nTo start the RAG Chatbot, run:")
        print(f"{Colors.BOLD}python run_app.py{Colors.ENDC}")
    else:
        print(f"\n{Colors.FAIL}❌ Setup failed.{Colors.ENDC}")
        print("Please try again or manually create a .env file with GEMINI_API_KEY=your_key_here")

if __name__ == "__main__":
    main() 