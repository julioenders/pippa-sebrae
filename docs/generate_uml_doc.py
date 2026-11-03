"""
Gera documento HTML com diagramas UML de componentes para as 21 ferramentas PIPPA.
O HTML resultante pode ser aberto no Word para edição ou visualizado no navegador.
"""
import html as html_mod
from pathlib import Path

# ─── Configuração visual ───────────────────────────────────────────
BOX_W = 138
BOX_H = 54
GAP_X = 18
GAP_Y = 76
LABEL_W = 130
COLORS = {
    "datasource": ("#e8f5e9", "#43a047", "«fonte de dados»"),
    "api":        ("#e3f2fd", "#1565c0", "«api»"),
    "script":     ("#fff3e0", "#e65100", "«script»"),
    "datastore":  ("#ede7f6", "#5e35b1", "«artefato»"),
    "dashboard":  ("#fce4ec", "#c62828", "«dashboard»"),
    "component":  ("#f5f5f5", "#424242", "«componente»"),
    "actor":      ("#e0f7fa", "#00695c", "«ator»"),
    "cicd":       ("#eceff1", "#546e7a", "«ci/cd»"),
    "external":   ("#fff9c4", "#f9a825", "«externo»"),
}

# ─── Definição das 21 ferramentas ──────────────────────────────────
TOOLS = [
    {
        "id": "portal",
        "name": "PIPPA Portal",
        "subtitle": "Hub Central da Plataforma",
        "pattern": "HTML standalone com dados embutidos",
        "description": "Portal central que agrega e dá acesso às 20 ferramentas PIPPA. Contém arrays JS embutidos (TOOLS e QUESTIONS) que alimentam grid filtrável de cards, navegação por 6 macro-temas e 45 perguntas norteadoras.",
        "layers": [
            ("Dados Embutidos", [
                ("TOOLS[]\n(20 ferramentas)", "datastore"),
                ("QUESTIONS[]\n(45 perguntas)", "datastore"),
                ("MACRO_TEMAS[]\n(6 eixos)", "datastore"),
            ]),
            ("Motor de Navegação", [
                ("Busca textual\n(search)", "component"),
                ("Filtro por\nmacro-tema", "component"),
                ("Filtro por\npergunta", "component"),
            ]),
            ("Interface", [
                ("Grid de Cards\n(20 ferramentas)", "dashboard"),
                ("Sidebar\n(perguntas)", "dashboard"),
                ("Dicionário de\nMétricas (modal)", "dashboard"),
            ]),
        ],
    },
    {
        "id": "emendas",
        "name": "PIPPA Emendas Parlamentares",
        "subtitle": "Inteligência em Emendas Federais",
        "pattern": "Python pipeline (5 fases) → Parquet → HTML + FastAPI",
        "description": "Pipeline completo com 4 coletores, 2 enriquecedores, validação cruzada e persistência em Parquet. Gera dashboard HTML standalone e expõe API FastAPI. Automatizado via GitHub Actions.",
        "layers": [
            ("Fontes de Dados", [
                ("Portal da\nTransparência (CGU)", "datasource"),
                ("Tesouro\nTransparente", "datasource"),
                ("API Câmara\n(deputados)", "api"),
                ("API Senado\n(senadores)", "api"),
            ]),
            ("Coleta (collectors/)", [
                ("portal_\ntransparencia.py", "script"),
                ("tesouro_\ntransparente.py", "script"),
                ("camara_api.py", "script"),
                ("senado_api.py", "script"),
            ]),
            ("Enriquecimento + Pipeline", [
                ("partido_\nresolver.py", "script"),
                ("ibge_\nnormalizer.py", "script"),
                ("pipeline.py\n(orquestrador)", "script"),
            ]),
            ("Persistência", [
                ("Parquet\n(agregações)", "datastore"),
                ("cache_manager.py", "script"),
                ("dashboard_\nbuilder.py", "script"),
            ]),
            ("Saída", [
                ("html_renderer.py →\nemendas.html", "dashboard"),
                ("api.py\n(FastAPI)", "api"),
                ("GitHub Actions\n(semanal)", "cicd"),
            ]),
        ],
    },
    {
        "id": "compras",
        "name": "PIPPA Compras Públicas",
        "subtitle": "Compras Públicas e Orçamento Educacional",
        "pattern": "Python scripts → JSON embutido → HTML (6 sub-ferramentas)",
        "description": "Hub com 6 ferramentas integradas: Radar PNCP, PDDE, SICONFI, PNAE, Monitor PNCP 5 Anos e Fornecedores. Scripts Python coletam dados e injetam JSON no HTML via regex.",
        "layers": [
            ("Fontes de Dados", [
                ("API PNCP\n(licitações)", "api"),
                ("API SICONFI\n(Tesouro Nacional)", "api"),
                ("CSVs FNDE\n(PDDE/PNAE)", "datasource"),
            ]),
            ("Coleta (scripts/)", [
                ("coletar_pncp_\nmonitor.py", "script"),
                ("collect_\nsemester.py", "script"),
                ("collect_\npdde_pnae.py", "script"),
                ("update_\ncompras.py", "script"),
            ]),
            ("Saída", [
                ("index.html\n(6 abas)", "dashboard"),
                ("GitHub Actions\n(semanal)", "cicd"),
            ]),
        ],
    },
    {
        "id": "legislativo",
        "name": "PIPPA Legislativo",
        "subtitle": "Inteligência Legislativa",
        "pattern": "Hub HTML → 2 dashboards com chamadas API em tempo real",
        "description": "Hub com 2 ferramentas: Radar Legislativo (classifica proposições P0–P4) e Monitor de Pauta (agenda legislativa). Ambas consultam APIs da Câmara e Senado sob demanda no navegador.",
        "layers": [
            ("Usuário", [
                ("Usuário\n(seleciona período)", "actor"),
            ]),
            ("Dashboards", [
                ("Radar Legislativo\n(proposições P0–P4)", "dashboard"),
                ("Monitor de Pauta\n(sessões/comissões)", "dashboard"),
            ]),
            ("APIs (runtime fetch)", [
                ("API Câmara\n(/proposicoes, /eventos)", "api"),
                ("API Senado\n(/materia, /plenario)", "api"),
            ]),
            ("Classificação Client-side", [
                ("Scoring engine\n(10 critérios SEBRAE)", "component"),
                ("Classificação P0–P4\n(prioridade)", "component"),
            ]),
        ],
    },
    {
        "id": "pesquisas",
        "name": "PIPPA Análise Eleitoral 2026",
        "subtitle": "Pesquisas e Resultados Oficiais",
        "pattern": "Python → dados embutidos + HTML com API TSE runtime",
        "description": "Script Python coleta pesquisas via ElectioLab, calcula médias ponderadas e embute no HTML. Em paralelo, o dashboard consulta a API do TSE em tempo real para resultados oficiais.",
        "layers": [
            ("Fontes de Dados", [
                ("API ElectioLab\n(pesquisas)", "api"),
                ("TSE CDN\n(resultados oficiais)", "api"),
            ]),
            ("Pipeline (Python)", [
                ("update_polls.py\n(média ponderada)", "script"),
                ("GitHub Actions\n(3×/dia)", "cicd"),
            ]),
            ("Dashboard (runtime)", [
                ("index.html\n(pesquisas embutidas)", "dashboard"),
                ("TSE fetcher\n(resultados ao vivo)", "component"),
            ]),
        ],
    },
    {
        "id": "reforma",
        "name": "PIPPA Reforma Tributária",
        "subtitle": "Monitor de Impactos em MPEs",
        "pattern": "Python RSS → JSON cache → HTML com classificação client-side",
        "description": "Script Python coleta notícias via Google News RSS, salva cache JSON. O dashboard carrega o cache e classifica por tema (IBS/CBS/Seletivo), impacto MPE e credibilidade.",
        "layers": [
            ("Fonte de Dados", [
                ("Google News RSS\n(4 queries)", "datasource"),
            ]),
            ("Pipeline (Python)", [
                ("fetch_news.py\n(XML parser)", "script"),
                ("news_cache.json\n(cache local)", "datastore"),
                ("GitHub Actions\n(cada 6h)", "cicd"),
            ]),
            ("Dashboard (client-side)", [
                ("index.html\n(carrega cache)", "dashboard"),
                ("Classificador\n(tema, impacto, cred.)", "component"),
            ]),
        ],
    },
    {
        "id": "prototipo",
        "name": "PIPPA — Protótipo Paraíba",
        "subtitle": "Plataforma Completa em Produção",
        "pattern": "Plataforma externa em produção (pippa.sebrae.com.br)",
        "description": "Versão em produção implantada no SEBRAE Paraíba. Plataforma completa de inteligência territorial com dados socioeconômicos, demográficos e empresariais integrados.",
        "layers": [
            ("Fontes Integradas", [
                ("Dados\nSocioeconômicos", "datasource"),
                ("Dados\nDemográficos", "datasource"),
                ("Dados\nEmpresariais", "datasource"),
            ]),
            ("Plataforma", [
                ("PIPPA Paraíba\n(pippa.sebrae.com.br)", "external"),
            ]),
            ("Saídas", [
                ("Inteligência\nTerritorial", "dashboard"),
                ("Análise\nMunicipal", "dashboard"),
                ("Decisão baseada\nem evidências", "dashboard"),
            ]),
        ],
    },
    {
        "id": "catalogo",
        "name": "Catálogo de Fontes do Observatório",
        "subtitle": "Qual é a sua Estratégia?",
        "pattern": "HTML standalone com dados embutidos (17 fontes, 58 cubos)",
        "description": "Catálogo interativo com 17 fontes de dados e 58 cubos analíticos organizados por perguntas norteadoras. Todos os dados são arrays JS embutidos no HTML.",
        "layers": [
            ("Dados Embutidos", [
                ("FONTES[]\n(17 fontes)", "datastore"),
                ("CUBOS[]\n(58 cubos)", "datastore"),
                ("PERGUNTAS[]\n(norteadoras)", "datastore"),
            ]),
            ("Interface Interativa", [
                ("Busca\ninteligente", "component"),
                ("Cards\nexpandíveis", "dashboard"),
                ("Exportar\nWhatsApp", "component"),
            ]),
        ],
    },
    {
        "id": "mindmap",
        "name": "Mapa Mental — NAL",
        "subtitle": "Modelo Mental do Núcleo de Assessoria Legislativa",
        "pattern": "HTML standalone com mapa mental interativo SVG/CSS",
        "description": "Mapa mental interativo do NAL com 10 frentes de atuação. Estrutura de árvore embutida em JS, renderizada como SVG/CSS com pan, zoom e expand/collapse.",
        "layers": [
            ("Dados Embutidos", [
                ("TREE{}\n(10 ramos NAL)", "datastore"),
            ]),
            ("Motor de Renderização", [
                ("Mind map\nrenderer (JS)", "component"),
                ("Pan + Zoom\ncontrols", "component"),
                ("Expand/\nCollapse", "component"),
            ]),
            ("Saída Visual", [
                ("Mapa mental\ninterativo (SVG)", "dashboard"),
            ]),
        ],
    },
    {
        "id": "orcamento",
        "name": "PIPPA Orçamento",
        "subtitle": "Inteligência Orçamentária UPP 2027",
        "pattern": "HTML standalone com dados orçamentários embutidos + Chart.js",
        "description": "Inteligência orçamentária da UPP com 2 exercícios (2026 execução real R$ 39,4mi e 2027 planejamento R$ 58,7mi) em 4 camadas analíticas. Dados hardcoded.",
        "layers": [
            ("Dados Embutidos", [
                ("Orçamento 2026\n(execução real)", "datastore"),
                ("Orçamento 2027\n(planejamento)", "datastore"),
                ("Núcleos UPP\n(NAL/PE/RelGov)", "datastore"),
            ]),
            ("Visualização (Chart.js)", [
                ("Camada Descritiva\n(KPIs, barras)", "component"),
                ("Camada Diagnóstica\n(comparativos)", "component"),
                ("Camada Preditiva\n(projeções)", "component"),
                ("Camada Prescritiva\n(alertas)", "component"),
            ]),
            ("Dashboards", [
                ("index.html\n(hub)", "dashboard"),
                ("2026.html\n(execução)", "dashboard"),
                ("2027.html\n(planejamento)", "dashboard"),
            ]),
        ],
    },
    {
        "id": "projeto2027",
        "name": "Projeto de Implantação Nacional 2027",
        "subtitle": "Escopo, Roadmap e Governança Ágil",
        "pattern": "HTML standalone — documento estático/apresentação",
        "description": "Documento de escopo para implantação nacional: 3 eixos, 15 epics, 69 features, 17 sprints, R$ 2.015.000. Inclui radar de maturidade, OKRs, RACI e gestão de riscos.",
        "layers": [
            ("Conteúdo Estruturado", [
                ("3 Eixos\n(Nacional/Estadual/\nAplicada)", "datastore"),
                ("15 Epics\n69 Features\n(MoSCoW)", "datastore"),
                ("17 Sprints\n4 Releases\n(trimestral)", "datastore"),
            ]),
            ("Documentação", [
                ("projeto.html\n(escopo completo)", "dashboard"),
                ("apresentacao.html\n(slides)", "dashboard"),
                ("index.html\n(hub)", "dashboard"),
            ]),
            ("Artefatos de Gestão", [
                ("Radar de\nMaturidade (6D)", "component"),
                ("OKRs + RACI\n+ Riscos", "component"),
                ("Glossário\ninterativo", "component"),
            ]),
        ],
    },
    {
        "id": "transformalab",
        "name": "TransformaLab — PIPPA",
        "subtitle": "Plataforma de Experimentação em Políticas Públicas",
        "pattern": "HTML standalone com dados sintéticos + Chart.js",
        "description": "Plataforma de experimentação com 3 modelos de laboratório, 27 labs estaduais, framework de 6 etapas com gates. Dados demonstrativos gerados via funções JS.",
        "layers": [
            ("Dados Demonstrativos", [
                ("UFS[]\n(27 estados)", "datastore"),
                ("EXPERIMENTOS[]\n(12 ativos)", "datastore"),
                ("CHAMADAS[]\nLAB_MODELS[]", "datastore"),
            ]),
            ("Motor de Simulação", [
                ("Gerador\n(rnd/pick)", "component"),
                ("Framework\n6 etapas + gates", "component"),
                ("3 Modelos de\nLaboratório", "component"),
            ]),
            ("Interface", [
                ("Hub TransformaLab\n(27 labs)", "dashboard"),
                ("Cards de\nExperimentos", "dashboard"),
                ("Chart.js\n(resultados)", "dashboard"),
            ]),
        ],
    },
    {
        "id": "indicadores",
        "name": "PIPPA Indicadores — Ambiente de Negócios",
        "subtitle": "6 Temas de Indicadores Compostos",
        "pattern": "14 scripts Python + HTML com botão 'Consultar APIs' em runtime",
        "description": "Painel de indicadores compostos com 6 temas. Scripts Python coletam dados de APIs públicas (REDESIM, PNCP, BCB, IBGE). Dashboards HTML consultam APIs ao vivo via botão.",
        "layers": [
            ("APIs Públicas", [
                ("REDESIM Gov\n(tempo abertura)", "api"),
                ("API PNCP\n(compras públicas)", "api"),
                ("BCB SGS\n(crédito/Selic)", "api"),
                ("IBGE SIDRA\n(PIB/demografia)", "api"),
            ]),
            ("Pipeline (14 scripts)", [
                ("Scripts de\ncoleta Python", "script"),
                ("Observatório Sebrae\n(Tesseract OLAP)", "api"),
            ]),
            ("Dashboards (6 temas)", [
                ("Burocracia e\nFormalização", "dashboard"),
                ("Compras Públicas\ne MEI", "dashboard"),
                ("Crédito, Emprego\ne Diversidade", "dashboard"),
            ]),
        ],
    },
    {
        "id": "raioxmunicipal",
        "name": "Raio-X Territorial",
        "subtitle": "Diagnóstico Socioeconômico em Tempo Real",
        "pattern": "HTML standalone com chamadas API em tempo real (IBGE + BCB)",
        "description": "Dashboard drill-down (Brasil→Região→Estado→Município) consultando APIs públicas em tempo real para população, PIB, VAB, empresas, emprego, Selic, IPCA e crédito.",
        "layers": [
            ("Usuário", [
                ("Usuário\n(seleciona território)", "actor"),
            ]),
            ("APIs (runtime fetch)", [
                ("IBGE Agregados\n(população, PIB)", "api"),
                ("IBGE Localidades\n(municípios, UFs)", "api"),
                ("BCB SGS\n(Selic, IPCA, crédito)", "api"),
            ]),
            ("Processamento Client-side", [
                ("Narrativa\nautomática", "component"),
                ("KPIs dinâmicos\n(Chart.js)", "component"),
                ("Drill-down\n4 níveis", "component"),
            ]),
            ("Saída", [
                ("Dashboard\nterritorial", "dashboard"),
                ("Exportar\nWhatsApp", "component"),
            ]),
        ],
    },
    {
        "id": "atuacaoupp",
        "name": "Atuação UPP 2026",
        "subtitle": "Entregas Estratégicas da Unidade de Políticas Públicas",
        "pattern": "HTML standalone — conteúdo estático institucional",
        "description": "Portal de entregas dos 3 núcleos da UPP (abril–outubro 2026): NAL, Projetos Especiais e RelGov. Conteúdo 100% estático sem APIs ou scripts.",
        "layers": [
            ("Hub (index.html)", [
                ("Landing page\nUPP 2026", "dashboard"),
            ]),
            ("3 Núcleos", [
                ("nal.html\n(Assessoria Legislativa)", "dashboard"),
                ("projetos-especiais.html\n(48 entregas)", "dashboard"),
                ("relgov.html\n(18 entregas)", "dashboard"),
            ]),
            ("Conteúdo", [
                ("PLP 108\nReforma Tributária", "component"),
                ("Movimenta\n(164 ações)", "component"),
                ("Contrata+Brasil\nPró-Catadores", "component"),
            ]),
        ],
    },
    {
        "id": "impacto",
        "name": "PIPPA Impacto",
        "subtitle": "Portfólio de Evidências — Prestação de Contas",
        "pattern": "HTML standalone — fetch dinâmico do portal + Chart.js",
        "description": "Dashboard que faz fetch da página do portal PIPPA em runtime, extrai o array TOOLS via regex e computa KPIs consolidados (ferramentas, eixos, APIs, indicadores).",
        "layers": [
            ("Fonte Interna", [
                ("pippa-portal/\nindex.html", "datasource"),
            ]),
            ("Processamento Runtime", [
                ("fetch() portal\n+ regex TOOLS[]", "script"),
                ("Cálculo de KPIs\n(cobertura, eixos)", "component"),
            ]),
            ("Saída", [
                ("Dashboard\nportfólio", "dashboard"),
                ("Chart.js\n(gráficos)", "component"),
            ]),
        ],
    },
    {
        "id": "stakeholders",
        "name": "PIPPA Stakeholders",
        "subtitle": "Mapa Parlamentar — CRM Legislativo",
        "pattern": "Python pipeline → cache JS + HTML com API runtime",
        "description": "CRM visual de parlamentares com cache pré-computado (Python) + consulta ao vivo de APIs. Scoring ICP/RIG (PB×MI×BC) e overlay de resultados eleitorais TSE 2026.",
        "layers": [
            ("APIs Legislativas", [
                ("API Câmara\n(deputados/frentes)", "api"),
                ("API Senado\n(senadores/comissões)", "api"),
                ("TSE CDN\n(eleições 2026)", "api"),
            ]),
            ("Pipeline Python", [
                ("build_cache.py\n(pré-computa dados)", "script"),
                ("build_eleicao_\n2026.py (TSE)", "script"),
            ]),
            ("Cache Intermediário", [
                ("stakeholders_\ncache.js", "datastore"),
                ("candidatos_\n2026.js", "datastore"),
            ]),
            ("Dashboard", [
                ("index.html\n(CRM + ICP/RIG)", "dashboard"),
                ("APIs ao vivo\n(fallback)", "api"),
            ]),
        ],
    },
    {
        "id": "credito",
        "name": "PIPPA Crédito e Fomento",
        "subtitle": "Radar de Oportunidades para MPEs",
        "pattern": "Python → JSON + HTML com fallback API BCB runtime",
        "description": "Radar de 14 séries BCB SGS. Script Python coleta via IPEADATA (mirror) com fallback BCB direto. Dashboard tenta API live primeiro, cai para data.json.",
        "layers": [
            ("APIs Banco Central", [
                ("IPEADATA\n(mirror BCB SGS)", "api"),
                ("BCB SGS direto\n(fallback)", "api"),
            ]),
            ("Pipeline Python", [
                ("fetch_data.py\n(14 séries)", "script"),
                ("GitHub Actions\n(diário útil)", "cicd"),
            ]),
            ("Armazenamento", [
                ("data.json\n(cache local)", "datastore"),
            ]),
            ("Dashboard", [
                ("index.html\n(radar 14 indicadores)", "dashboard"),
                ("BCB API live\n→ data.json fallback", "component"),
            ]),
        ],
    },
    {
        "id": "consultas",
        "name": "PIPPA Consultas Públicas",
        "subtitle": "Monitor de Participação Social",
        "pattern": "HTML standalone com chamadas API em tempo real",
        "description": "Monitor de audiências e consultas públicas da Câmara e Senado sob demanda. Classificação automática de relevância para MPEs client-side.",
        "layers": [
            ("Usuário", [
                ("Usuário\n(seleciona período)", "actor"),
            ]),
            ("Dashboard (runtime fetch)", [
                ("index.html\n(monitor)", "dashboard"),
            ]),
            ("APIs Legislativas", [
                ("API Câmara\n(/eventos audiências)", "api"),
                ("API Senado\n(/plenario/agenda)", "api"),
            ]),
            ("Classificação", [
                ("Engine SEBRAE\n(relevância MPE)", "component"),
                ("Filtros\n(órgão/status)", "component"),
            ]),
        ],
    },
    {
        "id": "regulatorio",
        "name": "PIPPA Regulatório",
        "subtitle": "Monitor do Diário Oficial da União",
        "pattern": "HTML standalone com fetch API DOU + heurística 3 eixos",
        "description": "Monitor em tempo real do DOU. Consulta API da Imprensa Nacional, aplica heurística de 3 eixos (relevância MPE, alcance setorial, potência normativa) e apresenta normas com score justificado.",
        "layers": [
            ("Usuário", [
                ("Usuário\n(seleciona datas)", "actor"),
            ]),
            ("API DOU", [
                ("Imprensa Nacional\n(in.gov.br/buscar)", "api"),
            ]),
            ("Classificação (3 eixos)", [
                ("Relevância MPE\n(0–0.5)", "component"),
                ("Alcance Setorial\n(0–0.3)", "component"),
                ("Potência Normativa\n(multiplicador)", "component"),
            ]),
            ("Saída", [
                ("Dashboard DOU\n(normas scored)", "dashboard"),
                ("Justificativa\ntransparente", "component"),
            ]),
        ],
    },
    {
        "id": "impostometro",
        "name": "PIPPA Impostômetro",
        "subtitle": "Arrecadação Tributária Federal",
        "pattern": "Python script → patching de variáveis JS no HTML",
        "description": "Script Python coleta dados RREO/SICONFI e IBGE SIDRA, depois faz regex replace para atualizar variáveis JS diretamente no index.html. Dashboard exibe contador animado com projeção linear.",
        "layers": [
            ("Fontes de Dados", [
                ("Tesouro Nacional\nRREO/SICONFI", "api"),
                ("IBGE SIDRA\n(Contas Nacionais)", "api"),
            ]),
            ("Pipeline Python", [
                ("atualizar_dados.py\n(fetch + patch HTML)", "script"),
            ]),
            ("Variáveis Patcheadas", [
                ("var RREO_DATA\n(no HTML)", "datastore"),
                ("var IBGE_SETORES\n(no HTML)", "datastore"),
            ]),
            ("Dashboard", [
                ("Contador animado\n(projeção linear)", "dashboard"),
                ("Evolução bimestral\n+ comparativo", "dashboard"),
            ]),
        ],
    },
]


