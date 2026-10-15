import re

with open('pippa-quem-somos/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

pairs = [
    ('::-webkit-scrollbar-track{background:var(--bg)}', '::-webkit-scrollbar-track{background:var(--scrollbar-track)}'),
    ('::-webkit-scrollbar-thumb:hover{background:rgba(42,79,218,.08)}', '::-webkit-scrollbar-thumb:hover{background:var(--accent)}'),
    ('backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,.06)', 'backdrop-filter:blur(16px);border-bottom:1px solid var(--border)'),
    ('border:1px solid rgba(255,255,255,.08)', 'border:1px solid var(--border)'),
    ('.header-sep{width:1px;height:20px;background:rgba(255,255,255,.12);}', '.header-sep{width:1px;height:20px;background:var(--border);}'),
    ('.closing{text-align:center;padding:60px 0;border-top:1px solid rgba(255,255,255,.06);margin-top:64px;}', '.closing{text-align:center;padding:60px 0;border-top:1px solid var(--border);margin-top:64px;}'),
    ('.footer{text-align:center;padding:32px 48px;border-top:1px solid rgba(255,255,255,.04);font-size:11px;color:#334155;}', '.footer{text-align:center;padding:32px 48px;border-top:1px solid var(--border);font-size:11px;color:var(--text-muted);}'),
    ('.footer span{color:#475569;}', '.footer span{color:var(--text-muted);}'),
    ('.cycle-arrow{color:#475569;font-size:16px;}', '.cycle-arrow{color:var(--text-muted);font-size:16px;}'),
    ('color:#475569', 'color:var(--text-muted)'),
    ('color:#334155', 'color:var(--text-muted)'),
    ('border:2px solid rgba(42,79,218,.08)', 'border:2px solid var(--accent-ring)'),
    ('border:1px solid rgba(42,79,218,.08)', 'border:1px solid var(--accent-ring)'),
]

for old, new in pairs:
    html = html.replace(old, new)

# Add font-family to headings
html = html.replace('.hero-title{font-size:48px;font-weight:800;letter-spacing:-2px;', '.hero-title{font-family:var(--font-heading);font-size:48px;font-weight:800;letter-spacing:-2px;')
html = html.replace('.section-title{font-size:28px;font-weight:700;', '.section-title{font-family:var(--font-heading);font-size:28px;font-weight:700;')

# Header logo - remove gradient, use simple color
html = re.sub(
    r'\.header-logo\{[^}]+\}',
    '.header-logo{font-size:22px;font-weight:800;color:var(--accent);letter-spacing:-1px;}',
    html, count=1
)

# Add theme toggle
TOGGLE_BTN = '<button class="theme-toggle" onclick="toggleTheme()" aria-label="Alternar tema"><svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg><svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg></button>'

if 'toggleTheme' not in html:
    # Wrap header-back and toggle in a controls div
    html = html.replace(
        '  <a href="../pippa-portal/index.html" class="header-back">',
        '  <div style="display:flex;align-items:center;gap:8px">\n    ' + TOGGLE_BTN + '\n    <a href="../pippa-portal/index.html" class="header-back">'
    )
    html = html.replace(
        '    Voltar ao Portal\n  </a>\n</header>',
        '    Voltar ao Portal\n    </a>\n  </div>\n</header>'
    )
    # Add toggleTheme JS
    html = html.replace(
        '</body>',
        '<script>function toggleTheme(){var h=document.documentElement,n=h.getAttribute("data-theme")==="dark"?"light":"dark";h.setAttribute("data-theme",n);localStorage.setItem("pippa-theme",n)}</script>\n</body>'
    )

with open('pippa-quem-somos/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('OK')
