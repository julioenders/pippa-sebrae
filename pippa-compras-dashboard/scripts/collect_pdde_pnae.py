"""
Processa dados PDDE e PNAE exportados do SIGEF/FNDE.

Como os sistemas FNDE (SIGEF, Antonieta de Barros) exigem captcha e
não possuem API REST pública, os dados devem ser obtidos manualmente:

  1. PDDE: https://www.fnde.gov.br/sigefweb/index.php/liberacoes
     - Selecionar programa PDDE, ano desejado, UF
     - Exportar CSV/Excel → salvar em scripts/data/pdde_raw/

  2. PNAE: https://www.fnde.gov.br/sigefweb/index.php/liberacoes
     - Selecionar programa PNAE, ano desejado, UF
     - Exportar CSV/Excel → salvar em scripts/data/pnae_raw/

Ou colocar JSONs prontos em:
  - scripts/data/pdde_cache.json
  - scripts/data/pdde_mun.json
  - scripts/data/pnae_cache.json
  - scripts/data/pnae_mun.json

Uso:
    python scripts/collect_pdde_pnae.py              # processa CSVs se existirem
    python scripts/collect_pdde_pnae.py --check      # verifica dados existentes
"""

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

UF_REGIAO = {
    "AC":"NO","AL":"NE","AM":"NO","AP":"NO","BA":"NE","CE":"NE","DF":"CO",
    "ES":"SE","GO":"CO","MA":"NE","MG":"SE","MS":"CO","MT":"CO","PA":"NO",
    "PB":"NE","PE":"NE","PI":"NE","PR":"SU","RJ":"SE","RN":"NE","RO":"NO",
    "RR":"NO","RS":"SU","SC":"SU","SE":"NE","SP":"SE","TO":"NO"
}


def find_csv_files(folder):
    if not folder.exists():
        return []
    return sorted(folder.glob("*.csv"))


