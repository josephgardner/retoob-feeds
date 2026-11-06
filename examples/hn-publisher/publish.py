#!/usr/bin/env python3
"""Bounded HN public-API connector; emits static Retoob feeds, no credentials."""
import argparse
import concurrent.futures
import html
import importlib.util
import json
import pathlib
import re
import shutil
import tempfile
import urllib.request
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('static_publisher', ROOT / 'examples/static-publisher/publish.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
API = 'https://hacker-news.firebaseio.com/v0/'
LISTS = {'top': 'topstories', 'new': 'newstories'}
MAX_BODY = 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('HN API redirects are not accepted')


def get_json(path):
    # Only internally constructed fixed-origin API paths. Never fetch story URLs.
    if not re.fullmatch(r'(topstories|newstories|item/[1-9][0-9]*)\.json', path):
        raise ValueError('Unsupported HN API path')
    request = urllib.request.Request(API + path, headers={'User-Agent': 'Retoob-HN/1.0 (+https://github.com/josephgardner/retoob-feeds)', 'Accept': 'application/json'})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ValueError('HN API response exceeds 1 MiB')
        return json.loads(body)


def youtube_id(raw):
    if not isinstance(raw, str) or len(raw) > 4096:
        return None
    try:
        u = urlsplit(raw)
        if u.scheme not in ('http', 'https') or u.username or u.password or u.port not in (None, 80, 443):
            return None
        if u.hostname in ('youtu.be', 'www.youtu.be'):
            candidate = u.path.lstrip('/')
        elif u.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
            if u.path == '/watch':
                values = parse_qs(u.query).get('v', [])
                if len(values) != 1:
                    return None
                candidate = values[0]
            else:
                match = re.fullmatch(r'/(shorts|live|embed)/([A-Za-z0-9_-]{11})/?', u.path)
                candidate = match[2] if match else ''
        else:
            return None
        return candidate if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate) else None
    except ValueError:
        return None


def entry(item, item_id):
    if item is None:
        return None
    if not isinstance(item, dict) or item.get('id') != item_id:
        raise ValueError('HN item identity mismatch')
    if item.get('deleted') or item.get('dead') or item.get('type') != 'story':
        return None
    video = youtube_id(item.get('url'))
    if video is None:
        return None
    title = item.get('title')
    stamp = item.get('time')
    if not isinstance(title, str) or not title.strip() or len(title) > 2000 or type(stamp) is not int or not 0 < stamp < 253402300800:
        raise ValueError('Invalid HN video story metadata')
    title = html.unescape(title)
    title = ''.join(c for c in title if ord(c) >= 32).strip()
    if not title:
        raise ValueError('Empty HN story title')
    published = datetime.fromtimestamp(stamp, timezone.utc).isoformat().replace('+00:00', 'Z')
    return {'id': f'hn-{item_id}', 'videoId': video, 'title': title, 'savedAt': published,
            'communitySource': {'name': 'Hacker News', 'url': 'https://news.ycombinator.com/',
                                'itemId': str(item_id), 'discussionUrl': f'https://news.ycombinator.com/item?id={item_id}'}}


def collect(limit=500, fetch=get_json, workers=6):
    if not 1 <= limit <= 500 or not 1 <= workers <= 8:
        raise ValueError('limit must be 1–500; workers must be 1–8')
    windows = {}
    for name, endpoint in LISTS.items():
        ids = fetch(endpoint + '.json')
        if not isinstance(ids, list) or len(ids) > 500 or any(type(i) is not int or i <= 0 for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('Invalid HN discovery window')
        windows[name] = ids[:limit]
    ids = sorted({i for values in windows.values() for i in values})
    # Share item fetches between windows; fail the entire refresh on any error.
    # Never persist fetched titles or retain old content on an explicit deletion.
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        items = dict(zip(ids, pool.map(lambda i: fetch(f'item/{i}.json'), ids)))
    entries = {i: entry(items[i], i) for i in ids}
    return {name: [entries[i] for i in values if entries[i] is not None] for name, values in windows.items()}


def generate_site(site, ledger, state, collections, base_url, schema):
    next_state = json.loads(json.dumps(state))
    feeds = []
    for name, entries in collections.items():
        list_id = f'hn-{name}-videos'
        source = {'baseUrl': base_url, 'listId': list_id, 'publicationEpoch': f'{list_id}-20261105',
                  'title': f'Hacker News — {"top-story" if name == "top" else "newest-story"} videos',
                  'description': f'YouTube links in the current HN {name} discovery window (up to 500 stories), ordered by submission date. Imported mentions, not curator endorsements. Refreshed every 6 hours; not a complete video archive.',
                  'entries': entries}
        feed, new_ledger = publisher.generate(source, state.get(name))
        publisher.write_site(site, feed, schema)
        next_state[name] = new_ledger
        feeds.append(feed)
    (site / 'index.html').write_text(publisher.page('Hacker News video feeds', '<ul>' + ''.join(f'<li><a href="{html.escape(f["home_page_url"], quote=True)}">{html.escape(f["title"])}</a> — {len(f["items"])} videos</li>' for f in feeds) + '</ul>'))
    ledger.write_bytes(publisher.encoded(next_state))
    return feeds


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', required=True, type=pathlib.Path)
    p.add_argument('--output', required=True, type=pathlib.Path, help='Empty staging directory; publish only after all validation succeeds')
    p.add_argument('--base-url', default='https://algoplay.com/retoob-feeds')
    p.add_argument('--schema', required=True, type=pathlib.Path)
    p.add_argument('--initialize', action='store_true')
    args = p.parse_args()
    if args.initialize == args.state.exists():
        p.error('Use --initialize only for a new publication, then retain the ledger')
    if args.output.exists() and any(args.output.iterdir()):
        p.error('Output must be empty')
    if args.output.resolve() == args.state.resolve() or args.output.resolve() in args.state.resolve().parents:
        p.error('State must remain outside the public site')
    schema = json.loads(args.schema.read_text())
    if schema['$id'] != publisher.SCHEMA_URL:
        p.error('Use the pinned local profile-1 schema')
    state = json.loads(args.state.read_text()) if args.state.exists() else {}
    collections = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as temporary:
        staged = pathlib.Path(temporary)
        ledger = staged / 'ledger.json'
        feeds = generate_site(staged / 'site', ledger, state, collections, args.base_url, schema)
        # A successful fetch of every bounded item is required before either
        # snapshot or ledger is replaced. The caller validates and deploys both.
        args.output.mkdir(exist_ok=True)
        for child in (staged / 'site').iterdir():
            if child.is_dir():
                shutil.copytree(child, args.output / child.name)
            else:
                shutil.copy2(child, args.output / child.name)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        pending = args.state.with_suffix('.tmp')
        pending.write_bytes(ledger.read_bytes())
        pending.replace(args.state)
    for feed in feeds:
        print(f'{feed["feed_url"]}: {len(feed["items"])} cards, revision {feed["_retoob"]["revision"]}')


if __name__ == '__main__':
    main()
