#!/usr/bin/env python3
"""
Pipeline Pause Control System
============================

Ermöglicht das intelligente Pausieren und Fortsetzen der Pipeline
bei Rate-Limiting-Problemen ohne Datenverlust.
"""

import time
import sys
from pathlib import Path
import argparse

def create_pause_flag():
    """Erstelle Pause-Flag für laufende Pipeline."""
    flag_file = Path("data/pipeline_pause.flag")
    flag_file.parent.mkdir(exist_ok=True)
    
    with open(flag_file, "w") as f:
        f.write(f"Pipeline paused at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Reason: HTTP 429 Rate Limiting\n")
        f.write("Action: Waiting for rate limit reset\n")
    
    print("🛑 PIPELINE PAUSE ACTIVATED")
    print(f"   Flag created: {flag_file}")
    print("   Pipeline will pause after current batch")
    print("   Use 'resume' command to continue")

def remove_pause_flag():
    """Entferne Pause-Flag zum Fortsetzen."""
    flag_file = Path("data/pipeline_pause.flag")
    
    if flag_file.exists():
        flag_file.unlink()
        print("▶️ PIPELINE RESUMED")
        print("   Pause flag removed")
        print("   Pipeline will continue processing")
    else:
        print("ℹ️ No pause flag found - pipeline not paused")

def check_pause_status():
    """Prüfe aktuellen Pause-Status."""
    flag_file = Path("data/pipeline_pause.flag")
    
    if flag_file.exists():
        print("⏸️ PIPELINE IS CURRENTLY PAUSED")
        with open(flag_file, "r") as f:
            content = f.read()
        print(f"   Details:\n{content}")
        
        # Berechne Pause-Dauer
        stats = flag_file.stat()
        pause_duration = time.time() - stats.st_mtime
        print(f"   Paused for: {pause_duration/60:.1f} minutes")
    else:
        print("▶️ PIPELINE IS RUNNING")
        print("   No pause flag detected")

def intelligent_wait(minutes: int):
    """Warte intelligent auf Rate-Limit-Reset."""
    print(f"⏱️ INTELLIGENT WAIT: {minutes} minutes")
    print("   Waiting for rate limit to reset...")
    print("   Pipeline will auto-resume after wait")
    
    # Pause mit Countdown
    total_seconds = minutes * 60
    for remaining in range(total_seconds, 0, -30):
        mins, secs = divmod(remaining, 60)
        print(f"   Time remaining: {mins:02d}:{secs:02d} - Rate limit cooling down...")
        time.sleep(min(30, remaining))
    
    # Auto-resume
    remove_pause_flag()
    print("✅ RATE LIMIT COOLDOWN COMPLETE")

def main():
    parser = argparse.ArgumentParser(description="Pipeline Pause Control")
    parser.add_argument("action", choices=["pause", "resume", "status", "wait"],
                       help="Action to perform")
    parser.add_argument("--minutes", "-m", type=int, default=15,
                       help="Minutes to wait for rate limit reset (default: 15)")
    
    args = parser.parse_args()
    
    if args.action == "pause":
        create_pause_flag()
    elif args.action == "resume":
        remove_pause_flag()
    elif args.action == "status":
        check_pause_status()
    elif args.action == "wait":
        create_pause_flag()
        intelligent_wait(args.minutes)

if __name__ == "__main__":
    main()