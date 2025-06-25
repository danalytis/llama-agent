#!/usr/bin/env python3
"""
Ollama AI Agent - Main Script
A beautiful, interactive AI coding assistant with function calling capabilities.
"""

import sys
import argparse
from pathlib import Path

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.agent import OllamaAgent
from core.config import AgentConfig
from utils.terminal import check_ollama_connection
from utils.display import rich_print


def main():
    parser = argparse.ArgumentParser(
        description="Ollama AI Agent with function calling"
    )
    parser.add_argument("--prompt", type=str, help="Single user input prompt")
    parser.add_argument(
        "--interactive", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed debug output"
    )
    parser.add_argument(
        "--model", type=str, default="qwen2.5-coder:7b", help="Ollama model to use"
    )
    parser.add_argument(
        "--list-models", action="store_true", help="List available Ollama models"
    )
    parser.add_argument(
        "--typing-speed",
        type=float,
        default=0.03,
        help="Typing animation speed (0.005-0.2)",
    )
    parser.add_argument(
        "--no-typing", action="store_true", help="Disable typing animation"
    )
    parser.add_argument(
        "--no-syntax", action="store_true", help="Disable syntax highlighting"
    )
    parser.add_argument(
        "--no-rich", action="store_true", help="Disable Rich formatting entirely"
    )

    args = parser.parse_args()

    # Create configuration
    config = AgentConfig(
        model=args.model,
        verbose=args.verbose,
        typing_speed=args.typing_speed,
        typing_enabled=not args.no_typing,
        syntax_highlighting=not args.no_syntax,
        rich_enabled=not args.no_rich,
    )

    # Validate typing speed
    if not (0.005 <= config.typing_speed <= 0.2):
        rich_print("Error: typing speed must be between 0.005 and 0.2", style="red")
        sys.exit(1)

    # Handle list models command
    if args.list_models:
        agent = OllamaAgent(config)
        agent.list_models()
        return

    # Check if Ollama is running
    if not check_ollama_connection():
        rich_print(
            "Error: Cannot connect to Ollama. Make sure it's running with: ollama serve",
            style="red",
        )
        sys.exit(1)

    # Create and run agent
    agent = OllamaAgent(config)

    if args.interactive:
        agent.run_interactive()
    else:
        if not args.prompt:
            rich_print(
                "error: must provide --prompt or use --interactive mode", style="red"
            )
            sys.exit(1)

        agent.run_single_prompt(args.prompt)


if __name__ == "__main__":
    main()
