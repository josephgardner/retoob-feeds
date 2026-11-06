#!/usr/bin/env python3
"""Offline, independently implemented manual-collection connector (Python stdlib).

Writes a complete static site and a content-free revision ledger. No Retoob
imports, database, network, account, or provider metadata API is used.
"""
import argparse
import hashlib
import html
import json
import pathlib
import re
from datetime import datetime
from urllib.parse import urlsplit

SCHEMA_URL = "https://algoplay.com/retoob-feeds/schemas/retoob-feed-v1.schema.json"
MAX_REVISION = 9007199254740991


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("IDs must contain 1–128 letters, digits, underscores or hyphens")
    return value


def text(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError("Expected nonempty plain text")
    return value


def instant(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("savedAt must be a UTC RFC3339 timestamp ending in Z")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def increment(value):
    if type(value) is not int or not 0 <= value < MAX_REVISION:
        raise ValueError("Invalid or exhausted revision; start a new publication epoch")
    return value + 1


def generate(source, state=None):
    origin = source["baseUrl"].rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("baseUrl must be a public HTTPS URL without credentials, query, or fragment")
    list_id, epoch = identifier(source["listId"]), identifier(source["publicationEpoch"])
    identity = [origin, list_id, epoch]
    if state is not None and state["identity"] != identity:
        raise ValueError("Ledger belongs to another origin, list, or epoch; use a new ledger with --initialize")
    ledger = json.loads(json.dumps(state)) if state is not None else {"identity": identity, "cards": {}, "revision": 0}
    home = f"{origin}/{list_id}/"
    groups, seen = {}, set()
    if len(source["entries"]) > 1000:
        raise ValueError("This small connector accepts at most 1000 recommendations")
    for entry in source["entries"]:
        entry_id = identifier(entry["id"])
        if entry_id in seen:
            raise ValueError("Duplicate recommendation ID")
        seen.add(entry_id)
        video = entry["videoId"]
        if not isinstance(video, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
            raise ValueError("Expected an 11-character YouTube videoId")
        instant(entry["savedAt"])
        offset = entry.get("startSeconds", 0)
        if type(offset) is not int or not 0 <= offset <= 2147483647:
            raise ValueError("Invalid startSeconds")
        recommendation = {"id": entry_id, "kind": "manual", "recommendationBasis": "explicit", "createdAt": entry["savedAt"], "recommendedAt": entry["savedAt"], "startSeconds": offset}
        if "communitySource" in entry:
            community = entry["communitySource"]
            def public_url(value):
                parsed = urlsplit(value)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                    raise ValueError("Community provenance URLs must use HTTPS without credentials")
                return value
            recommendation = {"id": entry_id, "kind": "community", "recommendationBasis": "mention",
                              "publisher": {"name": text(community["name"]), "url": public_url(community["url"])},
                              "sourceUrl": public_url(community["url"]), "upstreamItemId": text(community["itemId"]),
                              "discussionUrl": public_url(community["discussionUrl"]),
                              "upstreamPublishedAt": {"value": entry["savedAt"], "precision": "exact"}, "startSeconds": offset}
        if "note" in entry:
            recommendation["note"] = text(entry["note"])
        groups.setdefault(video, []).append((entry, recommendation))
    items = []
    for video, entries in groups.items():
        entries.sort(key=lambda pair: (instant(pair[0]["savedAt"]), pair[0]["id"]), reverse=True)
        selected = entries[0][0]
        permalink = f"{home}items/{video}/"
        watch = f"https://www.youtube.com/watch?v={video}"
        item = {"id": permalink, "url": permalink, "external_url": watch, "title": text(selected["title"]), "content_text": "\n\n".join("Curator note: " + r["note"] for _, r in entries if "note" in r), "date_published": selected["savedAt"], "_retoob": {"version": 1, "itemId": video, "contentKey": f"youtube:{video}", "sortAt": selected["savedAt"], "dateBasis": "recommendation", "playback": {"mode": "external", "provider": "youtube", "url": watch, "startSeconds": selected.get("startSeconds", 0)}, "recommendations": [r for _, r in entries]}}
        if "communitySource" in selected:
            item["_retoob"]["dateBasis"] = "publication"
            item["content_text"] = "\n\n".join(
                f'Imported {r["publisher"]["name"]} mention: {r["discussionUrl"]}. Not a verified endorsement.'
                for _, r in entries)
        item["image"] = f"https://i.ytimg.com/vi/{video}/hqdefault.jpg"
        card_hash = digest(item)
        old = ledger["cards"].get(video, {"revision": 0})
        revision = old["revision"] if old.get("hash") == card_hash else increment(old["revision"])
        ledger["cards"][video] = {"hash": card_hash, "revision": revision}
        item["_retoob"]["revision"] = revision
        items.append(item)
    items.sort(key=lambda item: (instant(item["_retoob"]["sortAt"]), item["_retoob"]["itemId"]), reverse=True)
    feed = {"version": "https://jsonfeed.org/version/1.1", "title": text(source["title"]), "description": text(source["description"]), "home_page_url": home, "feed_url": home + "feed.json", "_retoob": {"version": 1, "schema": SCHEMA_URL, "listId": list_id, "publicationEpoch": epoch, "semantics": "snapshot", "itemCount": len(items)}, "items": items}
    feed_hash = digest(feed)
    revision = ledger["revision"] if ledger.get("hash") == feed_hash else increment(ledger["revision"])
    ledger.update(hash=feed_hash, revision=revision)
    feed["_retoob"]["revision"] = revision
    if len(encoded(feed)) > 10 * 1024 * 1024:
        raise ValueError("Feed exceeds 10 MiB")
    return feed, ledger


def page(title, body, feed_url=None):
    discovery = f'<link rel="alternate" type="application/feed+json" href="{html.escape(feed_url, quote=True)}">' if feed_url else ""
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(title)}</title>{discovery}<main><h1>{html.escape(title)}</h1>{body}</main></html>\n'


def write_site(output, feed, schema):
    output.mkdir(parents=True, exist_ok=True)
    home = output / feed["_retoob"]["listId"]
    home.mkdir(exist_ok=True)
    (home / "feed.json").write_bytes(encoded(feed))
    links = []
    for item in feed["items"]:
        card = home / "items" / item["_retoob"]["itemId"]
        card.mkdir(parents=True, exist_ok=True)
        body = f'<p>{html.escape(item["content_text"])}</p><p><a href="{html.escape(item["external_url"], quote=True)}">Watch on YouTube</a></p>'
        (card / "index.html").write_text(page(item["title"], body))
        links.append(f'<li><a href="{html.escape(item["url"], quote=True)}">{html.escape(item["title"])}</a></li>')
    body = f'<p>{html.escape(feed["description"])}</p><p><a href="feed.json">Subscribe to this video feed</a></p><ul>{"".join(links)}</ul>'
    (home / "index.html").write_text(page(feed["title"], body, feed["feed_url"]))
    (output / "index.html").write_text(page("Algoplay video feeds", f'<p><a href="{html.escape(feed["home_page_url"], quote=True)}">{html.escape(feed["title"])}</a></p>'))
    (output / "schemas").mkdir(exist_ok=True)
    (output / "schemas/retoob-feed-v1.schema.json").write_bytes(encoded(schema))
    (output / ".nojekyll").write_text("")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("--state", required=True, type=pathlib.Path, help="Private content-free ledger, outside the published directory")
    parser.add_argument("--output", required=True, type=pathlib.Path, help="New, empty deployment directory")
    parser.add_argument("--schema", required=True, type=pathlib.Path, help="Pinned local profile-1 schema; never fetched from input")
    parser.add_argument("--initialize", action="store_true", help="First publication only; creates a ledger for the explicit new epoch")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Use an empty output directory so removed item pages cannot survive")
    if args.output.resolve() in args.state.resolve().parents or args.output.resolve() == args.state.resolve():
        parser.error("State must be outside the public output")
    if args.initialize == args.state.exists():
        parser.error("Use --initialize only for the first publication; retain the ledger for every update")
    schema = json.loads(args.schema.read_text())
    if schema["$id"] != SCHEMA_URL:
        parser.error("Pinned schema $id does not match the profile-1 schema URI")
    feed, state = generate(json.loads(args.source.read_text()), json.loads(args.state.read_text()) if args.state.exists() else None)
    write_site(args.output, feed, schema)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    pending = args.state.with_suffix(".tmp")
    pending.write_bytes(encoded(state))
    pending.replace(args.state)
    print(f'Generated {feed["feed_url"]}: {len(feed["items"])} cards, revision {feed["_retoob"]["revision"]}')


if __name__ == "__main__":
    main()
