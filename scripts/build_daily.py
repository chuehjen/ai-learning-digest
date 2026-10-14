#!/usr/bin/env python3
"""Build a source-linked daily AI news index from public RSS/Atom feeds.

This deliberately does not invent article summaries: the message uses publisher
headlines, source names, and original links. The selection is automated.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
BJT = ZoneInfo("Asia/Shanghai")
ATOM = "{http://www.w3.org/2005/Atom}"
SOURCES = [
    ("OpenAI", "https://openai.com/news/rss.xml", "primary"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "primary"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "primary"),
    ("AWS ML", "https://aws.amazon.com/blogs/machine-learning/feed/", "primary"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "press"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "press"),
]


def cleaned(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def canonical_link(link: str) -> str:
    parts = urlsplit(link.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def published_date(text: str) -> datetime | None:
    if not text:
        return None
    try:
        value = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_feed(content: bytes, source: str, kind: str) -> list[dict]:
    root = ET.fromstring(content)
    entries = root.findall("./channel/item")
    atom = not entries
    if atom:
        entries = root.findall(f"{ATOM}entry")
    result = []
    for entry in entries:
        if atom:
            title = entry.findtext(f"{ATOM}title") or ""
            link = next(
                (node.get("href", "") for node in entry.findall(f"{ATOM}link")
                 if node.get("rel", "alternate") == "alternate"),
                "",
            )
            date_text = entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated") or ""
        else:
            title = entry.findtext("title") or ""
            link = entry.findtext("link") or ""
            date_text = entry.findtext("pubDate") or ""
        title = cleaned(title)
        link = canonical_link(link)
        date = published_date(date_text)
        if title and link and date:
            result.append({
                "title": title,
                "url": link,
                "source": source,
                "source_type": kind,
                "published_at_utc": date.isoformat().replace("+00:00", "Z"),
                "_published": date,
            })
    return result


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AI-Learning-Digest/1.0 (+https://github.com/chuehjen/ai-learning-digest)"},
    )
    with urllib.request.urlopen(request, timeout=18) as response:
        return response.read(4_000_000)


def previous_urls(today: str) -> set[str]:
    urls = set()
    for file in (ROOT / "archive" / "daily").glob("*.json"):
        if file.stem >= today:
            continue
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            urls.update(item["url"] for item in data.get("items", []))
        except (OSError, ValueError, KeyError):
            continue
    return urls


def choose_items(items: list[dict], now: datetime, seen: set[str]) -> list[dict]:
    cutoff = now - timedelta(days=7)
    unique = {}
    for item in items:
        if cutoff <= item["_published"] <= now + timedelta(hours=2):
            unique.setdefault(item["url"], item)
    promotional = re.compile(r"\b(ticket|discount|save \d+%|register now|sponsor|giveaway)\b", re.I)
    candidates = sorted(
        (item for item in unique.values() if not promotional.search(item["title"])),
        key=lambda x: x["_published"],
        reverse=True,
    )
    # Prefer source announcements, then reporting. Only consider previously
    # published links after exhausting all new stories, even from busy feeds.
    unseen = [item for item in candidates if item["url"] not in seen]
    repeated = [item for item in candidates if item["url"] in seen]
    selected = []
    per_source = {}
    for pool in (unseen, repeated):
        for source_type, target, source_limit in (("primary", 3, 1), ("press", 5, 1), ("any", 5, 2)):
            for item in pool:
                if len(selected) >= target:
                    break
                if source_type != "any" and item["source_type"] != source_type:
                    continue
                if item in selected or per_source.get(item["source"], 0) >= source_limit:
                    continue
                selected.append(item)
                per_source[item["source"]] = per_source.get(item["source"], 0) + 1
    return selected


def build(now: datetime) -> dict:
    date_bjt = now.astimezone(BJT).date().isoformat()
    items = []
    errors = []
    for source, url, kind in SOURCES:
        try:
            items.extend(parse_feed(fetch_feed(url), source, kind))
        except (OSError, ET.ParseError, ValueError) as error:
            errors.append(f"{source}: {type(error).__name__}")
    selected = choose_items(items, now, previous_urls(date_bjt))
    if len(selected) < 5:
        raise RuntimeError(f"Only {len(selected)} usable items; feed errors: {', '.join(errors)}")
    for item in selected:
        del item["_published"]
    display_date = now.astimezone(BJT).strftime("%m月%d日")
    lines = [f"【AI 每日动态｜{display_date}】"]
    for number, item in enumerate(selected, start=1):
        lines.extend((f"{number}. {item['title']} — {item['source']}", item["url"]))
    lines.append("英文原文为主；标题与链接来自原发布方，供你挑选精读。")
    return {
        "schema_version": 1,
        "kind": "daily",
        "date_bjt": date_bjt,
        "generated_at_utc": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "message": "\n".join(lines),
        "items": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    data = build(now)
    output = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(output)
    else:
        (ROOT / "archive" / "daily").mkdir(parents=True, exist_ok=True)
        (ROOT / "daily.json").write_text(output, encoding="utf-8")
        (ROOT / "archive" / "daily" / f"{data['date_bjt']}.json").write_text(output, encoding="utf-8")
        print(f"Wrote daily digest for {data['date_bjt']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"Digest generation failed: {error}", file=sys.stderr)
        sys.exit(1)
