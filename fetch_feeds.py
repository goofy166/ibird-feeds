python#!/usr/bin/env python3
"""
Fetches birding RSS feeds directly and saves them as feeds.json.
Runs as a GitHub Action every hour.
"""

import json
import re
import time
import random
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    {"url": "https://www.birdwatchingdaily.com/feed/", "name": "BirdWatching Daily", "color": 0},
    {"url": "https://10000birds.com/feed",             "name": "10,000 Birds",        "color": 1},
    {"url": "https://www.birdsandblooms.com/feed/",    "name": "Birds & Blooms",      "color": 2},
]

HTML_ENTITIES = [
    ("&nbsp;","&#160;"),("&copy;","&#169;"),("&mdash;","&#8212;"),
    ("&ndash;","&#8211;"),("&hellip;","&#8230;"),("&ldquo;","&#8220;"),
    ("&rdquo;","&#8221;"),("&lsquo;","&#8216;"),("&rsquo;","&#8217;"),
    ("&trade;","&#8482;"),("&reg;","&#174;"),("&deg;","&#176;"),
]

def fix_entities(raw):
    for bad, good in HTML_ENTITIES:
        raw = raw.replace(bad, good)
    return raw

def strip_html(html):
    html = re.sub(r"<[^>]+>", "", html)
    for entity, char in [("&amp;","&"),("&lt;","<"),("&gt;",">"),
                          ("&quot;",'"'),("&#39;","'"),("&nbsp;"," ")]:
        html = html.replace(entity, char)
    return re.sub(r"\s+", " ", html).strip()

def extract_image(text):
    m = re.search(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))[^"\']*["\']', text, re.I)
    if m:
        return m.group(1)
    m = re.search(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)', text, re.I)
    return m.group(0) if m else None

def fetch_feed(feed):
    req = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "Mozilla/5.0 (compatible; ibird-feeds/2.0)"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")

    raw = fix_entities(raw)

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        # Strip any remaining bad entities with regex as fallback
        raw = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)\w+;', ' ', raw)
        root = ET.fromstring(raw)

    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    if not items:
        raise ValueError("No items found in feed")

    item = random.choice(items[:5])

    def get_text(*tags):
        for tag in tags:
            child = item.find(tag)
            if child is not None and child.text:
                return child.text.strip()
            for prefix in ["{http://purl.org/dc/elements/1.1/}", "{http://www.w3.org/2005/Atom}"]:
                child = item.find(prefix + tag)
                if child is not None and child.text:
                    return child.text.strip()
        return ""

    title    = get_text("title")
    link_el  = item.find("link")
    link     = get_text("link") or (link_el.get("href","") if link_el is not None else "")
    pub_date = get_text("pubDate", "published", "updated")
    content  = get_text("{http://purl.org/rss/1.0/modules/content/}encoded", "description", "summary", "content")

    image = extract_image(content)
    if not image:
        media = item.find("{http://search.yahoo.com/mrss/}thumbnail")
        if media is not None:
            image = media.get("url", "")
    if not image:
        enclosure = item.find("enclosure")
        if enclosure is not None:
            enc_url = enclosure.get("url", "")
            if re.search(r"\.(jpg|jpeg|png|webp|gif)", enc_url, re.I):
                image = enc_url

    return {
        "name":    feed["name"],
        "color":   feed["color"],
        "title":   title or "Untitled",
        "summary": strip_html(content)[:180],
        "link":    link or "#",
        "date":    pub_date,
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
        time.sleep(1)

    output = {
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stories": stories,
    }

    with open("feeds.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(stories)}/{len(FEEDS)} stories to feeds.json")
    if not stories:
        raise SystemExit("No stories fetched — failing the action so we notice")

if __name__ == "__main__":
    main()
