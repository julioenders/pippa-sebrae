"""
Coletor de dados PNCP para o Monitor de Contratacoes Publicas (5 anos).

Consulta a API do PNCP mes a mes, para cada UF e modalidade,
agregando valores estimados, homologados e contagens.

Uso:
    python scripts/coletar_pncp_monitor.py

Gera o arquivo scripts/pncp_monitor_cache.js com os dados prontos
para ser colado no index.html.

Tempo estimado: ~2 horas (com rate limiting de 3s entre requests).
O script salva progresso incremental — pode ser interrompido e retomado.
Em caso de erro 429 (rate limit), aguarda 60s automaticamente.
"""

import json
import os
import sys
import time
from datetime import datetime, date

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

PNCP_BASE = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
MODALIDADES = [6, 8, 5, 9, 12]
UFS = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
    "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
]
UF_NOMES = {
    "AC":"Acre","AL":"Alagoas","AM":"Amazonas","AP":"Amapa","BA":"Bahia",
    "CE":"Ceara","DF":"Distrito Federal","ES":"Espirito Santo","GO":"Goias",
    "MA":"Maranhao","MG":"Minas Gerais","MS":"Mato Grosso do Sul",
    "MT":"Mato Grosso","PA":"Para","PB":"Paraiba","PE":"Pernambuco",
    "PI":"Piaui","PR":"Parana","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte",
    "RO":"Rondonia","RR":"Roraima","RS":"Rio Grande do Sul",
    "SC":"Santa Catarina","SE":"Sergipe","SP":"Sao Paulo","TO":"Tocantins"
}
UF_REGIAO = {
    "AC":"NO","AL":"NE","AM":"NO","AP":"NO","BA":"NE","CE":"NE","DF":"CO",
    "ES":"SE","GO":"CO","MA":"NE","MG":"SE","MS":"CO","MT":"CO","PA":"NO",
    "PB":"NE","PE":"NE","PI":"NE","PR":"SU","RJ":"SE","RN":"NE","RO":"NO",
    "RR":"NO","RS":"SU","SC":"SU","SE":"NE","SP":"SE","TO":"NO"
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "pncp_progress.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "pncp_monitor_cache.js")

DELAY = 3
MAX_PAGES = 100
PAGE_SIZE = 50


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def fetch_month(uf, year, month, modalidade):
    di = f"{year}{month:02d}01"
    if month == 12:
        df = f"{year}1231"
    else:
        next_month_first = date(year, month + 1, 1)
        last_day = date(next_month_first.year, next_month_first.month, 1)
        from calendar import monthrange
        _, last = monthrange(year, month)
        df = f"{year}{month:02d}{last:02d}"

    total_est = 0
    total_hom = 0
    total_qtd = 0
    municipios = {}
    page = 1

    while page <= MAX_PAGES:
        params = {
            "dataInicial": di,
            "dataFinal": df,
            "uf": uf,
            "codigoModalidadeContratacao": modalidade,
            "pagina": page,
            "tamanhoPagina": PAGE_SIZE,
        }
        try:
            r = requests.get(PNCP_BASE, params=params, timeout=30)
            if r.status_code == 429:
                print(f"  Rate limit — aguardando 60s...")
                time.sleep(60)
                continue
            data = r.json()
            items = data if isinstance(data, list) else (data.get("data") or [])
            if not items:
                break
            for item in items:
                est = item.get("valorTotalEstimado") or 0
                hom = item.get("valorTotalHomologado") or 0
                total_est += est
                total_hom += hom
                total_qtd += 1
                mun_nome = (item.get("unidadeOrgao") or {}).get("municipioNome", "")
                mun_cod = (item.get("unidadeOrgao") or {}).get("codigoIbge", "")
                if mun_nome and mun_cod:
                    if mun_cod not in municipios:
                        municipios[mun_cod] = {"nome": mun_nome, "est": 0, "hom": 0, "qtd": 0}
                    municipios[mun_cod]["est"] += est
                    municipios[mun_cod]["hom"] += hom
                    municipios[mun_cod]["qtd"] += 1
            if len(items) < PAGE_SIZE:
                break
            page += 1
            time.sleep(DELAY)
        except Exception as e:
            print(f"  ERRO {uf}/{year}/{month:02d}/mod{modalidade} p{page}: {e}")
            time.sleep(3)
            break

    return total_est, total_hom, total_qtd, municipios


def collect_all():
    progress = load_progress()
    current_year = datetime.now().year
    years = list(range(current_year - 4, current_year + 1))
    current_month = datetime.now().month

    total_queries = len(UFS) * len(years) * 12 * len(MODALIDADES)
    done = 0

    results = progress.get("results", {})
    mun_results = progress.get("mun_results", {})

    for year in years:
        max_month = current_month if year == current_year else 12
        for month in range(1, max_month + 1):
            for uf in UFS:
                key = f"{uf}_{year}_{month:02d}"
                if key in results and all(f"{key}_m{m}" in results[key] for m in MODALIDADES):
                    done += len(MODALIDADES)
                    continue

                if key not in results:
                    results[key] = {}

                for mod in MODALIDADES:
                    mod_key = f"{key}_m{mod}"
                    if mod_key in results[key]:
                        done += 1
                        continue

                    est, hom, qtd, muns = fetch_month(uf, year, month, mod)
                    results[key][mod_key] = {"est": est, "hom": hom, "qtd": qtd}

                    for mun_cod, mun_data in muns.items():
                        mun_key = f"{uf}_{year}_{mun_cod}"
                        if mun_key not in mun_results:
                            mun_results[mun_key] = {"nome": mun_data["nome"], "uf": uf, "ano": year, "cod": mun_cod, "est": 0, "hom": 0, "qtd": 0}
                        mun_results[mun_key]["est"] += mun_data["est"]
                        mun_results[mun_key]["hom"] += mun_data["hom"]
                        mun_results[mun_key]["qtd"] += mun_data["qtd"]

                    done += 1
                    pct = done / total_queries * 100
                    print(f"  [{pct:5.1f}%] {uf} {year}/{month:02d} mod{mod}: {qtd} contratacoes | Est={est:,.0f} | Hom={hom:,.0f}")
                    time.sleep(DELAY)

                progress["results"] = results
                progress["mun_results"] = mun_results
                save_progress(progress)

    return results, mun_results


def aggregate(results, mun_results):
    uf_year = {}
    for key, mods in results.items():
        parts = key.split("_")
        if len(parts) < 3:
            continue
        uf, year = parts[0], int(parts[1])
        uy_key = f"{uf}_{year}"
        if uy_key not in uf_year:
            uf_year[uy_key] = {"uf": uf, "ano": year, "nome": UF_NOMES.get(uf, uf), "regiao": UF_REGIAO.get(uf, ""), "estimado": 0, "homologado": 0, "qtd": 0}
        for mod_data in mods.values():
            if isinstance(mod_data, dict):
                uf_year[uy_key]["estimado"] += mod_data.get("est", 0)
                uf_year[uy_key]["homologado"] += mod_data.get("hom", 0)
                uf_year[uy_key]["qtd"] += mod_data.get("qtd", 0)

    cache = sorted(uf_year.values(), key=lambda x: (x["ano"], x["uf"]))

    mun_cache = []
    for mun_data in mun_results.values():
        if mun_data["qtd"] > 0:
            mun_cache.append({
                "uf": mun_data["uf"],
                "ano": mun_data["ano"],
                "cod": mun_data["cod"],
                "nome": mun_data["nome"],
                "estimado": round(mun_data["est"], 2),
                "homologado": round(mun_data["hom"], 2),
                "qtd": mun_data["qtd"],
            })
    mun_cache.sort(key=lambda x: (x["ano"], x["uf"], x["nome"]))

    return cache, mun_cache


def write_js(cache, mun_cache):
    today = datetime.now().strftime("%d/%m/%Y")

    lines = [f"const PNCP_MONITOR_CACHE = {json.dumps(cache, ensure_ascii=False)};"]
    lines.append(f"const PNCP_MONITOR_CACHE_DATE = '{today}';")
    lines.append(f"const PNCP_MONITOR_MUN_CACHE = {json.dumps(mun_cache, ensure_ascii=False)};")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nArquivo gerado: {OUTPUT_FILE}")
    print(f"  {len(cache)} registros UF/ano")
    print(f"  {len(mun_cache)} registros municipio/ano")
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"  Tamanho: {size_kb:.1f} KB")


def main():
    print("=" * 60)
    print("PNCP Monitor — Coleta de Dados de Contratacoes Publicas")
    print("=" * 60)
    print(f"API: {PNCP_BASE}")
    print(f"UFs: {len(UFS)} | Modalidades: {len(MODALIDADES)}")
    print(f"Delay entre requests: {DELAY}s")
    print()

    results, mun_results = collect_all()
    cache, mun_cache = aggregate(results, mun_results)
    write_js(cache, mun_cache)
    print("\nPronto! Cole o conteudo do arquivo JS no index.html.")


if __name__ == "__main__":
    main()
