import requests, json, time, sys
from calendar import monthrange

PNCP = 'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao'
MODS = [6, 8, 5, 9, 12]
UFS = ['AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT',
       'PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO']
UF_N = {
    'AC':'Acre','AL':'Alagoas','AM':'Amazonas','AP':'Amapa','BA':'Bahia',
    'CE':'Ceara','DF':'Distrito Federal','ES':'Espirito Santo','GO':'Goias',
    'MA':'Maranhao','MG':'Minas Gerais','MS':'Mato Grosso do Sul',
    'MT':'Mato Grosso','PA':'Para','PB':'Paraiba','PE':'Pernambuco',
    'PI':'Piaui','PR':'Parana','RJ':'Rio de Janeiro','RN':'Rio Grande do Norte',
    'RO':'Rondonia','RR':'Roraima','RS':'Rio Grande do Sul',
    'SC':'Santa Catarina','SE':'Sergipe','SP':'Sao Paulo','TO':'Tocantins'
}
UF_R = {
    'AC':'NO','AL':'NE','AM':'NO','AP':'NO','BA':'NE','CE':'NE','DF':'CO',
    'ES':'SE','GO':'CO','MA':'NE','MG':'SE','MS':'CO','MT':'CO','PA':'NO',
    'PB':'NE','PE':'NE','PI':'NE','PR':'SU','RJ':'SE','RN':'NE','RO':'NO',
    'RR':'NO','RS':'SU','SC':'SU','SE':'NE','SP':'SE','TO':'NO'
}

OUTPATH = 'C:/Users/julio.albuquerque/Documents/Github/pippa-sebrae/pippa-compras-dashboard/scripts/pncp_monitor_data.json'
DELAY = 3
errors = 0

def fetch_semester(uf, year, half):
    global errors
    if half == 1:
        di, df = f'{year}0101', f'{year}0630'
    else:
        di = f'{year}0701'
        _, last = monthrange(year, 10)
        df = f'{year}1231' if year < 2026 else f'{year}1009'

    est_total, hom_total, qtd_total = 0, 0, 0
    for mod in MODS:
        try:
            r = requests.get(PNCP, params={
                'dataInicial': di, 'dataFinal': df, 'uf': uf,
                'codigoModalidadeContratacao': mod,
                'pagina': 1, 'tamanhoPagina': 50
            }, timeout=30)
            if r.status_code == 429:
                print(f'  429 rate limit - aguardando 60s...', flush=True)
                time.sleep(60)
                r = requests.get(PNCP, params={
                    'dataInicial': di, 'dataFinal': df, 'uf': uf,
                    'codigoModalidadeContratacao': mod,
                    'pagina': 1, 'tamanhoPagina': 50
                }, timeout=30)
            if r.status_code != 200:
                errors += 1
                continue
            data = r.json()
            if isinstance(data, dict):
                total_reg = data.get('totalRegistros', 0)
                items = data.get('data', [])
            elif isinstance(data, list):
                total_reg = len(data)
                items = data
            else:
                continue

            n = len(items)
            if n == 0:
                continue

            page_est = sum((it.get('valorTotalEstimado') or 0) for it in items)
            page_hom = sum((it.get('valorTotalHomologado') or 0) for it in items)

            if total_reg > n:
                factor = total_reg / n
                page_est *= factor
                page_hom *= factor

            est_total += page_est
            hom_total += page_hom
            qtd_total += total_reg

        except Exception as e:
            errors += 1
            print(f'  ERRO {uf} {year} H{half} mod{mod}: {e}', flush=True)

        time.sleep(DELAY)

    return est_total, hom_total, qtd_total

cache = {}
years = [2026]
total_ops = len(UFS) * len(years) * 2
done = 0
t0 = time.time()

print(f'Coletando PNCP: {len(UFS)} UFs x {len(years)} anos x 2 semestres x {len(MODS)} modalidades', flush=True)
print(f'Total combinacoes UF/semestre: {total_ops}', flush=True)
print(f'Delay: {DELAY}s entre requests', flush=True)
print(flush=True)

for year in years:
    for half in [1, 2]:
        for uf in UFS:
            key = f'{uf}_{year}'
            if key not in cache:
                cache[key] = {'uf': uf, 'ano': year, 'nome': UF_N[uf], 'regiao': UF_R[uf], 'estimado': 0, 'homologado': 0, 'qtd': 0}

            est, hom, qtd = fetch_semester(uf, year, half)
            cache[key]['estimado'] += est
            cache[key]['homologado'] += hom
            cache[key]['qtd'] += qtd

            done += 1
            elapsed = time.time() - t0
            eta = (elapsed / done) * (total_ops - done)
            print(f'[{done/total_ops*100:5.1f}%] {uf} {year} H{half} | ETA: {eta/60:.0f}min | err: {errors}', flush=True)

result = sorted(cache.values(), key=lambda x: (x['ano'], x['uf']))
for row in result:
    row['estimado'] = round(row['estimado'], 2)
    row['homologado'] = round(row['homologado'], 2)

print(f'\nTotal: {len(result)} registros em {(time.time()-t0)/60:.1f} min | {errors} erros', flush=True)

with open(OUTPATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False)
print(f'Salvo em: {OUTPATH}', flush=True)
