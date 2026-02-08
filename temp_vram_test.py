"""
VRAM-Test: Prüfe VRAM-Verbrauch des Chatbots
"""
import os
import subprocess
import time

os.environ['ENABLE_HYBRID_RETRIEVAL'] = 'false'
os.environ['ENABLE_SPARSE_RETRIEVAL'] = 'false'

def get_vram_usage():
    """Hole VRAM-Nutzung via nvidia-smi."""
    result = subprocess.run(
        ['nvidia-smi', '--query-gpu=memory.used,memory.free,memory.total', '--format=csv,noheader,nounits'],
        capture_output=True, text=True
    )
    used, free, total = [int(x.strip()) for x in result.stdout.strip().split(',')]
    return used, free, total

print("=" * 60)
print("VRAM-TEST: Chatbot mit llama3.1:8b")
print("=" * 60)

# Vorher
used, free, total = get_vram_usage()
print(f"\n[VORHER] VRAM: {used} MiB / {total} MiB (frei: {free} MiB)")

# Starte Chatbot
print("\nLade Chatbot...")
from src.agent.react_agent import create_react_agent
agent = create_react_agent()

print("\nSende Test-Anfrage um LLM zu laden...")
response = agent.chat("Hallo, wie geht es dir?")
print(f"Response: {response[:100]}...")

# Kurz warten damit VRAM sich stabilisiert
time.sleep(2)

# Nachher
used_after, free_after, total = get_vram_usage()
print(f"\n[NACHHER] VRAM: {used_after} MiB / {total} MiB (frei: {free_after} MiB)")

vram_diff = used_after - used
print(f"\n[VERBRAUCH] Chatbot benötigt ca. {vram_diff} MiB VRAM")
print(f"[VERFÜGBAR] Noch {free_after} MiB frei")

print("\n" + "=" * 60)
print("BGE-Reranker-v2-m3 Anforderungen:")
print("  - Modellgröße: ~568 MB (laut Ollama)")
print("  - Geschätzter VRAM: ~800-1200 MiB")
print("=" * 60)

if free_after > 1200:
    print(f"\n✅ Genug VRAM frei ({free_after} MiB) - Reranker sollte passen!")
else:
    print(f"\n⚠️ Nur {free_after} MiB frei - Reranker könnte knapp werden")
    print(f"   Context-Window müsste reduziert werden")

# Prüfe aktuelles Context-Window
print("\n" + "=" * 60)
print("Aktuelles Context-Window:")
result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
print(result.stdout)
