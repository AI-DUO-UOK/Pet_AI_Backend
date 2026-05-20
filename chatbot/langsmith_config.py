"""
LangSmith Configuration Module

This module handles the setup of LangSmith tracing for LangChain operations.
LangSmith enables debugging, testing, and monitoring of LLM applications.

Set up your environment variables in .env file:
    LANGCHAIN_API_KEY: Your LangSmith API key
    LANGCHAIN_TRACING_V2: Set to "true" to enable tracing
    LANGCHAIN_ENDPOINT: LangSmith API endpoint
    LANGCHAIN_PROJECT: Project name for organizing traces
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def setup_langsmith():
    """
    Configure LangSmith tracing for LangChain operations.
    
    This function sets up environment variables required by LangChain
    to send traces and metrics to LangSmith.
    
    Returns:
        bool: True if LangSmith is properly configured, False otherwise
    """
    
    # Get LangSmith API key (prompt if not set)
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        from getpass import getpass
        api_key = getpass("Enter LangSmith API Key (or press Enter to skip): ").strip()
        if not api_key:
            print("⚠️  LangSmith tracing disabled - API key not provided")
            return False
        os.environ["LANGCHAIN_API_KEY"] = api_key
    
    # Enable tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    
    # Set endpoint
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    
    # Set project name
    project_name = os.getenv("LANGCHAIN_PROJECT", "Pet_AI")
    os.environ["LANGCHAIN_PROJECT"] = project_name
    
    print(f"✅ LangSmith tracing enabled - Project: {project_name}")
    return True


def disable_langsmith():
    """
    Disable LangSmith tracing.
    Useful for development or when you don't want tracing enabled.
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    print("⚠️  LangSmith tracing disabled")


def is_langsmith_enabled():
    """
    Check if LangSmith tracing is currently enabled.
    
    Returns:
        bool: True if enabled, False otherwise
    """
    return os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
