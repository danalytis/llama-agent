"""
Configuration management for the Ollama AI Agent
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class AgentConfig:
    """Configuration for the AI agent"""

    model: str = "qwen2.5-coder:7b"
    verbose: bool = False
    typing_speed: float = 0.03
    typing_enabled: bool = True
    syntax_highlighting: bool = True
    rich_enabled: bool = True
    max_turns: int = 20
    api_base: str = "http://localhost:11434"

    def toggle_verbose(self) -> None:
        """Toggle verbose mode"""
        self.verbose = not self.verbose

    def toggle_syntax_highlighting(self) -> None:
        """Toggle syntax highlighting"""
        self.syntax_highlighting = not self.syntax_highlighting

    def toggle_typing(self) -> None:
        """Toggle typing animation"""
        self.typing_enabled = not self.typing_enabled

    def set_typing_speed(self, speed: float) -> bool:
        """Set typing speed, returns True if valid"""
        if 0.005 <= speed <= 0.2:
            self.typing_speed = speed
            return True
        return False


# System prompt for the AI agent
SYSTEM_PROMPT = """
You are a helpful AI coding agent.

When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

- When asked about "root" directory chose '.' as the value for directory argument instead
- List files and directories
- Read file contents
- Execute Python files with optional arguments
- Write or overwrite files

All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.

IMPORTANT: When you need to call a function, respond with a JSON object in this exact format:
{
  "function_call": {
    "name": "function_name",
    "arguments": {
      "param1": "value1",
      "param2": "value2"
    }
  }
}

Available functions:
- get_files_info: Lists files in directory. Parameters: {"directory": "path"}
- get_file_content: Reads file content. Parameters: {"file_path": "path"}
- write_file: Writes to file. Parameters: {"file_path": "path", "content": "text"}
- run_python_file: Runs Python script. Parameters: {"file_path": "path", "args": ["arg1", "arg2"]}

If you don't need to call a function, just respond normally with text.
"""
