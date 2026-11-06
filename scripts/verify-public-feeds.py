#!/usr/bin/env python3
"""Bounded Pages propagation verification against the exact staged publication."""
import json
import pathlib
import sys
import time
import urllib.request

root = pathlib.Path(sys.argv[1])
pending = {path: json.loads(path.read_text()) for path in sorted(root.glob('*/feed.json'))}
deadline = time.monotonic() + 300
for attempt in range(10):
    for path, expected in list(pending.items()):
        if time.monotonic() >= deadline:
            raise SystemExit('Public verification deadline exceeded')
        try:
            request = urllib.request.Request(expected['feed_url'], headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read(10 * 1024 * 1024 + 1)
            if len(body) <= 10 * 1024 * 1024 and json.loads(body) == expected:
                del pending[path]
        except (OSError, ValueError):
            pass
    if not pending:
        print('Verified every public feed against validated staged JSON')
        break
    if attempt < 9:
        time.sleep(20)
else:
    raise SystemExit('Public feeds did not converge within the verification budget: ' + ', '.join(path.parent.name for path in pending))
