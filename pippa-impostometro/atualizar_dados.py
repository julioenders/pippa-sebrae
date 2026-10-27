"""
Atualiza os dados do PIPPA Impostometro consultando:
  1. API RREO/SICONFI do Tesouro Nacional (arrecadacao tributaria)
  2. API SIDRA do IBGE (PIB setorial para estimativa por setor)

Executar a cada novo bimestre publicado (a cada 2 meses).

Uso: python atualizar_dados.py
"""
import urllib.request, json, re, datetime, pathlib

API_RREO = 'https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo'
API_IBGE = 'https://apisidra.ibge.gov.br/values/t/1846/n1/all/v/585/p/last%204/c11255/90687,90691,90696,90697,90705/d/v585%200/h/y'
TARGET_COL = 'Até o Bimestre (c)'
CODES = ['ReceitaTributaria', 'Impostos', 'Taxas', 'ReceitaDeContribuicoes', 'ContribuicoesSociais']
YEAR = datetime.date.today().year
HTML_PATH = pathlib.Path(__file__).parent / 'index.html'


def fetch_rreo_period(year, period):
    url = (f'{API_RREO}?an_exercicio={year}&nr_periodo={period}'
           f'&co_tipo_demonstrativo=RREO&id_ente=1'
           f'&no_anexo=RREO-Anexo%2001&limit=1000')
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read())
        items = data.get('items', [])
        if not items:
            return None
        out = {}
        for it in items:
            if it['cod_conta'] in CODES and it['coluna'] == TARGET_COL:
                out[it['cod_conta']] = it['valor']
        return out if out else None
    except Exception:
        return None


def fetch_rreo():
    result = {}
    for year in [YEAR - 1, YEAR]:
        result[str(year)] = {}
        for period in range(1, 7):
            data = fetch_rreo_period(year, period)
            if data:
                result[str(year)][str(period)] = data
                total = data.get('ReceitaTributaria', 0) + data.get('ReceitaDeContribuicoes', 0)
                print(f'  RREO {year} P{period}: R$ {total / 1e12:.3f} tri')
    result['atualizado'] = datetime.date.today().isoformat()
    return result


def fetch_ibge_setores():
    print('  Consultando IBGE SIDRA (Tabela 1846)...')
    try:
        with urllib.request.urlopen(API_IBGE, timeout=20) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f'  ERRO IBGE: {e}')
        return None

    sectors = {}
    for row in data[1:]:
        name = row['D4N']
        value = float(row['V']) if row['V'] else 0
        sectors[name] = sectors.get(name, 0) + value

    va_total = sectors.get('Valor adicionado a preços básicos', 0)
    if not va_total:
        print('  ERRO: VA total nao encontrado')
        return None

    servicos_total = sectors.get('Serviços - total', 0)
    comercio = sectors.get('Comércio', 0)
    servicos_excl = servicos_total - comercio

    shares = {
        'Servicos': round(servicos_excl / va_total, 3),
        'Industria': round(sectors.get('Indústria - total', 0) / va_total, 3),
        'Comercio': round(comercio / va_total, 3),
        'Agropecuaria': round(sectors.get('Agropecuária - total', 0) / va_total, 3),
    }

    for name, pct in shares.items():
        print(f'  {name}: {pct*100:.1f}%')

    return {
        'periodo': f'Ultimos 4 trimestres anualizados',
        'fonte': 'IBGE — Contas Nacionais Trimestrais (Tabela 1846, var. 585)',
        'shares': shares,
        'va_total_mi': round(va_total),
        'atualizado': datetime.date.today().isoformat(),
    }


def update_html(rreo_data, ibge_data):
    html = HTML_PATH.read_text(encoding='utf-8')
    updated = False

    rreo_json = json.dumps(rreo_data, indent=2)
    pattern_rreo = r'var RREO_DATA = \{[\s\S]*?\n\};'
    new_html = re.sub(pattern_rreo, f'var RREO_DATA = {rreo_json};', html, count=1)
    if new_html != html:
        html = new_html
        updated = True
        print('  RREO_DATA atualizado')

    if ibge_data:
        ibge_json = json.dumps(ibge_data, indent=2)
        pattern_ibge = r'var IBGE_SETORES = \{[\s\S]*?\n\};'
        new_html = re.sub(pattern_ibge, f'var IBGE_SETORES = {ibge_json};', html, count=1)
        if new_html != html:
            html = new_html
            updated = True
            print('  IBGE_SETORES atualizado')

    if updated:
        HTML_PATH.write_text(html, encoding='utf-8')
    return updated


if __name__ == '__main__':
    print('=== PIPPA Impostometro — Atualizacao de Dados ===\n')

    print('[1/2] Consultando API RREO/SICONFI...')
    rreo = fetch_rreo()
    cur_p = [k for k in rreo.get(str(YEAR), {}) if k != 'atualizado']
    prev_p = [k for k in rreo.get(str(YEAR - 1), {}) if k != 'atualizado']
    print(f'  {YEAR}: {len(cur_p)} bimestres | {YEAR - 1}: {len(prev_p)} bimestres\n')

    print('[2/2] Consultando IBGE SIDRA...')
    ibge = fetch_ibge_setores()
    print()

    if update_html(rreo, ibge):
        print(f'index.html atualizado com sucesso ({rreo["atualizado"]})')
    else:
        print('Nenhuma alteracao necessaria ou erro ao atualizar')
