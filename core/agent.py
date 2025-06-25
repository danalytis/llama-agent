"""
Main AI Agent implementation
"""

import json
import requests
import os
from typing import List, Dict, Optional
from core.config import AgentConfig, SYSTEM_PROMPT
from core.functions import execute_function, get_file_language
from utils.display import (
    rich_print,
    typewriter_print,
    print_syntax_highlighted,
    print_file_table,
    format_help_text,
    print_startup_banner,
    print_status_table,
    print_models_table,
)
from utils.terminal import setup_readline_history, save_readline_history


class OllamaAgent:
    """Main AI Agent class"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def call_ollama_api(self, messages: List[Dict]) -> Dict:
        """Call Ollama's REST API"""
        url = f"{self.config.api_base}/api/chat"

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": 4096, "temperature": 0.1},
        }

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            raise Exception(
                f"Ollama API error: {response.status_code} - {response.text}"
            )

        return response.json()

    def parse_function_call(self, text: str) -> Optional[Dict]:
        """Parse function call from model response"""
        text = text.strip()

        start_idx = text.find("{")
        end_idx = text.rfind("}") + 1

        if start_idx == -1 or end_idx == 0:
            return None

        try:
            json_str = text[start_idx:end_idx]
            parsed = json.loads(json_str)

            if "function_call" in parsed:
                return parsed["function_call"]
        except json.JSONDecodeError:
            pass

        return None

    def should_show_function_result(self, func_name: str, user_prompt: str) -> bool:
        """Determine if function result should be shown to user"""
        if self.config.verbose:
            return True

        # Keywords that indicate user wants to see content
        show_keywords = [
            "show",
            "display",
            "view",
            "see",
            "content",
            "contents",
            "read",
            "what is",
            "what's",
            "tell me about",
            "examine",
            "look at",
            "open",
            "check",
            "inspect",
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
        """Process a single conversation turn"""
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

                    rich_print(f"🔧 Calling function: {func_name}", style="bold yellow")

                    # Execute function
                    ai_result, user_result, extra_data = execute_function(
                        func_name, func_args, self.config.verbose
                    )

                    # Show result if appropriate
                    show_result = self.should_show_function_result(
                        func_name, user_prompt
                    )

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
                                    lang_part = (
                                        header.split("(")[1].split(")")[0].split(",")[0]
                                    )
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
                    self.messages.append(
                        {"role": "assistant", "content": assistant_response}
                    )
                    self.messages.append(
                        {"role": "user", "content": f"Function result: {ai_result}"}
                    )

                    if self.config.verbose:
                        rich_print(
                            "[DEBUG] Added function result to conversation", style="dim"
                        )

                else:
                    # Regular response
                    typewriter_print(
                        assistant_response,
                        self.config.typing_speed,
                        self.config.typing_enabled,
                        style="white",
                    )
                    self.messages.append(
                        {"role": "assistant", "content": assistant_response}
                    )
                    break

            except Exception as e:
                rich_print(f"❌ Error: {e}", style="red")
                break

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
                # TODO: Validate model exists
                self.config.model = new_model
                rich_print(f"✅ Switched to model: {new_model}", style="green")

        elif cmd == "clear":
            self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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

        elif cmd == "status":
            status_data = {
                "🤖 Model": self.config.model,
                "💬 Conversation turns": len(
                    [m for m in self.messages if m["role"] != "system"]
                ),
                "🔧 Verbose mode": "enabled" if self.config.verbose else "disabled",
                "🎨 Syntax highlighting": (
                    "enabled" if self.config.syntax_highlighting else "disabled"
                ),
                "🎭 Typing animation": (
                    f"enabled (speed: {self.config.typing_speed})"
                    if self.config.typing_enabled
                    else "disabled"
                ),
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
            "Syntax highlighting": (
                "enabled" if self.config.syntax_highlighting else "disabled"
            ),
            "Typing animation": (
                f"enabled (speed: {self.config.typing_speed})"
                if self.config.typing_enabled
                else "disabled"
            ),
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
