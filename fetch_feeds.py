import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import html
import time
import random
from datetime import datetime, timezone

# ── Fallback image pools (public domain via Wikimedia Commons) ───────────────
FALLBACK_IMAGES = {
    "butterflies": [
        "https://upload.wikimedia.org/wikipedia/commons/e/e7/Monarch_Butterfly_Danaus_plexippus_Mating_Carrots_3000px.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/9d/Vanessa_cardui_09.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/47/Papilio_glaucus_top.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/14/Actias_luna_MHNT.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/a5/Blue_morpho_butterfly.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/71/Red_Admiral_Butterfly_UV_1.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/54/Gulf_fritillary_agraulis_vanillae.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/b/b3/Papilio_polyxenes_asterius.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/3/3e/Spicebush_Swallowtail.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/0/04/Danaus_plexippus_on_Asclepias_tuberosa.jpg",
    ],
    "insects": [
        "https://upload.wikimedia.org/wikipedia/commons/4/4d/Apis_mellifera_flying.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/d/d0/Sympetrum_flaveolum_-_side_%28aka%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/Praying_mantis_india.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/8/8a/Coccinella_magnifica01.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/41/Common_European_Bumblebee.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/3/39/GrasshopperSpirit.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/6/6e/Chrysopa_perla_2.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/99/Argiope_aurantia_020.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/b/b1/Bombus_pensylvanicus_foraging.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/e/e0/Firefly_in_the_night.jpg",
    ],
    "wildlife": [
        "https://upload.wikimedia.org/wikipedia/commons/0/05/RedFoxInSnow.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/5f/Coast_Miwok_at_Point_Reyes.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/a7/Grizzly_bear_fishing.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/b/b9/Above_Gotham.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/12/White_shark.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/9b/Grizzlybear_fishing.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/3/3b/Florida_panther.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/6/6d/Good_Food_Display_-_NCI_Visuals_Online.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/1b/Wolf_picture2.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/e/e0/SNH_Freshwater_Habitat.jpg",
    ],
    "birds": [
        "https://upload.wikimedia.org/wikipedia/commons/4/45/Eopsaltria_australis_-_Mogo_Campground.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/ae/Goldfinch_on_a_branch.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/1e/Phalacrocorax_carbo_-Wexford%2C_Ireland-8.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/b/ba/Juvenile_Raggiana_Bird-of-Paradise.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/f/f8/Psephotus_haematonotus_male.jpg",
    ],
}

def get_fallback_image(category):
    pool = FALLBACK_IMAGES.get(category, [])
    return random.choice(pool) if pool else ""


# ── Feed definitions ─────────────────────────────────────────────────────────
FEEDS = [
    # Birds (0-4)
    {"url": "https://www.birdwatchingdaily.com/feed/",
     "name": "BWatching Daily",  "base_cat": "birds",    "color": 0},
    {"url": "https://www.10000birds.com/feed",
     "name": "10,000 Birds",     "base_cat": "birds",    "color": 1},
    {"url": "https://www.birdsandblooms.com/feed/",
     "name": "Birds & Blooms",   "base_cat": "birds",    "color": 2},
    {"url": "https://www.allaboutbirds.org/news/feed/",
     "name": "All About Birds",  "base_cat": "birds",    "color": 3},
    {"url": "https://birdwatchinghq.com/feed/",
     "name": "BWatching HQ",     "base_cat": "birds",    "color": 4},
    # Wildlife / Nature (5-9)
    {"url": "https://www.theguardian.com/environment/wildlife/rss",
     "name": "Guardian",         "base_cat": "wildlife", "color": 5},
    {"url": "https://earthsky.org/feed/",
     "name": "EarthSky",         "base_cat": "wildlife", "color": 6},
    {"url": "https://hakaimagazine.com/feed/",
     "name": "Hakai",            "base_cat": "wildlife", "color": 7},
    {"url": "https://www.mercurynews.com/tag/wildlife/feed/",
     "name": "Mercury News",     "base_cat": "wildlife", "color": 8},
    {"url": "https://www.outsideonline.com/feed/",
     "name": "Outside Online",   "base_cat": "wildlife", "color": 9},
    # Science — keyword-routed to insects or butterflies (10-15)
    {"url": "https://www.smithsonianmag.com/rss/latest_articles/",
     "name": "Smithsonian",      "base_cat": "science",  "color": 10},
    {"url": "https://www.sciencenews.org/feed",
     "name": "Science News",     "base_cat": "science",  "color": 11},
    {"url": "https://www.newscientist.com/feed/home/",
     "name": "New Scientist",    "base_cat": "science",  "color": 12},
    {"url": "https://phys.org/rss-feed/biology-news/zoology/",
     "name": "Phys.org",         "base_cat": "science",  "color": 13},
    {"url": "https://www.livescience.com/feeds/all",
     "name": "Live Science",     "base_cat": "science",  "color": 14},
    {"url": "https://www.birds.cornell.edu/home/feed/",
     "name": "Cornell",          "base_cat": "science",  "color": 15},
]

