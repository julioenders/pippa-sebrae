"""
Aplica Brandbook Sebrae nos hub pages PIPPA.
Transforma o template dark-only Inter para light/dark com Plus Jakarta Sans + Figtree.
"""
import re, sys, os

BRANDBOOK_TOKENS = """:root{
  --azul-sebrae:#2a4fda;--atlantico:#0b2574;--ceu:#65b7fb;--offwhite:#eff3ee;
  --font-heading:'Plus Jakarta Sans',sans-serif;--font-body:'Figtree',sans-serif;
  --bg:#eff3ee;--surface:#ffffff;--surface2:#f5f7f4;
  --border:rgba(0,0,0,.1);--border-hover:rgba(42,79,218,.35);
  --text:#1a1a1a;--text-muted:#6b7280;--text-accent:#2a4fda;
  --accent:#2a4fda;--accent-hover:#1e3fb8;--accent-light:rgba(42,79,218,.08);
  --emerald:#61b466;--purple:#be64e3;--blue:#2a4fda;--amber:#f39d72;--cyan:#65b7fb;--red:#e0565d;--pink:#ff80c8;--teal:#61b466;
  --emerald-light:#9ff0bd;--purple-light:#be64e3;
  --secondary:#6b7280;--muted:#6b7280;
  --highlight-bg:rgba(42,79,218,.06);--accent-ring:rgba(42,79,218,.12);
  --shadow:0 1px 3px rgba(0,0,0,.06);--shadow-md:0 4px 12px rgba(0,0,0,.08);
  --scrollbar-track:#eff3ee;--scrollbar-thumb:rgba(42,79,218,.2);
  --radius:12px;
}
[data-theme="dark"]{
  --bg:#080f1e;--surface:#0f1a2e;--surface2:#162038;
  --border:rgba(255,255,255,.08);--border-hover:rgba(101,183,251,.35);
  --text:#eff3ee;--text-muted:#8b9dc3;--text-accent:#65b7fb;
  --accent:#65b7fb;--accent-hover:#90ccfd;--accent-light:rgba(101,183,251,.08);
  --secondary:#8b9dc3;--muted:#8b9dc3;
  --highlight-bg:rgba(101,183,251,.08);--accent-ring:rgba(101,183,251,.12);
  --shadow:0 1px 3px rgba(0,0,0,.3);--shadow-md:0 4px 12px rgba(0,0,0,.4);
  --scrollbar-track:#080f1e;--scrollbar-thumb:rgba(42,79,218,.3);
}"""

GOOGLE_FONTS = '<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">'

ANTIFLASH = """<script>(function(){var t=localStorage.getItem('pippa-theme');if(!t)t=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';document.documentElement.setAttribute('data-theme',t)})()</script>"""

THEME_TOGGLE_BTN = """<button class="theme-toggle" onclick="toggleTheme()" aria-label="Alternar tema"><svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg><svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg></button>"""

THEME_TOGGLE_CSS = """.theme-toggle{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;background:transparent;border:1px solid var(--border);border-radius:8px;cursor:pointer;color:var(--text-muted);transition:all .2s;}
.theme-toggle:hover{border-color:var(--border-hover);color:var(--text-accent);background:var(--highlight-bg);}
.theme-toggle svg{width:18px;height:18px;}
.icon-sun{display:none;}
[data-theme="dark"] .icon-sun{display:block;}
[data-theme="dark"] .icon-moon{display:none;}"""

TOGGLE_JS = """<script>function toggleTheme(){var h=document.documentElement,n=h.getAttribute('data-theme')==='dark'?'light':'dark';h.setAttribute('data-theme',n);localStorage.setItem('pippa-theme',n)}</script>"""

