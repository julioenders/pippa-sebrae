"""Fetch BCB SGS series and write pippa-credito-fomento/data.json."""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

SERIES = [432, 433, 13522, 4390, 20542, 20543, 20544, 21082, 21083, 20714, 20715, 25433, 25434, 20631]
ULTIMOS = 24
TIMEOUT = 15
RETRIES = 2
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")


def fetch_serie(serie_id: int) -> list:
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados/ultimos/{ULTIMOS}?formato=json"
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "PIPPA-Credito/1.0 (+https://github.com/julioenders/pippa-sebrae)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                ct = resp.headers.get("Content-Type", "")
                if "json" not in ct:
                    raise ValueError(f"Expected JSON, got {ct}")
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < RETRIES:
                time.sleep(2 ** attempt)
                continue
            print(f"  FAIL serie {serie_id}: {e}", file=sys.stderr)
            return []


def main():
    series_data = {}
    ok = 0
    for sid in SERIES:
        print(f"Fetching serie {sid}...", end=" ", flush=True)
        data = fetch_serie(sid)
        series_data[str(sid)] = data
        if data:
            ok += 1
            print(f"OK ({len(data)} registros)")
        else:
            print("EMPTY")

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "series": series_data,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n{ok}/{len(SERIES)} series fetched -> {OUTPUT}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
