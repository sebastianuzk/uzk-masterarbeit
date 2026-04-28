#!/usr/bin/env python3
"""
Main entry point for the Autonomous Chatbot Agent.

Supports two agent modes:
- Single-Agent: Original ReactAgent with all tools
- Multi-Agent: Orchestrated system with specialized agents

Usage:
    # Single-Agent mode (default)
    python main.py
    python main.py --agent-mode single
    
    # Multi-Agent mode
    python main.py --agent-mode multi
    
    # Start Streamlit UI
    python main.py --ui
    python main.py --ui --agent-mode multi
"""

import argparse
import sys
import traceback
from pathlib import Path
from typing import NoReturn

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Chatbot Agent for KLIPS 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                        # CLI with Single-Agent
    python main.py --agent-mode multi     # CLI with Multi-Agent
    python main.py --ui                   # Streamlit UI with Single-Agent
    python main.py --ui --agent-mode multi  # Streamlit UI with Multi-Agent
        """
    )
    
    parser.add_argument(
        "--agent-mode",
        type=str,
        choices=["single", "multi", "confirmation", "constrained"],
        default="single",
        help="Agent mode: 'single' for ReactAgent, 'multi' for Multi-Agent system, 'confirmation' for ConfirmationAgent, 'constrained' for ConstrainedAgent (default: single)"
    )
    
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Start Streamlit web interface instead of CLI"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    
    return parser.parse_args()


def run_cli(agent_mode: str, debug: bool = False) -> None:
    """
    Start the agent in CLI mode.
    
    Args:
        agent_mode: "single" or "multi"
        debug: Enable debug output
    """
    from src.agent import create_agent
    
    print("=" * 60)
    print("🤖 Autonomous Chatbot Agent for KLIPS 2.0")
    print("=" * 60)
    print()
    
    # Create agent
    logger.info(f"Initializing agent in {agent_mode.upper()} mode...")
    print(f"Initializing agent in {agent_mode.upper()} mode...")
    agent = create_agent(mode=agent_mode)
    print()
    
    # Show available tools
    print("📦 Available tools:")
    for tool in agent.get_available_tools():
        print(f"   • {tool}")
    print()
    
    # Multi-Agent: show available agents
    if agent_mode == "multi" and hasattr(agent, 'get_available_agents'):
        print("🎭 Available agents:")
        for agent_name in agent.get_available_agents():
            print(f"   • {agent_name}")
        print()
    
    print("=" * 60)
    print("Enter your question (or 'quit'/'exit' to quit)")
    print("Enter 'clear' to clear the chat history")
    print("=" * 60)
    print()
    
    # Chat loop
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == "clear":
                agent.clear_memory()
                print("🗑️ Chat history cleared.\n")
                continue
            
            if user_input.lower() == "status":
                memory_info = agent.get_memory_summary()
                print(f"\n📊 Status:")
                print(f"   Messages: {memory_info['total_messages']}")
                print(f"   User: {memory_info['human_messages']}")
                print(f"   AI: {memory_info['ai_messages']}\n")
                continue
            
            # Send request to agent
            print("\n🤔 Agent is thinking...\n")
            response = agent.chat(user_input)
            print(f"🤖 Agent: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=debug)
            print(f"\n❌ Error: {e}\n")
            if debug:
                traceback.print_exc()


def run_streamlit(agent_mode: str) -> NoReturn:
    """
    Start the Streamlit web interface.
    
    Args:
        agent_mode: "single" or "multi"
    """
    import subprocess
    
    streamlit_path = project_root / "src" / "ui" / "streamlit_app.py"
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(streamlit_path),
        "--",
        f"--agent-mode={agent_mode}"
    ]
    
    logger.info(f"Starting Streamlit UI in {agent_mode.upper()} mode...")
    print(f"🚀 Starting Streamlit UI in {agent_mode.upper()} mode...")
    subprocess.run(cmd)
    sys.exit(0)


def main() -> None:
    """Main function."""
    args = parse_arguments()
    
    # Set up logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level)
    
    if args.ui:
        run_streamlit(args.agent_mode)
    else:
        run_cli(args.agent_mode, debug=args.debug)


if __name__ == "__main__":
    main()
