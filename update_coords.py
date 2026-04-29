#!/usr/bin/env python3
"""
Fetches precise Google Maps coordinates for all Singapore MRT/LRT stations
and writes an updated version of sg-mrt-map.html.

Usage:
    python update_coords.py YOUR_GOOGLE_API_KEY

The script reads sg-mrt-map.html, looks up each station via the Places API,
and writes sg-mrt-map-updated.html with the corrected coordinates.
Both files should be in the same folder as this script.
"""

import sys
import re
import json
import time
import urllib.request
import urllib.parse

# ── Config ────────────────────────────────────────────────────────────────────

HTML_IN  = "sg-mrt-map.html"
HTML_OUT = "sg-mrt-map-updated.html"
DELAY    = 0.15   # seconds between API calls (be polite to Google)

# LRT line codes — used to build a better search query
LRT_LINES = {"BP", "SL", "PL"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_stations(html):
    """
    Pull station entries out of the HTML file using regex.
    Matches lines like: {n:"Jurong East", l:["NS","EW"], a:1.3330, o:103.7425},
    Returns a list of dicts with keys: name, lines, lat, lng
    """
    pattern = re.compile(
        r'\{n:"([^"]+)",\s*l:\[([^\]]+)\],\s*a:([\d.]+),\s*o:([\d.]+)\}'
    )
    stations = []
    for m in pattern.finditer(html):
        name      = m.group(1)
        lines_raw = m.group(2)                           # e.g. "NS","EW"
        lat       = float(m.group(3))
        lng       = float(m.group(4))
        lines     = re.findall(r'"([A-Z]+)"', lines_raw) # ['NS', 'EW']
        stations.append({"name": name, "lines": lines, "lat": lat, "lng": lng})
    return stations


def fetch_coords(name, lines, api_key):
    """
    Query Google Places Text Search for a station.
    Returns (lat, lng) on success, or (None, None) on failure.
    """
    is_lrt   = all(l in LRT_LINES for l in lines)
    transit  = "LRT" if is_lrt else "MRT"
    query    = f"{name} {transit} Station Singapore"

    params = urllib.parse.urlencode({
        "query": query,
        "key":   api_key,
    })
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())

        status = data.get("status")
        if status == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return round(loc["lat"], 6), round(loc["lng"], 6)
        else:
            print(f"    ! API status: {status}")
            return None, None

    except Exception as e:
        print(f"    ! Request error: {e}")
        return None, None


def build_js_array(stations):
    """Rebuild the const S = [...] block from the station list."""
    lines_out = ["const S = ["]
    for s in stations:
        lines_str = ",".join(f'"{l}"' for l in s["lines"])
        lines_out.append(
            f'  {{n:"{s["name"]}", l:[{lines_str}], a:{s["lat"]}, o:{s["lng"]}}},'
        )
    lines_out.append("];")
    return "\n".join(lines_out)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python update_coords.py YOUR_GOOGLE_API_KEY")
        sys.exit(1)

    api_key = sys.argv[1].strip()

    # Read the HTML file
    try:
        with open(HTML_IN, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"Error: '{HTML_IN}' not found. Make sure it's in the same folder as this script.")
        sys.exit(1)

    # Parse current stations out of the HTML
    stations = parse_stations(html)
    if not stations:
        print("Error: couldn't find any station data in the HTML file.")
        sys.exit(1)

    print(f"Found {len(stations)} stations. Starting coordinate lookup...\n")

    updated     = 0
    failed      = []

    for i, s in enumerate(stations, 1):
        print(f"[{i:3}/{len(stations)}] {s['name']}...")
        lat, lng = fetch_coords(s["name"], s["lines"], api_key)

        if lat is not None:
            s["lat"] = lat
            s["lng"] = lng
            print(f"          → {lat}, {lng}")
            updated += 1
        else:
            # Keep the original coordinate from the HTML as fallback
            print(f"          → keeping original ({s['lat']}, {s['lng']})")
            failed.append(s["name"])

        time.sleep(DELAY)

    # Build the new JS array
    new_array = build_js_array(stations)

    # Replace the old array in the HTML
    # The block starts with "const S = [" and ends with "];"
    new_html = re.sub(
        r'const S = \[.*?\];',
        new_array,
        html,
        count=1,
        flags=re.DOTALL
    )

    if new_html == html:
        print("\nWarning: couldn't find 'const S = [...]' in the HTML to replace.")
        print("Writing the new array to 'stations_updated.js' instead.")
        with open("stations_updated.js", "w", encoding="utf-8") as f:
            f.write(new_array)
    else:
        with open(HTML_OUT, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"\nDone! Updated {updated}/{len(stations)} stations.")
        if failed:
            print(f"Kept original coords for: {', '.join(failed)}")
        print(f"\nOutput written to: {HTML_OUT}")

if __name__ == "__main__":
    main()