def svg_diagram(tool):
    tid = tool["id"]
    layers = tool["layers"]
    max_items = max(len(items) for _, items in layers)
    svg_w = max(max_items * (BOX_W + GAP_X) + GAP_X + LABEL_W, 500)
    svg_h = len(layers) * (BOX_H + GAP_Y) + GAP_Y + 10
    marker_id = f"arrow-{tid}"

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
                 f'width="{svg_w}" height="{svg_h}" '
                 f'style="max-width:100%;height:auto;font-family:Segoe UI,Figtree,Arial,sans-serif;">')

    parts.append('<defs>')
    parts.append(f'<marker id="{marker_id}" viewBox="0 0 10 10" refX="10" refY="5" '
                 f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
                 f'<path d="M 0 0 L 10 5 L 0 10 z" fill="#9e9e9e"/></marker>')
    parts.append('</defs>')

    box_centers = []

    for li, (layer_name, items) in enumerate(layers):
        y = GAP_Y // 2 + li * (BOX_H + GAP_Y)
        total_w = len(items) * BOX_W + (len(items) - 1) * GAP_X
        start_x = LABEL_W + (svg_w - LABEL_W - total_w) / 2

        label_y = y + BOX_H / 2
        wrapped = layer_name.split(" ")
        lbl_lines = []
        cur = ""
        for w in wrapped:
            test = f"{cur} {w}".strip()
            if len(test) > 16 and cur:
                lbl_lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lbl_lines.append(cur)
        lbl_start_y = label_y - (len(lbl_lines) - 1) * 6
        for j, ll in enumerate(lbl_lines):
            parts.append(f'<text x="{LABEL_W - 14}" y="{lbl_start_y + j * 12}" '
                         f'text-anchor="end" font-size="10" fill="#6b7280" '
                         f'font-weight="600">{html_mod.escape(ll)}</text>')
        parts.append(f'<line x1="{LABEL_W - 8}" y1="{y}" '
                     f'x2="{LABEL_W - 8}" y2="{y + BOX_H}" '
                     f'stroke="#d1d5db" stroke-width="2" stroke-linecap="round"/>')

        layer_centers = []
        for ii, (label, ctype) in enumerate(items):
            x = start_x + ii * (BOX_W + GAP_X)
            bg, stroke, stereo = COLORS.get(ctype, COLORS["component"])
            cx = x + BOX_W / 2
            cy = y + BOX_H / 2
            layer_centers.append((cx, cy))

            parts.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" '
                         f'rx="6" fill="{bg}" stroke="{stroke}" stroke-width="1.5"/>')

            parts.append(f'<text x="{cx}" y="{y + 12}" text-anchor="middle" '
                         f'font-size="8" fill="{stroke}" font-weight="600">{stereo}</text>')

            lines = label.split("\n")
            for j, line in enumerate(lines):
                ty = y + 24 + j * 13
                escaped = html_mod.escape(line)
                parts.append(f'<text x="{cx}" y="{ty}" text-anchor="middle" '
                             f'font-size="10" fill="#333">{escaped}</text>')

        box_centers.append(layer_centers)

    for li in range(len(layers) - 1):
        top_centers = box_centers[li]
        bot_centers = box_centers[li + 1]
        top_y = GAP_Y // 2 + li * (BOX_H + GAP_Y) + BOX_H
        bot_y = GAP_Y // 2 + (li + 1) * (BOX_H + GAP_Y)
        mid_y = (top_y + bot_y) / 2

        all_xs = [c[0] for c in top_centers] + [c[0] for c in bot_centers]
        bus_left = min(all_xs)
        bus_right = max(all_xs)

        for cx, _ in top_centers:
            parts.append(f'<line x1="{cx}" y1="{top_y}" x2="{cx}" y2="{mid_y}" '
                         f'stroke="#bdbdbd" stroke-width="1.2" stroke-dasharray="4,3"/>')

        if bus_left < bus_right:
            parts.append(f'<line x1="{bus_left}" y1="{mid_y}" '
                         f'x2="{bus_right}" y2="{mid_y}" '
                         f'stroke="#bdbdbd" stroke-width="1.2"/>')

        for cx, _ in bot_centers:
            parts.append(f'<line x1="{cx}" y1="{mid_y}" '
                         f'x2="{cx}" y2="{bot_y}" '
                         f'stroke="#9e9e9e" stroke-width="1.2" marker-end="url(#{marker_id})"/>')

    parts.append('</svg>')
    return "\n".join(parts)


