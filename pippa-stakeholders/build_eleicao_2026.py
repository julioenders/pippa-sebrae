"""
Busca resultados oficiais do TSE (CDN) para eleições 2026 e cruza com parlamentares atuais.
Gera um JS map para embedding no PIPPA Stakeholders.
"""
import json, urllib.request, ssl, unicodedata, sys

TSE_BASE = "https://resultados.tse.jus.br/oficial/ele2026/6259/dados"
CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_API = "https://legis.senado.leg.br/dadosabertos"
TSE_PRES = "https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json"

UFS = ["ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt",
       "pa","pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to"]

CARGOS_ESTADUAL = {
    "0006": "Deputado Federal",
    "0007": "Deputado Estadual",
    "0005": "Senador",
    "0003": "Governador",
}

CARGO_PRIORITY = {"Presidente": 5, "Governador": 4, "Senador": 3, "Deputado Federal": 2, "Deputado Estadual": 1}

ctx = ssl.create_default_context()

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PIPPA/1.0"})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            return json.loads(r.read())
    except Exception:
        return None

def normalize(s):
    s = s.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def tokenize(s):
    return set(normalize(s).split())

STOPWORDS = {"de","da","do","das","dos","e","a","o","dr","dr.","dra","dra."}

def name_match_strict(parl_norm, tse_full_norm, tse_urna_norm):
    """Strict matching: requires high token overlap with non-stopword tokens."""
    p_tokens = tokenize(parl_norm) - STOPWORDS
    f_tokens = tokenize(tse_full_norm) - STOPWORDS
    u_tokens = tokenize(tse_urna_norm) - STOPWORDS

    if not p_tokens or not f_tokens:
        return False

    if parl_norm == tse_full_norm:
        return True

    common_full = p_tokens & f_tokens
    if len(common_full) >= 2:
        ratio = len(common_full) / max(len(p_tokens), len(f_tokens))
        if ratio >= 0.5:
            return True

    if len(u_tokens) >= 2 and len(p_tokens) >= 2:
        common_urna = p_tokens & u_tokens
        if len(common_urna) >= 2:
            ratio = len(common_urna) / max(len(p_tokens), len(u_tokens))
            if ratio >= 0.6:
                return True

    return False

def extract_candidates(data):
    cands = []
    for carg in data.get("carg", []):
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    cands.append({
                        "nome": c.get("nm", ""),
                        "urna": c.get("nmu", ""),
                        "partido": par.get("sg", ""),
                        "votos": c.get("vap", "0"),
                        "pct": c.get("pvap", "0"),
                        "eleito": c.get("e", "") == "s",
                        "sit": c.get("dvt", ""),
                    })
    return cands

# 1. Fetch current deputies
print("Buscando deputados da Camara (legislatura 57)...")
deps = []
url = f"{CAMARA_API}/deputados?idLegislatura=57&ordem=ASC&ordenarPor=nome&itens=100"
while url:
    d = fetch_json(url)
    if not d:
        break
    deps.extend(d.get("dados", []))
    nl = next((l["href"] for l in d.get("links", []) if l["rel"] == "next"), None)
    url = nl
print(f"  {len(deps)} deputados")

# 2. Fetch current senators
print("Buscando senadores...")
sens = []
for endpoint in [
    f"{SENADO_API}/senador/lista/atual?format=json",
    f"{SENADO_API}/senador/lista/legislatura/57?format=json",
]:
    sd = fetch_json(endpoint)
    if not sd:
        continue
    for top_key in ["ListaParlamentarEmExercicio", "ListaParlamentarLegislatura"]:
        if top_key not in sd:
            continue
        try:
            lista = sd[top_key].get("Parlamentares", {}).get("Parlamentar", [])
            if not isinstance(lista, list):
                lista = [lista]
            for s in lista:
                ip = s.get("IdentificacaoParlamentar", {})
                sid = ip.get("CodigoParlamentar", "")
                if any(x["id"] == sid for x in sens):
                    continue
                sens.append({
                    "id": sid,
                    "nome": ip.get("NomeParlamentar") or ip.get("NomeCompletoParlamentar", ""),
                    "partido": ip.get("SiglaPartidoParlamentar", ""),
                    "uf": ip.get("UfParlamentar", ""),
                })
        except Exception as e:
            print(f"  Erro parsing: {e}")
    if sens:
        break
print(f"  {len(sens)} senadores")

# Build lookup by UF for efficient matching
parl_by_uf = {}
for d in deps:
    key = normalize(d["nome"])
    uf = d["siglaUf"].lower()
    parl_by_uf.setdefault(uf, {})[key] = {
        "id": d["id"], "nome": d["nome"], "partido": d["siglaPartido"],
        "uf": d["siglaUf"], "casa": "camara"
    }
for s in sens:
    key = normalize(s["nome"])
    uf = s["uf"].lower()
    parl_by_uf.setdefault(uf, {})[key] = {
        "id": s["id"], "nome": s["nome"], "partido": s["partido"],
        "uf": s["uf"], "casa": "senado"
    }