def transform(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Replace Google Fonts link
    html = re.sub(
        r'<link href="https://fonts\.googleapis\.com/css2\?family=Inter[^"]*" rel="stylesheet">',
        GOOGLE_FONTS,
        html
    )

    # 2. Add anti-flash script after fonts link (if not already present)
    if 'pippa-theme' not in html:
        html = html.replace(GOOGLE_FONTS, GOOGLE_FONTS + '\n' + ANTIFLASH)

    # 3. Replace :root block
    html = re.sub(
        r':root\{[^}]+\}',
        BRANDBOOK_TOKENS.split('\n', 1)[0],  # we'll do this differently
        html,
        count=1
    )
    # Actually, let me do it properly - find the :root block and replace it
    # Reset and do it properly
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Replace Google Fonts
    html = re.sub(
        r'<link href="https://fonts\.googleapis\.com/css2\?family=Inter[^"]*" rel="stylesheet">',
        GOOGLE_FONTS,
        html
    )

    # 2. Add anti-flash
    if 'pippa-theme' not in html:
        html = html.replace(GOOGLE_FONTS, GOOGLE_FONTS + '\n' + ANTIFLASH)

    # 3. Replace :root{...} with Brandbook tokens
    root_pattern = re.compile(r':root\{[^}]+\}', re.DOTALL)
    html = root_pattern.sub(BRANDBOOK_TOKENS, html, count=1)

    # 4. Update body font
    html = re.sub(
        r"body\{font-family:'Inter'[^;]*;",
        "body{font-family:var(--font-body);",
        html
    )
    # Update body background
    html = re.sub(
        r"background:var\(--bg\);color:var\(--text\)",
        "background:var(--bg);color:var(--text);transition:background .3s,color .3s",
        html
    )
    html = re.sub(
        r"background:#0b1120;color:#c8d6e5",
        "background:var(--bg);color:var(--text);transition:background .3s,color .3s",
        html
    )

    # 5. Update header gradient from dark-only to Brandbook
    html = re.sub(
        r"background:linear-gradient\(135deg,#0d1b2a 0%,var\(--bg\) 100%\)",
        "background:linear-gradient(45deg,var(--atlantico),var(--azul-sebrae))",
        html
    )
    # Header border
    html = re.sub(
        r"border-bottom:2px solid rgba\(16,185,129,\.2\)",
        "border-bottom:2px solid var(--border)",
        html
    )
    html = re.sub(
        r"border-bottom:2px solid rgba\(168,85,247,\.2\)",
        "border-bottom:2px solid var(--border)",
        html
    )

    # 6. Update header radial gradient
    html = re.sub(
        r"background:radial-gradient\(ellipse 80% 60%[^)]*rgba\(16,185,129,\.08\),transparent 70%\)",
        "background:radial-gradient(ellipse 80% 60% at 50% 30%,rgba(42,79,218,.08),transparent 70%)",
        html
    )
    html = re.sub(
        r"background:radial-gradient\(ellipse 80% 60%[^)]*rgba\(168,85,247,\.08\),transparent 70%\)",
        "background:radial-gradient(ellipse 80% 60% at 50% 30%,rgba(42,79,218,.08),transparent 70%)",
        html
    )

    # 7. Update header-logo gradient (PIPPA text)
    html = re.sub(
        r"background:linear-gradient\(135deg,#10b981,#34d399\);-webkit-background-clip:text;-webkit-text-fill-color:transparent",
        "color:var(--ceu)",
        html
    )
    html = re.sub(
        r"background:linear-gradient\(135deg,var\(--emerald\),var\(--emerald-light\)\);-webkit-background-clip:text;-webkit-text-fill-color:transparent",
        "color:#ffffff",
        html
    )
    html = re.sub(
        r"background:linear-gradient\(135deg,var\(--purple\),var\(--purple-light\)\);-webkit-background-clip:text;-webkit-text-fill-color:transparent",
        "color:#ffffff",
        html
    )

    # 8. Make header text colors use vars (for dark/light)
    html = re.sub(r"color:#64748b", "color:var(--text-muted)", html)
    html = re.sub(r"color:#94a3b8", "color:var(--text-muted)", html)
    html = re.sub(r"color:#e2e8f0", "color:var(--text)", html)
    html = re.sub(r"color:#c8d6e5", "color:var(--text)", html)
    html = re.sub(r"color:#8b9dc3", "color:var(--text-muted)", html)

    # 9. Update backgrounds
    html = re.sub(r"background:#0b1120", "background:var(--bg)", html)
    html = re.sub(r"background:var\(--surface\)", "background:var(--surface)", html)
    html = re.sub(r"background:rgba\(11,17,32,\.92\)", "background:var(--bg)", html)
    html = re.sub(r"background:rgba\(17,24,39,\.6\)", "background:var(--surface)", html)

    # 10. Update portal-btn colors to use Brandbook
    html = re.sub(
        r"border:1px solid rgba\(16,185,129,\.3\);color:var\(--emerald-light\)",
        "border:1px solid var(--border);color:var(--text-accent)",
        html
    )
    html = re.sub(
        r"border:1px solid rgba\(168,85,247,\.3\);color:var\(--purple-light\)",
        "border:1px solid var(--border);color:var(--text-accent)",
        html
    )
    html = re.sub(
        r"background:rgba\(16,185,129,\.1\)",
        "background:var(--highlight-bg)",
        html
    )
    html = re.sub(
        r"background:rgba\(168,85,247,\.1\)",
        "background:var(--highlight-bg)",
        html
    )

    # 11. Update card hover colors
    html = re.sub(
        r"border-color:rgba\(16,185,129,\.3\)",
        "border-color:var(--border-hover)",
        html
    )
    html = re.sub(
        r"border-color:rgba\(168,85,247,\.3\)",
        "border-color:var(--border-hover)",
        html
    )
    html = re.sub(
        r"border-color:rgba\(16,185,129,\.25\)",
        "border-color:var(--border-hover)",
        html
    )
    html = re.sub(
        r"border-color:rgba\(168,85,247,\.25\)",
        "border-color:var(--border-hover)",
        html
    )

    # 12. Header logo bg
    html = re.sub(
        r"background:rgba\(16,185,129,\.12\);border:1px solid rgba\(16,185,129,\.25\)",
        "background:rgba(42,79,218,.12);border:1px solid rgba(42,79,218,.25)",
        html
    )
    html = re.sub(
        r"background:rgba\(168,85,247,\.12\);border:1px solid rgba\(168,85,247,\.25\)",
        "background:rgba(42,79,218,.12);border:1px solid rgba(42,79,218,.25)",
        html
    )
    html = re.sub(
        r"color:var\(--emerald-light\)",
        "color:var(--text-accent)",
        html
    )

    # 13. Scrollbar
    html = re.sub(
        r"background:rgba\(16,185,129,\.25\)",
        "background:var(--scrollbar-thumb)",
        html
    )
    html = re.sub(
        r"background:rgba\(168,85,247,\.25\)",
        "background:var(--scrollbar-thumb)",
        html
    )
    html = re.sub(
        r"::-webkit-scrollbar-track\{background:transparent\}",
        "::-webkit-scrollbar-track{background:var(--scrollbar-track)}",
        html
    )

    # 14. Stat box bg
    html = re.sub(
        r"background:rgba\(255,255,255,\.03\)",
        "background:var(--surface)",
        html
    )

    # 15. Intro box bg
    html = re.sub(
        r"background:rgba\(16,185,129,\.04\);border:1px solid rgba\(16,185,129,\.1\)",
        "background:var(--highlight-bg);border:1px solid var(--accent-ring)",
        html
    )
    html = re.sub(
        r"background:rgba\(168,85,247,\.04\);border:1px solid rgba\(168,85,247,\.1\)",
        "background:var(--highlight-bg);border:1px solid var(--accent-ring)",
        html
    )

    # 16. Footer
    html = re.sub(
        r"border-top:1px solid var\(--border\);color:var\(--muted\)",
        "border-top:1px solid var(--border);color:var(--text-muted)",
        html
    )

    # 17. Section title border
    html = re.sub(
        r"\.section-title\{([^}]*)\}",
        lambda m: ".section-title{" + m.group(1).replace("border-bottom:1px solid var(--border)", "border-bottom:1px solid var(--border);color:var(--text)") + "}",
        html
    )

    # 18. Add theme toggle CSS before </style>
    if 'theme-toggle' not in html:
        html = html.replace('</style>', THEME_TOGGLE_CSS + '\n</style>')

    # 19. Add theme toggle button to header-controls
    if 'toggleTheme' not in html:
        html = re.sub(
            r'(<div class="header-controls">)',
            r'\1\n      ' + THEME_TOGGLE_BTN,
            html
        )

    # 20. Add toggleTheme JS
    if 'function toggleTheme' not in html:
        html = html.replace('</body>', TOGGLE_JS + '\n</body>')

    # 21. Card border and background
    html = re.sub(
        r"border:1px solid rgba\(255,255,255,\.06\)",
        "border:1px solid var(--border)",
        html
    )
    html = re.sub(
        r"background:rgba\(255,255,255,\.04\)",
        "background:var(--highlight-bg)",
        html
    )

    # 22. Card-icon backgrounds with inline styles need to be updated
    # purple-light card-icon bg
    html = re.sub(
        r'background:rgba\(168,85,247,\.12\);color:var\(--purple-light\)',
        'background:rgba(42,79,218,.08);color:var(--text-accent)',
        html
    )
    html = re.sub(
        r'background:rgba\(79,140,255,\.12\);color:var\(--blue\)',
        'background:rgba(42,79,218,.08);color:var(--text-accent)',
        html
    )
    html = re.sub(
        r'background:rgba\(6,182,212,\.12\);color:var\(--cyan\)',
        'background:rgba(101,183,251,.08);color:var(--ceu)',
        html
    )

    # Card-feat inline styles
    html = re.sub(
        r'background:rgba\(168,85,247,\.1\);color:var\(--purple-light\)',
        'background:var(--highlight-bg);color:var(--text-accent)',
        html
    )
    html = re.sub(
        r'background:rgba\(6,182,212,\.1\);color:var\(--cyan\)',
        'background:rgba(101,183,251,.08);color:var(--ceu)',
        html
    )

    # Card-sub inline styles
    html = re.sub(
        r'style="color:var\(--purple-light\)"',
        'style="color:var(--text-accent)"',
        html
    )
    html = re.sub(
        r'style="color:var\(--blue\)"',
        'style="color:var(--text-accent)"',
        html
    )

    # 23. Update header h1 to use white color (since gradient bg)
    html = re.sub(
        r'\.header h1\{([^}]*)\}',
        '.header h1{font-size:1.35rem;font-weight:700;letter-spacing:-.5px;color:#ffffff}',
        html
    )

    # 24. Header-sub color
    html = re.sub(
        r'\.header-sub\{[^}]*\}',
        '.header-sub{font-size:.78rem;color:rgba(255,255,255,.6);margin-top:.2rem}',
        html
    )

    # 25. Header logo color
    html = re.sub(
        r'color:var\(--text-accent\)"\s*>UPP<',
        'color:#ffffff">UPP<',
        html
    )

    # 26. Stat-box val colors - keep original accent colors but make them theme-aware
    # card-stat val colors that are emerald
    html = re.sub(
        r'style="color:var\(--emerald-light\)"',
        'style="color:var(--text-accent)"',
        html
    )

    # 27. Header backdrop-filter for sticky headers
    if 'backdrop-filter' in html and '.header{' in html:
        html = re.sub(
            r'(\.header\{[^}]*?)background:rgba\([^)]+\)',
            r'\1background:var(--bg)',
            html
        )

    # 28. Highlight box green colors
    html = re.sub(r"border-left:3px solid #10b981", "border-left:3px solid var(--accent)", html)
    html = re.sub(r"color:#a7f3d0", "color:var(--text)", html)

    # 29. Section divider
    html = re.sub(
        r"background:linear-gradient\(90deg,#10b981,#34d399\)",
        "background:linear-gradient(90deg,var(--azul-sebrae),var(--ceu))",
        html
    )

    # 30. Hero gradient (quem-somos style)
    html = re.sub(
        r"background:linear-gradient\(135deg,#10b981 0%,#34d399 40%,#6ee7b7 100%\);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text",
        "color:var(--text-accent)",
        html
    )

    # 31. Green accent colors
    html = re.sub(r"color:#10b981", "color:var(--text-accent)", html)
    html = re.sub(r"color:#34d399", "color:var(--text-accent)", html)
    html = re.sub(r"color:#6ee7b7", "color:var(--ceu)", html)

    # 32. Box-shadow dark
    html = re.sub(
        r"box-shadow:0 8px 32px rgba\(0,0,0,\.3\)",
        "box-shadow:var(--shadow-md)",
        html
    )

    # 33. Header font updates for headings
    html = re.sub(r"font-family:'Inter','Segoe UI',system-ui,sans-serif", "font-family:var(--font-body)", html)
    html = re.sub(r"font-family:'Inter',sans-serif", "font-family:var(--font-body)", html)

    # 34. Make header h1 span use white since bg is now blue gradient
    # The span with PIPPA text should be white
    # Already handled by step 7 replacements

    # 35. Fix any remaining rgba(16,185,129,...) emerald references
    html = re.sub(r"rgba\(16,185,129,\.12\)", "rgba(42,79,218,.08)", html)
    html = re.sub(r"rgba\(16,185,129,\.06\)", "var(--highlight-bg)", html)
    html = re.sub(r"rgba\(16,185,129,\.1\)", "var(--accent-ring)", html)
    html = re.sub(r"rgba\(16,185,129,\.08\)", "rgba(42,79,218,.08)", html)

    # 36. Fix remaining purple rgba
    html = re.sub(r"rgba\(168,85,247,\.12\)", "rgba(42,79,218,.08)", html)
    html = re.sub(r"rgba\(168,85,247,\.06\)", "var(--highlight-bg)", html)
    html = re.sub(r"rgba\(168,85,247,\.1\)", "var(--accent-ring)", html)

    # 37. Dark background for header (since it uses gradient)
    # Make sure header text is white
    html = re.sub(r"color:var\(--text-muted\)}", "color:var(--text-muted)}", html)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  OK: {filepath}")


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = sys.argv[1:] if len(sys.argv) > 1 else [
        'pippa-atuacao-upp/index.html',
        'pippa-legislativo/index.html',
        'pippa-projeto-2027/index.html',
    ]
    for t in targets:
        path = os.path.join(base, t)
        if os.path.exists(path):
            print(f"Transformando: {t}")
            transform(path)
        else:
            print(f"  NAO ENCONTRADO: {path}")