def generate_html():
    sections = []
    for i, tool in enumerate(TOOLS, 1):
        diagram = svg_diagram(tool)
        layers_desc = ""
        for layer_name, items in tool["layers"]:
            comps = ", ".join(label.replace("\n", " ") for label, _ in items)
            layers_desc += f"<li><strong>{layer_name}:</strong> {html_mod.escape(comps)}</li>\n"

        sections.append(f"""
    <div class="tool-section" style="page-break-before:always;">
      <div class="tool-number">{i:02d} / {len(TOOLS)}</div>
      <h2>{html_mod.escape(tool['name'])}</h2>
      <p class="tool-subtitle">{html_mod.escape(tool['subtitle'])}</p>
      <table class="meta-table">
        <tr><th>Padrão Arquitetural</th><td>{html_mod.escape(tool['pattern'])}</td></tr>
        <tr><th>Descrição</th><td>{html_mod.escape(tool['description'])}</td></tr>
      </table>
      <h3>Diagrama de Componentes UML</h3>
      <div class="diagram-wrap">
        {diagram}
      </div>
      <h3>Camadas e Componentes</h3>
      <ul class="layer-list">
        {layers_desc}
      </ul>
    </div>
""")

    legend_items = "".join(
        f'<span class="legend-item"><span class="legend-box" style="background:{bg};border-color:{stroke};"></span>{stereo}</span>'
        for _, (bg, stroke, stereo) in COLORS.items()
    )

    toc_items = "".join(
        f'<li><a href="#tool-{t["id"]}">{html_mod.escape(t["name"])}</a> — {html_mod.escape(t["subtitle"])}</li>\n'
        for t in TOOLS
    )

    for i, t in enumerate(TOOLS):
        sections[i] = sections[i].replace(
            'class="tool-section"',
            f'class="tool-section" id="tool-{t["id"]}"',
            1
        )

    body = "\n".join(sections)

    doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PIPPA — Arquitetura UML das Ferramentas</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