all_parls = {}
for uf_dict in parl_by_uf.values():
    all_parls.update(uf_dict)
print(f"  Total parlamentares: {len(all_parls)}")

# 3. Fetch TSE results and cross-reference
results = {}

def match_for_uf(cands, cargo_nome, uf, uf_parls):
    """Match TSE candidates against parlamentares from a specific UF."""
    for c in cands:
        tse_full = normalize(c["nome"])
        tse_urna = normalize(c["urna"])
        for pkey, p in uf_parls.items():
            if name_match_strict(pkey, tse_full, tse_urna):
                new_priority = CARGO_PRIORITY.get(cargo_nome, 0)
                if pkey in results:
                    old_priority = CARGO_PRIORITY.get(results[pkey]["cargo2026"], 0)
                    if new_priority <= old_priority:
                        continue
                results[pkey] = {
                    "nome": p["nome"], "casa": p["casa"],
                    "cargo2026": cargo_nome, "uf2026": uf.upper(),
                    "eleito": c["eleito"], "votos": c["votos"], "pct": c["pct"],
                    "sit": c["sit"], "nome_urna": c["urna"],
                    "partido_tse": c["partido"]
                }

# Presidente (match against all parlamentares)
print("Buscando resultado Presidente...")
pres = fetch_json(TSE_PRES)
if pres:
    cands = extract_candidates(pres)
    for c in cands:
        tse_full = normalize(c["nome"])
        tse_urna = normalize(c["urna"])
        for pkey, p in all_parls.items():
            if name_match_strict(pkey, tse_full, tse_urna):
                results[pkey] = {
                    "nome": p["nome"], "casa": p["casa"],
                    "cargo2026": "Presidente", "uf2026": "BR",
                    "eleito": c["eleito"], "votos": c["votos"], "pct": c["pct"],
                    "sit": c["sit"], "nome_urna": c["urna"],
                    "partido_tse": c["partido"]
                }
print(f"  {len(results)} matches")

# Per-UF cargos: match parlamentares against candidates in the SAME UF
for cargo_code, cargo_nome in CARGOS_ESTADUAL.items():
    print(f"Buscando {cargo_nome}...")
    for uf in UFS:
        url = f"{TSE_BASE}/{uf}/{uf}-c{cargo_code}-e006259-u.json"
        data = fetch_json(url)
        if not data:
            continue
        cands = extract_candidates(data)
        uf_parls = parl_by_uf.get(uf, {})
        if uf_parls:
            match_for_uf(cands, cargo_nome, uf, uf_parls)
    print(f"  {len(results)} matches total")

# 4. Post-process: verify matches by comparing names visually
# Flag entries where urna name shares < 1 significant word with parlamentar name
flagged = []
for pkey, r in list(results.items()):
    p_tokens = tokenize(pkey) - STOPWORDS
    u_tokens = tokenize(r["nome_urna"]) - STOPWORDS
    f_tokens = tokenize(r.get("nome_urna", "")) - STOPWORDS
    common = p_tokens & (u_tokens | f_tokens)
    if len(common) == 0:
        flagged.append(pkey)
        del results[pkey]

if flagged:
    print(f"\nRemovidos {len(flagged)} falsos positivos:")
    for f in flagged[:10]:
        print(f"  - {f}")

# 5. Output
print(f"\nTotal parlamentares com candidatura 2026: {len(results)}")
eleitos = sum(1 for r in results.values() if r["eleito"])
nao_eleitos = sum(1 for r in results.values() if not r["eleito"])
print(f"  Eleitos: {eleitos}")
print(f"  Nao eleitos: {nao_eleitos}")

by_cargo = {}
for r in results.values():
    c = r["cargo2026"]
    by_cargo.setdefault(c, {"eleitos": 0, "nao": 0})
    if r["eleito"]:
        by_cargo[c]["eleitos"] += 1
    else:
        by_cargo[c]["nao"] += 1
for c, v in sorted(by_cargo.items()):
    print(f"  {c}: {v['eleitos']} eleitos, {v['nao']} nao eleitos")

# Build compact JS map
js_map = {}
for pkey, r in results.items():
    js_map[pkey] = {
        "cargo": r["cargo2026"],
        "uf": r["uf2026"],
        "eleito": r["eleito"],
        "urna": r["nome_urna"]
    }

# Output as JS variable for direct embedding
lines = ["var CANDIDATOS_2026 = {"]
for pkey, v in sorted(js_map.items()):
    e = "true" if v["eleito"] else "false"
    urna = v["urna"].replace("'", "\\'")
    lines.append(f"  '{pkey}': {{ cargo: '{v['cargo']}', uf: '{v['uf']}', eleito: {e}, urna: '{urna}' }},")
lines.append("};")

with open("candidatos_2026.js", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"\nSalvo em candidatos_2026.js ({len(js_map)} entries)")
