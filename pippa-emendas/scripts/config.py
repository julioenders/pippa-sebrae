"""Constantes e configuracoes do PIPPA - Emendas Parlamentares."""

# --- Fontes de Dados ---

PORTAL_TRANSPARENCIA_CSV_URL = (
    "https://dadosabertos-download.cgu.gov.br/"
    "PortalDaTransparencia/saida/emendas-parlamentares/"
    "EmendasParlamentares.zip"
)

TESOURO_TRANSPARENTE_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "83e419da-1552-46bf-bfc3-05160b2c46c9/resource/"
    "66d69917-a5d8-4500-b4b2-ef1f5d062430/download/"
    "emendas-parlamentares.csv"
)

CAMARA_API_BASE = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_API_BASE = "https://legis.senado.leg.br/dadosabertos"

# --- Legislaturas ---

LEGISLATURAS = {
    55: {"inicio": 2015, "fim": 2018, "label": "55ª (2015-2019)"},
    56: {"inicio": 2019, "fim": 2022, "label": "56ª (2019-2023)"},
    57: {"inicio": 2023, "fim": 2026, "label": "57ª (2023-2027)"},
}

# --- Encoding do CSV do Portal ---

PORTAL_CSV_ENCODING = "latin-1"
PORTAL_CSV_SEPARATOR = ";"

TESOURO_CSV_ENCODING = "latin-1"
TESOURO_CSV_SEPARATOR = ";"

# --- Anos excluidos ---

ANO_MINIMO = 2015  # 2014 tem dados incompletos

# --- Estados ---

UF_CODES = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}

UF_SIGLAS = {v: k for k, v in UF_CODES.items()}

REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
}

UF_REGIAO = {}
for regiao, ufs in REGIOES.items():
    for uf in ufs:
        UF_REGIAO[uf] = regiao

# --- Tipos de Emenda ---

TIPOS_EMENDA = {
    "individual_definida": "Emenda Individual - Transferências com Finalidade Definida",
    "individual_especial": "Emenda Individual - Transferências Especiais",
    "bancada": "Emenda de Bancada",
    "comissao": "Emenda de Comissão",
    "relator": "Emenda de Relator",
}

TIPOS_SEM_AUTOR_INDIVIDUAL = {"Emenda de Bancada", "Emenda de Comissão", "Emenda de Relator"}

# --- Validacao cruzada ---

DIVERGENCIA_ALERTA_PCT = 5.0
DIVERGENCIA_CRITICO_PCT = 15.0

# --- Paleta Visual (design system PIPPA) ---

COLORS = {
    "bg": "#0f1117",
    "surface": "#1a1d27",
    "surface2": "#242836",
    "border": "#2e3348",
    "text": "#e4e6ef",
    "text_muted": "#8b8fa8",
    "accent": "#10b981",
    "accent_hover": "#34d399",
    "primary": "#4f8cff",
    "light_blue": "#60a5fa",
    "purple": "#a855f7",
    "pink": "#f472b6",
    "alert": "#ef4444",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "orange": "#ff8c42",
}

SERIES_COLORS = [
    "#4f8cff", "#10b981", "#f59e0b", "#a855f7", "#ef4444",
    "#f472b6", "#22c55e", "#60a5fa", "#f97316", "#8b8fa8",
    "#14b8a6", "#dc2626", "#8b5cf6", "#2563eb", "#6b7280",
]

FONT_FAMILY = "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"

# --- Cache ---

CACHE_DIR = "data/cache"
CACHE_TTL_DOWNLOAD = 24 * 3600       # 24h para CSVs baixados
CACHE_TTL_API = 7 * 24 * 3600        # 7 dias para dados de parlamentares

# --- Fuzzy matching ---

FUZZY_MATCH_THRESHOLD = 85  # score minimo (0-100) para aceitar match
