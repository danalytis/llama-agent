"""
Main AI Agent implementation with improved function calling
"""

import json
import requests
import os
import re
from typing import List, Dict, Optional, Tuple
from core.config import AgentConfig, SYSTEM_PROMPT, STRICT_SYSTEM_PROMPT
from core.functions import execute_function, get_file_language
from core.prompts import PromptsManager
from utils.display import (
    rich_print,
    typewriter_print,
    print_syntax_highlighted,
    print_file_table,
    format_help_text,
    print_startup_banner,
    print_status_table,
    print_models_table,
    print_prompts_table,
)
from utils.terminal import setup_readline_history, save_readline_history


class OllamaAgent:
    """Main AI Agent class with improved function calling"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.prompts_manager = PromptsManager()

        # Allow switching between prompts based on model behavior
        system_prompt = STRICT_SYSTEM_PROMPT if config.enforce_function_calls else SYSTEM_PROMPT
        self.messages = [{"role": "system", "content": system_prompt}]
        self.function_call_failures = 0  # Track failures for adaptive behavior

    def set_initial_prompt(self, prompt_name: str) -> None:
        """Set initial system prompt from file"""
        if prompt_name:
            prompt_content = self.prompts_manager.get_prompt(prompt_name)
            if prompt_content:
                self.messages[0] = {"role": "system", "content": prompt_content}
                self.prompts_manager.set_current_prompt_name(prompt_name)
                rich_print(f"📝 Loaded system prompt: {prompt_name}", style="green")
            else:
                rich_print(f"⚠️ Prompt '{prompt_name}' not found, using default", style="yellow")

    def manage_context_window(self) -> None:
        """Manage conversation context to prevent overflow"""
        # Keep system prompt + last N messages
        if len(self.messages) > self.config.max_context_messages:
            # Always keep the system prompt
            system_msg = self.messages[0]
            # Keep the most recent messages
            recent_messages = self.messages[-(self.config.max_context_messages - 1):]
            self.messages = [system_msg] + recent_messages

            if self.config.verbose:
                rich_print("🔄 Context window trimmed to prevent overflow", style="dim")

    def reinforce_system_prompt(self) -> None:
        """Add a reminder about function calling to reinforce behavior"""
        reminder = {
            "role": "system",
            "content": "REMINDER: You MUST use function calls for ALL file operations. "
                      "Respond ONLY with JSON function calls, not explanations."
        }
        self.messages.append(reminder)

    def call_ollama_api(self, messages: List[Dict]) -> Dict:
        """Call Ollama's REST API with improved error handling"""
        url = f"{self.config.api_base}/api/chat"

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": 4096,
                "temperature": self.config.temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1  # Reduce repetition
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code != 200:
                raise Exception(
                    f"Ollama API error: {response.status_code} - {response.text}"
                )
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception("Ollama API timeout - model may be too slow")
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")

    def parse_function_call(self, text: str) -> Optional[Dict]:
        """Enhanced function call parsing with multiple strategies"""
        text = text.strip()

        # Strategy 1: Direct JSON parsing
        try:
            # Look for JSON object
            json_match = re.search(r'\{.*"function_call".*\}', text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if "function_call" in parsed:
                    return parsed["function_call"]
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from code blocks
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_block_match:
            try:
                parsed = json.loads(code_block_match.group(1))
                if "function_call" in parsed:
                    return parsed["function_call"]
            except json.JSONDecodeError:
                pass

        # Strategy 3: Flexible parsing for common patterns
        # Look for function names and arguments separately
        func_patterns = [
            r'function[_\s]*name["\s:]*(["\']?)(\w+)\1',
            r'name["\s:]*(["\']?)(\w+)\1',
            r'"(\w+)"\s*:\s*\{.*arguments',
        ]

        for pattern in func_patterns:
            match = re.search(pattern, text)
            if match:
                func_name = match.group(2) if match.lastindex >= 2 else match.group(1)

                # Try to find arguments
                args_match = re.search(r'arguments["\s:]*(\{[^}]*\})', text, re.DOTALL)
                if args_match:
                    try:
                        arguments = json.loads(args_match.group(1))
                        return {"name": func_name, "arguments": arguments}
                    except json.JSONDecodeError:
                        # Try with empty arguments
                        return {"name": func_name, "arguments": {}}

        # Strategy 4: Heuristic detection
        # If response mentions file operations but no valid JSON, enforce function calling
        file_operation_keywords = [
            "create", "write", "save", "read", "list", "show", "display",
            "file", "directory", "folder", "script", "code"
        ]

        if any(keyword in text.lower() for keyword in file_operation_keywords):
            # Model tried to explain instead of using functions
            self.function_call_failures += 1
            if self.config.verbose:
                rich_print("⚠️ Model provided explanation instead of function call", style="yellow")
            return None

        return None

    def should_show_function_result(self, func_name: str, user_prompt: str) -> bool:
        """Determine if function result should be shown to user"""
        if self.config.verbose:
            return True

        # Keywords that indicate user wants to see content
        show_keywords = [
            "show", "display", "view", "see", "content", "contents",
            "read", "what is", "what's", "tell me about", "examine",
            "look at", "open", "check", "inspect"
        ]

        user_lower = user_prompt.lower()

        # Show file content when explicitly requested
        if func_name == "get_file_content":
            for keyword in show_keywords:
                if keyword in user_lower:
                    return True

        # Always show file listings and operations
        if func_name in ["get_files_info", "write_file", "run_python_file"]:
            return True

        return False

    def process_conversation_turn(self, user_prompt: str) -> None:
        """Process a single conversation turn with improved function calling"""
        # Manage context window before processing
        self.manage_context_window()

        # If we've had multiple function call failures, reinforce the prompt
        if self.function_call_failures >= 2:
            self.reinforce_system_prompt()
            self.function_call_failures = 0

        for i in range(1, self.config.max_turns):
            try:
                response = self.call_ollama_api(self.messages)
                assistant_response = response["message"]["content"]

                if self.config.verbose:
                    rich_print(f"\n--- Turn {i} ---", style="dim")
                    rich_print(f"Model response: {assistant_response}", style="dim")

                function_call = self.parse_function_call(assistant_response)

                if function_call:
                    func_name = function_call.get("name")
                    func_args = function_call.get("arguments", {})

                    # Validate function name
                    valid_functions = ["get_files_info", "get_file_content", "write_file", "run_python_file"]
                    if func_name not in valid_functions:
                        rich_print(f"⚠️ Invalid function: {func_name}", style="yellow")
                        # Add error to context and retry
                        self.messages.append({"role": "assistant", "content": assistant_response})
                        error_msg = f"Error: '{func_name}' is not a valid function. Valid functions are: {', '.join(valid_functions)}"
                        self.messages.append({"role": "user", "content": error_msg})
                        continue

                    rich_print(f"🔧 Calling function: {func_name}", style="bold yellow")

                    # Execute function
                    ai_result, user_result, extra_data = execute_function(
                        func_name, func_args, self.config.verbose
                    )

                    # Show result if appropriate
                    show_result = self.should_show_function_result(func_name, user_prompt)

                    if show_result:
                        rich_print("\n📋 Function Result:", style="bold green")

                        # Handle different display types
                        if func_name == "get_files_info" and extra_data:
                            print_file_table(extra_data, self.config.rich_enabled)
                        elif func_name == "get_file_content" and ":" in user_result:
                            # Extract file info and content
                            parts = user_result.split(":", 1)
                            if len(parts) == 2:
                                header, content = parts
                                rich_print(header, style="bold cyan")
                                # Extract language from header
                                if "(" in header and ")" in header:
                                    lang_part = header.split("(")[1].split(")")[0].split(",")[0]
                                    print_syntax_highlighted(
                                        content,
                                        lang_part,
                                        self.config.syntax_highlighting,
                                    )
                                else:
                                    print(content)
                            else:
                                print(user_result)
                        else:
                            print(user_result)
                        print()

                    # Add to conversation
                    self.messages.append({"role": "assistant", "content": assistant_response})
                    self.messages.append({"role": "user", "content": f"Function result: {ai_result}"})

                    if self.config.verbose:
                        rich_print("[DEBUG] Added function result to conversation", style="dim")

                else:
                    # No function call detected
                    if self.should_enforce_function_call(assistant_response, user_prompt):
                        # Model should have used a function but didn't
                        self.function_call_failures += 1
                        rich_print("⚠️ Enforcing function call usage...", style="yellow")

                        # Add a correction message
                        self.messages.append({"role": "assistant", "content": assistant_response})
                        correction = (
                            "You must use a function call to complete this request. "
                            "Please respond with ONLY a JSON function call, not an explanation."
                        )
                        self.messages.append({"role": "user", "content": correction})
                        continue
                    else:
                        # Legitimate text response
                        typewriter_print(
                            assistant_response,
                            self.config.typing_speed,
                            self.config.typing_enabled,
                            style="white",
                        )
                        self.messages.append({"role": "assistant", "content": assistant_response})
                        break

            except Exception as e:
                rich_print(f"❌ Error: {e}", style="red")
                break

    def should_enforce_function_call(self, response: str, user_prompt: str) -> bool:
        """Determine if the model should have used a function call"""
        # Keywords indicating file operations
        action_keywords = [
            "create", "write", "make", "generate", "build",
            "show", "list", "display", "read", "view", "see",
            "run", "execute", "test", "check"
        ]

        file_keywords = [
            "file", "script", "code", "program", "directory",
            "folder", "content", ".py", ".txt", ".js"
        ]

        response_lower = response.lower()
        prompt_lower = user_prompt.lower()

        # Check if user asked for a file operation
        has_action = any(keyword in prompt_lower for keyword in action_keywords)
        has_file_ref = any(keyword in prompt_lower for keyword in file_keywords)

        # Check if model is trying to explain instead of doing
        explaining_phrases = [
            "you can", "you could", "you should", "to create",
            "to write", "here's how", "you need to", "i would",
            "let me explain", "to do this"
        ]

        is_explaining = any(phrase in response_lower for phrase in explaining_phrases)

        return (has_action and has_file_ref) or is_explaining

    def list_models(self) -> None:
        """List available Ollama models"""
        try:
            response = requests.get(f"{self.config.api_base}/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                models = [model["name"] for model in models_data["models"]]
                print_models_table(models, self.config.model, self.config.rich_enabled)
            else:
                rich_print("No models found or Ollama not running", style="red")
        except Exception as e:
            rich_print(f"Error listing models: {e}", style="red")

    def handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns True to continue, False to exit"""
        cmd_parts = command[1:].split()
        cmd = cmd_parts[0].lower()

        if cmd in ["quit", "exit", "q"]:
            rich_print("👋 Goodbye!", style="green")
            return False

        elif cmd == "help":
            format_help_text(self.config.rich_enabled)

        elif cmd == "listmodels":
            self.list_models()

        elif cmd == "model":
            if len(cmd_parts) < 2:
                rich_print("❌ Usage: /model <model_name>", style="red")
                rich_print("💡 Use /listmodels to see available models", style="dim")
            else:
                new_model = cmd_parts[1]
                self.config.model = new_model
                rich_print(f"✅ Switched to model: {new_model}", style="green")

        elif cmd == "clear":
            system_prompt = STRICT_SYSTEM_PROMPT if self.config.enforce_function_calls else SYSTEM_PROMPT
            self.messages = [{"role": "system", "content": system_prompt}]
            self.function_call_failures = 0
            rich_print("🧹 Conversation history cleared", style="green")

        elif cmd == "verbose":
            self.config.toggle_verbose()
            status = "enabled" if self.config.verbose else "disabled"
            rich_print(f"🔧 Verbose mode {status}", style="blue")

        elif cmd == "syntax":
            self.config.toggle_syntax_highlighting()
            status = "enabled" if self.config.syntax_highlighting else "disabled"
            rich_print(f"🎨 Syntax highlighting {status}", style="blue")

        elif cmd == "typing":
            if len(cmd_parts) < 2:
                current_status = (
                    f"enabled (speed: {self.config.typing_speed})"
                    if self.config.typing_enabled
                    else "disabled"
                )
                rich_print(f"🎭 Typing animation: {current_status}", style="blue")
                rich_print("💡 Usage: /typing <speed> or /typing off", style="dim")
            else:
                param = cmd_parts[1].lower()
                if param == "off":
                    self.config.typing_enabled = False
                    rich_print("🎭 Typing animation disabled", style="blue")
                else:
                    try:
                        speed = float(param)
                        if self.config.set_typing_speed(speed):
                            self.config.typing_enabled = True
                            rich_print(
                                f"🎭 Typing animation enabled (speed: {speed})",
                                style="blue",
                            )
                        else:
                            rich_print(
                                "❌ Speed must be between 0.005 and 0.2", style="red"
                            )
                    except ValueError:
                        rich_print(
                            "❌ Invalid speed. Use a number (e.g., 0.03) or 'off'",
                            style="red",
                        )

        elif cmd == "enforce":
            self.config.enforce_function_calls = not self.config.enforce_function_calls
            status = "strict" if self.config.enforce_function_calls else "flexible"
            # Update system prompt
            system_prompt = STRICT_SYSTEM_PROMPT if self.config.enforce_function_calls else SYSTEM_PROMPT
            self.messages[0] = {"role": "system", "content": system_prompt}
            rich_print(f"🎯 Function call enforcement: {status}", style="blue")

        elif cmd == "prompt":
            if len(cmd_parts) < 2:
                # List available prompts
                prompts_info = self.prompts_manager.list_prompts()
                current = self.prompts_manager.get_current_prompt_name()
                print_prompts_table(prompts_info, current, self.config.rich_enabled)
                rich_print("\n💡 Usage: /prompt <name> to switch prompts", style="dim")
                rich_print("💡 Usage: /prompt view <name> to preview a prompt", style="dim")
            else:
                subcommand = cmd_parts[1].lower()

                if subcommand == "view" and len(cmd_parts) > 2:
                    # Preview a prompt
                    prompt_name = cmd_parts[2]
                    preview = self.prompts_manager.preview_prompt(prompt_name)
                    if preview:
                        rich_print(f"\n📝 Preview of '{prompt_name}' prompt:", style="bold cyan")
                        print_syntax_highlighted(preview, "markdown", self.config.syntax_highlighting)
                    else:
                        rich_print(f"❌ Prompt '{prompt_name}' not found", style="red")

                elif subcommand == "reload":
                    # Reload prompts from disk
                    self.prompts_manager.load_prompts()
                    rich_print("🔄 Reloaded prompts from disk", style="green")

                elif subcommand == "save":
                    # Save current system prompt to file
                    if len(cmd_parts) > 2:
                        name = cmd_parts[2]
                        current_prompt = self.messages[0]["content"]
                        if self.prompts_manager.save_prompt(name, current_prompt):
                            rich_print(f"💾 Saved current prompt as '{name}.md'", style="green")
                    else:
                        rich_print("❌ Usage: /prompt save <name>", style="red")

                else:
                    # Switch to a different prompt
                    prompt_name = cmd_parts[1]
                    prompt_content = self.prompts_manager.get_prompt(prompt_name)

                    if prompt_content:
                        # Update system prompt
                        self.messages[0] = {"role": "system", "content": prompt_content}
                        self.prompts_manager.set_current_prompt_name(prompt_name)
                        self.function_call_failures = 0
                        rich_print(f"✅ Switched to prompt: {prompt_name}", style="green")
                    else:
                        rich_print(f"❌ Prompt '{prompt_name}' not found", style="red")
                        rich_print("💡 Use /prompt to see available prompts", style="dim")

        elif cmd == "status":
            status_data = {
                "🤖 Model": self.config.model,
                "📝 System Prompt": self.prompts_manager.get_current_prompt_name(),
                "💬 Conversation turns": len([m for m in self.messages if m["role"] != "system"]),
                "🔧 Verbose mode": "enabled" if self.config.verbose else "disabled",
                "🎨 Syntax highlighting": (
                    "enabled" if self.config.syntax_highlighting else "disabled"
                ),
                "🎭 Typing animation": (
                    f"enabled (speed: {self.config.typing_speed})"
                    if self.config.typing_enabled
                    else "disabled"
                ),
                "🎯 Function enforcement": "strict" if self.config.enforce_function_calls else "flexible",
                "📊 Context window": f"{len(self.messages)}/{self.config.max_context_messages} messages",
                "🌡️ Temperature": str(self.config.temperature),
                "📂 Working directory": os.getcwd(),
            }
            print_status_table(status_data, self.config.rich_enabled)

        elif cmd == "pwd":
            rich_print(f"📂 Current directory: {os.getcwd()}", style="blue")

        elif cmd == "ls":
            directory = cmd_parts[1] if len(cmd_parts) > 1 else "."
            try:
                files = os.listdir(directory)
                rich_print(f"📁 Files in '{directory}':", style="bold blue")
                for file in sorted(files):
                    full_path = os.path.join(directory, file)
                    if os.path.isdir(full_path):
                        rich_print(f"  📁 {file}/", style="cyan")
                    else:
                        size = os.path.getsize(full_path)
                        rich_print(f"  📄 {file} ({size} bytes)", style="white")
            except Exception as e:
                rich_print(f"❌ Error listing directory: {e}", style="red")

        elif cmd == "cat":
            if len(cmd_parts) < 2:
                rich_print("❌ Usage: /cat <filename>", style="red")
            else:
                filename = cmd_parts[1]
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        content = f.read()
                        if len(content) > 1500:
                            content = (
                                content[:1500]
                                + f"\n... [truncated - showing first 1500 of {len(content)} characters]"
                            )
                            content += f"\n💡 Use AI prompt 'show me the full content of {filename}' for complete file"

                        rich_print(f"📄 Content of '{filename}':", style="bold cyan")
                        language = get_file_language(filename)
                        print_syntax_highlighted(
                            content, language, self.config.syntax_highlighting
                        )
                except Exception as e:
                    rich_print(f"❌ Error reading file: {e}", style="red")

        else:
            rich_print(f"❌ Unknown command: /{cmd}", style="red")
            rich_print("💡 Use /help to see available commands", style="dim")

        return True

    def run_interactive(self) -> None:
        """Run in interactive mode"""
        config_info = {
            "Model": self.config.model,
            "System Prompt": self.prompts_manager.get_current_prompt_name(),
            "Syntax highlighting": (
                "enabled" if self.config.syntax_highlighting else "disabled"
            ),
            "Typing animation": (
                f"enabled (speed: {self.config.typing_speed})"
                if self.config.typing_enabled
                else "disabled"
            ),
            "Function enforcement": "strict" if self.config.enforce_function_calls else "flexible",
            "Commands": "Type /help for commands",
            "History": "Use ↑/↓ arrow keys",
        }

        print_startup_banner(self.config.model, config_info, self.config.rich_enabled)

        # Setup command history
        history_file = setup_readline_history()

        try:
            while True:
                try:
                    user_input = input(f"\n[{self.config.model}]> ").strip()

                    if not user_input:
                        continue

                    # Handle slash commands
                    if user_input.startswith("/"):
                        if not self.handle_slash_command(user_input):
                            break
                        continue

                    # Regular AI prompt
                    self.messages.append({"role": "user", "content": user_input})
                    self.process_conversation_turn(user_input)

                except KeyboardInterrupt:
                    rich_print(
                        "\n\n👋 Interrupted. Use /quit to exit gracefully.",
                        style="yellow",
                    )
                    continue
                except EOFError:
                    rich_print("\n👋 Goodbye!", style="green")
                    break
        finally:
            save_readline_history(history_file)

    def run_single_prompt(self, prompt: str) -> None:
        """Run a single prompt"""
        self.messages.append({"role": "user", "content": prompt})
        self.process_conversation_turn(prompt)