@page {{ margin: 2cm; }}
body {{
  font-family: 'Figtree', 'Segoe UI', Arial, sans-serif;
  color: #1a1a1a;
  background: #fff;
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 32px;
  line-height: 1.6;
}}
.cover {{
  text-align: center;
  padding: 80px 0 60px;
  border-bottom: 3px solid #2a4fda;
  margin-bottom: 40px;
  page-break-after: always;
}}
.cover-logo {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 56px;
  font-weight: 800;
  color: #2a4fda;
  letter-spacing: -3px;
}}
.cover-sub {{
  font-size: 14px;
  color: #6b7280;
  margin-top: 8px;
  letter-spacing: 2px;
  text-transform: uppercase;
}}
.cover h1 {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #0b2574;
  margin-top: 40px;
  line-height: 1.3;
}}
.cover-meta {{
  font-size: 13px;
  color: #9ca3af;
  margin-top: 24px;
}}
.cover-meta strong {{
  color: #374151;
}}
.cover-stats {{
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-top: 36px;
  flex-wrap: wrap;
}}
.cover-stat {{
  text-align: center;
}}
.cover-stat-val {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 32px;
  font-weight: 700;
  color: #2a4fda;
}}
.cover-stat-lbl {{
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 1px;
}}

/* TOC */
.toc {{
  page-break-after: always;
  margin-bottom: 40px;
}}
.toc h2 {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 22px;
  color: #0b2574;
  border-bottom: 2px solid #2a4fda;
  padding-bottom: 8px;
  margin-bottom: 16px;
}}
.toc ol {{
  columns: 1;
  padding-left: 24px;
}}
.toc li {{
  font-size: 13px;
  margin-bottom: 6px;
  line-height: 1.5;
}}
.toc a {{
  color: #2a4fda;
  text-decoration: none;
}}
.toc a:hover {{
  text-decoration: underline;
}}

