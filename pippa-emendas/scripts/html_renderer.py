"""Renderizador HTML do dashboard PIPPA - Emendas Parlamentares.

Gera HTML single-file com design system identico ao PIPPA Compras.
Usa Chart.js via CDN, dados embarcados como JSON.
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from config import SERIES_COLORS, UF_SIGLAS, UF_CODES
from models import QualityFlag, PipelineStats


def _to_sigla(nome: str) -> str:
    s = nome.strip().upper()
    if s in UF_CODES:
        return s
    norm = s.title()
    if norm in UF_SIGLAS:
        return UF_SIGLAS[norm]
    for full, sigla in UF_SIGLAS.items():
        if full.upper() == s:
            return sigla
    return ""


def _fmt(valor: float) -> str:
    if abs(valor) >= 1e9:
        return f"R$ {valor/1e9:,.1f} bi"
    if abs(valor) >= 1e6:
        return f"R$ {valor/1e6:,.1f} mi"
    if abs(valor) >= 1e3:
        return f"R$ {valor/1e3:,.0f} mil"
    return f"R$ {valor:,.0f}"


def render_dashboard(
    data: dict,
    stats: PipelineStats,
    quality_flags: list[QualityFlag],
    df_estado: pd.DataFrame,
    ano_filtro: int | None = None,
) -> str:
    data_json = json.dumps(data, ensure_ascii=False, default=str)
    series_json = json.dumps(SERIES_COLORS)
    gen_timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    titulo_periodo = f"Ano {ano_filtro}" if ano_filtro else "2015-2026"

    total_empenhado = df_estado["valor_empenhado"].sum() if "valor_empenhado" in df_estado.columns else 0
    total_pago = df_estado["valor_pago"].sum() if "valor_pago" in df_estado.columns else 0
    total_liquidado = df_estado["valor_liquidado"].sum() if "valor_liquidado" in df_estado.columns else 0
    execucao_pct = (total_pago / total_empenhado * 100) if total_empenhado > 0 else 0

    q_alerta = sum(1 for f in quality_flags if f.status == "ALERTA")
    q_critico = sum(1 for f in quality_flags if f.status == "CRITICO")

    if q_critico > 0:
        thermo_class = "thermo-red"
        thermo_text = f"CRITICO — {q_critico} divergencias"
    elif q_alerta > 0:
        thermo_class = "thermo-yellow"
        thermo_text = f"ATENCAO — {q_alerta} alertas"
    else:
        thermo_class = "thermo-green"
        thermo_text = "Dados validados"

    exec_color = "kpi-accent" if execucao_pct >= 60 else "kpi-warning" if execucao_pct >= 40 else "kpi-alert"

    match_total = stats.match_exato + stats.match_fuzzy + stats.match_nao_encontrado + stats.match_nao_aplicavel
    pct_exato = (stats.match_exato / match_total * 100) if match_total > 0 else 0
    pct_fuzzy = (stats.match_fuzzy / match_total * 100) if match_total > 0 else 0
    pct_nao = (stats.match_nao_encontrado / match_total * 100) if match_total > 0 else 0
    pct_na = (stats.match_nao_aplicavel / match_total * 100) if match_total > 0 else 0

    ufs_raw = df_estado["uf_destino"].dropna().unique().tolist() if "uf_destino" in df_estado.columns else []
    ufs = sorted(set(s for s in (_to_sigla(u) for u in ufs_raw) if s))
    uf_options = "".join(f'<option value="{uf}">{uf}</option>' for uf in ufs)

    anos = sorted(df_estado["ano"].dropna().unique().astype(int).tolist()) if "ano" in df_estado.columns else []
    ano_from = anos[0] if anos else 2015
    ano_to = anos[-1] if anos else 2026
    ano_options_from = "".join(
        f'<option value="{a}" {"selected" if a == ano_from else ""}>{a}</option>' for a in anos
    )
    ano_options_to = "".join(
        f'<option value="{a}" {"selected" if a == ano_to else ""}>{a}</option>' for a in anos
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PIPPA Emendas Parlamentares | {titulo_periodo}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-treemap@2.3.1"></script>
  <style>
    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface2: #242836;
      --border: #2e3348;
      --text: #e4e6ef;
      --text-muted: #8b8fa8;
      --accent: #10b981;
      --accent-hover: #34d399;
      --primary: #4f8cff;
      --purple: #a855f7;
      --pink: #f472b6;
      --alert: #ef4444;
      --success: #22c55e;
      --warning: #f59e0b;
      --radius: 10px;
      --shadow: 0 2px 12px rgba(0,0,0,0.3);
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}

    .header {{
      background: linear-gradient(135deg, #1a1d27 0%, #242836 100%);
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .header-left {{ display: flex; align-items: center; gap: 16px; }}

    .logo {{
      font-size: 22px;
      font-weight: 700;
      background: linear-gradient(135deg, #10b981, #4f8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }}

    .logo-sub {{
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 400;
    }}

    .header-controls {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .thermometer {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
    }}

    .thermo-green {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
    .thermo-yellow {{ background: rgba(245,158,11,0.15); color: #f59e0b; }}
    .thermo-red {{ background: rgba(239,68,68,0.15); color: #ef4444; }}

    .header-date {{
      font-size: 13px;
      color: var(--text-muted);
    }}

    .btn {{
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 8px 20px;
      border-radius: var(--radius);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }}

    .btn:hover {{ background: var(--accent-hover); transform: translateY(-1px); }}

    .btn-outline {{
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
    }}

    .btn-outline:hover {{ border-color: var(--accent); color: var(--accent); background: transparent; }}

    .info-btn {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 1px solid var(--border);
      background: var(--surface2);
      color: var(--text-muted);
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-right: 10px;
    }}

    .info-btn:hover {{ border-color: var(--accent); color: var(--accent); }}

    .date-range {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: var(--text-muted);
    }}

    .layout {{
      display: grid;
      grid-template-columns: 280px 1fr;
      min-height: calc(100vh - 64px);
    }}

    .sidebar {{
      background: var(--surface);
      border-right: 1px solid var(--border);
      padding: 16px;
      overflow-y: auto;
      max-height: calc(100vh - 64px);
      position: sticky;
      top: 64px;
    }}

    .search-input {{
      width: 100%;
      background: var(--surface2);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 12px;
      border-radius: var(--radius);
      font-size: 13px;
      outline: none;
      margin-bottom: 16px;
    }}

    .search-input:focus {{ border-color: var(--accent); }}
    .search-input::placeholder {{ color: var(--text-muted); }}

    .filter-section {{
      margin-bottom: 4px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }}

    .filter-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      cursor: pointer;
      background: var(--surface2);
      transition: background 0.2s;
      user-select: none;
    }}

    .filter-header:hover {{ background: var(--border); }}

    .filter-title {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-muted);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .filter-arrow {{
      font-size: 10px;
      color: var(--text-muted);
      transition: transform 0.2s;
    }}

    .filter-section.open .filter-arrow {{ transform: rotate(180deg); }}

    .filter-badge {{
      background: var(--accent);
      color: #fff;
      font-size: 10px;
      min-width: 18px;
      height: 18px;
      border-radius: 9px;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 0 5px;
      font-weight: 700;
    }}

    .filter-badge.visible {{ display: flex; }}

    .filter-body {{
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.25s ease, padding 0.25s ease;
      padding: 0 12px;
    }}

    .filter-section.open .filter-body {{
      max-height: 300px;
      padding: 10px 12px;
    }}

    .filter-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .filter-chip {{
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s;
      user-select: none;
    }}

    .filter-chip:hover {{ border-color: var(--accent); color: var(--text); }}
    .filter-chip.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

    .filter-clear {{
      font-size: 11px;
      color: var(--accent);
      cursor: pointer;
      margin-top: 8px;
      display: block;
      text-align: right;
    }}

    .filter-clear:hover {{ text-decoration: underline; }}

    .sidebar-footer {{
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-muted);
      text-align: center;
      line-height: 1.6;
    }}

    .main {{
      padding: 20px 24px;
      overflow-y: auto;
    }}

    .kpi-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}

    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      text-align: center;
    }}

    .kpi-value {{
      font-size: 32px;
      font-weight: 700;
      line-height: 1;
      margin-bottom: 4px;
    }}

    .kpi-label {{
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .kpi-accent {{ color: var(--accent); }}
    .kpi-primary {{ color: var(--primary); }}
    .kpi-purple {{ color: var(--purple); }}
    .kpi-warning {{ color: var(--warning); }}
    .kpi-alert {{ color: var(--alert); }}

    .kpi-bar-secondary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      margin-bottom: 24px;
    }}

    .kpi-card-sm {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 12px;
      text-align: center;
    }}

    .kpi-card-sm .kpi-value {{ font-size: 24px; }}
    .kpi-card-sm .kpi-label {{ font-size: 11px; }}

    .section-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      margin-top: 8px;
    }}

    .section-title {{
      font-size: 16px;
      font-weight: 600;
    }}

    .section-count {{
      font-size: 13px;
      color: var(--text-muted);
      background: var(--surface2);
      padding: 4px 10px;
      border-radius: 12px;
    }}

    .charts-row {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }}

    .charts-row-3 {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }}

    .chart-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
    }}

    .chart-title {{
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 12px;
      color: var(--text);
    }}

    .chart-wrapper {{
      position: relative;
      height: 280px;
    }}

    .chart-wrapper-tall {{
      position: relative;
      height: 400px;
    }}

    .chart-card-full {{
      grid-column: 1 / -1;
    }}

    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}

    .data-table thead th {{
      background: var(--surface2);
      color: var(--text-muted);
      font-weight: 600;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
    }}

    .data-table thead th:hover {{ color: var(--accent); }}

    .data-table tbody td {{
      padding: 9px 14px;
      border-bottom: 1px solid rgba(255,255,255,0.03);
    }}

    .data-table tbody tr:hover {{ background: rgba(16,185,129,0.05); }}

    .data-table .num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}

    .filter-bar {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}

    .filter-bar label {{
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .select-input {{
      background: var(--surface2);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 14px;
      border-radius: var(--radius);
      font-size: 14px;
      outline: none;
      cursor: pointer;
      min-width: 120px;
    }}

    .select-input:focus {{ border-color: var(--accent); }}

    .text-input {{
      background: var(--surface2);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 14px;
      border-radius: var(--radius);
      font-size: 13px;
      outline: none;
      min-width: 180px;
    }}

    .text-input:focus {{ border-color: var(--accent); }}
    .text-input::placeholder {{ color: var(--text-muted); }}

    .quality-bar {{
      display: flex;
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
      background: rgba(255,255,255,0.03);
    }}

    .seg-exato {{ background: var(--success); }}
    .seg-fuzzy {{ background: var(--warning); }}
    .seg-nao {{ background: var(--alert); }}
    .seg-na {{ background: var(--text-muted); }}

    .quality-legend {{
      display: flex;
      gap: 16px;
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 10px;
      flex-wrap: wrap;
    }}

    .quality-legend span::before {{
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 4px;
      vertical-align: middle;
    }}

    .ql-exato::before {{ background: var(--success); }}
    .ql-fuzzy::before {{ background: var(--warning); }}
    .ql-nao::before {{ background: var(--alert); }}
    .ql-na::before {{ background: var(--text-muted); }}

    .info-note {{
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.6;
      padding: 12px 16px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-top: 12px;
    }}

    .nav-tabs {{
      display: flex;
      gap: 4px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0;
    }}

    .nav-tab {{
      padding: 10px 20px;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      background: none;
      border: none;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .nav-tab:hover {{ color: var(--text); }}
    .nav-tab.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}

    .info-modal-backdrop {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15,17,23,0.8);
      z-index: 300;
      align-items: center;
      justify-content: center;
    }}

    .info-modal-backdrop.active {{ display: flex; }}

    .info-modal {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 28px;
      max-width: 620px;
      width: 90%;
      max-height: 80vh;
      overflow-y: auto;
    }}

    .info-modal h2 {{
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 16px;
      background: linear-gradient(135deg, #10b981, #4f8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .info-modal h3 {{
      font-size: 13px;
      font-weight: 600;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-top: 16px;
      margin-bottom: 8px;
    }}

    .info-modal ul {{ list-style: none; padding: 0; }}

    .info-modal li {{
      font-size: 13px;
      color: var(--text-muted);
      padding: 4px 0;
      display: flex;
      align-items: flex-start;
      gap: 8px;
      line-height: 1.5;
    }}

    .info-modal li::before {{
      content: '\\2022';
      color: var(--accent);
      font-weight: 700;
      flex-shrink: 0;
    }}

    .info-modal .info-footer {{
      margin-top: 20px;
      padding-top: 12px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-muted);
      text-align: center;
      line-height: 1.6;
    }}

    .info-close {{
      float: right;
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
      padding: 0 4px;
    }}

    .info-close:hover {{ color: var(--text); }}

    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--success);
      color: #fff;
      padding: 10px 20px;
      border-radius: var(--radius);
      font-size: 13px;
      font-weight: 600;
      z-index: 400;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.3s;
    }}

    .toast.show {{ opacity: 1; transform: translateY(0); }}

    .footer-bar {{
      padding: 14px 28px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      background: var(--surface);
    }}

    @media (max-width: 768px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .sidebar {{
        position: static;
        max-height: none;
        border-right: none;
        border-bottom: 1px solid var(--border);
      }}
      .header {{ flex-wrap: wrap; gap: 12px; }}
      .kpi-bar {{ grid-template-columns: repeat(2, 1fr); }}
      .charts-row {{ grid-template-columns: 1fr; }}
      .charts-row-3 {{ grid-template-columns: 1fr; }}
    }}

    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--text-muted); }}
  </style>
</head>
<body>

  <header class="header">
    <div class="header-left">
      <div>
        <div class="logo">PIPPA Emendas Parlamentares</div>
        <div class="logo-sub">Plataforma de Inteligencia em Politicas Publicas Aplicadas</div>
      </div>
      <button class="info-btn" onclick="toggleInfoModal()" title="Sobre o painel">i</button>
    </div>
    <div class="header-controls">
      <div class="thermometer {thermo_class}">{thermo_text}</div>
      <div class="date-range">
        <select id="anoFrom" class="select-input" style="width:90px;" title="Ano inicial" onchange="applyAllFilters()">
          {ano_options_from}
        </select>
        <span>a</span>
        <select id="anoTo" class="select-input" style="width:90px;" title="Ano final" onchange="applyAllFilters()">
          {ano_options_to}
        </select>
        <button class="btn" id="btnFetch" onclick="fetchData()">Buscar Emendas</button>
      </div>
      <select id="ufHeader" class="select-input" style="width:80px;" title="Filtrar por UF" onchange="onUfHeaderChange(); applyAllFilters()">
        <option value="">UF</option>
        {uf_options}
      </select>
      <select id="munHeader" class="select-input" style="width:160px;" title="Municipio" onchange="applyAllFilters()">
        <option value="">Municipio</option>
      </select>
      <button class="btn btn-outline" onclick="applyAllFilters()">Filtrar</button>
      <button class="btn btn-outline" onclick="openExportModal()">Exportar WhatsApp</button>
    </div>
  </header>

  <div id="loadingOverlay" style="display:none;position:fixed;inset:0;background:rgba(15,17,23,0.92);z-index:500;align-items:center;justify-content:center;flex-direction:column;gap:16px;">
    <div style="width:48px;height:48px;border:4px solid var(--border);border-top:4px solid var(--accent);border-radius:50%;animation:spin 0.8s linear infinite;"></div>
    <div id="loadingText" style="color:var(--text);font-size:16px;font-weight:600;">Buscando emendas...</div>
    <div id="loadingProgress" style="color:var(--text-muted);font-size:13px;">Consultando dados processados</div>
  </div>
  <style>
    @keyframes spin {{ 0%{{ transform:rotate(0deg); }} 100%{{ transform:rotate(360deg); }} }}
    #loadingOverlay.active {{ display:flex !important; }}
    .empty-state {{ text-align:center; padding:80px 20px; }}
    .empty-state-icon {{ font-size:64px; margin-bottom:16px; }}
    .empty-state-title {{ font-size:20px; font-weight:600; margin-bottom:8px; color:var(--text); }}
    .empty-state p {{ color:var(--text-muted); font-size:14px; max-width:500px; margin:0 auto; line-height:1.6; }}
  </style>

  <div class="layout">

    <aside class="sidebar">
      <input type="text" class="search-input" placeholder="Buscar estado, autor, partido..." id="globalSearch" oninput="applyAllFilters()">

      <div class="filter-section open" data-section="regiao">
        <div class="filter-header" onclick="toggleSection(this)">
          <div class="filter-title">Regiao <span class="filter-badge" id="badge-regiao"></span></div>
          <span class="filter-arrow">&#9660;</span>
        </div>
        <div class="filter-body">
          <div class="filter-group">
            <span class="filter-chip" data-filter="regiao" data-value="Norte" onclick="toggleFilter(this)">Norte</span>
            <span class="filter-chip" data-filter="regiao" data-value="Nordeste" onclick="toggleFilter(this)">Nordeste</span>
            <span class="filter-chip" data-filter="regiao" data-value="Sudeste" onclick="toggleFilter(this)">Sudeste</span>
            <span class="filter-chip" data-filter="regiao" data-value="Sul" onclick="toggleFilter(this)">Sul</span>
            <span class="filter-chip" data-filter="regiao" data-value="Centro-Oeste" onclick="toggleFilter(this)">Centro-Oeste</span>
          </div>
          <span class="filter-clear" onclick="clearFilter('regiao')">Limpar</span>
        </div>
      </div>

      <div class="filter-section" data-section="uf">
        <div class="filter-header" onclick="toggleSection(this)">
          <div class="filter-title">UF <span class="filter-badge" id="badge-uf"></span></div>
          <span class="filter-arrow">&#9660;</span>
        </div>
        <div class="filter-body">
          <div class="filter-group">
            {_render_uf_chips(ufs)}
          </div>
          <span class="filter-clear" onclick="clearFilter('uf')">Limpar</span>
        </div>
      </div>

      <div class="filter-section" data-section="partido">
        <div class="filter-header" onclick="toggleSection(this)">
          <div class="filter-title">Partido <span class="filter-badge" id="badge-partido"></span></div>
          <span class="filter-arrow">&#9660;</span>
        </div>
        <div class="filter-body">
          <div class="filter-group" id="partidoChips"></div>
          <span class="filter-clear" onclick="clearFilter('partido')">Limpar</span>
        </div>
      </div>

      <div class="sidebar-footer">
        PIPPA Emendas v2.0<br>
        Sebrae Nacional<br>
        APIs: CGU / Camara / Senado
      </div>
    </aside>

    <div class="main">

      <div class="nav-tabs">
        <button class="nav-tab active" onclick="showTab('estados', this)">Estados</button>
        <button class="nav-tab" onclick="showTab('municipios', this)">Municipios</button>
        <button class="nav-tab" onclick="showTab('autores', this)">Autores</button>
        <button class="nav-tab" onclick="showTab('partidos', this)">Partidos</button>
        <button class="nav-tab" onclick="showTab('temporal', this)">Serie Temporal</button>
        <button class="nav-tab" onclick="showTab('qualidade', this)">Qualidade</button>
      </div>

      <div class="kpi-bar">
        <div class="kpi-card">
          <div class="kpi-value kpi-accent" id="kpiEmpenhado">{_fmt(total_empenhado)}</div>
          <div class="kpi-label">Empenhado</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value kpi-primary" id="kpiPago">{_fmt(total_pago)}</div>
          <div class="kpi-label">Pago</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value {exec_color}" id="kpiExecucao">{execucao_pct:.1f}%</div>
          <div class="kpi-label">Execucao</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value kpi-accent" id="kpiEmendas">{stats.total_emendas:,}</div>
          <div class="kpi-label">Emendas</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value kpi-purple" id="kpiAutores">{stats.total_autores_unicos:,}</div>
          <div class="kpi-label">Autores</div>
        </div>
      </div>

      <!-- ESTADOS -->
      <div id="tab-estados" class="tab-content active">
        <div class="section-header">
          <div class="section-title">Emendas por Estado</div>
          <span class="section-count" id="countEstados">{len(ufs)} UFs</span>
        </div>


        <div class="charts-row">
          <div class="chart-card">
            <div class="chart-title">Empenhado vs Pago por UF (Top 15)</div>
            <div class="chart-wrapper-tall"><canvas id="chartEstadoBars"></canvas></div>
          </div>
          <div class="chart-card">
            <div class="chart-title">Taxa de Execucao por UF (%)</div>
            <div class="chart-wrapper-tall"><canvas id="chartEstadoExec"></canvas></div>
          </div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Empenhado vs Pago por Regiao</div>
          <div class="chart-wrapper"><canvas id="chartRegiao"></canvas></div>
        </div>
      </div>

      <!-- MUNICIPIOS -->
      <div id="tab-municipios" class="tab-content">
        <div class="section-header">
          <div class="section-title">Emendas por Municipio</div>
          <span class="section-count" id="countMun">0 municipios</span>
        </div>
        <div class="filter-bar">
          <label>Estado:</label>
          <select id="munUfFilter" class="select-input" onchange="filterMunicipios()">
            <option value="">Todos</option>
            {uf_options}
          </select>
          <label>Buscar:</label>
          <input type="text" id="munSearch" class="text-input" placeholder="Nome do municipio..." oninput="filterMunicipios()">
        </div>
        <div class="chart-card">
          <table class="data-table" id="munTable">
            <thead>
              <tr>
                <th onclick="sortMunTable(0)">Municipio</th>
                <th onclick="sortMunTable(1)">UF</th>
                <th onclick="sortMunTable(2)" class="num">Empenhado</th>
                <th onclick="sortMunTable(3)" class="num">Pago</th>
                <th onclick="sortMunTable(4)" class="num">Execucao</th>
                <th onclick="sortMunTable(5)" class="num">Emendas</th>
              </tr>
            </thead>
            <tbody id="munTbody"></tbody>
          </table>
        </div>
      </div>

      <!-- AUTORES -->
      <div id="tab-autores" class="tab-content">
        <div class="section-header">
          <div class="section-title">Top 20 Autores Individuais</div>
        </div>
        <div class="chart-card">
          <div class="chart-wrapper-tall"><canvas id="chartAutores"></canvas></div>
        </div>
        <div class="info-note" style="margin-top:16px;">
          Autores identificados via cruzamento com APIs da Camara e do Senado. Emendas de bancada, comissao e relator nao possuem autor individual.
        </div>
      </div>

      <!-- PARTIDOS -->
      <div id="tab-partidos" class="tab-content">
        <div class="section-header">
          <div class="section-title">Emendas por Partido</div>
        </div>
        <div class="chart-card" style="margin-bottom:16px;">
          <div class="chart-title">Distribuicao por Partido (Empenhado)</div>
          <div class="chart-wrapper-tall"><canvas id="chartPartidoTreemap"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Top 15 Partidos — Empenhado vs Pago</div>
          <div class="chart-wrapper-tall"><canvas id="chartPartidoBars"></canvas></div>
        </div>
        <div class="info-note">
          Partidos atribuidos via cruzamento com APIs da Camara e do Senado por legislatura.
        </div>
      </div>

      <!-- SERIE TEMPORAL -->
      <div id="tab-temporal" class="tab-content">
        <div class="section-header">
          <div class="section-title">Evolucao Temporal</div>
        </div>
        <div class="chart-card" style="margin-bottom:16px;">
          <div class="chart-title">Evolucao Anual — Empenhado, Pago e Liquidado</div>
          <div class="chart-wrapper"><canvas id="chartSerieTemporal"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Evolucao por Tipo de Emenda (Empenhado)</div>
          <div class="chart-wrapper"><canvas id="chartTipoStacked"></canvas></div>
        </div>
      </div>

      <!-- QUALIDADE -->
      <div id="tab-qualidade" class="tab-content">
        <div class="section-header">
          <div class="section-title">Diagnostico de Qualidade</div>
        </div>
        <div class="kpi-bar" style="margin-bottom:20px;">
          <div class="kpi-card">
            <div class="kpi-value kpi-accent">{stats.match_exato:,}</div>
            <div class="kpi-label">Match Exato</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value kpi-warning">{stats.match_fuzzy:,}</div>
            <div class="kpi-label">Match Fuzzy</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value kpi-alert">{stats.match_nao_encontrado:,}</div>
            <div class="kpi-label">Nao Encontrado</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value kpi-purple">{q_alerta}</div>
            <div class="kpi-label">Alertas</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value kpi-alert">{q_critico}</div>
            <div class="kpi-label">Criticos</div>
          </div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Identificacao de Partido</div>
          <div class="quality-bar" style="margin-bottom:8px;">
            <div class="seg-exato" style="width:{pct_exato:.1f}%"></div>
            <div class="seg-fuzzy" style="width:{pct_fuzzy:.1f}%"></div>
            <div class="seg-nao" style="width:{pct_nao:.1f}%"></div>
            <div class="seg-na" style="width:{pct_na:.1f}%"></div>
          </div>
          <div class="quality-legend">
            <span class="ql-exato">Exato: {stats.match_exato:,} ({pct_exato:.1f}%)</span>
            <span class="ql-fuzzy">Fuzzy: {stats.match_fuzzy:,} ({pct_fuzzy:.1f}%)</span>
            <span class="ql-nao">Nao encontrado: {stats.match_nao_encontrado:,} ({pct_nao:.1f}%)</span>
            <span class="ql-na">Bancada/Comissao/Relator: {stats.match_nao_aplicavel:,} ({pct_na:.1f}%)</span>
          </div>
        </div>
        <div class="info-note">
          <strong>KPIs de Qualidade</strong><br><br>
          <strong>Match Exato</strong> — Autor da emenda identificado com nome identico nas APIs da Camara ou Senado.<br>
          <strong>Match Fuzzy</strong> — Autor identificado por similaridade de nome (score >= 85%), quando o nome no Portal difere levemente do cadastro legislativo.<br>
          <strong>Nao Encontrado</strong> — Autor nao localizado em nenhuma base legislativa. Pode indicar nome incorreto, parlamentar de legislatura anterior ou dado inconsistente na fonte.<br>
          <strong>Alertas</strong> — Divergencia entre 5% e 15% nos totais pagos ao comparar Portal da Transparencia (CGU) com Tesouro Transparente (Tesouro Nacional).<br>
          <strong>Criticos</strong> — Divergencia acima de 15% entre as fontes, indicando inconsistencia significativa nos dados.<br><br>
          <strong>Identificacao de Partido</strong> — Barra proporcional mostrando como os autores foram identificados: match exato (verde), fuzzy (amarelo), nao encontrado (vermelho) e bancada/comissao/relator (cinza, nao possuem autor individual).
        </div>
      </div>

    </div>

  </div>

  <div class="footer-bar">
    <div>Fontes: Portal da Transparencia (CGU) / Tesouro Transparente / API Camara / API Senado</div>
    <div>PIPPA — SEBRAE Nacional | {titulo_periodo} | Gerado em {gen_timestamp}</div>
  </div>

  <!-- Info Modal -->
  <div class="info-modal-backdrop" id="infoModal" onclick="if(event.target===this)toggleInfoModal()">
    <div class="info-modal">
      <button class="info-close" onclick="toggleInfoModal()">&times;</button>
      <h2>PIPPA Emendas Parlamentares</h2>
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:8px;">
        Painel de inteligencia sobre emendas parlamentares federais — valores empenhados, pagos, autores, partidos e municipios beneficiados.
      </p>

      <h3>Fontes de Dados</h3>
      <ul>
        <li>Portal da Transparencia (CGU) — emendas parlamentares federais desde 2015.</li>
        <li>Tesouro Transparente — repasses do Tesouro Nacional para validacao cruzada.</li>
        <li>API Camara dos Deputados — identificacao de deputados e partidos por legislatura.</li>
        <li>API Senado Federal — identificacao de senadores e partidos por legislatura.</li>
      </ul>

      <h3>O que o Painel Faz</h3>
      <ul>
        <li>Consolida emendas parlamentares de todas as modalidades (individual, bancada, comissao, relator).</li>
        <li>Identifica autores e partidos via cruzamento com APIs do Legislativo (match exato e fuzzy).</li>
        <li>Calcula taxas de execucao (pago/empenhado) por estado, municipio, partido e autor.</li>
        <li>Validacao cruzada CGU vs Tesouro para garantia de qualidade dos dados.</li>
      </ul>

      <h3>Indicadores</h3>
      <ul>
        <li>Valor empenhado, liquidado e pago por estado, municipio, autor e partido.</li>
        <li>Taxa de execucao orcamentaria por unidade federativa.</li>
        <li>Evolucao temporal com serie historica e composicao por tipo de emenda.</li>
        <li>Diagnostico de qualidade: match de autores e validacao cruzada de fontes.</li>
      </ul>

      <div class="info-footer">
        PIPPA — Plataforma de Inteligencia em Politicas Publicas Aplicadas<br>
        SEBRAE Nacional — Observatorio
      </div>
    </div>
  </div>

  <!-- Export Modal -->
  <div class="info-modal-backdrop" id="exportModal" onclick="if(event.target===this)closeExportModal()">
    <div class="info-modal">
      <button class="info-close" onclick="closeExportModal()">&times;</button>
      <h2>Exportar para WhatsApp</h2>
      <div id="exportContent" style="background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:16px;font-size:13px;white-space:pre-wrap;line-height:1.6;max-height:400px;overflow-y:auto;"></div>
      <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end;">
        <button class="btn btn-outline" onclick="closeExportModal()">Fechar</button>
        <button class="btn" onclick="copyExport()">Copiar</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

<script>
const DATA = {data_json};
const SERIES_COLORS = {series_json};

const UF_REGIAO = {{
  AC:'Norte',AL:'Nordeste',AM:'Norte',AP:'Norte',BA:'Nordeste',CE:'Nordeste',
  DF:'Centro-Oeste',ES:'Sudeste',GO:'Centro-Oeste',MA:'Nordeste',MG:'Sudeste',
  MS:'Centro-Oeste',MT:'Centro-Oeste',PA:'Norte',PB:'Nordeste',PE:'Nordeste',
  PI:'Nordeste',PR:'Sul',RJ:'Sudeste',RN:'Nordeste',RO:'Norte',RR:'Norte',
  RS:'Sul',SC:'Sul',SE:'Nordeste',SP:'Sudeste',TO:'Norte'
}};

const REGIAO_ORDER = ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste'];
const REGIAO_COLORS = {{ 'Norte': '#4f8cff', 'Nordeste': '#10b981', 'Sudeste': '#f59e0b', 'Sul': '#a855f7', 'Centro-Oeste': '#ef4444' }};

let activeFilters = {{ regiao: [], uf: [], partido: [] }};
let charts = {{}};

function fmtReais(v) {{
  if (Math.abs(v) >= 1e9) return 'R$ ' + (v/1e9).toFixed(1) + ' bi';
  if (Math.abs(v) >= 1e6) return 'R$ ' + (v/1e6).toFixed(1) + ' mi';
  if (Math.abs(v) >= 1e3) return 'R$ ' + (v/1e3).toFixed(0) + ' mil';
  return 'R$ ' + v.toFixed(0);
}}

// ── Header Filters ──────────────────────────────────────────

function getAnoRange() {{
  const from = parseInt(document.getElementById('anoFrom').value) || 0;
  const to = parseInt(document.getElementById('anoTo').value) || 9999;
  return {{ from, to }};
}}

function getHeaderUf() {{
  return document.getElementById('ufHeader').value;
}}

function getHeaderMun() {{
  return document.getElementById('munHeader').value;
}}

function onUfHeaderChange() {{
  const uf = getHeaderUf();
  const sel = document.getElementById('munHeader');
  sel.innerHTML = '<option value="">Municipio</option>';
  if (!uf) return;
  const muns = DATA.municipios
    .filter(m => m.uf === uf)
    .sort((a, b) => b.empenhado - a.empenhado)
    .slice(0, 200);
  muns.forEach(m => {{
    sel.innerHTML += '<option value="' + m.municipio + '">' + m.municipio + '</option>';
  }});
}}

function applyAllFilters() {{
  renderKPIs();
  renderEstadoCharts();
  renderPartidoCharts();
  renderAutorChart();
  renderSerieCharts();
  filterMunicipios();
}}

// ── Data helpers ────────────────────────────────────────────

function filterByAno(items) {{
  const {{ from, to }} = getAnoRange();
  return items.filter(d => d.ano >= from && d.ano <= to);
}}

function filterByUf(items) {{
  const uf = getHeaderUf();
  if (!uf) return items;
  return items.filter(d => d.uf === uf);
}}

function aggregate(items, key) {{
  const map = {{}};
  items.forEach(d => {{
    const k = d[key];
    if (!map[k]) map[k] = {{ empenhado: 0, pago: 0, qtd: 0 }};
    map[k].empenhado += d.empenhado;
    map[k].pago += d.pago;
    map[k].qtd += d.qtd;
  }});
  return Object.entries(map).map(([k, v]) => ({{
    [key]: k, ...v,
    execucao: v.empenhado > 0 ? +(v.pago / v.empenhado * 100).toFixed(1) : 0
  }})).sort((a, b) => b.empenhado - a.empenhado);
}}

// ── Sidebar Filters ─────────────────────────────────────────

function toggleSection(el) {{
  el.closest('.filter-section').classList.toggle('open');
}}

function toggleFilter(el) {{
  el.classList.toggle('active');
  const f = el.dataset.filter;
  const v = el.dataset.value;
  if (!activeFilters[f]) return;
  const idx = activeFilters[f].indexOf(v);
  if (idx >= 0) activeFilters[f].splice(idx, 1);
  else activeFilters[f].push(v);
  const badge = document.getElementById('badge-' + f);
  if (badge) {{
    badge.textContent = activeFilters[f].length;
    badge.classList.toggle('visible', activeFilters[f].length > 0);
  }}
  applyAllFilters();
}}

function clearFilter(f) {{
  activeFilters[f] = [];
  document.querySelectorAll('[data-filter="' + f + '"]').forEach(c => c.classList.remove('active'));
  const badge = document.getElementById('badge-' + f);
  if (badge) {{ badge.textContent = ''; badge.classList.remove('visible'); }}
  applyAllFilters();
}}

function showTab(tab, el) {{
  document.querySelectorAll('.nav-tab').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  if (tab === 'municipios') filterMunicipios();
}}

function getPartidoUfs() {{
  if (!activeFilters.partido.length) return null;
  const ufs = new Set();
  DATA.autores.forEach(d => {{
    if (activeFilters.partido.includes(d.partido) && d.uf) ufs.add(d.uf);
  }});
  return ufs;
}}

function getFilteredEstados() {{
  let items = filterByAno(DATA.estados);
  const uf = getHeaderUf();
  if (uf) items = items.filter(d => d.uf === uf);
  if (activeFilters.regiao.length) items = items.filter(d => activeFilters.regiao.includes(UF_REGIAO[d.uf]));
  if (activeFilters.uf.length) items = items.filter(d => activeFilters.uf.includes(d.uf));
  const partidoUfs = getPartidoUfs();
  if (partidoUfs) items = items.filter(d => partidoUfs.has(d.uf));
  const search = (document.getElementById('globalSearch').value || '').toLowerCase();
  if (search) items = items.filter(d => d.uf.toLowerCase().includes(search));
  return aggregate(items, 'uf');
}}

// ── KPIs ────────────────────────────────────────────────────

function renderKPIs() {{
  const estados = getFilteredEstados();
  const totalEmp = estados.reduce((s, d) => s + d.empenhado, 0);
  const totalPago = estados.reduce((s, d) => s + d.pago, 0);
  const execPct = totalEmp > 0 ? (totalPago / totalEmp * 100).toFixed(1) : '0.0';
  const totalQtd = estados.reduce((s, d) => s + d.qtd, 0);

  const uf = getHeaderUf();
  const search = (document.getElementById('globalSearch').value || '').toLowerCase();
  let autoresFiltered = DATA.autores;
  if (uf) autoresFiltered = autoresFiltered.filter(d => d.uf === uf);
  if (activeFilters.regiao.length) autoresFiltered = autoresFiltered.filter(d => activeFilters.regiao.includes(UF_REGIAO[d.uf]));
  if (activeFilters.uf.length) autoresFiltered = autoresFiltered.filter(d => activeFilters.uf.includes(d.uf));
  if (activeFilters.partido.length) autoresFiltered = autoresFiltered.filter(d => activeFilters.partido.includes(d.partido));
  if (search) autoresFiltered = autoresFiltered.filter(d => d.nome.toLowerCase().includes(search) || d.partido.toLowerCase().includes(search) || d.uf.toLowerCase().includes(search));

  document.getElementById('kpiEmpenhado').textContent = fmtReais(totalEmp);
  document.getElementById('kpiPago').textContent = fmtReais(totalPago);
  document.getElementById('kpiExecucao').textContent = execPct + '%';
  document.getElementById('kpiEmendas').textContent = totalQtd.toLocaleString('pt-BR');
  document.getElementById('kpiAutores').textContent = autoresFiltered.length.toLocaleString('pt-BR');
}}

// ── Charts ──────────────────────────────────────────────────

const chartOpts = {{
  responsive: true,
  maintainAspectRatio: false,
  plugins: {{ legend: {{ labels: {{ color: '#8b8fa8', font: {{ size: 11 }} }} }} }}
}};

// ── Charts ──────────────────────────────────────────────────

function renderEstadoCharts() {{
  const estados = getFilteredEstados();
  const top15 = estados.slice(0, 15);

  if (charts.estadoBars) charts.estadoBars.destroy();
  charts.estadoBars = new Chart(document.getElementById('chartEstadoBars'), {{
    type: 'bar',
    data: {{
      labels: top15.map(d => d.uf),
      datasets: [
        {{ label: 'Empenhado', data: top15.map(d => d.empenhado), backgroundColor: '#4f8cff' }},
        {{ label: 'Pago', data: top15.map(d => d.pago), backgroundColor: 'rgba(96,165,250,0.5)' }}
      ]
    }},
    options: {{
      ...chartOpts,
      indexAxis: 'y',
      plugins: {{
        ...chartOpts.plugins,
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmtReais(ctx.raw) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b8fa8', callback: v => fmtReais(v) }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ ticks: {{ color: '#e4e6ef' }}, grid: {{ display: false }} }}
      }}
    }}
  }});

  if (charts.estadoExec) charts.estadoExec.destroy();
  const sorted = [...estados].sort((a, b) => a.execucao - b.execucao);
  const execTop = sorted.slice(-15);
  charts.estadoExec = new Chart(document.getElementById('chartEstadoExec'), {{
    type: 'bar',
    data: {{
      labels: execTop.map(d => d.uf),
      datasets: [{{
        label: 'Execucao %',
        data: execTop.map(d => d.execucao),
        backgroundColor: execTop.map(d => d.execucao >= 60 ? '#22c55e' : d.execucao >= 40 ? '#f59e0b' : '#ef4444')
      }}]
    }},
    options: {{
      ...chartOpts,
      indexAxis: 'y',
      plugins: {{
        ...chartOpts.plugins,
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx => ctx.raw.toFixed(1) + '%' }} }}
      }},
      scales: {{
        x: {{ max: 100, ticks: {{ color: '#8b8fa8', callback: v => v + '%' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ ticks: {{ color: '#e4e6ef' }}, grid: {{ display: false }} }}
      }}
    }}
  }});

  const regiaoEmp = {{}};
  const regiaoPago = {{}};
  REGIAO_ORDER.forEach(r => {{ regiaoEmp[r] = 0; regiaoPago[r] = 0; }});
  estados.forEach(d => {{
    const r = UF_REGIAO[d.uf];
    if (r) {{ regiaoEmp[r] += d.empenhado; regiaoPago[r] += d.pago; }}
  }});

  if (charts.regiao) charts.regiao.destroy();
  charts.regiao = new Chart(document.getElementById('chartRegiao'), {{
    type: 'bar',
    data: {{
      labels: REGIAO_ORDER,
      datasets: [
        {{ label: 'Empenhado', data: REGIAO_ORDER.map(r => regiaoEmp[r]), backgroundColor: REGIAO_ORDER.map(r => REGIAO_COLORS[r]) }},
        {{ label: 'Pago', data: REGIAO_ORDER.map(r => regiaoPago[r]), backgroundColor: REGIAO_ORDER.map(r => REGIAO_COLORS[r] + '80') }}
      ]
    }},
    options: {{
      ...chartOpts,
      indexAxis: 'y',
      plugins: {{
        ...chartOpts.plugins,
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmtReais(ctx.raw) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b8fa8', callback: v => fmtReais(v) }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ ticks: {{ color: '#e4e6ef', font: {{ size: 12 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function getFilteredPartidos() {{
  const uf = getHeaderUf();
  const hasUfFilter = uf || activeFilters.regiao.length || activeFilters.uf.length || activeFilters.partido.length;
  const search = (document.getElementById('globalSearch').value || '').toLowerCase();

  if (hasUfFilter || search) {{
    let autores = DATA.autores.slice();
    if (uf) autores = autores.filter(d => d.uf === uf);
    if (activeFilters.regiao.length) autores = autores.filter(d => activeFilters.regiao.includes(UF_REGIAO[d.uf]));
    if (activeFilters.uf.length) autores = autores.filter(d => activeFilters.uf.includes(d.uf));
    if (activeFilters.partido.length) autores = autores.filter(d => activeFilters.partido.includes(d.partido));
    if (search) autores = autores.filter(d => d.partido.toLowerCase().includes(search) || d.nome.toLowerCase().includes(search) || d.uf.toLowerCase().includes(search));
    return aggregate(autores, 'partido');
  }}
  const raw = filterByAno(DATA.partidos);
  let partidos = aggregate(raw, 'partido');
  if (search) partidos = partidos.filter(d => d.partido.toLowerCase().includes(search));
  return partidos;
}}

function renderPartidoCharts() {{
  const partidos = getFilteredPartidos();
  const top15tree = partidos.slice(0, 15);

  if (charts.partidoTreemap) charts.partidoTreemap.destroy();
  charts.partidoTreemap = new Chart(document.getElementById('chartPartidoTreemap'), {{
    type: 'treemap',
    data: {{
      datasets: [{{
        tree: top15tree,
        key: 'empenhado',
        groups: ['partido'],
        spacing: 2,
        borderWidth: 2,
        borderColor: '#1a1d27',
        backgroundColor: function(ctx) {{
          if (ctx.type !== 'data') return 'transparent';
          return SERIES_COLORS[ctx.dataIndex % SERIES_COLORS.length];
        }},
        labels: {{
          display: true,
          align: 'center',
          position: 'middle',
          color: '#fff',
          font: {{ size: 12, weight: 'bold' }},
          formatter: function(ctx) {{
            if (ctx.type !== 'data') return '';
            const g = ctx.raw.g;
            const v = ctx.raw.v;
            if (!g) return '';
            return [g, fmtReais(v)];
          }}
        }}
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            title: function(items) {{
              if (!items.length) return '';
              return items[0].raw.g || '';
            }},
            label: function(ctx) {{
              return 'Empenhado: ' + fmtReais(ctx.raw.v);
            }}
          }}
        }}
      }}
    }}
  }});

  const top15 = partidos.slice(0, 15).reverse();
  if (charts.partidoBars) charts.partidoBars.destroy();
  charts.partidoBars = new Chart(document.getElementById('chartPartidoBars'), {{
    type: 'bar',
    data: {{
      labels: top15.map(d => d.partido),
      datasets: [
        {{ label: 'Empenhado', data: top15.map(d => d.empenhado), backgroundColor: '#4f8cff' }},
        {{ label: 'Pago', data: top15.map(d => d.pago), backgroundColor: 'rgba(96,165,250,0.5)' }}
      ]
    }},
    options: {{
      ...chartOpts,
      indexAxis: 'y',
      plugins: {{
        ...chartOpts.plugins,
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmtReais(ctx.raw) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b8fa8', callback: v => fmtReais(v) }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ ticks: {{ color: '#e4e6ef' }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function renderAutorChart() {{
  let autores = DATA.autores.slice();
  const uf = getHeaderUf();
  if (uf) autores = autores.filter(d => d.uf === uf);
  if (activeFilters.regiao.length) autores = autores.filter(d => activeFilters.regiao.includes(UF_REGIAO[d.uf]));
  if (activeFilters.uf.length) autores = autores.filter(d => activeFilters.uf.includes(d.uf));
  if (activeFilters.partido.length) autores = autores.filter(d => activeFilters.partido.includes(d.partido));
  const search = (document.getElementById('globalSearch').value || '').toLowerCase();
  if (search) autores = autores.filter(d => d.nome.toLowerCase().includes(search) || d.partido.toLowerCase().includes(search) || d.uf.toLowerCase().includes(search));
  autores = autores.sort((a, b) => b.empenhado - a.empenhado).slice(0, 20).reverse();
  const labels = autores.map(d => d.nome + ' (' + d.partido + '/' + d.uf + ')');
  const colors = autores.map(d => d.confianca === 'exato' ? '#4f8cff' : '#f59e0b');

  if (charts.autores) charts.autores.destroy();
  charts.autores = new Chart(document.getElementById('chartAutores'), {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [{{
        label: 'Empenhado',
        data: autores.map(d => d.empenhado),
        backgroundColor: colors
      }}]
    }},
    options: {{
      ...chartOpts,
      indexAxis: 'y',
      plugins: {{
        ...chartOpts.plugins,
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx => fmtReais(ctx.raw) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b8fa8', callback: v => fmtReais(v) }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ ticks: {{ color: '#e4e6ef', font: {{ size: 10 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function renderSerieCharts() {{
  const {{ from, to }} = getAnoRange();
  const uf = getHeaderUf();
  const partidoUfs = getPartidoUfs();
  const hasUfFilter = uf || activeFilters.regiao.length || activeFilters.uf.length || partidoUfs;

  let serie;
  if (hasUfFilter) {{
    let items = DATA.estados.filter(d => d.ano >= from && d.ano <= to);
    if (uf) items = items.filter(d => d.uf === uf);
    if (activeFilters.regiao.length) items = items.filter(d => activeFilters.regiao.includes(UF_REGIAO[d.uf]));
    if (activeFilters.uf.length) items = items.filter(d => activeFilters.uf.includes(d.uf));
    if (partidoUfs) items = items.filter(d => partidoUfs.has(d.uf));
    const byAno = {{}};
    items.forEach(d => {{
      if (!byAno[d.ano]) byAno[d.ano] = {{ ano: d.ano, empenhado: 0, pago: 0, liquidado: 0 }};
      byAno[d.ano].empenhado += d.empenhado;
      byAno[d.ano].pago += d.pago;
    }});
    serie = Object.values(byAno).sort((a, b) => a.ano - b.ano);
  }} else {{
    serie = DATA.serie.filter(d => d.ano >= from && d.ano <= to);
  }}
  const anos = serie.map(d => d.ano);

  if (charts.serie) charts.serie.destroy();
  charts.serie = new Chart(document.getElementById('chartSerieTemporal'), {{
    type: 'line',
    data: {{
      labels: anos,
      datasets: [
        {{ label: 'Empenhado', data: serie.map(d => d.empenhado), borderColor: '#4f8cff', backgroundColor: 'rgba(79,140,255,0.1)', fill: true, borderWidth: 3, pointRadius: 5, tension: 0.3 }},
        {{ label: 'Pago', data: serie.map(d => d.pago), borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.1)', fill: true, borderWidth: 3, pointRadius: 5, tension: 0.3 }},
        {{ label: 'Liquidado', data: serie.map(d => d.liquidado), borderColor: '#f59e0b', borderDash: [5,3], borderWidth: 2, pointRadius: 4, tension: 0.3, fill: false }}
      ]
    }},
    options: {{
      ...chartOpts,
      plugins: {{
        ...chartOpts.plugins,
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmtReais(ctx.raw) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b8fa8' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ ticks: {{ color: '#8b8fa8', callback: v => fmtReais(v) }}, grid: {{ color: 'rgba(255,255,255,0.08)' }} }}
      }}
    }}
  }});

  const {{ from: f2, to: t2 }} = getAnoRange();
  const uf2 = getHeaderUf();
  const partidoUfs2 = getPartidoUfs();
  const hasSpatialFilter = uf2 || activeFilters.regiao.length || activeFilters.uf.length || partidoUfs2;

  let tipoSrc;
  if (hasSpatialFilter && DATA.tipos_uf && DATA.tipos_uf.length) {{
    let items = DATA.tipos_uf.filter(d => d.ano >= f2 && d.ano <= t2);
    if (uf2) items = items.filter(d => d.uf === uf2);
    if (activeFilters.regiao.length) items = items.filter(d => activeFilters.regiao.includes(UF_REGIAO[d.uf]));
    if (activeFilters.uf.length) items = items.filter(d => activeFilters.uf.includes(d.uf));
    if (partidoUfs2) items = items.filter(d => partidoUfs2.has(d.uf));
    const byKey = {{}};
    items.forEach(d => {{
      const k = d.tipo + '|' + d.ano;
      if (!byKey[k]) byKey[k] = {{ tipo: d.tipo, ano: d.ano, empenhado: 0 }};
      byKey[k].empenhado += d.empenhado;
    }});
    tipoSrc = Object.values(byKey);
  }} else {{
    tipoSrc = DATA.tipos.filter(d => d.ano >= f2 && d.ano <= t2);
  }}

  const tiposUnicos = [...new Set(tipoSrc.map(d => d.tipo))];
  const anosUnicos = [...new Set(tipoSrc.map(d => d.ano))].sort();
  const datasets = tiposUnicos.map((tipo, i) => {{
    const dataByAno = {{}};
    tipoSrc.filter(d => d.tipo === tipo).forEach(d => {{ dataByAno[d.ano] = (dataByAno[d.ano] || 0) + d.empenhado; }});
    return {{
      label: tipo,
      data: anosUnicos.map(a => dataByAno[a] || 0),
      backgroundColor: SERIES_COLORS[i % SERIES_COLORS.length],
    }};
  }});

  if (charts.tipoStacked) charts.tipoStacked.destroy();
  charts.tipoStacked = new Chart(document.getElementById('chartTipoStacked'), {{
    type: 'bar',
    data: {{ labels: anosUnicos, datasets: datasets }},
    options: {{
      ...chartOpts,
      plugins: {{
        ...chartOpts.plugins,
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmtReais(ctx.raw) }} }}
      }},
      scales: {{
        x: {{ stacked: true, ticks: {{ color: '#8b8fa8' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ stacked: true, ticks: {{ color: '#8b8fa8', callback: v => fmtReais(v) }}, grid: {{ color: 'rgba(255,255,255,0.08)' }} }}
      }}
    }}
  }});
}}

// ── Municipios Table ────────────────────────────────────────

function filterMunicipios() {{
  const headerUf = getHeaderUf();
  const headerMun = getHeaderMun();
  const uf = document.getElementById('munUfFilter').value || headerUf;
  const search = document.getElementById('munSearch').value.toLowerCase() || (headerMun ? headerMun.toLowerCase() : '');
  const globalSearch = (document.getElementById('globalSearch').value || '').toLowerCase();
  let filtered = DATA.municipios;
  if (uf) filtered = filtered.filter(m => m.uf === uf);
  if (search) filtered = filtered.filter(m => m.municipio.toLowerCase().includes(search));
  if (globalSearch && !search) filtered = filtered.filter(m => m.municipio.toLowerCase().includes(globalSearch) || m.uf.toLowerCase().includes(globalSearch));
  if (activeFilters.regiao.length) {{
    filtered = filtered.filter(m => activeFilters.regiao.includes(UF_REGIAO[m.uf]));
  }}
  if (activeFilters.uf.length) {{
    filtered = filtered.filter(m => activeFilters.uf.includes(m.uf));
  }}
  const partidoUfs = getPartidoUfs();
  if (partidoUfs) {{
    filtered = filtered.filter(m => partidoUfs.has(m.uf));
  }}
  filtered.sort((a, b) => b.empenhado - a.empenhado);
  document.getElementById('countMun').textContent = filtered.length + ' municipios';
  filtered = filtered.slice(0, 100);
  const tbody = document.getElementById('munTbody');
  tbody.innerHTML = filtered.map(m => {{
    const exec = m.empenhado > 0 ? (m.pago / m.empenhado * 100).toFixed(1) : '0.0';
    return `<tr>
      <td>${{m.municipio}}</td>
      <td>${{m.uf}}</td>
      <td class="num">${{fmtReais(m.empenhado)}}</td>
      <td class="num">${{fmtReais(m.pago)}}</td>
      <td class="num">${{exec}}%</td>
      <td class="num">${{m.qtd}}</td>
    </tr>`;
  }}).join('');
}}

let sortCol = -1, sortAsc = true;
function sortMunTable(col) {{
  if (sortCol === col) sortAsc = !sortAsc;
  else {{ sortCol = col; sortAsc = col < 2; }}
  const keys = ['municipio', 'uf', 'empenhado', 'pago', null, 'qtd'];
  const key = keys[col];
  if (!key && col === 4) {{
    DATA.municipios.sort((a, b) => {{
      const ea = a.empenhado > 0 ? a.pago / a.empenhado : 0;
      const eb = b.empenhado > 0 ? b.pago / b.empenhado : 0;
      return sortAsc ? ea - eb : eb - ea;
    }});
  }} else if (key) {{
    DATA.municipios.sort((a, b) => {{
      if (typeof a[key] === 'string') return sortAsc ? a[key].localeCompare(b[key]) : b[key].localeCompare(a[key]);
      return sortAsc ? a[key] - b[key] : b[key] - a[key];
    }});
  }}
  filterMunicipios();
}}

// ── Export / Modal ───────────────────────────────────────────

let exportText = '';

function toggleInfoModal() {{
  document.getElementById('infoModal').classList.toggle('active');
}}

function openExportModal() {{
  const estados = getFilteredEstados();
  const totalEmp = estados.reduce((s,d) => s + d.empenhado, 0);
  const totalPago = estados.reduce((s,d) => s + d.pago, 0);
  const execPct = totalEmp > 0 ? (totalPago/totalEmp*100).toFixed(1) : '0.0';
  const totalQtd = estados.reduce((s,d) => s + d.qtd, 0);

  let t = '\\ud83c\\udfe6 *PIPPA Emendas Parlamentares*\\n';
  t += '\\ud83d\\udcc5 ' + new Date().toLocaleDateString('pt-BR') + '\\n\\n';
  t += '\\ud83d\\udcca *Resumo Geral*\\n';
  t += '\\ud83d\\udcb0 Empenhado: ' + fmtReais(totalEmp) + '\\n';
  t += '\\u2705 Pago: ' + fmtReais(totalPago) + '\\n';
  t += '\\ud83d\\udcca Execucao: ' + execPct + '%\\n';
  t += '\\ud83d\\udccb Emendas: ' + totalQtd.toLocaleString('pt-BR') + '\\n\\n';

  t += '\\ud83c\\udfc6 *TOP 5 ESTADOS:*\\n\\n';
  estados.slice(0, 5).forEach((d, i) => {{
    t += (i+1) + '. ' + d.uf + ' — ' + fmtReais(d.empenhado) + ' (exec: ' + d.execucao.toFixed(1) + '%)\\n';
  }});

  t += '\\n\\ud83c\\udfe2 *TOP 5 PARTIDOS:*\\n\\n';
  getFilteredPartidos().slice(0, 5).forEach((d, i) => {{
    t += (i+1) + '. ' + d.partido + ' — ' + fmtReais(d.empenhado) + '\\n';
  }});

  t += '\\n\\ud83d\\udd17 Fonte: Portal da Transparencia / Camara / Senado\\n';
  t += '\\ud83d\\udce1 PIPPA — Sebrae Nacional';

  exportText = t;
  document.getElementById('exportContent').textContent = t;
  document.getElementById('exportModal').classList.add('active');
}}

function closeExportModal() {{
  document.getElementById('exportModal').classList.remove('active');
}}

function copyExport() {{
  navigator.clipboard.writeText(exportText).then(() => showToast('Copiado para WhatsApp!')).catch(() => {{
    const ta = document.createElement('textarea');
    ta.value = exportText;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('Copiado!');
  }});
}}

function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}}

// ── Fetch API ───────────────────────────────────────────────

const API_BASE = window.location.protocol === 'file:' ? 'http://localhost:8050' : window.location.origin;

async function fetchData() {{
  const btn = document.getElementById('btnFetch');
  const overlay = document.getElementById('loadingOverlay');
  const loadText = document.getElementById('loadingText');
  const loadProg = document.getElementById('loadingProgress');

  btn.disabled = true;
  overlay.classList.add('active');

  loadText.textContent = 'Buscando emendas...';
  loadProg.textContent = 'Consultando dados processados';

  try {{
    const res = await fetch(API_BASE + '/api/dados');
    if (!res.ok) {{
      const err = await res.json();
      throw new Error(err.error || 'Erro ao buscar dados');
    }}

    loadText.textContent = 'Processando dados...';
    const freshData = await res.json();

    DATA.estados = freshData.estados || [];
    DATA.partidos = freshData.partidos || [];
    DATA.autores = freshData.autores || [];
    DATA.serie = freshData.serie || [];
    DATA.tipos = freshData.tipos || [];
    DATA.tipos_uf = freshData.tipos_uf || [];
    DATA.municipios = freshData.municipios || [];

    if (freshData._stats) {{
      document.getElementById('kpiAutores').textContent = (freshData._stats.total_autores_unicos || 0).toLocaleString('pt-BR');
    }}

    buildPartidoChips();
    applyAllFilters();
    showToast('Dados atualizados com sucesso!');

  }} catch (e) {{
    showToast('Erro: ' + e.message);
    console.error(e);
  }} finally {{
    overlay.classList.remove('active');
    btn.disabled = false;
  }}
}}

// ── Init ────────────────────────────────────────────────────

function buildPartidoChips() {{
  const partidos = [...new Set(DATA.autores.map(d => d.partido).filter(p => p && p !== '?'))].sort();
  const container = document.getElementById('partidoChips');
  container.innerHTML = '';
  partidos.forEach(p => {{
    const chip = document.createElement('span');
    chip.className = 'filter-chip';
    chip.dataset.filter = 'partido';
    chip.dataset.value = p;
    chip.textContent = p;
    chip.onclick = function() {{ toggleFilter(this); }};
    container.appendChild(chip);
  }});
}}

buildPartidoChips();
applyAllFilters();

</script>
</body>
</html>"""


def _render_uf_chips(ufs: list[str]) -> str:
    return "\n".join(
        f'            <span class="filter-chip" data-filter="uf" data-value="{uf}" onclick="toggleFilter(this)">{uf}</span>'
        for uf in ufs
    )
