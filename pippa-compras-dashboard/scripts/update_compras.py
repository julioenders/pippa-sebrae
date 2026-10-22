"""
Atualiza os dados do PIPPA Compras Públicas no dashboard HTML.

1. Monitor PNCP 5 Anos — coleta via API PNCP (contratações por UF/ano)
2. Execução Orçamentária — coleta via API SICONFI/Tesouro Nacional (RREO)
3. PDDE/PNAE — atualiza se existirem JSONs novos em scripts/data/

Uso:
    python scripts/update_compras.py              # atualiza PNCP Monitor + SICONFI
    python scripts/update_compras.py --with-pdde  # + PDDE/PNAE se houver JSONs
    python scripts/update_compras.py --skip-pncp  # só SICONFI (rápido)
    python scripts/update_compras.py --skip-siconfi  # só PNCP
"""

import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone, timedelta
from calendar import monthrange

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
HTML_FILE = os.path.join(ROOT, "index.html")
BRT = timezone(timedelta(hours=-3))

PNCP_BASE = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
MODS = [6, 8, 5, 9, 12]
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
DELAY = 4
errors = 0


def fetch_semester(uf, year, half):
    global errors
    if half == 1:
        di, df = f"{year}0101", f"{year}0630"
    else:
        di = f"{year}0701"
        hoje = date.today()
        if year < hoje.year:
            df = f"{year}1231"
        else:
            df = hoje.strftime("%Y%m%d")

    est_total, hom_total, qtd_total = 0, 0, 0
    for mod in MODS:
        for attempt in range(3):
            try:
                r = requests.get(PNCP_BASE, params={
                    "dataInicial": di, "dataFinal": df, "uf": uf,
                    "codigoModalidadeContratacao": mod,
                    "pagina": 1, "tamanhoPagina": 50
                }, timeout=30)
                if r.status_code == 429:
                    wait = 30 * (attempt + 1)
                    print(f"  429 rate limit, aguardando {wait}s...", flush=True)
                    time.sleep(wait)
                    continue
                if r.status_code != 200:
                    errors += 1
                    break
                data = r.json()
                if isinstance(data, dict):
                    total_reg = data.get("totalRegistros", 0)
                    items = data.get("data", [])
                elif isinstance(data, list):
                    total_reg = len(data)
                    items = data
                else:
                    break

                n = len(items)
                if n == 0:
                    break

                page_est = sum((it.get("valorTotalEstimado") or 0) for it in items)
                page_hom = sum((it.get("valorTotalHomologado") or 0) for it in items)

                if total_reg > n:
                    factor = total_reg / n
                    page_est *= factor
                    page_hom *= factor

                est_total += page_est
                hom_total += page_hom
                qtd_total += total_reg
                break
            except Exception as e:
                errors += 1
                if attempt == 2:
                    print(f"  ERRO {uf} {year} H{half} mod{mod}: {e}", flush=True)
                time.sleep(5)

        time.sleep(DELAY)

    return est_total, hom_total, qtd_total


def collect_pncp_monitor():
    """Coleta dados do Monitor PNCP por UF e ano (últimos 5 anos)."""
    current_year = date.today().year
    years = list(range(current_year - 4, current_year + 1))
    cache = {}
    total_ops = len(UFS) * len(years) * 2
    done = 0
    t0 = time.time()

    print(f"  {len(UFS)} UFs x {len(years)} anos x 2 semestres x {len(MODS)} modalidades")
    print(f"  Total: {total_ops} combinações, delay {DELAY}s")

    for year in years:
        for half in [1, 2]:
            for uf in UFS:
                key = f"{uf}_{year}"
                if key not in cache:
                    cache[key] = {
                        "uf": uf, "ano": year, "nome": UF_NOMES[uf],
                        "regiao": UF_REGIAO[uf], "estimado": 0, "homologado": 0, "qtd": 0
                    }

                est, hom, qtd = fetch_semester(uf, year, half)
                cache[key]["estimado"] += est
                cache[key]["homologado"] += hom
                cache[key]["qtd"] += qtd

                done += 1
                elapsed = time.time() - t0
                eta = (elapsed / done) * (total_ops - done) if done > 0 else 0
                if done % 10 == 0 or done == total_ops:
                    print(f"  [{done/total_ops*100:5.1f}%] {uf} {year} H{half} | ETA: {eta/60:.0f}min | err: {errors}", flush=True)

    result = sorted(cache.values(), key=lambda x: (x["ano"], x["uf"]))
    for row in result:
        row["estimado"] = round(row["estimado"], 2)
        row["homologado"] = round(row["homologado"], 2)

    print(f"  Coletados: {len(result)} registros em {(time.time()-t0)/60:.1f} min | {errors} erros")
    return result


