"""Busca noticias sobre Reforma Tributaria via Google News RSS.

Salva resultado como JSON para consumo pelo dashboard estático.
Roda via GitHub Actions (sem restrição CORS server-side).
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

SEARCH_QUERIES = [
    '"reforma tributária"',
    '"IBS" OR "CBS" OR "imposto seletivo"',
    '"IVA dual" OR "split payment" OR "comitê gestor IBS"',
    '"Simples Nacional" reforma OR tributária',
]

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "news_cache.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PIPPA-Bot/1.0)"}


def fetch_rss(query: str, days: int = 14) -> list[dict]:
    encoded = quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"  ERRO ao buscar '{query}': {e}")
        return []

    root = ET.fromstring(xml_bytes)
    cutoff = datetime.utcnow() - timedelta(days=days)
    items = []

    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        if title_el is None:
            continue

        raw_title = title_el.text or ""
        link = link_el.text if link_el is not None else ""
        pub_date = pub_el.text if pub_el is not None else ""

        parts = raw_title.rsplit(" - ", 1)
        title = parts[0].strip() if len(parts) > 1 else raw_title
        source = parts[1].strip() if len(parts) > 1 else "Desconhecida"

        items.append({
            "fullTitle": raw_title,
            "title": title,
            "source": source,
            "link": link,
            "pubDate": pub_date,
        })

    return items


def main():
    print(f"Buscando noticias - {datetime.utcnow().isoformat()}Z")
    all_items = []
    seen = set()

    for i, q in enumerate(SEARCH_QUERIES, 1):
        print(f"  Query {i}/{len(SEARCH_QUERIES)}: {q}")
        items = fetch_rss(q)
        for item in items:
            key = item["title"][:60].lower()
            if key not in seen:
                seen.add(key)
                all_items.append(item)
        print(f"    {len(items)} resultados, {len(all_items)} unicos total")

    output = {
        "updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(all_items),
        "items": all_items,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo {len(all_items)} noticias em {OUTPUT}")


if __name__ == "__main__":
    main()
