#!/usr/bin/env python3
"""Build compatibility HTML routes only in the Pages artifact, not in the Git tree."""
import argparse
import html
import json
import pathlib
import re
import shutil
from urllib.parse import urlsplit, urlencode


def prepare(source, output):
    if output.exists():
        raise ValueError('Use new Pages staging output')
    shutil.copytree(source, output)
    for path in source.glob('*/feed.json'):
        feed = json.loads(path.read_text())
        list_id = feed['_retoob']['listId']
        if not re.fullmatch('[A-Za-z0-9_-]{1,128}', list_id):
            raise ValueError('Invalid feed identity')
        parsed = urlsplit(feed['feed_url'])
        suffix = '/' + list_id + '/feed.json'
        if not parsed.path.endswith(suffix):
            raise ValueError('Unexpected publication path')
        viewer = parsed.path[:-len(suffix)] + '/index.html'
        routes = [(output / list_id / 'index.html', {'feed': list_id})]
        for item in feed['items']:
            item_id = item['_retoob']['itemId']
            if not re.fullmatch('[A-Za-z0-9_-]{1,128}', item_id):
                raise ValueError('Invalid card identity')
            routes.append((output / list_id / 'items' / item_id / 'index.html', {'feed': list_id, 'item': item_id}))
        for destination, query in routes:
            target = html.escape(viewer + '?' + urlencode(query), quote=True)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=' +
                target + '"><title>Retoob video feed</title><a href="' + target + '">Open video feed</a>\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    prepare(args.source, args.output)