SICONFI_BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
UF_IBGE = {
    "RO":11,"AC":12,"AM":13,"RR":14,"PA":15,"AP":16,"TO":17,
    "MA":21,"PI":22,"CE":23,"RN":24,"PB":25,"PE":26,"AL":27,"SE":28,"BA":29,
    "MG":31,"ES":32,"RJ":33,"SP":35,
    "PR":41,"SC":42,"RS":43,
    "MS":50,"MT":51,"GO":52,"DF":53
}


def find_latest_period(year, ente):
    for p in range(6, 0, -1):
        try:
            r = requests.get(SICONFI_BASE, params={
                "an_exercicio": year, "nr_periodo": p,
                "co_tipo_demonstrativo": "RREO", "id_ente": ente
            }, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("items"):
                    return p
        except Exception:
            pass
        time.sleep(1)
    return None


def collect_siconfi():
    """Coleta dados de execução orçamentária via SICONFI/RREO (Tesouro Nacional)."""
    current_year = date.today().year
    start_year = current_year - 6
    years = list(range(start_year, current_year + 1))
    results = []
    t0 = time.time()

    print(f"  {len(UF_IBGE)} UFs x {len(years)} anos ({start_year}-{current_year})")

    ref_ente = 11
    year_periods = {}
    print("  Detectando períodos disponíveis...", flush=True)
    for year in years:
        p = find_latest_period(year, ref_ente)
        year_periods[year] = p
        print(f"    {year}: período {p}", flush=True)

    total_ops = len(UF_IBGE) * len(years)
    done = 0
    siconfi_errors = 0

    for year in years:
        period = year_periods.get(year)
        if not period:
            print(f"  AVISO: {year} sem dados RREO disponíveis", flush=True)
            done += len(UF_IBGE)
            continue

        for uf, ente in sorted(UF_IBGE.items()):
            done += 1
            try:
                r = requests.get(SICONFI_BASE, params={
                    "an_exercicio": year, "nr_periodo": period,
                    "co_tipo_demonstrativo": "RREO", "id_ente": ente
                }, timeout=30)

                if r.status_code == 429:
                    print(f"  429 rate limit, aguardando 30s...", flush=True)
                    time.sleep(30)
                    r = requests.get(SICONFI_BASE, params={
                        "an_exercicio": year, "nr_periodo": period,
                        "co_tipo_demonstrativo": "RREO", "id_ente": ente
                    }, timeout=30)

                if r.status_code != 200:
                    siconfi_errors += 1
                    continue

                items = r.json().get("items", [])
                emp, liq, pago = 0, 0, 0
                for it in items:
                    if it.get("cod_conta") != "DespesasExcetoIntraOrcamentarias":
                        continue
                    col = it.get("coluna", "")
                    val = it.get("valor", 0) or 0
                    if "EMPENHADAS ATÉ" in col:
                        emp = val
                    elif "LIQUIDADAS ATÉ" in col:
                        liq = val
                    elif "PAGAS ATÉ" in col:
                        pago = val

                if emp > 0 or liq > 0 or pago > 0:
                    results.append({
                        "ano": year, "uf": uf, "nome": UF_NOMES[uf],
                        "regiao": UF_REGIAO[uf],
                        "empenhado": round(emp, 2),
                        "liquidado": round(liq, 2),
                        "pago": round(pago, 2)
                    })

            except Exception as e:
                siconfi_errors += 1
                print(f"  ERRO {uf} {year}: {e}", flush=True)

            if done % 10 == 0 or done == total_ops:
                elapsed = time.time() - t0
                eta = (elapsed / done) * (total_ops - done) if done > 0 else 0
                print(f"  [{done/total_ops*100:5.1f}%] {uf} {year} P{period} | ETA: {eta/60:.0f}min | err: {siconfi_errors}", flush=True)

            time.sleep(1.5)

    results.sort(key=lambda x: (x["ano"], x["uf"]))
    print(f"  Coletados: {len(results)} registros em {(time.time()-t0)/60:.1f} min | {siconfi_errors} erros")
    return results


def replace_js_var(html, varname, value, is_string=False):
    if is_string:
        pattern = re.compile(
            r"(const\s+" + re.escape(varname) + r"\s*=\s*)'[^']*';",
        )
        replacement = r"\g<1>'" + value + "';"
    else:
        pattern = re.compile(
            r"(const\s+" + re.escape(varname) + r"\s*=\s*)\[.*?\];",
            re.DOTALL,
        )
        new_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        replacement = r"\g<1>" + new_json.replace("\\", "\\\\") + ";"

    new_html, count = pattern.subn(replacement, html)
    if count == 0:
        print(f"  AVISO: {varname} não encontrado no HTML")
    return new_html


def main():
    with_pdde = "--with-pdde" in sys.argv
    skip_pncp = "--skip-pncp" in sys.argv
    skip_siconfi = "--skip-siconfi" in sys.argv
    now = datetime.now(BRT)
    date_str = now.strftime("%d/%m/%Y")

    print(f"[{now:%Y-%m-%d %H:%M}] Atualizando PIPPA Compras Públicas...")

    html = open(HTML_FILE, "r", encoding="utf-8").read()

    # 1. Monitor PNCP
    if not skip_pncp:
        print("\n=== Monitor PNCP 5 Anos ===")
        pncp_data = collect_pncp_monitor()
        html = replace_js_var(html, "PNCP_MONITOR_CACHE", pncp_data)
        html = replace_js_var(html, "PNCP_MONITOR_CACHE_DATE", date_str, is_string=True)

    # 2. Execução Orçamentária (SICONFI)
    if not skip_siconfi:
        print("\n=== Execução Orçamentária (SICONFI/RREO) ===")
        exec_data = collect_siconfi()
        if exec_data:
            html = replace_js_var(html, "EXEC_CACHE", exec_data)
            html = replace_js_var(html, "EXEC_CACHE_DATE", date_str, is_string=True)

    # 3. PDDE/PNAE (se JSONs existirem)
    if with_pdde:
        data_dir = os.path.join(SCRIPT_DIR, "data")
        pdde_file = os.path.join(data_dir, "pdde_cache.json")
        pdde_mun_file = os.path.join(data_dir, "pdde_mun.json")
        pnae_file = os.path.join(data_dir, "pnae_cache.json")
        pnae_mun_file = os.path.join(data_dir, "pnae_mun.json")

        if os.path.exists(pdde_file):
            print("\n=== PDDE ===")
            with open(pdde_file, encoding="utf-8") as f:
                pdde_data = json.load(f)
            html = replace_js_var(html, "PDDE_CACHE", pdde_data)
            html = replace_js_var(html, "PDDE_CACHE_DATE", date_str, is_string=True)
            print(f"  {len(pdde_data)} registros PDDE atualizados")

            if os.path.exists(pdde_mun_file):
                with open(pdde_mun_file, encoding="utf-8") as f:
                    pdde_mun = json.load(f)
                html = replace_js_var(html, "PDDE_MUN_RAW", pdde_mun)
                print(f"  {len(pdde_mun)} registros PDDE municipal atualizados")

        if os.path.exists(pnae_file):
            print("\n=== PNAE ===")
            with open(pnae_file, encoding="utf-8") as f:
                pnae_data = json.load(f)
            html = replace_js_var(html, "PNAE_CACHE", pnae_data)
            html = replace_js_var(html, "PNAE_CACHE_DATE", date_str, is_string=True)
            print(f"  {len(pnae_data)} registros PNAE atualizados")

            if os.path.exists(pnae_mun_file):
                with open(pnae_mun_file, encoding="utf-8") as f:
                    pnae_mun = json.load(f)
                html = replace_js_var(html, "PNAE_MUN_RAW", pnae_mun)
                print(f"  {len(pnae_mun)} registros PNAE municipal atualizados")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  Salvo: {HTML_FILE}")
    print(f"[{now:%Y-%m-%d %H:%M}] Concluído.")


if __name__ == "__main__":
    main()
