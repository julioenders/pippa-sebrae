#!/usr/bin/env python3
"""
build_cache.py — Gera stakeholders_cache.js com dados pre-computados
das APIs da Camara, Senado e TSE para o PIPPA Stakeholders.

Uso: python build_cache.py
Saida: stakeholders_cache.js (mesmo diretorio)
"""

import json
import time
import unicodedata
import re
import sys
import os
from xml.etree import ElementTree
from pathlib import Path

try:
    import requests
except ImportError:
    print("Instalando requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

LEGISLATURA = 57
TIMEOUT = 45

FRENTES_RELEVANTES_KW = [
    'empreendedorismo', 'micro', 'pequen', 'simples', 'mei',
    'desburocratiz', 'livre iniciativa', 'comercio', 'industria',
    'inovacao', 'tecnologia', 'digital', 'startup',
    'cooperativ', 'credito', 'turismo', 'agronegocio',
    'reforma tributaria', 'municipio', 'desenvolvimento'
]

COMISSOES_CHAVE_CAMARA = ['CDE', 'CICS', 'CFFC', 'CFT', 'CTRAB', 'CCTI', 'CDU', 'CAPADR', 'CE', 'CME']
COMISSOES_CHAVE_SENADO = ['CAE', 'CI', 'CDR', 'CMA', 'CCT', 'CE', 'CDH', 'CAS']

AUTORIA_KEYWORDS = [
    'microempresa', 'pequena empresa', 'pequeno porte', 'simples nacional',
    'mei', 'microempreendedor', 'empreendedorismo', 'desburocratiza',
    'sebrae', 'pronampe', 'redesim', 'startup', 'cooperativa',
    'credito produtivo', 'microcredito', 'fomento'
]

AUTORIA_SEARCH_KEYWORDS = [
    ['microempresa', 'pequena+empresa', 'simples+nacional'],
    ['empreendedorismo', 'microempreendedor', 'MEI'],
    ['desburocratizacao', 'pronampe', 'startup'],
    ['cooperativa', 'microcredito', 'credito+produtivo']
]


def normalize(s):
    if not s:
        return ''
    s = s.lower()
    s = unicodedata.normalize('NFD', s)
    s = re.sub(r'[̀-ͯ]', '', s)
    return s.strip()


def safe_get(url, headers=None, retries=3, delay=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers or {}, timeout=TIMEOUT)
            if r.status_code == 429:
                wait = delay * (attempt + 1)
                print(f"  429 rate limit, aguardando {wait}s...")
                time.sleep(wait)
                continue
            return r
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"  Erro: {e}")
    return None