/* Legend */
.legend {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 16px 0 32px;
  padding: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}}
.legend-item {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #374151;
}}
.legend-box {{
  width: 16px;
  height: 16px;
  border-radius: 3px;
  border: 1.5px solid;
  flex-shrink: 0;
}}

/* Tool Sections */
.tool-section {{
  margin-bottom: 48px;
  padding-top: 20px;
}}
.tool-number {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 12px;
  font-weight: 700;
  color: #2a4fda;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: 4px;
}}
.tool-section h2 {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #0b2574;
  margin-bottom: 4px;
  line-height: 1.3;
}}
.tool-subtitle {{
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 16px;
  font-style: italic;
}}
.meta-table {{
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
  font-size: 13px;
}}
.meta-table th {{
  text-align: left;
  width: 180px;
  padding: 8px 12px;
  background: #f0f4ff;
  border: 1px solid #e0e5f0;
  color: #0b2574;
  font-weight: 600;
  vertical-align: top;
}}
.meta-table td {{
  padding: 8px 12px;
  border: 1px solid #e0e5f0;
  color: #374151;
  line-height: 1.5;
}}
.tool-section h3 {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: #2a4fda;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 20px 0 12px;
}}
.diagram-wrap {{
  background: #fafbfc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 8px;
  text-align: center;
  overflow-x: auto;
}}
.layer-list {{
  padding-left: 20px;
  font-size: 13px;
}}
.layer-list li {{
  margin-bottom: 6px;
  line-height: 1.5;
}}
.layer-list strong {{
  color: #0b2574;
}}

