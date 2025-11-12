#!/usr/bin/env python3
"""
LangSmith Status Check für ARES-Evaluation
==========================================
"""

import os
from config.settings import settings

def main():
    print('🔍 LANGSMITH-STATUS FÜR ARES-EVALUATION:')
    print()

    print('📊 Aktuelle LangSmith-Konfiguration:')
    print(f'   🎯 LANGSMITH_TRACING: {settings.LANGSMITH_TRACING}')
    api_key_status = "Gesetzt" if settings.LANGSMITH_API_KEY else "Nicht gesetzt"
    print(f'   🔑 LANGSMITH_API_KEY: {api_key_status}')
    print(f'   📁 LANGSMITH_PROJECT: {settings.LANGSMITH_PROJECT}')
    print()

    if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
        print('✅ LangSmith ist für ARES-Evaluation aktiviert!')
        print('📈 Alle Agent-Runs werden automatisch getrackt')
        print('🔍 Evaluation-Sessions werden in LangSmith sichtbar')
        print()
        print('💡 VORTEILE:')
        print('   🎯 Detaillierte Trace-Analyse der Agent-Durchläufe')
        print('   📊 Performance-Metriken für jeden Evaluation-Run')
        print('   🔍 Debugging von Agent-Entscheidungen')
        print('   📈 Langzeit-Performance-Tracking')
        print()
        print('🎯 ARES-EVALUATION MIT LANGSMITH:')
        print('   - Jeder Testfall wird als separater Run getrackt')
        print('   - Agent-Reasoning wird vollständig aufgezeichnet')
        print('   - Tool-Aufrufe (RAG, etc.) werden detailliert geloggt')
        print('   - Performance-Metriken werden automatisch erfasst')
    else:
        print('❌ LangSmith ist nicht vollständig konfiguriert')
        print()
        print('🔧 ZUM AKTIVIEREN:')
        print('   1. Setze LANGSMITH_TRACING=true in .env')
        print('   2. Setze gültigen LANGSMITH_API_KEY in .env')
        print('   3. Optional: Setze LANGSMITH_PROJECT in .env')
        print()
        print('📋 EMPFOHLENE .env EINTRÄGE:')
        print('   LANGSMITH_TRACING=true')
        print('   LANGSMITH_API_KEY=lsv2_pt_....')
        print('   LANGSMITH_PROJECT=ares-evaluation')

if __name__ == "__main__":
    main()