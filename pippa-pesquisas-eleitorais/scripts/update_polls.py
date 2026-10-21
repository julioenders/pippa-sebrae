"""
Atualiza o dashboard PIPPA Pesquisas Eleitorais com dados da ElectioLab API.

Modo padrão: mantém pesquisas de 1º turno embarcadas e busca apenas 2º turno.
Com --full: rebusca tudo (lento, ~10min por rate limits da API).

Uso:
    python scripts/update_polls.py          # só 2º turno (rápido)
    python scripts/update_polls.py --full   # tudo
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from math import sqrt, exp, log

ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT / "index.html"
BASE = "https://electiolab.com/api/v1"
CARGOS = ("presidente", "governador", "senador")
BRT = timezone(timedelta(hours=-3))

METHODOLOGY_WEIGHTS = {"presencial": 1.0, "telefonica": 0.9, "mista": 0.85, "online": 0.8}
RECENCY_HALF_LIFE = 14

CANDIDATE_COLORS = {
    "Lula": "#e0565d", "Tarcísio": "#2a4fda", "Caiado": "#f39d72",
    "Flávio Bolsonaro": "#1e3fb8", "Zema": "#be64e3", "Marçal": "#65b7fb",
    "Simone Tebet": "#61b466", "Marina Silva": "#22c55e", "Tabata Amaral": "#ffc542",
    "Haddad": "#e0565d", "Eduardo Paes": "#4f8cff",
}


def api_get(path, retries=5):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(BASE + path)
            req.add_header("User-Agent", "PIPPA-Sebrae/1.0")
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.loads(r.read())
            time.sleep(3)
            return result
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"  Rate limit, aguardando {wait}s...", flush=True)
                time.sleep(wait)
            elif attempt == retries - 1:
                raise
            else:
                print(f"  Retry {attempt+1}: {e}", flush=True)
                time.sleep(5)
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  Retry {attempt+1}: {e}", flush=True)
            time.sleep(5)


def fetch_all_polls(election_id):
    all_polls = []
    offset = 0
    while True:
        data = api_get(f"/polls?election_id={election_id}&limit=100&offset={offset}&format=json")
        if data is None:
            break
        items = data.get("data", [])
        all_polls.extend(items)
        if len(items) < 100:
            break
        offset += 100
    return all_polls


def normalize_method(m):
    if not m:
        return "mista"
    m = m.lower().strip()
    if "presencial" in m:
        return "presencial"
    if "telef" in m:
        return "telefonica"
    if "online" in m or "internet" in m or "digital" in m:
        return "online"
    return "mista"


def compute_weighted_averages(polls, cargo="presidente", state=None):
    filtered = [p for p in polls if p["position"] == cargo]
    if state:
        filtered = [p for p in filtered if p.get("state") == state]
    if not filtered:
        return []
    today = datetime.now(BRT).date()
    candidates = {}
    for poll in filtered:
        try:
            dt = datetime.strptime(poll["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        days_old = (today - dt).days
        recency_w = exp(-log(2) * days_old / RECENCY_HALF_LIFE)
        sample_w = sqrt(poll.get("sample", 0) or 100)
        method_w = METHODOLOGY_WEIGHTS.get(poll.get("method", "mista"), 0.85)
        weight = recency_w * sample_w * method_w
        for c in poll.get("candidates", []):
            name = c["name"]
            if name not in candidates:
                candidates[name] = {"name": name, "party": c.get("party", ""), "values": [], "weights": [], "samples": []}
            candidates[name]["values"].append(c["pct"])
            candidates[name]["weights"].append(weight)
            candidates[name]["samples"].append(poll.get("sample", 0))
    results = []
    for name, info in candidates.items():
        total_w = sum(info["weights"])
        if total_w == 0:
            continue
        avg = sum(v * w for v, w in zip(info["values"], info["weights"])) / total_w
        n = len(info["values"])
        if n >= 2:
            variance = sum(w * (v - avg) ** 2 for v, w in zip(info["values"], info["weights"])) / total_w
            se = sqrt(variance) / sqrt(n)
            ci_low, ci_high = round(avg - 1.96 * se, 1), round(avg + 1.96 * se, 1)
        else:
            ci_low, ci_high = round(avg - 2, 1), round(avg + 2, 1)
        color = CANDIDATE_COLORS.get(name, "#8b9dc3")
        results.append({"n": name, "p": info["party"], "cl": color, "avg": round(avg, 1),
                        "lo": max(0, ci_low), "hi": min(100, ci_high), "cnt": n, "smp": sum(info["samples"])})
    results.sort(key=lambda x: -x["avg"])
    return results


def extract_existing(html, varname):
    m = re.search(r"const\s+" + re.escape(varname) + r"\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            print(f"  AVISO: falha ao parsear {varname} existente")
    return []


def replace_js_const(html, varname, value):
    pattern = re.compile(r"(const\s+" + re.escape(varname) + r"\s*=\s*)\[.*?\];", re.DOTALL)
    new_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    new_html, count = pattern.subn(r"\g<1>" + new_json.replace("\\", "\\\\") + ";", html)
    if count == 0:
        print(f"  AVISO: {varname} não encontrado no HTML")
    return new_html


def main():
    full_mode = "--full" in sys.argv
    now = datetime.now(BRT)
    print(f"[{now:%Y-%m-%d %H:%M}] Atualizando pesquisas eleitorais ({'completo' if full_mode else 'só 2º turno'})...")

    html = HTML_FILE.read_text(encoding="utf-8")
    existing_raw = extract_existing(html, "RAW_POLLS")
    existing_sr = extract_existing(html, "SECOND_ROUND")
    print(f"  Dados embarcados: {len(existing_raw)} pesquisas 1T, {len(existing_sr)} cenários 2T")

    print("  Buscando eleições ativas na API...")
    elections_data = api_get("/elections")
    elections = elections_data["data"]
    active = [e for e in elections if e["year"] == 2026 and e["is_active"] and e["type"] in CARGOS]
    round1 = [e for e in active if e.get("round", 1) == 1]
    round2 = [e for e in active if e["round"] == 2]
    print(f"  {len(round1)} eleições 1T, {len(round2)} eleições 2T")

    # ── 1T ────────────────────────────────────────────────────────────
    all_raw = existing_raw
    if full_mode:
        all_raw = []
        for e in round1:
            print(f"  1T: {e['name']}...", end=" ", flush=True)
            polls = fetch_all_polls(e["id"])
            print(f"{len(polls)} pesquisas")
            for p in polls:
                all_raw.append({
                    "id": p.get("id", ""),
                    "src": (p.get("institute") or {}).get("name", "Desconhecido"),
                    "dt": p.get("publication_date", ""),
                    "pos": e["type"],
                    "uf": e.get("state") or "BR",
                    "n": p.get("sample_size") or 0,
                    "me": p.get("margin_of_error") or 0,
                    "mt": normalize_method(p.get("methodology")),
                    "c": [
                        {"n": r.get("candidate", {}).get("name", ""), "p": r.get("candidate", {}).get("party", ""), "v": r.get("percentage", 0)}
                        for r in p.get("results", [])
                    ],
                })
    else:
        print(f"  Mantendo {len(all_raw)} pesquisas 1T existentes")

    # ── 2T ────────────────────────────────────────────────────────────
    sr_keys = set(f"{p.get('source','')}|{p.get('date','')}|{p.get('position','')}" for p in existing_sr)
    all_sr = list(existing_sr)
    new_r2 = 0

    for e in round2:
        print(f"  2T: {e['name']}...", end=" ", flush=True)
        polls = fetch_all_polls(e["id"])
        added = 0
        for p in polls:
            results = p.get("results", [])
            if len(results) < 2:
                continue
            inst = (p.get("institute") or {}).get("name", "Desconhecido")
            dt = p.get("publication_date", "")
            key = f"{inst}|{dt}|{e['type']}"
            if key in sr_keys:
                continue
            sr_keys.add(key)
            all_sr.append({
                "source": inst, "date": dt,
                "sample": p.get("sample_size") or 0,
                "margin": p.get("margin_of_error"),
                "position": e["type"], "state": e.get("state"),
                "candidates": [
                    {"name": r.get("candidate", {}).get("name", ""), "party": r.get("candidate", {}).get("party", ""), "pct": r.get("percentage", 0)}
                    for r in results
                ],
            })
            added += 1
            new_r2 += 1
        print(f"{len(polls)} pesquisas ({added} novas)")

    all_raw.sort(key=lambda x: x.get("dt", ""), reverse=True)
    all_sr.sort(key=lambda x: x.get("date", ""), reverse=True)

    # ── Médias ponderadas ─────────────────────────────────────────────
    polls_for_avg = [{
        "position": p.get("pos", ""), "state": p.get("uf", "BR"),
        "date": p.get("dt", ""), "sample": p.get("n", 0),
        "method": p.get("mt", "mista"),
        "candidates": [{"name": c.get("n", ""), "pct": c.get("v", 0), "party": c.get("p", "")} for c in p.get("c", [])],
    } for p in all_raw]

    pres_avgs = compute_weighted_averages(polls_for_avg, "presidente")
    state_avgs = []
    for pos in ("governador", "senador"):
        states = set(p.get("uf", "") for p in all_raw if p.get("pos") == pos)
        for uf in sorted(states):
            avgs = compute_weighted_averages(polls_for_avg, pos, uf)
            for a in avgs:
                a["pos"] = pos
                a["uf"] = uf
                state_avgs.append(a)

    n_polls = len(all_raw)
    n_ufs = len(set(p.get("uf", "") for p in all_raw))
    print(f"\n  Resumo: {n_polls} pesquisas 1T, {len(all_sr)} cenários 2T ({new_r2} novos)")

    # ── Reescrever HTML ───────────────────────────────────────────────
    print("  Atualizando HTML...")
    html = replace_js_const(html, "RAW_POLLS", all_raw)
    html = replace_js_const(html, "PRES_AVGS", pres_avgs)
    html = replace_js_const(html, "STATE_AVGS", state_avgs)
    html = replace_js_const(html, "SECOND_ROUND", all_sr)

    data_info_pattern = re.compile(r'(id="dataInfo">).*?(</span>)')
    html = data_info_pattern.sub(
        rf"\g<1>{n_polls} pesquisas + {len(all_sr)} cenários 2T — atualizado {now:%d/%m/%Y %H:%M}\g<2>",
        html,
    )

    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"  Salvo: {HTML_FILE}")
    print(f"[{now:%Y-%m-%d %H:%M}] Concluído: {n_polls} pesquisas 1T + {len(all_sr)} cenários 2T ({new_r2} novos)")


if __name__ == "__main__":
    main()
