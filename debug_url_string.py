#!/usr/bin/env python3
"""
🔧 DEBUG: URL String Analysis
=============================

Analysiere die problematische PDF-URL genauer.
"""

target_url = "https://wiso.uni-koeln.de/sites/fakultaet/dokumente/studium/master/brochure-Master-Information_Systems.pdf"

print("🔍 URL STRING ANALYSIS")
print("=" * 50)
print(f"URL: {repr(target_url)}")
print(f"Length: {len(target_url)}")
print()

print("📊 SUFFIX ANALYSIS:")
print(f"   Original URL: {target_url}")
print(f"   lower(): {target_url.lower()}")
print(f"   endswith('.pdf'): {target_url.lower().endswith('.pdf')}")
print(f"   endswith('pdf'): {target_url.lower().endswith('pdf')}")
print()

print("🔍 CHARACTER ANALYSIS (last 10 chars):")
url_lower = target_url.lower()
for i, char in enumerate(url_lower[-10:], start=len(url_lower)-10):
    print(f"   [{i:2}]: '{char}' ({ord(char):3}) {char.encode('utf-8')}")

print()
print("📋 BYTE REPRESENTATION (last 10 bytes):")
url_bytes = url_lower.encode('utf-8')
for i, byte in enumerate(url_bytes[-10:], start=len(url_bytes)-10):
    print(f"   [{i:2}]: {byte:3} (0x{byte:02x}) '{chr(byte) if 32 <= byte <= 126 else '?'}'")

print()
print("🧪 MANUAL TEST:")
expected_suffix = '.pdf'
actual_suffix = url_lower[-4:]
print(f"   Expected suffix: {repr(expected_suffix)}")
print(f"   Actual suffix: {repr(actual_suffix)}")
print(f"   Match: {actual_suffix == expected_suffix}")

print()
print("🔍 EXTENDED ANALYSIS:")
print(f"   URL ends with 'pdf': {url_lower.endswith('pdf')}")
print(f"   URL ends with '.pdf': {url_lower.endswith('.pdf')}")
print(f"   URL contains '.pdf': '.pdf' in url_lower")
print(f"   Last 5 chars: {repr(url_lower[-5:])}")