# Mapping for migrating old-format stories (source → name, base_cat, color)
SOURCE_TO_META = {
    "BirdWatching Daily":    ("birds",    "BWatching Daily", 0),
    "10,000 Birds":          ("birds",    "10,000 Birds",    1),
    "Birds & Blooms":        ("birds",    "Birds & Blooms",  2),
    "All About Birds":       ("birds",    "All About Birds", 3),
    "BirdWatching HQ":       ("birds",    "BWatching HQ",    4),
    "The Guardian Wildlife": ("wildlife", "Guardian",        5),
    "EarthSky":              ("wildlife", "EarthSky",        6),
    "Hakai Magazine":        ("wildlife", "Hakai",           7),
    "Mercury News Wildlife": ("wildlife", "Mercury News",    8),
    "Outside Online":        ("wildlife", "Outside Online",  9),
    "Smithsonian Magazine":  ("science",  "Smithsonian",     10),
    "Science News":          ("science",  "Science News",    11),
    "New Scientist":         ("science",  "New Scientist",   12),
    "Phys.org Zoology":      ("science",  "Phys.org",        13),
    "Live Science":          ("science",  "Live Science",    14),
    "Cornell Conservation":  ("science",  "Cornell",         15),
}

NS = {
    "media":   "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc":      "http://purl.org/dc/elements/1.1/",
}

MAX_STORIES = 500
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; iBirdFeedBot/1.0; "
        "+https://github.com/goofy166/ibird-feeds)"
    )
}

BUTTERFLY_KW = [
    "butterfly", "butterflies", "moth", "moths", "lepidoptera",
    "caterpillar", "caterpillars", "monarch", "pollinator", "pollinators",
    "milkweed", "swallowtail", "fritillary",
]
INSECT_KW = [
    "insect", "insects", "bee", "bees", "wasp", "wasps", "ant", "ants",
    "beetle", "beetles", "fly", "flies", "bug", "bugs", "cricket", "crickets",
    "dragonfly", "grasshopper", "cockroach", "termite", "mosquito",
    "firefly", "fireflies", "mantis", "cicada", "aphid", "larva", "larvae",
    "spider", "arachnid",
]


def resolve_category(base_cat, title, summary):
    if base_cat != "science":
        return base_cat
    text = (title + " " + summary).lower()
    if any(kw in text for kw in BUTTERFLY_KW):
        return "butterflies"
    if any(kw in text for kw in INSECT_KW):
        return "insects"
    return "insects"


def fix_entities(text):
    return html.unescape(text) if text else ""


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date_to_iso(raw):
    if not raw:
        return ""
    raw = raw.strip()
    if "T" in raw and (raw.endswith("Z") or "+" in raw[-6:]):
        return raw[:19] + "Z"
    import email.utils
    try:
        t = email.utils.parsedate_to_datetime(raw)
        return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    return raw[:20]


def extract_image(item, channel=None):
    for tag in ("media:content", "media:thumbnail"):
        el = item.find(tag, NS)
        if el is not None:
            url = el.get("url") or el.text
            if url and url.startswith("http"):
                return url.strip()
    enc = item.find("enclosure")
    if enc is not None:
        url = enc.get("url", "")
        if url.startswith("http") and any(
            ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ):
            return url.strip()
    ce = item.find("content:encoded", NS)
    if ce is not None and ce.text:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', ce.text, re.I)
        if m and m.group(1).startswith("http"):
            return m.group(1).strip()
    desc = item.find("description")
    if desc is not None and desc.text:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc.text, re.I)
        if m and m.group(1).startswith("http"):
            return m.group(1).strip()
    if channel is not None:
        img_el = channel.find("image/url")
        if img_el is not None and img_el.text:
            return img_el.text.strip()
    return ""


