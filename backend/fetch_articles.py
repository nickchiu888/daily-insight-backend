from datetime import datetime, timezone
from pathlib import Path
import json
import os

import feedparser
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
PUBLIC_DIR = ROOT_DIR / "public"
SOURCES_YML = BACKEND_DIR / "sources.yml"
OUTPUT_JSON = PUBLIC_DIR / "articles.json"


def load_sources():
    with open(SOURCES_YML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def parse_entry(source, entry):
    # 發佈時間
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    published_at = dt.isoformat()

    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

    categories = []
    tags = getattr(entry, "tags", []) or []
    for tag in tags:
        term = getattr(tag, "term", None)
        if term:
            categories.append(term)

    article_id = f"{source['id']}::{getattr(entry, 'id', getattr(entry, 'link', ''))}"

    return {
        "id": article_id,
        "source_id": source["id"],
        "source_name": source["name"],
        "title": getattr(entry, "title", "(無標題)"),
        "url": getattr(entry, "link", ""),
        "summary_raw": summary,
        "categories_raw": categories,
        "published_at": published_at,
    }


def fetch_source(source):
    print(f"Fetching: {source['name']} ({source['rss']})")
    feed = feedparser.parse(source["rss"])

    max_items = source.get("max_items", 30)
    articles = []
    for entry in feed.entries[:max_items]:
        article = parse_entry(source, entry)
        articles.append(article)
    return articles


def main():
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    sources = load_sources()
    all_articles = []

    for src in sources:
        try:
            articles = fetch_source(src)
            all_articles.extend(articles)
        except Exception as e:
            print(f"[ERROR] fetch {src['id']} failed: {e}")

    all_articles.sort(key=lambda a: a["published_at"], reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(sources),
        "article_count": len(all_articles),
        "articles": all_articles,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_articles)} articles to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
