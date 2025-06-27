"""
Display utilities and formatting functions
"""

import time
from typing import List, Tuple, Optional
from utils.terminal import is_terminal_compatible, get_terminal_width

# Rich imports with fallback
try:
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Initialize console
RICH_ENABLED = RICH_AVAILABLE and is_terminal_compatible()
console = Console(width=get_terminal_width()) if RICH_ENABLED else None


def rich_print(
    text: str,
    style: Optional[str] = None,
    panel: bool = False,
    title: Optional[str] = None,
) -> None:
    """Print with rich formatting if available, fallback to regular print"""
    if RICH_ENABLED and console:
        if panel:
            console.print(Panel(text, title=title, style=style))
        else:
            console.print(text, style=style)
    else:
        print(text)


def print_syntax_highlighted(
    code: str, language: str = "python", enabled: bool = True
) -> None:
    """Print code with syntax highlighting"""
    if enabled and RICH_ENABLED and console:
        try:
            # Limit width to prevent terminal corruption
            width = min(get_terminal_width() - 4, 120)
            syntax = Syntax(
                code,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
                code_width=width,
            )
            console.print(syntax)
        except Exception:
            # Fallback if syntax highlighting fails
            print_code_plain(code, language)
    else:
        print_code_plain(code, language)


def print_code_plain(code: str, language: str) -> None:
    """Print code without syntax highlighting but with line numbers"""
    print(f"Content ({language}):")
    print("-" * 40)
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        print(f"{i:3d} | {line}")
    print("-" * 40)


def print_file_table(
    files_data: List[Tuple[str, str, str]], enabled: bool = True
) -> None:
    """Print file listing as a table"""
    if enabled and RICH_ENABLED and console:
        try:
            table = Table(title="📁 Directory Contents", width=get_terminal_width() - 4)
            table.add_column("Name", style="cyan", no_wrap=False, max_width=40)
            table.add_column("Type", style="magenta", width=10)
            table.add_column("Size", justify="right", style="green", width=12)

            for name, file_type, size in files_data:
                icon = "📁" if file_type == "directory" else "📄"
                # Truncate long filenames
                display_name = name if len(name) <= 35 else name[:32] + "..."
                table.add_row(f"{icon} {display_name}", file_type, size)

            console.print(table)
        except Exception:
            print_file_list_plain(files_data)
    else:
        print_file_list_plain(files_data)


def print_file_list_plain(files_data: List[Tuple[str, str, str]]) -> None:
    """Print file listing without rich formatting"""
    print("📁 Directory Contents:")
    print("-" * 60)
    for name, file_type, size in files_data:
        icon = "📁" if file_type == "directory" else "📄"
        print(f"{icon} {name:<30} {file_type:<10} {size:>10}")
    print("-" * 60)


def typewriter_print(
    text: str, speed: float = 0.03, enabled: bool = True, style: Optional[str] = None
) -> None:
    """Print text with typewriter effect"""
    if not enabled or speed <= 0:
        rich_print(text, style=style)
        return

    for char in text:
        if RICH_ENABLED and console and style:
            console.print(char, end="", style=style)
        else:
            print(char, end="", flush=True)

        if char != "\n":
            time.sleep(speed)

    print()  # Final newline


def format_help_text(rich_enabled: bool = True) -> None:
    """Display help text"""
    help_content = """
📚 Available slash commands:
  /quit, /exit, /q     - Exit the interactive session
  /help               - Show this help message
  /listmodels         - List all available Ollama models
  /model <name>       - Switch to a different model
  /prompt             - List view and change system_prompts
  /clear              - Clear conversation history
  /verbose            - Toggle verbose mode on/off
  /syntax             - Toggle syntax highlighting on/off
  /typing <speed>     - Enable typing animation (speed: 0.01-0.1)
  /typing off         - Disable typing animation
  /status             - Show current session status
  /pwd                - Show current working directory
  /ls [directory]     - Quick file listing (doesn't use AI)
  /cat <file>         - Quick file content view (doesn't use AI)

💡 Regular prompts (not starting with /) will be sent to the AI model.
💡 Typing speeds: 0.01=very fast, 0.03=normal, 0.05=slow, 0.1=very slow
    """

    if rich_enabled and RICH_ENABLED and console:
        try:
            help_panel = Panel(
                help_content.strip(),
                title="🤖 AI Agent Help",
                style="bold blue",
                width=get_terminal_width() - 4,
            )
            console.print(help_panel)
        except Exception:
            print(help_content)
    else:
        print(help_content)


