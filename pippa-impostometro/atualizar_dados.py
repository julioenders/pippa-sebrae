"""
Atualiza os dados do PIPPA Impostometro consultando a API RREO/SICONFI do Tesouro Nacional.
Executa a cada novo bimestre publicado (a cada 2 meses).

Uso: python atualizar_dados.py
"""
import urllib.request, json, re, datetime, pathlib

API = 'https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo'
TARGET_COL = 'Até o Bimestre (c)'
CODES = ['ReceitaTributaria', 'Impostos', 'Taxas', 'ReceitaDeContribuicoes', 'ContribuicoesSociais']
YEAR = datetime.date.today().year
HTML_PATH = pathlib.Path(__file__).parent / 'index.html'


def fetch_period(year, period):
    url = (f'{API}?an_exercicio={year}&nr_periodo={period}'
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


def fetch_all():
    result = {}
    for year in [YEAR - 1, YEAR]:
        result[str(year)] = {}
        for period in range(1, 7):
            data = fetch_period(year, period)
            if data:
                result[str(year)][str(period)] = data
                total = (data.get('ReceitaTributaria', 0) + data.get('ReceitaDeContribuicoes', 0))
                print(f'  {year} P{period}: R$ {total / 1e12:.3f} tri')
    result['atualizado'] = datetime.date.today().isoformat()
    return result


def update_html(rreo_data):
    html = HTML_PATH.read_text(encoding='utf-8')
    json_str = json.dumps(rreo_data, indent=2)
    pattern = r'var RREO_DATA = \{[\s\S]*?\n\};'
    replacement = f'var RREO_DATA = {json_str};'
    new_html = re.sub(pattern, replacement, html, count=1)
    if new_html == html:
        print('ERRO: nao encontrou o bloco RREO_DATA no HTML')
        return False
    HTML_PATH.write_text(new_html, encoding='utf-8')
    return True


if __name__ == '__main__':
    print('Consultando API RREO/SICONFI...')
    data = fetch_all()
    cur_periods = list(data.get(str(YEAR), {}).keys())
    prev_periods = list(data.get(str(YEAR - 1), {}).keys())
    print(f'\n{YEAR}: {len(cur_periods)} bimestres | {YEAR - 1}: {len(prev_periods)} bimestres')

    if update_html(data):
        print(f'index.html atualizado com sucesso ({data["atualizado"]})')
    else:
        print('Falha ao atualizar index.html')