/* Footer */
.doc-footer {{
  text-align: center;
  padding: 32px 0;
  border-top: 2px solid #e5e7eb;
  margin-top: 48px;
  font-size: 11px;
  color: #9ca3af;
}}

@media print {{
  body {{ padding: 0; }}
  .tool-section {{ page-break-inside: avoid; }}
  .diagram-wrap {{ border: 1px solid #ccc; }}
}}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-logo">PIPPA</div>
  <div class="cover-sub">Plataforma de Inteligência em Políticas Públicas Aplicadas</div>
  <h1>Documentação Arquitetural<br>Diagramas UML de Componentes</h1>
  <div class="cover-meta">
    <strong>SEBRAE Nacional</strong> — Unidade de Políticas Públicas<br>
    Novembro 2026 · v1.0
  </div>
  <div class="cover-stats">
    <div class="cover-stat"><div class="cover-stat-val">21</div><div class="cover-stat-lbl">Diagramas</div></div>
    <div class="cover-stat"><div class="cover-stat-val">20</div><div class="cover-stat-lbl">Ferramentas</div></div>
    <div class="cover-stat"><div class="cover-stat-val">16</div><div class="cover-stat-lbl">APIs Integradas</div></div>
    <div class="cover-stat"><div class="cover-stat-val">29</div><div class="cover-stat-lbl">Agentes Python</div></div>
  </div>
</div>

<div class="toc">
  <h2>Sumário</h2>
  <ol>
    {toc_items}
  </ol>
  <h3 style="margin-top:24px;">Legenda dos Estereótipos UML</h3>
  <div class="legend">
    {legend_items}
  </div>
</div>

{body}

<div class="doc-footer">
  PIPPA — Plataforma de Inteligência em Políticas Públicas Aplicadas · SEBRAE Nacional<br>
  Documento gerado automaticamente · Novembro 2026
</div>

</body>
</html>"""

    return doc


if __name__ == "__main__":
    out_path = Path(__file__).parent / "pippa_uml_arquitetura.html"
    html_content = generate_html()
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Documento gerado: {out_path}")
    print(f"Tamanho: {len(html_content):,} bytes")
    print(f"Ferramentas documentadas: {len(TOOLS)}")
