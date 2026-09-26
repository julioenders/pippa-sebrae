# PIPPA - Emendas Parlamentares

**Status:** Em andamento
**Responsável:** Julio Albuquerque
**Início:** 2026-09-24
**Última atualização:** 2026-09-24

## Objetivo

Consolidar dados de emendas parlamentares federais destinadas a estados e municípios brasileiros, com enriquecimento de partido e UF do autor, gerando dashboards interativos com totais empenhados e pagos por Estado, Município, Autor e Partido.

## Fontes de Dados

| Fonte | Tipo | Filtros aplicados |
|---|---|---|
| Portal da Transparência (CGU) — CSV | Download ZIP (~32 MB, 94k linhas) | Todos os anos (2015+) |
| Tesouro Transparente — CSV | Download direto (~67 MB) | Validação cruzada de repasses |
| API Câmara dos Deputados | REST `/deputados` por legislatura | Partido, UF, nome |
| API Senado Federal | REST `/senador/lista` por legislatura | Partido, UF, nome |

## Entregas

| Artefato | Caminho | Formato |
|---|---|---|
| Dashboard completo | `output/pippa_emendas_completo.html` | HTML interativo (Plotly) |
| Dashboard por ano | `output/pippa_emendas_<ano>.html` | HTML interativo (Plotly) |
| Relatório de qualidade | `output/quality_report.json` | JSON |

## Como Reproduzir

```bash
# Passo 1 — Coleta, enriquecimento e geração do dashboard
python3 scripts/gerar_dashboard.py

# Com filtro por ano
python3 scripts/gerar_dashboard.py --ano 2025
```

## Observações

- Dados de 2014 excluídos por incompletude (campos "Sem informação")
- Partido do autor obtido via cruzamento com APIs da Câmara/Senado por legislatura
- Emendas de relator (RP9) e de bancada tratadas como categorias separadas (sem autor individual)
- Validação cruzada entre Portal da Transparência e Tesouro Transparente para detectar divergências > 5%
- Indicadores de confiança no match de partido: EXATO, FUZZY, NAO_ENCONTRADO
