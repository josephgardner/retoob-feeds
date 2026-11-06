#!/usr/bin/env python3
"""Replace only HN-owned public directories after successful feed validation."""
import html
import json
import pathlib
import shutil
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
source = pathlib.Path(sys.argv[1])
docs = ROOT / 'docs'
for name in ('hn-top-videos', 'hn-new-videos'):
    incoming = source / name
    if not (incoming / 'feed.json').is_file():
        raise SystemExit('Incomplete HN staging site')
for name in ('hn-top-videos', 'hn-new-videos'):
    destination = docs / name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source / name, destination)
stamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
status = {'lastSuccessfulRefreshAt': stamp, 'scheduledIntervalHours': 6}
(docs / 'hn-status.json').write_text(json.dumps(status, indent=2) + '\n')
links = []
for path in sorted(docs.glob('*/feed.json')):
    feed = json.loads(path.read_text())
    links.append(f'<li><a href="{html.escape(feed["home_page_url"], quote=True)}">{html.escape(feed["title"])}</a> — {len(feed["items"])} videos. <a href="{html.escape(feed["feed_url"], quote=True)}">Feed JSON</a></li>')
(docs / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Algoplay video feeds</title><main><h1>Algoplay video feeds</h1><p>Paste a Feed JSON URL into Retoob on your TV.</p><ul>' + ''.join(links) + f'</ul><p>HN last successfully refreshed: {stamp}. Scheduled every six hours; delays are possible. These are imported mentions, not verified endorsements.</p></main></html>\n')
print('Replaced HN streams; preserved all other feeds')
