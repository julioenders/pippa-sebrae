"""
Gerador de dados estáticos do Cubo RF (Receita Federal) para o dashboard PIPPA Legislativo.

Consulta a API OLAP do Observatório Sebrae e gera JSONs compactos com:
- Empresas ativas por setor (Division) e porte
- Empresas ativas por estado e porte
- Resumo nacional

Uso:
    python scripts/gerar_dados_rf.py

Os JSONs são salvos em data/ e commitados no repositório.
O dashboard os carrega como "API local" sem necessidade de backend.
"""

import json
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Instalando requests...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

BASE_URL = "https://apiv2-observatorio.sebrae.com.br/tesseract/data.jsonrecords"
TOKEN = os.getenv("OBSERVATORIO_TOKEN", "f38eaf2bd57685d925db8db0a91979db")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

FILTROS_OBRIGATORIOS = {
    "Registration Status": "2",
    "Sebrae Commercial Company Indicator": "1",
}

SETORES = {
    "41": "Agropecuaria",
    "12": "Industria Extrativa",
    "11": "Industria de Transformacao",
    "13": "SIUP",
    "61": "Construcao Civil",
    "21": "Comercio",
    "31": "Servicos",
}


def query_olap(drilldowns, measures="Establishments", filters=None, limit=None):
    params = {
        "token": TOKEN,
        "cube": "RF",
        "drilldowns": drilldowns,
        "measures": measures,
        "locale": "pt",
        **FILTROS_OBRIGATORIOS,
    }
    if filters:
        params.update(filters)
    if limit:
        params["limit"] = limit

    try:
        r = requests.get(BASE_URL, params=params, timeout=180)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        print(f"  ERRO: {e}")
        return []


def gerar_setores_porte():
    """Empresas ativas por Divisão CNAE e Porte Sebrae."""
    print("Consultando: Sector, Company Size Sebrae...")
    rows = query_olap("Sector,Company Size Sebrae")

    result = {}
    for row in rows:
        setor_id = str(row.get("Sector ID", row.get("ID Sector", "")))
        setor_nome = row.get("Sector", SETORES.get(setor_id, "Outro"))
        porte = row.get("Company Size Sebrae", "Outro")
        qtd = row.get("Establishments", 0)

        if setor_id not in result:
            result[setor_id] = {"nome": setor_nome, "portes": {}}
        result[setor_id]["portes"][porte] = qtd

    for setor_id in result:
        portes = result[setor_id]["portes"]
        result[setor_id]["total"] = sum(portes.values())

    print(f"  {len(result)} setores encontrados")
    return result


def gerar_estados_porte():
    """Empresas ativas por Estado e Porte Sebrae."""
    print("Consultando: State, Company Size Sebrae...")
    rows = query_olap("State,Company Size Sebrae")

    result = {}
    for row in rows:
        uf = row.get("State", "")
        porte = row.get("Company Size Sebrae", "Outro")
        qtd = row.get("Establishments", 0)

        if not uf:
            continue
        if uf not in result:
            result[uf] = {"portes": {}}
        result[uf]["portes"][porte] = qtd

    for uf in result:
        portes = result[uf]["portes"]
        result[uf]["total"] = sum(portes.values())

    print(f"  {len(result)} estados encontrados")
    return result


def gerar_resumo_nacional():
    """Resumo nacional: totais por porte."""
    print("Consultando: Company Size Sebrae (nacional)...")
    rows = query_olap("Company Size Sebrae")

    portes = {}
    for row in rows:
        porte = row.get("Company Size Sebrae", "Outro")
        qtd = row.get("Establishments", 0)
        portes[porte] = qtd

    total = sum(portes.values())

    print("Consultando: Sector (totais)...")
    rows_setor = query_olap("Sector")
    setores_totais = {}
    for row in rows_setor:
        setor = row.get("Sector", "Outro")
        qtd = row.get("Establishments", 0)
        setores_totais[setor] = qtd

    resumo = {
        "total_empresas": total,
        "por_porte": portes,
        "por_setor": setores_totais,
    }

    print(f"  Total nacional: {total:,} empresas")
    return resumo


def gerar_divisoes_top():
    """Top divisões CNAE por número de empresas."""
    print("Consultando: Division (top divisões)...")
    rows = query_olap("Division")

    divisoes = []
    for row in rows:
        div_id = row.get("Division ID", row.get("ID Division", ""))
        div_nome = row.get("Division", "")
        qtd = row.get("Establishments", 0)
        if div_nome and qtd > 0:
            divisoes.append({
                "id": div_id,
                "nome": div_nome,
                "total": qtd,
            })

    divisoes.sort(key=lambda x: x["total"], reverse=True)
    print(f"  {len(divisoes)} divisões encontradas")
    return divisoes


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Gerando dados RF para: {OUTPUT_DIR}")
    print(f"API: {BASE_URL}")
    print()

    setores = gerar_setores_porte()
    estados = gerar_estados_porte()
    resumo = gerar_resumo_nacional()
    divisoes = gerar_divisoes_top()

    meta = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "fonte": "API OLAP Observatório Sebrae (cubo RF)",
        "filtros": "Registration Status=2 (ativas), Sebrae Commercial Company Indicator=1 (mercantis)",
        "nota": "Snapshot sem dimensão temporal — reflete a carga mais recente da Receita Federal",
    }

    output = {
        "_meta": meta,
        "resumo": resumo,
        "setores": setores,
        "estados": estados,
        "divisoes": divisoes,
    }

    filepath = os.path.join(OUTPUT_DIR, "rf_empresas.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(filepath) / 1024
    print(f"\nArquivo gerado: {filepath} ({size_kb:.1f} KB)")
    print("Pronto!")


if __name__ == "__main__":
    main()
