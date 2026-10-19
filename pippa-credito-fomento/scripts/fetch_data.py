"""Fetch BCB series via IPEADATA mirror and write pippa-credito-fomento/data.json.

IPEADATA mirrors BCB SGS data with CORS support and no WAF blocking.
Output format matches BCB SGS JSON: [{data: "DD/MM/YYYY", valor: "X,XX"}, ...]
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

IPEADATA_MAP = {
    432:   {"ipea": "BM366_TJOVER366", "nome": "Selic Meta",              "ultimos": 500},
    433:   {"ipea": "BM12_TJOVER12",   "nome": "Selic Over (efetiva)"},
    13522: {"ipea": "PRECOS12_IPCAGA12","nome": "IPCA Acumulado 12 meses"},
    4390:  {"ipea": "BM12_TJCDI12",    "nome": "CDI Over"},
    20542: {"ipea": "BM12_CSPJ12",     "nome": "Saldo Credito PJ Total"},
    20543: {"ipea": "BM12_CRLSPJ12",   "nome": "Saldo Credito PJ Rec. Livres"},
    20544: {"ipea": "BM12_CRDSPJ12",   "nome": "Saldo Credito PJ Rec. Direcionados"},
    21082: {"ipea": "BM12_CINPJ12",    "nome": "Inadimplencia PJ Total"},
    21083: {"ipea": "BM12_CRLINPJ12",  "nome": "Inadimplencia PJ Rec. Livres"},
    20714: {"ipea": "BM12_CTJPJ12",    "nome": "Taxa Media Juros PJ Total"},
    20715: {"ipea": "BM12_CRLTJPJ12",  "nome": "Taxa Media Juros PJ Rec. Livres"},
    25433: {"ipea": "BM12_CCAPJ12",    "nome": "Concessoes Credito PJ Total"},
    25434: {"ipea": "BM12_CRLCAPJ12",  "nome": "Concessoes Credito PJ Rec. Livres"},
    20631: {"ipea": "BM12_CSDPJ12",    "nome": "Spread Medio PJ Total"},
}

ULTIMOS_DEFAULT = 24
TIMEOUT = 20
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")


def fetch_ipeadata(ipea_code: str, ultimos: int) -> list:
    url = (
        f"http://www.ipeadata.gov.br/api/odata4/"
        f"ValoresSerie(SERCODIGO='{ipea_code}')"
    )
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "PIPPA-Credito/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            vals = data.get("value", [])
            vals = [v for v in vals if v.get("VALVALOR") is not None]
            vals = vals[-ultimos:]
            result = []
            for v in vals:
                dt = v["VALDATA"][:10]
                parts = dt.split("-")
                data_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
                raw = v["VALVALOR"]
                valor = str(raw).replace(".", ",") if isinstance(raw, float) else str(raw)
                result.append({"data": data_fmt, "valor": valor})
            return result
    except Exception as e:
        print(f"  IPEADATA error: {e}", file=sys.stderr)
        return []


def fetch_bcb_direct(serie_id: int, ultimos: int) -> list:
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados/ultimos/{ultimos}?formato=json"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "PIPPA-Credito/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "json" not in ct:
                return []
            return json.loads(resp.read().decode())
    except Exception:
        return []


def main():
    series_data = {}
    ok = 0

    for sgs_id, info in IPEADATA_MAP.items():
        ultimos = info.get("ultimos", ULTIMOS_DEFAULT)
        nome = info["nome"]
        ipea = info["ipea"]

        print(f"[{sgs_id}] {nome} (IPEA: {ipea})...", end=" ", flush=True)

        data = fetch_ipeadata(ipea, ultimos)

        if not data:
            print("IPEA empty, trying BCB direct...", end=" ", flush=True)
            data = fetch_bcb_direct(sgs_id, ultimos)

        series_data[str(sgs_id)] = data
        if data:
            ok += 1
            last = data[-1]
            print(f"OK ({len(data)} reg, ultimo: {last['data']} = {last['valor']})")
        else:
            print("EMPTY")

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fonte": "IPEADATA (espelho BCB SGS)",
        "series": series_data,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n{ok}/{len(IPEADATA_MAP)} series fetched -> {OUTPUT}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
