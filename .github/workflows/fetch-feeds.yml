import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import html
import time
from datetime import datetime, timezone

FEEDS = [
    # Birding
    {"name": "BirdWatching Daily",    "url": "https://www.birdwatchingdaily.com/feed/"},
    {"name": "10,000 Birds",          "url": "https://www.10000birds.com/feed"},
    {"name": "Birds & Blooms",        "url": "https://www.birdsandblooms.com/feed/"},
    {"name": "All About Birds",       "url": "https://www.allaboutbirds.org/news/feed/"},
    {"name": "BirdWatching HQ",       "url": "https://birdwatchinghq.com/feed/"},
    # Nature / Environment
    {"name": "The Guardian Wildlife", "url": "https://www.theguardian.com/environment/wildlife/rss"},
    {"name": "EarthSky",              "url": "https://earthsky.org/feed/"},
    {"name": "Hakai Magazine",        "url": "https://hakaimagazine.com/feed/"},
    {"name": "Mercury News Wildlife", "url": "https://www.mercurynews.com/tag/wildlife/feed/"},
    {"name": "Outside Online",        "url": "https://www.outsideonline.com/feed/"},
    # Science
    {"name": "Smithsonian Magazine",  "url": "https://www.smithsonianmag.com/rss/latest_articles/"},
    {"name": "Science News",          "url": "https://www.sciencenews.org/feed"},
    {"name": "New Scientist",         "url": "https://www.newscientist.com/feed/home/"},
    {"name": "Phys.org Zoology",      "url": "https://phys.org/rss-feed/biology-news/zoology/"},
    {"name": "Live Science",          "url": "https://www.livescience.com/feeds/all"},
    {"name": "Cornell Conservation",  "url": "https://www.birds.cornell.edu/home/feed/"},
]

NS = {
    "media":   "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc":      "http://purl.org/dc/elements/1.1/",
    "atom":    "http://www.w3.org/2005/Atom",
}

MAX_STORIES = 500   # cap on total archive size
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; iBirdFeedBot/1.0; "
        "+https://github.com/goofy166/ibird-feeds)"
    )
}


def fix_entities(text):
    if not text:
        return ""
    return html.unescape(text)


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_image(item, channel=None):
    """Try multiple strategies to pull the best image URL from an RSS item."""

    # 1. media:content / media:thumbnail
    for tag in ("media:content", "media:thumbnail"):
        el = item.find(tag, NS)
        if el is not None:
            url = el.get("url") or el.text
            if url and url.startswith("http"):
                return url.strip()

    # 2. enclosure
    enc = item.find("enclosure")
    if enc is not None:
        url = enc.get("url", "")
        if url.startswith("http") and any(
            ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ):
            return url.strip()

    # 3. content:encoded – grab first <img src="...">
    ce = item.find("content:encoded", NS)
    if ce is not None and ce.text:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', ce.text, re.I)
        if m:
            url = m.group(1)
            if url.startswith("http"):
                return url.strip()

    # 4. description – same img search
    desc = item.find("description")
    if desc is not None and desc.text:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc.text, re.I)
        if m:
            url = m.group(1)
            if url.startswith("http"):
                return url.strip()

    # 5. channel-level image
    if channel is not None:
        img_el = channel.find("image/url")
        if img_el is not None and img_el.text:
            return img_el.text.strip()

    return ""


def fetch_feed(feed_info):
    url = feed_info["url"]
    source = feed_info["name"]
    stories = []

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()

        root = ET.fromstring(raw)

        # Detect RSS vs Atom
        if root.tag == "rss" or root.tag.endswith("}rss"):
            channel = root.find("channel")
            if channel is None:
                return stories
            items = channel.findall("item")
            for item in items[:10]:
                title_el = item.find("title")
                link_el  = item.find("link")
                desc_el  = item.find("description")
                pub_el   = item.find("pubDate")

                title   = fix_entities(title_el.text if title_el is not None else "")
                link    = (link_el.text or "").strip() if link_el is not None else ""
                summary = strip_html(fix_entities(desc_el.text if desc_el is not None else ""))[:180]
                pub     = (pub_el.text or "").strip() if pub_el is not None else ""
                image   = extract_image(item, channel)

                if title and link:
                    stories.append({
                        "title":   title,
                        "link":    link,
                        "summary": summary,
                        "pubDate": pub,
                        "image":   image,
                        "source":  source,
                    })

        else:
            # Atom feed
            atom_ns = "http://www.w3.org/2005/Atom"
            entries = root.findall(f"{{{atom_ns}}}entry")
            for entry in entries[:10]:
                title_el = entry.find(f"{{{atom_ns}}}title")
                link_el  = entry.find(f"{{{atom_ns}}}link")
                sum_el   = (entry.find(f"{{{atom_ns}}}summary") or
                            entry.find(f"{{{atom_ns}}}content"))
                pub_el   = (entry.find(f"{{{atom_ns}}}published") or
                            entry.find(f"{{{atom_ns}}}updated"))

                title   = fix_entities(title_el.text if title_el is not None else "")
                link    = (link_el.get("href", "") if link_el is not None else "")
                summary = strip_html(fix_entities(sum_el.text if sum_el is not None else ""))[:180]
                pub     = (pub_el.text or "").strip() if pub_el is not None else ""
                image   = extract_image(entry)

                if title and link:
                    stories.append({
                        "title":   title,
                        "link":    link,
                        "summary": summary,
                        "pubDate": pub,
                        "image":   image,
                        "source":  source,
                    })

    except Exception as e:
        print(f"[WARN] Failed to fetch {source} ({url}): {e}")

    return stories


def load_existing(path="feeds.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("stories", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main():
    existing = load_existing()
    existing_urls = {s["link"] for s in existing}

    new_stories = []
    for feed in FEEDS:
        fetched = fetch_feed(feed)
        for story in fetched:
            if story["link"] not in existing_urls:
                new_stories.append(story)
                existing_urls.add(story["link"])
        time.sleep(1)

    # Prepend newest stories (LIFO), cap at MAX_STORIES
    all_stories = new_stories + existing
    all_stories = all_stories[:MAX_STORIES]

    if not all_stories:
        print("[ERROR] No stories fetched at all — aborting.")
        raise SystemExit(1)

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count":   len(all_stories),
        "stories": all_stories,
    }

    with open("feeds.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    added = len(new_stories)
    total = len(all_stories)
    print(f"[OK] Added {added} new stories. Archive total: {total}.")


if __name__ == "__main__":
    main()
