"""
Function execution handlers for the AI agent
"""

import os
import sys
import subprocess
from typing import Dict, Tuple, List
from utils.display import rich_print


def get_file_language(file_path: str) -> str:
    """Detect programming language from file extension"""
    ext = os.path.splitext(file_path)[1].lower()
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".fish": "fish",
        ".ps1": "powershell",
        ".html": "html",
        ".htm": "html",
        ".xml": "xml",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        ".sql": "sql",
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "rst",
        ".txt": "text",
        ".log": "text",
        ".dockerfile": "dockerfile",
        ".makefile": "makefile",
        ".r": "r",
        ".R": "r",
        ".m": "matlab",
        ".pl": "perl",
        ".vim": "vim",
    }
    return language_map.get(ext, "text")


def execute_get_files_info(
    arguments: Dict, verbose: bool = False
) -> Tuple[str, str, List[Tuple[str, str, str]]]:
    """List files in directory"""
    directory = arguments.get("directory", ".")

    if verbose:
        rich_print(f"  📂 Listing files in: {directory}", style="dim")

    try:
        files = os.listdir(directory)
        file_info = []
        files_data = []

        for file in sorted(files):
            full_path = os.path.join(directory, file)
            try:
                size = os.path.getsize(full_path)
                is_dir = os.path.isdir(full_path)
                file_type = "directory" if is_dir else "file"

                # For AI context
                file_info.append(f"{file} ({file_type}, {size} bytes)")

                # For display
                if size > 1024 * 1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                elif size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size} B"
                files_data.append((file, file_type, size_str))

            except:
                file_info.append(f"{file} (unknown)")
                files_data.append((file, "unknown", "unknown"))

        ai_result = f"Files in '{directory}':\n" + "\n".join(file_info)
        user_result = f"📁 Files in '{directory}'"

        return ai_result, user_result, files_data

    except FileNotFoundError:
        error_msg = f"❌ Error: Directory '{directory}' not found"
        return error_msg, error_msg, []
    except PermissionError:
        error_msg = f"❌ Error: Permission denied accessing '{directory}'"
        return error_msg, error_msg, []


def execute_get_file_content(arguments: Dict, verbose: bool = False) -> Tuple[str, str]:
    """Read file content"""
    file_path = arguments.get("file_path")
    if not file_path:
        error_msg = "❌ Error: file_path parameter required"
        return error_msg, error_msg

    if verbose:
        rich_print(f"  📖 Reading file: {file_path}", style="dim")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

            # AI gets limited but sufficient content
            if len(content) > 2000:
                ai_content = (
                    content[:2000]
                    + f"\n[Note: This file has {len(content)} total characters. The above excerpt should be sufficient to answer most questions about this file.]"
                )
            else:
                ai_content = content

            ai_result = f"Content of '{file_path}':\n{ai_content}"

            # User display format
            language = get_file_language(file_path)
            user_result = f"📄 {file_path} ({language}, {len(content)} chars):{content}"

            return ai_result, user_result

    except FileNotFoundError:
        error_msg = f"❌ Error: File '{file_path}' not found"
        return error_msg, error_msg
    except PermissionError:
        error_msg = f"❌ Error: Permission denied reading '{file_path}'"
        return error_msg, error_msg
    except UnicodeDecodeError:
        error_msg = (
            f"❌ Error: Cannot read '{file_path}' - binary file or encoding issue"
        )
        return error_msg, error_msg


def execute_write_file(arguments: Dict, verbose: bool = False) -> Tuple[str, str]:
    """Write content to file"""
    file_path = arguments.get("file_path")
    content = arguments.get("content", "")

    if not file_path:
        error_msg = "❌ Error: file_path parameter required"
        return error_msg, error_msg

    if verbose:
        rich_print(f"  ✍️  Writing to file: {file_path}", style="dim")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        result = f"✅ Successfully wrote {len(content)} characters to '{file_path}'"
        return result, result
    except PermissionError:
        error_msg = f"❌ Error: Permission denied writing to '{file_path}'"
        return error_msg, error_msg
    except Exception as e:
        error_msg = f"❌ Error writing to '{file_path}': {str(e)}"
        return error_msg, error_msg


def execute_run_python_file(arguments: Dict, verbose: bool = False) -> Tuple[str, str]:
    """Run Python script"""
    file_path = arguments.get("file_path")
    args = arguments.get("args", [])

    if not file_path:
        error_msg = "❌ Error: file_path parameter required"
        return error_msg, error_msg

    if verbose:
        rich_print(
            f"  🐍 Running Python file: {file_path} with args: {args}", style="dim"
        )

    try:
        cmd = [sys.executable, file_path] + args

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, cwd=os.getcwd()
        )

        output = ""
        if result.stdout:
            output += f"📤 STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"🚨 STDERR:\n{result.stderr}\n"
        output += f"🔢 Return code: {result.returncode}"

        return output, output

    except subprocess.TimeoutExpired:
        error_msg = f"⏰ Error: Script '{file_path}' timed out after 30 seconds"
        return error_msg, error_msg
    except FileNotFoundError:
        error_msg = f"❌ Error: Python file '{file_path}' not found"
        return error_msg, error_msg
    except Exception as e:
        error_msg = f"❌ Error running '{file_path}': {str(e)}"
        return error_msg, error_msg


# Function registry
FUNCTION_HANDLERS = {
    "get_files_info": execute_get_files_info,
    "get_file_content": execute_get_file_content,
    "write_file": execute_write_file,
    "run_python_file": execute_run_python_file,
}


def execute_function(
    function_name: str, arguments: Dict, verbose: bool = False
) -> Tuple[str, str, any]:
    """Execute a function and return results"""
    if function_name not in FUNCTION_HANDLERS:
        error_msg = f"❌ Error: Unknown function '{function_name}'"
        return error_msg, error_msg, None

    try:
        handler = FUNCTION_HANDLERS[function_name]
        result = handler(arguments, verbose)

        # Handle different return formats
        if function_name == "get_files_info":
            ai_result, user_result, files_data = result
            return ai_result, user_result, files_data
        else:
            ai_result, user_result = result
            return ai_result, user_result, None

    except Exception as e:
        error_msg = f"❌ Error executing {function_name}: {str(e)}"
        return error_msg, error_msg, None
