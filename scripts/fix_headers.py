"""Fix header element colors for all transformed hub/dashboard pages.
Header has blue gradient bg, so portal-btn, header-logo, theme-toggle need white colors.
"""
import os, sys

files = sys.argv[1:] if len(sys.argv) > 1 else []

for filepath in files:
    if not os.path.exists(filepath):
        print(f'  SKIP: {filepath}')
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    changes = 0

    # header-logo bg+color for blue gradient header
    old = 'background:rgba(42,79,218,.12);border:1px solid rgba(42,79,218,.25);border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;color:var(--text-accent)'
    new = 'background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;color:#ffffff'
    if old in html:
        html = html.replace(old, new)
        changes += 1

    # Also for 22px header-logo
    old2 = 'font-size:22px;font-weight:800;color:var(--text-accent)'
    new2 = 'font-size:22px;font-weight:800;color:#ffffff'
    if '.header-logo{' in html and old2 in html:
        html = html.replace(old2, new2)

    # portal-btn - white on blue gradient
    old = '.portal-btn{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;font-size:.75rem;font-weight:600;text-decoration:none;border:1px solid var(--border);color:var(--text-accent);transition:all .2s}'
    new = '.portal-btn{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;font-size:.75rem;font-weight:600;text-decoration:none;border:1px solid rgba(255,255,255,.25);color:rgba(255,255,255,.85);transition:all .2s}'
    if old in html:
        html = html.replace(old, new)
        changes += 1

    old = '.portal-btn:hover{background:var(--highlight-bg)}'
    new = '.portal-btn:hover{background:rgba(255,255,255,.1);color:#ffffff}'
    if old in html:
        html = html.replace(old, new)

    # theme-toggle - white on blue gradient
    old = '.theme-toggle{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;background:transparent;border:1px solid var(--border);border-radius:8px;cursor:pointer;color:var(--text-muted);transition:all .2s;}'
    new = '.theme-toggle{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;background:transparent;border:1px solid rgba(255,255,255,.25);border-radius:8px;cursor:pointer;color:rgba(255,255,255,.85);transition:all .2s;}'
    if old in html:
        html = html.replace(old, new)
        changes += 1

    old = '.theme-toggle:hover{border-color:var(--border-hover);color:var(--text-accent);background:var(--highlight-bg);}'
    new = '.theme-toggle:hover{border-color:rgba(255,255,255,.5);color:#ffffff;background:rgba(255,255,255,.1);}'
    if old in html:
        html = html.replace(old, new)

    # card stat vals with inline style
    html = html.replace('style="color:var(--text-accent)"', 'style="color:var(--accent)"')

    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  FIXED ({changes}): {filepath}')
    else:
        print(f'  NO CHANGES: {filepath}')