def build_story(title, link, summary, date, image, feed_info, fetched_at):
    cat = resolve_category(feed_info["base_cat"], title, summary)
    if not image:
        image = get_fallback_image(cat)
    return {
        "title":      title,
        "link":       link,
        "summary":    summary,
        "date":       date,
        "image":      image,
        "name":       feed_info["name"],
        "category":   cat,
        "color":      feed_info["color"],
        "fetched_at": fetched_at,
    }


def fetch_feed(feed_info):
    url = feed_info["url"]
    stories = []
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()

        root = ET.fromstring(raw)

        if root.tag == "rss" or root.tag.endswith("}rss"):
            channel = root.find("channel")
            if channel is None:
                return stories
            for item in channel.findall("item")[:10]:
                title   = fix_entities((item.findtext("title") or "").strip())
                link    = (item.findtext("link") or "").strip()
                summary = strip_html(fix_entities(item.findtext("description") or ""))[:180]
                date    = parse_date_to_iso(item.findtext("pubDate") or "")
                image   = extract_image(item, channel)
                if title and link:
                    stories.append(build_story(title, link, summary, date, image, feed_info, fetched_at))
        else:
            atom = "http://www.w3.org/2005/Atom"
            for entry in root.findall(f"{{{atom}}}entry")[:10]:
                title_el = entry.find(f"{{{atom}}}title")
                link_el  = entry.find(f"{{{atom}}}link")
                sum_el   = (entry.find(f"{{{atom}}}summary") or entry.find(f"{{{atom}}}content"))
                pub_el   = (entry.find(f"{{{atom}}}published") or entry.find(f"{{{atom}}}updated"))
                title   = fix_entities((title_el.text or "").strip() if title_el is not None else "")
                link    = (link_el.get("href", "") if link_el is not None else "")
                summary = strip_html(fix_entities(sum_el.text if sum_el is not None else ""))[:180]
                date    = parse_date_to_iso(pub_el.text if pub_el is not None else "")
                image   = extract_image(entry)
                if title and link:
                    stories.append(build_story(title, link, summary, date, image, feed_info, fetched_at))

    except Exception as e:
        print(f"[WARN] Failed to fetch {feed_info['name']} ({url}): {e}")

    return stories


def migrate_story(story):
    """Upgrade old-format stories (source/pubDate) to new format."""
    if "category" in story:
        # Already new format — just ensure image fallback
        if not story.get("image"):
            story["image"] = get_fallback_image(story.get("category", "wildlife"))
        return story

    source = story.get("source", "")
    meta   = SOURCE_TO_META.get(source)
    if meta:
        base_cat, name, color = meta
    else:
        base_cat, name, color = "wildlife", source, 5

    title   = story.get("title", "")
    summary = story.get("summary", "")
    cat     = resolve_category(base_cat, title, summary)
    image   = story.get("image", "") or get_fallback_image(cat)
    date    = parse_date_to_iso(story.get("pubDate", ""))

    return {
        "title":      title,
        "link":       story.get("link", ""),
        "summary":    summary,
        "date":       date,
        "image":      image,
        "name":       name,
        "category":   cat,
        "color":      color,
        "fetched_at": story.get("fetched_at", ""),
    }


def load_existing(path="feeds.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stories = data.get("stories", [])
        return [migrate_story(s) for s in stories]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main():
    existing       = load_existing()
    existing_urls  = {s["link"] for s in existing}
    new_stories    = []

    for feed in FEEDS:
        fetched = fetch_feed(feed)
        for story in fetched:
            if story["link"] not in existing_urls:
                new_stories.append(story)
                existing_urls.add(story["link"])
        time.sleep(1)

    all_stories = (new_stories + existing)[:MAX_STORIES]

    if not all_stories:
        print("[ERROR] No stories fetched — aborting.")
        raise SystemExit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "updated":     now,
        "updated_utc": now,
        "count":       len(all_stories),
        "stories":     all_stories,
    }

    with open("feeds.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] Added {len(new_stories)} new stories. Archive: {len(all_stories)} total.")


if __name__ == "__main__":
    main()
