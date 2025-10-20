#!/usr/bin/env python3
"""
Simple Plan-and-Execute Agent Test (Synchronous)
"""

import sys
from pathlib import Path

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.plan_and_execute_agent import app

def main():
    # Your query here
    query = "Was ist die Heimatstadt des Gewinners der Australian Open 2024 bei den Herren?"
    #query = "Wann fand die Australian Open 2024 statt?"

    # Run the agent (synchronous)
    config = {"configurable": {"thread_id": "test-thread"}, "recursion_limit": 50}
    inputs = {"input": query}

    print(f"🚀 Query: {query}")
    print("=" * 60)

    for event in app.stream(inputs, config=config):
        for k, v in event.items():
            if k != "__end__":
                print(f"[{k}] {v}")
                print("-" * 40)

if __name__ == "__main__":
    main()
