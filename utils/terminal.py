"""
Terminal detection and utilities
"""

import os
import sys
import requests
import readline
from typing import Optional


def is_terminal_compatible() -> bool:
    """Check if terminal supports rich formatting"""
    # Check for problematic terminals
    term = os.environ.get("TERM", "").lower()
    inside_emacs = os.environ.get("INSIDE_EMACS") is not None
    emacs_term = "emacs" in term or "eterm" in term

    # Disable rich in problematic environments
    if inside_emacs or emacs_term or term in ["dumb", "unknown"]:
        return False

    # Check if stdout is a tty
    if not sys.stdout.isatty():
        return False

    return True


def setup_readline_history() -> Optional[str]:
    """Setup readline for command history and arrow key navigation"""
    try:
        # Enable tab completion
        readline.parse_and_bind("tab: complete")

        # Set up history file
        history_file = os.path.expanduser("~/.ollama_agent_history")
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass  # No history file yet

        # Set maximum history length
        readline.set_history_length(1000)

        return history_file
    except ImportError:
        # readline not available (Windows without pyreadline)
        return None


def save_readline_history(history_file: Optional[str]) -> None:
    """Save command history to file"""
    if history_file:
        try:
            readline.write_history_file(history_file)
        except:
            pass  # Ignore errors when saving history


def check_ollama_connection(api_base: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f"{api_base}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def get_terminal_width() -> int:
    """Get terminal width, with fallback"""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80  # fallback width
