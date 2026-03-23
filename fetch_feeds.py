#!/usr/bin/env python3
"""
Fetches birding RSS feeds via rss2json and saves them as feeds.json.
Runs as a GitHub Action every hour — the HTML page reads feeds.json
from raw.githubusercontent.com instead of hitting rss2json directly.
"""

import json
import re
import time
import urllib.parse
import urllib.request

RSS2JSON = "https://api.rss2json.com/v1/api.json?rss_url="

FEEDS = [
    {"url": "https://www.birdwatchingdaily.com/feed/", "name": "BirdWatching Daily", "color": 0},
    {"url": "https://10000birds.com/feed",             "name": "10,000 Birds",        "color": 1},
    {"url": "https://www.birdsandblooms.com/feed/",    "name": "Birds & Blooms",      "color": 2},
]


def strip_html(html):
    html = re.sub(r"<[^>]+>", "", html)
    for entity, char in [("&amp;","&"),("&lt;","<"),("&gt;",">"),
                          ("&quot;",'"'),("&#39;","'"),("&nbsp;"," ")]:
        html = html.replace(entity, char)
    return re.sub(r"\s+", " ", html).strip()


def extract_image(html):
    """Pull first jpg/png/webp src from any <img> tag."""
    m = re.search(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))[^"\']*["\']', html, re.I)
    return m.group(1) if m else None


def fetch_feed(feed):
    url = RSS2JSON + urllib.parse.quote(feed["url"])
    req = urllib.request.Request(url, headers={"User-Agent": "ibird-feeds/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    if data.get("status") != "ok" or not data.get("items"):
        raise ValueError(f"Bad status: {data.get('status')} / {data.get('message')}")

    # Pick a random story from the top 5
    import random
    pool = data["items"][:5]
    item = random.choice(pool)

    raw_content = item.get("content") or ""
    raw_desc    = item.get("description") or ""
    body_html   = raw_content if len(raw_content) > len(raw_desc) else raw_desc

    enclosure_url = (item.get("enclosure") or {}).get("link", "")
    image = (
        item.get("thumbnail")
        or (enclosure_url if re.search(r"\.(jpg|jpeg|png|webp|gif)", enclosure_url, re.I) else None)
        or extract_image(raw_content)
        or extract_image(raw_desc)
    )

    return {
        "name":    feed["name"],
        "color":   feed["color"],
        "title":   (item.get("title") or "").strip() or "Untitled",
        "summary": strip_html(body_html)[:180],
        "link":    item.get("link") or "#",
        "date":    item.get("pubDate") or "",
        "image":   image or "",
    }


def main():
    stories = []
    for feed in FEEDS:
        try:
            story = fetch_feed(feed)
            stories.append(story)
            print(f"  ✓ {feed['name']}: {story['title'][:60]}")
        except Exception as e:
            print(f"  ✗ {feed['name']}: {e}")
        time.sleep(1)   # be polite between requests

    output = {
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stories": stories,
    }

    with open("feeds.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(stories)}/{len(FEEDS)} stories to feeds.json")


if __name__ == "__main__":
    main()
