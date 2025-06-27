"""
System prompts management utilities
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from utils.display import rich_print, print_syntax_highlighted


class PromptsManager:
    """Manages system prompts from files"""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.prompts_cache: Dict[str, str] = {}
        self.current_prompt_name: Optional[str] = "default"

    def ensure_prompts_directory(self) -> None:
        """Create prompts directory and default prompts if they don't exist"""
        if not self.prompts_dir.exists():
            self.prompts_dir.mkdir(exist_ok=True)
            rich_print(f"📁 Created prompts directory: {self.prompts_dir}", style="green")

            # Create default prompts
            self._create_default_prompts()

    def _create_default_prompts(self) -> None:
        """Create default prompt files"""
        # Default balanced prompt
        default_prompt = """You are an AI coding assistant that MUST use function calls to interact with files and directories.

CRITICAL RULES:
1. You MUST ALWAYS use function calls for ANY file system operation
2. You CANNOT provide file contents, code, or directory listings without using the appropriate function
3. When asked to write code or create files, you MUST use the write_file function
4. You MUST NOT give instructions or suggestions about files without first examining them with get_file_content or get_files_info

AVAILABLE FUNCTIONS:
1. get_files_info - Lists files in a directory
   - Use for: listing files, checking what exists, exploring directories
   - Arguments: {"directory": "path"} (use "." for current directory)

2. get_file_content - Reads a file's content
   - Use for: viewing code, reading files, examining content
   - Arguments: {"file_path": "path/to/file"}

3. write_file - Creates or overwrites a file
   - Use for: creating new files, saving code, updating files
   - Arguments: {"file_path": "path/to/file", "content": "file content"}

4. run_python_file - Executes a Python script
   - Use for: running scripts, testing code
   - Arguments: {"file_path": "script.py", "args": ["arg1", "arg2"]}

RESPONSE FORMAT:
You MUST respond with ONLY a JSON object when a function call is needed:
{
  "function_call": {
    "name": "function_name",
    "arguments": {
      "param1": "value1"
    }
  }
}

WORKFLOW EXAMPLES:
- User: "Show me what files are here" → Use get_files_info with directory="."
- User: "Create a hello world script" → Use write_file to create the script
- User: "What's in main.py?" → Use get_file_content with file_path="main.py"
- User: "Run the test script" → Use run_python_file with file_path="test.py"

IMPORTANT: Even if you know what a file might contain, you MUST use get_file_content to examine it first before discussing its contents."""

        # Strict prompt for better enforcement
        strict_prompt = """You are a function-calling AI agent. You communicate ONLY through function calls.

MANDATORY BEHAVIOR:
- EVERY response MUST be a function call in JSON format
- NEVER respond with plain text explanations
- NEVER give coding advice without examining files first
- ALWAYS write files when asked to create code

Function call format (ONLY valid response):
{"function_call": {"name": "function_name", "arguments": {"key": "value"}}}

Functions:
- get_files_info: List directory contents
- get_file_content: Read file
- write_file: Create/update file
- run_python_file: Execute Python script

Examples:
User: "list files" → {"function_call": {"name": "get_files_info", "arguments": {"directory": "."}}}
User: "create test.py" → {"function_call": {"name": "write_file", "arguments": {"file_path": "test.py", "content": "# code here"}}}"""

        # Creative/flexible prompt
        flexible_prompt = """You are a helpful AI coding assistant with access to function calls for file operations.

You can interact with files and directories using these functions:
- get_files_info(directory): List files in a directory
- get_file_content(file_path): Read a file's content
- write_file(file_path, content): Create or update a file
- run_python_file(file_path, args): Execute a Python script

When you need to perform file operations, respond with:
{
  "function_call": {
    "name": "function_name",
    "arguments": {"param": "value"}
  }
}

Feel free to explain your actions and provide helpful context along with function calls. You can combine explanations with function calls to create a more conversational experience.

If a task doesn't require file operations, you can respond normally without function calls."""

        # Minimal prompt
        minimal_prompt = """AI agent with file access.

Functions: get_files_info, get_file_content, write_file, run_python_file

Response format: {"function_call": {"name": "func", "arguments": {"arg": "val"}}}"""

        # Save default prompts
        prompts = {
            "default.md": default_prompt,
            "strict.md": strict_prompt,
            "flexible.md": flexible_prompt,
            "minimal.md": minimal_prompt
        }

        for filename, content in prompts.items():
            filepath = self.prompts_dir / filename
            filepath.write_text(content.strip())
            rich_print(f"✅ Created {filename}", style="dim green")

    def load_prompts(self) -> Dict[str, str]:
        """Load all available prompts from directory"""
        self.ensure_prompts_directory()
        self.prompts_cache.clear()

        # Supported extensions
        extensions = ['.md', '.txt', '.prompt']

        for file in self.prompts_dir.iterdir():
            if file.suffix in extensions and file.is_file():
                try:
                    content = file.read_text(encoding='utf-8')
                    prompt_name = file.stem
                    self.prompts_cache[prompt_name] = content
                except Exception as e:
                    rich_print(f"⚠️ Error loading {file.name}: {e}", style="yellow")

        return self.prompts_cache

    def list_prompts(self) -> List[Tuple[str, str, int]]:
        """List all available prompts with preview"""
        self.load_prompts()

        prompts_info = []
        for name, content in self.prompts_cache.items():
            # Get first line or first 80 chars as preview
            lines = content.strip().split('\n')
            preview = lines[0][:80] + "..." if len(lines[0]) > 80 else lines[0]
            prompts_info.append((name, preview, len(content)))

        return sorted(prompts_info)

    def get_prompt(self, name: str) -> Optional[str]:
        """Get a specific prompt by name"""
        if not self.prompts_cache:
            self.load_prompts()

        # Try exact match first
        if name in self.prompts_cache:
            return self.prompts_cache[name]

        # Try case-insensitive match
        for prompt_name, content in self.prompts_cache.items():
            if prompt_name.lower() == name.lower():
                return content

        return None

    def preview_prompt(self, name: str, max_lines: int = 20) -> Optional[str]:
        """Preview a prompt with line limit"""
        content = self.get_prompt(name)
        if content:
            lines = content.strip().split('\n')
            if len(lines) > max_lines:
                preview = '\n'.join(lines[:max_lines])
                preview += f"\n\n... [{len(lines) - max_lines} more lines]"
                return preview
            return content
        return None

    def save_prompt(self, name: str, content: str) -> bool:
        """Save a new prompt to file"""
        try:
            self.ensure_prompts_directory()
            filepath = self.prompts_dir / f"{name}.md"
            filepath.write_text(content.strip())
            self.prompts_cache[name] = content
            return True
        except Exception as e:
            rich_print(f"❌ Error saving prompt: {e}", style="red")
            return False

    def get_current_prompt_name(self) -> str:
        """Get the name of the currently active prompt"""
        return self.current_prompt_name or "custom"

    def set_current_prompt_name(self, name: str) -> None:
        """Set the name of the currently active prompt"""
        self.current_prompt_name = name