def fetch_deputados():
    print("1/7 Buscando deputados da Camara...")
    deputados = []
    seen = set()
    url = f'https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura={LEGISLATURA}&ordem=ASC&ordenarPor=nome&itens=100'

    r = safe_get(url, headers={'Accept': 'application/xml'})
    if not r or not r.ok:
        print("  ERRO: nao foi possivel buscar deputados")
        return deputados

    total = int(r.headers.get('x-total-count', 0))
    pages = max(1, (total + 99) // 100)

    def parse_xml(text):
        root = ElementTree.fromstring(text)
        for dep in root.iter('deputado_'):
            did = dep.findtext('id', '0')
            if not did or did == '0':
                continue
            did = int(did)
            if did in seen:
                continue
            seen.add(did)
            deputados.append({
                'id': did,
                'nome': dep.findtext('nome', ''),
                'partido': dep.findtext('siglaPartido', ''),
                'uf': dep.findtext('siglaUf', ''),
                'casa': 'camara',
                'foto': dep.findtext('urlFoto', ''),
                'email': dep.findtext('email', ''),
                'frentes': [],
                'orgaos': [],
                'orgaoRoles': {}
            })

    parse_xml(r.text)
    for pg in range(2, pages + 1):
        print(f"  Pagina {pg}/{pages}")
        r2 = safe_get(f'{url}&pagina={pg}', headers={'Accept': 'application/xml'})
        if r2 and r2.ok:
            parse_xml(r2.text)
        time.sleep(0.3)

    print(f"  {len(deputados)} deputados carregados")
    return deputados


def fetch_senadores():
    print("2/7 Buscando senadores...")
    senadores = []
    url = 'https://legis.senado.leg.br/dadosabertos/senador/lista/atual'

    r = safe_get(url, headers={'Accept': 'application/json'})
    if not r or not r.ok:
        print("  ERRO: nao foi possivel buscar senadores")
        return senadores

    data = r.json()
    lista = data.get('ListaParlamentarEmExercicio', {}).get('Parlamentares', {}).get('Parlamentar', [])
    if not isinstance(lista, list):
        lista = [lista]

    for s in lista:
        ident = s.get('IdentificacaoParlamentar', {})
        sid = ident.get('CodigoParlamentar')
        if not sid:
            continue
        senadores.append({
            'id': sid,
            'nome': ident.get('NomeParlamentar', ident.get('NomeCompletoParlamentar', '')),
            'partido': ident.get('SiglaPartidoParlamentar', ''),
            'uf': ident.get('UfParlamentar', ''),
            'casa': 'senado',
            'foto': ident.get('UrlFotoParlamentar', ''),
            'email': ident.get('EmailParlamentar', ''),
            'frentes': [],
            'orgaos': [],
            'orgaoRoles': {}
        })

    print(f"  {len(senadores)} senadores carregados")
    return senadores


def fetch_frentes(parlamentares):
    print("3/7 Buscando frentes parlamentares...")
    url = f'https://dadosabertos.camara.leg.br/api/v2/frentes?idLegislatura={LEGISLATURA}&itens=100'
    todas = []

    r = safe_get(url, headers={'Accept': 'application/xml'})
    if not r or not r.ok:
        print("  ERRO: nao foi possivel buscar frentes")
        return []

    total = int(r.headers.get('x-total-count', 0))
    pages = max(1, (total + 99) // 100)

    def parse_xml(text):
        root = ElementTree.fromstring(text)
        for f in root.iter('frentes_'):
            fid = f.findtext('id')
            titulo = f.findtext('titulo', '')
            if fid and titulo:
                todas.append({'id': int(fid), 'titulo': titulo})

    parse_xml(r.text)
    for pg in range(2, pages + 1):
        r2 = safe_get(f'{url}&pagina={pg}', headers={'Accept': 'application/xml'})
        if r2 and r2.ok:
            parse_xml(r2.text)
        time.sleep(0.3)

    relevantes = [f for f in todas if any(kw in f['titulo'].lower() for kw in FRENTES_RELEVANTES_KW)]
    print(f"  {len(todas)} frentes totais, {len(relevantes)} relevantes")

    parl_by_id = {p['id']: p for p in parlamentares if p['casa'] == 'camara'}

    for i, f in enumerate(relevantes):
        print(f"  Membros frente {i+1}/{len(relevantes)}: {f['titulo'][:50]}...")
        r2 = safe_get(f"https://dadosabertos.camara.leg.br/api/v2/frentes/{f['id']}/membros")
        if r2 and r2.ok:
            membros = r2.json().get('dados', [])
            for m in membros:
                mid = m.get('id')
                if mid in parl_by_id:
                    parl_by_id[mid]['frentes'].append(f['titulo'])
        time.sleep(0.4)

    return relevantes


def fetch_comissoes_camara(parlamentares):
    print("4/7 Buscando comissoes da Camara...")
    url = 'https://dadosabertos.camara.leg.br/api/v2/orgaos?codTipoOrgao=2&itens=100&ordem=ASC&ordenarPor=nome'
    comissoes = {}

    r = safe_get(url, headers={'Accept': 'application/xml'})
    if not r or not r.ok:
        print("  ERRO: nao foi possivel buscar orgaos")
        return comissoes

    orgaos = []
    root = ElementTree.fromstring(r.text)
    for o in root.iter('orgao_'):
        oid = o.findtext('id', '0')
        sigla = o.findtext('sigla', '')
        nome = o.findtext('nome', '')
        orgaos.append({'id': int(oid), 'sigla': sigla, 'nome': nome})

    relevantes = [o for o in orgaos if o['sigla'] in COMISSOES_CHAVE_CAMARA]
    print(f"  {len(relevantes)} comissoes-chave encontradas")

    parl_by_id = {p['id']: p for p in parlamentares if p['casa'] == 'camara'}

    for o in relevantes:
        print(f"  Membros {o['sigla']}...")
        r2 = safe_get(f"https://dadosabertos.camara.leg.br/api/v2/orgaos/{o['id']}/membros")
        if r2 and r2.ok:
            membros = r2.json().get('dados', [])
            member_ids = []
            for m in membros:
                mid = m.get('id')
                member_ids.append(mid)
                if mid in parl_by_id:
                    parl_by_id[mid]['orgaos'].append(o['sigla'])
                    parl_by_id[mid]['orgaoRoles'][o['sigla']] = m.get('titulo', 'Membro')
            comissoes[o['sigla']] = {'nome': o['nome'], 'membros': member_ids}
        time.sleep(0.4)

    return comissoes


def fetch_comissoes_senado(parlamentares):
    print("5/7 Buscando comissoes do Senado...")
    senadores = [p for p in parlamentares if p['casa'] == 'senado']

    for i, s in enumerate(senadores):
        print(f"  Senador {i+1}/{len(senadores)}: {s['nome'][:30]}...")
        url = f"https://legis.senado.leg.br/dadosabertos/senador/{s['id']}/comissoes"
        r = safe_get(url, headers={'Accept': 'application/json'})
        if r and r.ok:
            try:
                j = r.json()
                root = j.get('MembroComissaoParlamentar', j)
                parl = root.get('Parlamentar', root)
                coms = parl.get('Comissoes', parl.get('comissoes', {}))
                lista = coms.get('Comissao', coms.get('comissao', []))
                if not isinstance(lista, list):
                    lista = [lista]
                for c in lista:
                    ic = c.get('IdentificacaoComissao', c)
                    sigla = ic.get('SiglaComissao', ic.get('siglaComissao', ''))
                    if sigla and sigla not in s['orgaos']:
                        s['orgaos'].append(sigla)
                        role = c.get('DescricaoParticipacao', c.get('Participacao', c.get('participacao', 'Membro')))
                        s['orgaoRoles'][sigla] = role
            except Exception:
                pass
        time.sleep(0.5)


def fetch_autorias():
    print("6/7 Buscando autorias tematicas...")
    proposicoes = {}

    for batch in AUTORIA_SEARCH_KEYWORDS:
        for kw in batch:
            url = f'https://dadosabertos.camara.leg.br/api/v2/proposicoes?keywords={kw}&dataInicio=2023-01-01&itens=100&ordem=DESC&ordenarPor=id'
            r = safe_get(url)
            if r and r.ok:
                dados = r.json().get('dados', [])
                for prop in dados:
                    ementa = normalize(prop.get('ementa', ''))
                    if any(normalize(ak) in ementa for ak in AUTORIA_KEYWORDS):
                        if prop.get('id'):
                            proposicoes[prop['id']] = prop
            time.sleep(0.4)

    print(f"  {len(proposicoes)} proposicoes tematicas encontradas")

    dep_autorias = {}
    prop_ids = list(proposicoes.keys())
    for i in range(0, len(prop_ids), 5):
        batch = prop_ids[i:i+5]
        for pid in batch:
            url = f'https://dadosabertos.camara.leg.br/api/v2/proposicoes/{pid}/autores'
            r = safe_get(url)
            if r and r.ok:
                autores = r.json().get('dados', [])
                for autor in autores:
                    uri = autor.get('uri', '')
                    if '/deputados/' in uri:
                        parts = uri.split('/')
                        aid = int(parts[-1])
                        dep_autorias[aid] = dep_autorias.get(aid, 0) + 1
            time.sleep(0.3)
        if i % 25 == 0 and i > 0:
            print(f"  Processadas {i}/{len(prop_ids)} proposicoes...")

    print(f"  {len(dep_autorias)} deputados com autorias tematicas")
    return dep_autorias


def load_candidatos():
    """Carrega CANDIDATOS_2026 do index.html existente"""
    idx = Path(__file__).parent / 'index.html'
    text = idx.read_text(encoding='utf-8')
    start = text.find('var CANDIDATOS_2026 = {')
    if start < 0:
        return {}
    start = text.index('{', start)
    depth = 0
    end = start
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    snippet = text[start:end]
    result = {}
    for line in snippet.split('\n'):
        line = line.strip().rstrip(',')
        m = re.match(r"'([^']+)'\s*:\s*\{(.+)\}", line)
        if not m:
            continue
        key = m.group(1)
        body = m.group(2)
        cargo_m = re.search(r"cargo:\s*'([^']*)'", body)
        uf_m = re.search(r"uf:\s*'([^']*)'", body)
        eleito_m = re.search(r"eleito:\s*(true|false)", body)
        urna_m = re.search(r"urna:\s*'([^']*(?:'[^}]*)?)'", body)
        if cargo_m and uf_m and eleito_m:
            result[key] = {
                'cargo': cargo_m.group(1),
                'uf': uf_m.group(1),
                'eleito': eleito_m.group(1) == 'true',
                'urna': urna_m.group(1) if urna_m else key.upper()
            }
    return result


def match_election(nome, candidatos):
    norm = normalize(nome)
    if norm in candidatos:
        return candidatos[norm]
    for key in candidatos:
        if len(key) > 5 and len(norm) > 5:
            if norm in key or key in norm:
                return candidatos[key]
    return None


def main():
    print("=" * 60)
    print("PIPPA Stakeholders — Build Cache")
    print("=" * 60)

    candidatos = load_candidatos()
    print(f"Candidatos 2026 carregados: {len(candidatos)}")

    deputados = fetch_deputados()
    senadores = fetch_senadores()
    parlamentares = deputados + senadores

    for p in parlamentares:
        p['eleicao2026'] = match_election(p['nome'], candidatos)

    frentes = fetch_frentes(parlamentares)
    comissoes = fetch_comissoes_camara(parlamentares)
    fetch_comissoes_senado(parlamentares)
    autorias = fetch_autorias()

    print("7/7 Gerando stakeholders_cache.js...")

    autorias_str = {str(k): v for k, v in autorias.items()}

    cache = {
        'parlamentares': parlamentares,
        'frentes': [{'id': f['id'], 'titulo': f['titulo']} for f in frentes],
        'comissoesChave': comissoes,
        'autorias': autorias_str,
        'buildDate': time.strftime('%Y-%m-%d %H:%M'),
        'legislatura': LEGISLATURA
    }

    out = Path(__file__).parent / 'stakeholders_cache.js'
    with open(out, 'w', encoding='utf-8') as f:
        f.write('var STAKEHOLDERS_CACHE = ')
        json.dump(cache, f, ensure_ascii=False, indent=None, separators=(',', ':'))
        f.write(';\n')

    size_kb = out.stat().st_size / 1024
    print(f"\nCache gerado: {out.name} ({size_kb:.0f} KB)")
    print(f"  Parlamentares: {len(parlamentares)} ({len(deputados)} dep + {len(senadores)} sen)")
    print(f"  Frentes relevantes: {len(frentes)}")
    print(f"  Comissoes-chave: {len(comissoes)}")
    print(f"  Deputados com autorias: {len(autorias)}")
    print("Done!")


if __name__ == '__main__':
    main()