def print_startup_banner(model: str, config: dict, rich_enabled: bool = True) -> None:
    """Print startup banner"""
    if rich_enabled and RICH_ENABLED and console:
        try:
            title = Text("🤖 Interactive AI Agent", style="bold cyan")
            info_table = Table.grid(padding=1)
            info_table.add_column(style="bold blue")
            info_table.add_column(style="green")

            for key, value in config.items():
                info_table.add_row(f"{key}:", str(value))

            startup_panel = Panel(
                info_table,
                title=title,
                style="bold blue",
                width=get_terminal_width() - 4,
            )
            console.print(startup_panel)
            console.print("─" * min(50, get_terminal_width()), style="dim")
        except Exception:
            print_startup_plain(model, config)
    else:
        print_startup_plain(model, config)


def print_startup_plain(model: str, config: dict) -> None:
    """Print startup banner without rich formatting"""
    print("🤖 Interactive AI Agent")
    for key, value in config.items():
        print(f"{key}: {value}")
    print("-" * 50)


def print_status_table(status_data: dict, rich_enabled: bool = True) -> None:
    """Print status information as a table"""
    if rich_enabled and RICH_ENABLED and console:
        try:
            status_table = Table(
                title="📊 Session Status",
                show_header=False,
                width=get_terminal_width() - 4,
            )
            status_table.add_column("Property", style="bold blue", width=20)
            status_table.add_column("Value", style="green")

            for key, value in status_data.items():
                status_table.add_row(key, str(value))

            console.print(status_table)
        except Exception:
            print_status_plain(status_data)
    else:
        print_status_plain(status_data)


def print_status_plain(status_data: dict) -> None:
    """Print status without rich formatting"""
    print("📊 Session Status:")
    for key, value in status_data.items():
        print(f"  {key}: {value}")


def print_models_table(
    models: List[str], current_model: str, rich_enabled: bool = True
) -> None:
    """Print available models as a table"""
    if rich_enabled and RICH_ENABLED and console:
        try:
            table = Table(
                title="📦 Available Ollama Models", width=get_terminal_width() - 4
            )
            table.add_column("Model", style="cyan", no_wrap=False)
            table.add_column("Status", style="green", width=15)

            for model in models:
                if model == current_model:
                    table.add_row(f"🎯 {model}", "← current")
                else:
                    table.add_row(f"🤖 {model}", "available")

            console.print(table)
        except Exception:
            print_models_plain(models, current_model)
    else:
        print_models_plain(models, current_model)


def print_models_plain(models: List[str], current_model: str) -> None:
    """Print models without rich formatting"""
    print("📦 Available Ollama models:")
    for model in models:
        indicator = " ← current" if model == current_model else ""
        print(f"  - {model}{indicator}")
# Add this function to your existing display.py file

def print_prompts_table(
    prompts_info: List[Tuple[str, str, int]], current_prompt: str, rich_enabled: bool = True
) -> None:
    """Print available prompts as a table"""
    if rich_enabled and RICH_ENABLED and console:
        try:
            table = Table(
                title="📝 Available System Prompts", width=get_terminal_width() - 4
            )
            table.add_column("Name", style="cyan", no_wrap=False, width=15)
            table.add_column("Preview", style="white", no_wrap=False)
            table.add_column("Size", style="green", width=10)
            table.add_column("Status", style="yellow", width=10)

            for name, preview, size in prompts_info:
                status = "← current" if name == current_prompt else ""
                size_str = f"{size} chars"
                table.add_row(f"📄 {name}", preview, size_str, status)

            console.print(table)
        except Exception:
            print_prompts_plain(prompts_info, current_prompt)
    else:
        print_prompts_plain(prompts_info, current_prompt)


def print_prompts_plain(prompts_info: List[Tuple[str, str, int]], current_prompt: str) -> None:
    """Print prompts without rich formatting"""
    print("📝 Available System Prompts:")
    print("-" * 80)
    for name, preview, size in prompts_info:
        indicator = " ← current" if name == current_prompt else ""
        print(f"📄 {name:<15} | {preview[:50]:<50} | {size} chars{indicator}")
    print("-" * 80)