def parse_pdde_csvs(csv_dir):
    """Processa CSVs do PDDE exportados do SIGEF."""
    files = find_csv_files(csv_dir)
    if not files:
        return None, None

    print(f"  Encontrados {len(files)} CSVs PDDE")
    uf_year = defaultdict(lambda: {"custeio": 0, "capital": 0, "total": 0,
                                    "escolas": set(), "municipios": set(), "alunos": 0})
    mun_data = defaultdict(lambda: {"total": 0, "custeio": 0, "capital": 0, "escolas": set()})

    for f in files:
        encoding = "utf-8"
        try:
            with open(f, encoding="utf-8") as fh:
                fh.read(100)
        except UnicodeDecodeError:
            encoding = "latin-1"

        with open(f, encoding=encoding) as fh:
            reader = csv.DictReader(fh, delimiter=";")
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]
            print(f"    {f.name}: colunas = {headers[:10]}")

            for row in reader:
                row = {k.strip().lower(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                uf = row.get("uf", "").strip().upper()
                if not uf or uf not in UF_REGIAO:
                    continue

                try:
                    ano = int(row.get("ano", row.get("exercicio", "0")))
                except ValueError:
                    continue

                def to_float(v):
                    if not v:
                        return 0
                    return float(v.replace(".", "").replace(",", "."))

                custeio = to_float(row.get("custeio", row.get("valor_custeio", "0")))
                capital = to_float(row.get("capital", row.get("valor_capital", "0")))
                total = to_float(row.get("total", row.get("valor_total", "0")))
                if total == 0:
                    total = custeio + capital

                key = f"{uf}_{ano}"
                uf_year[key]["custeio"] += custeio
                uf_year[key]["capital"] += capital
                uf_year[key]["total"] += total

                escola = row.get("escola", row.get("cod_escola", ""))
                if escola:
                    uf_year[key]["escolas"].add(escola)
                mun = row.get("municipio", row.get("nome_municipio", ""))
                cod_mun = row.get("cod_municipio", row.get("codigo_municipio", ""))
                if mun:
                    uf_year[key]["municipios"].add(mun)
                alunos = int(float(row.get("alunos", row.get("qtd_alunos", "0")) or "0"))
                uf_year[key]["alunos"] += alunos

                if mun and cod_mun:
                    mkey = f"{uf}|{cod_mun}|{mun}|{ano}"
                    mun_data[mkey]["total"] += total
                    mun_data[mkey]["custeio"] += custeio
                    mun_data[mkey]["capital"] += capital
                    if escola:
                        mun_data[mkey]["escolas"].add(escola)

    cache = []
    for key, d in sorted(uf_year.items()):
        uf, ano = key.split("_")
        cache.append({
            "uf": uf, "ano": int(ano),
            "custeio": round(d["custeio"], 2),
            "capital": round(d["capital"], 2),
            "total": round(d["total"], 2),
            "escolas": len(d["escolas"]) if d["escolas"] else 0,
            "municipios": len(d["municipios"]) if d["municipios"] else 0,
            "alunos": d["alunos"]
        })

    mun_raw = []
    for key, d in sorted(mun_data.items()):
        uf, cod, nome, ano = key.split("|")
        mun_raw.append([uf, cod, nome, int(ano),
                        round(d["total"], 2), round(d["custeio"], 2),
                        round(d["capital"], 2), len(d["escolas"])])

    return cache, mun_raw


def parse_pnae_csvs(csv_dir):
    """Processa CSVs do PNAE exportados do SIGEF."""
    files = find_csv_files(csv_dir)
    if not files:
        return None, None

    print(f"  Encontrados {len(files)} CSVs PNAE")
    uf_year = defaultdict(lambda: {"valor": 0, "alunos": 0,
                                    "escolas": set(), "municipios": set()})
    mun_data = defaultdict(lambda: {"valor": 0, "alunos": 0, "escolas": set()})

    for f in files:
        encoding = "utf-8"
        try:
            with open(f, encoding="utf-8") as fh:
                fh.read(100)
        except UnicodeDecodeError:
            encoding = "latin-1"

        with open(f, encoding=encoding) as fh:
            reader = csv.DictReader(fh, delimiter=";")
            for row in reader:
                row = {k.strip().lower(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                uf = row.get("uf", "").strip().upper()
                if not uf or uf not in UF_REGIAO:
                    continue

                try:
                    ano = int(row.get("ano", row.get("exercicio", "0")))
                except ValueError:
                    continue

                def to_float(v):
                    if not v:
                        return 0
                    return float(v.replace(".", "").replace(",", "."))

                valor = to_float(row.get("valor", row.get("valor_total", "0")))
                alunos = int(float(row.get("alunos", row.get("qtd_alunos", "0")) or "0"))

                key = f"{uf}_{ano}"
                uf_year[key]["valor"] += valor
                uf_year[key]["alunos"] += alunos

                escola = row.get("escola", row.get("cod_escola", ""))
                if escola:
                    uf_year[key]["escolas"].add(escola)
                mun = row.get("municipio", row.get("nome_municipio", ""))
                if mun:
                    uf_year[key]["municipios"].add(mun)

                if mun:
                    mkey = f"{uf}|{mun}|{ano}"
                    mun_data[mkey]["valor"] += valor
                    mun_data[mkey]["alunos"] += alunos
                    if escola:
                        mun_data[mkey]["escolas"].add(escola)

    cache = []
    for key, d in sorted(uf_year.items()):
        uf, ano = key.split("_")
        cache.append({
            "uf": uf, "ano": int(ano),
            "valor": round(d["valor"], 2),
            "alunos": d["alunos"],
            "escolas": len(d["escolas"]) if d["escolas"] else 0,
            "municipios": len(d["municipios"]) if d["municipios"] else 0,
        })

    mun_raw = []
    for key, d in sorted(mun_data.items()):
        uf, nome, ano = key.split("|")
        mun_raw.append([uf, nome, int(ano), round(d["valor"], 2),
                        d["alunos"], len(d["escolas"])])

    return cache, mun_raw


def main():
    check_only = "--check" in sys.argv
    DATA_DIR.mkdir(exist_ok=True)

    print("=== Processamento PDDE/PNAE ===\n")

    if check_only:
        for name in ["pdde_cache.json", "pdde_mun.json", "pnae_cache.json", "pnae_mun.json"]:
            p = DATA_DIR / name
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                print(f"  {name}: {len(data)} registros")
            else:
                print(f"  {name}: não encontrado")
        return

    # PDDE
    pdde_csv_dir = DATA_DIR / "pdde_raw"
    pdde_json = DATA_DIR / "pdde_cache.json"
    pdde_mun_json = DATA_DIR / "pdde_mun.json"

    if pdde_csv_dir.exists() and list(pdde_csv_dir.glob("*.csv")):
        print("--- PDDE (de CSVs) ---")
        cache, mun = parse_pdde_csvs(pdde_csv_dir)
        if cache:
            pdde_json.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  Salvo: {pdde_json} ({len(cache)} registros)")
        if mun:
            pdde_mun_json.write_text(json.dumps(mun, ensure_ascii=False), encoding="utf-8")
            print(f"  Salvo: {pdde_mun_json} ({len(mun)} registros)")
    elif pdde_json.exists():
        print(f"  PDDE: usando JSON existente ({pdde_json})")
    else:
        print("  PDDE: nenhum dado encontrado")
        print("    Coloque CSVs em scripts/data/pdde_raw/ ou JSON em scripts/data/pdde_cache.json")

    # PNAE
    pnae_csv_dir = DATA_DIR / "pnae_raw"
    pnae_json = DATA_DIR / "pnae_cache.json"
    pnae_mun_json = DATA_DIR / "pnae_mun.json"

    if pnae_csv_dir.exists() and list(pnae_csv_dir.glob("*.csv")):
        print("\n--- PNAE (de CSVs) ---")
        cache, mun = parse_pnae_csvs(pnae_csv_dir)
        if cache:
            pnae_json.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  Salvo: {pnae_json} ({len(cache)} registros)")
        if mun:
            pnae_mun_json.write_text(json.dumps(mun, ensure_ascii=False), encoding="utf-8")
            print(f"  Salvo: {pnae_mun_json} ({len(mun)} registros)")
    elif pnae_json.exists():
        print(f"  PNAE: usando JSON existente ({pnae_json})")
    else:
        print("  PNAE: nenhum dado encontrado")
        print("    Coloque CSVs em scripts/data/pnae_raw/ ou JSON em scripts/data/pnae_cache.json")

    print("\nConcluído. Use 'python scripts/update_compras.py --with-pdde' para injetar no HTML.")


if __name__ == "__main__":
    main()
