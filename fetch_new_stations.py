#!/usr/bin/env python3
"""
Fetches Google Maps coordinates for new stations only and patches sg-mrt-map-v3.html.

Usage: python fetch_new_stations.py YOUR_GOOGLE_API_KEY
"""

import sys
import json
import urllib.request
import urllib.parse

HTML_IN  = "sg-mrt-map-v3.html"
HTML_OUT = "sg-mrt-map-v4.html"

NEW_STATIONS = [
    {"name": "Punggol Coast", "type": "MRT"},
    {"name": "Hume",          "type": "MRT"},
]

def fetch_coords(name, transit_type, api_key):
    query  = f"{name} {transit_type} Station Singapore"
    params = urllib.parse.urlencode({"query": query, "key": api_key})
    url    = f"https://maps.googleapis.com/maps/api/place/textsearch/json?{params}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    if data.get("status") == "OK" and data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return round(loc["lat"], 6), round(loc["lng"], 6)
    print(f"  ! No result for '{name}' (status: {data.get('status')})")
    return None, None

def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_new_stations.py YOUR_GOOGLE_API_KEY")
        sys.exit(1)

    api_key = sys.argv[1].strip()

    with open(HTML_IN, "r", encoding="utf-8") as f:
        html = f.read()

    for s in NEW_STATIONS:
        name = s["name"]
        print(f"Looking up: {name}...")
        lat, lng = fetch_coords(name, s["type"], api_key)
        if lat is None:
            print(f"  Skipping — keeping existing coordinates.\n")
            continue
        print(f"  → {lat}, {lng}")
        # Replace the placeholder coords for this station in-place
        # Matches the exact line format written by the previous scripts
        old = f'{{n:"{name}"'
        idx = html.find(old)
        if idx == -1:
            print(f"  ! Could not find '{name}' in HTML. Skipping.\n")
            continue
        line_end = html.index("}", idx) + 1
        original_entry = html[idx:line_end]
        # Rebuild with new coords, preserving the lines array
        import re
        m = re.search(r'l:\[([^\]]+)\]', original_entry)
        lines_str = m.group(1) if m else '""'
        new_entry = f'{{n:"{name}", l:[{lines_str}], a:{lat}, o:{lng}}}'
        html = html[:idx] + new_entry + html[line_end:]
        print(f"  Patched.\n")

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Done. Output written to {HTML_OUT}")

if __name__ == "__main__":
    main()
