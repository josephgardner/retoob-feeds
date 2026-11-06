#!/usr/bin/env python3
"""HN normalization, failure isolation, withdrawal and protocol checks."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

hn = load('hn', 'examples/hn-publisher/publish.py')
protocol = load('protocol', 'scripts/check-protocol.py')


def story(i, video='jNQXAC9IVRw'):
    return {'id': i, 'type': 'story', 'url': f'https://youtube.com/watch?v={video}',
            'title': 'An HN title &amp; more', 'time': 1793920000 + i}


class HNTest(unittest.TestCase):
    def test_urls_are_normalized_without_fetching_them(self):
        for url in ['https://youtu.be/jNQXAC9IVRw?t=4', 'http://youtube.com/watch?v=jNQXAC9IVRw',
                    'https://www.youtube.com/shorts/jNQXAC9IVRw', 'https://m.youtube.com/live/jNQXAC9IVRw']:
            self.assertEqual('jNQXAC9IVRw', hn.youtube_id(url))
        for url in ['https://youtube.com.evil.test/watch?v=jNQXAC9IVRw', 'https://youtube.com@127.0.0.1/watch?v=jNQXAC9IVRw',
                    'file:///watch?v=jNQXAC9IVRw', 'https://youtube.com/playlist?list=abc',
                    'https://youtube.com/watch?v=jNQXAC9IVRw&v=aqz-KE-bpKQ', 'https://youtu.be:9999/jNQXAC9IVRw']:
            self.assertIsNone(hn.youtube_id(url))

    def test_discovery_shares_fetches_and_drops_explicit_removals(self):
        data = {'topstories.json': [1, 2, 3], 'newstories.json': [2, 4],
                'item/1.json': story(1), 'item/2.json': dict(story(2), deleted=True),
                'item/3.json': dict(story(3), dead=True), 'item/4.json': dict(story(4), type='job')}
        calls = []
        def fetch(path):
            calls.append(path)
            return data[path]
        result = hn.collect(fetch=fetch, workers=1)
        self.assertEqual(['hn-1'], [e['id'] for e in result['top']])
        self.assertEqual([], result['new'])
        self.assertEqual(1, calls.count('item/2.json'))
        del data['item/3.json']
        with self.assertRaises(KeyError):
            hn.collect(fetch=fetch, workers=1)

    def test_bad_ids_and_bounds_fail_refresh(self):
        for value in [None, [True], [1, 1], [-1], list(range(1, 502))]:
            with self.assertRaises(ValueError):
                hn.collect(fetch=lambda _: value)
        with self.assertRaises(ValueError):
            hn.entry(story(2), 1)
        with self.assertRaises(ValueError):
            hn.collect(limit=501)
        with self.assertRaises(ValueError):
            hn.get_json('https://localhost/')

    def test_dedup_provenance_revisions_and_replacement(self):
        entries = [hn.entry(story(1), 1), hn.entry(story(2), 2)]
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            def build(name, state, values):
                return hn.generate_site(root / name, root / 'ledger.json', state,
                                        {'top': values}, 'https://algoplay.com/retoob-feeds', protocol.SCHEMA)[0]
            first = build('one', {}, entries)
            protocol.validate(root / 'one/hn-top-videos/feed.json')
            self.assertEqual(1, len(first['items']))
            item = first['items'][0]
            self.assertEqual('publication', item['_retoob']['dateBasis'])
            self.assertNotIn('mediaPublishedAt', item['_retoob'])
            self.assertEqual(2, len(item['_retoob']['recommendations']))
            for r in item['_retoob']['recommendations']:
                self.assertEqual('mention', r['recommendationBasis'])
                self.assertEqual('community', r['kind'])
                self.assertNotIn('recommendedAt', r)
                self.assertEqual('exact', r['upstreamPublishedAt']['precision'])
            state = json.loads((root / 'ledger.json').read_text())
            same = build('two', state, list(reversed(entries)))
            self.assertEqual(first, same)
            updated = build('three', state, entries[:1])
            self.assertEqual(2, updated['_retoob']['revision'])
            self.assertEqual(2, updated['items'][0]['_retoob']['revision'])
            state = json.loads((root / 'ledger.json').read_text())
            empty = build('four', state, [])
            protocol.validate(root / 'four/hn-top-videos/feed.json')
            self.assertEqual([], empty['items'])
            self.assertFalse((root / 'four/hn-top-videos/items').exists())
            self.assertNotIn('An HN title', (root / 'ledger.json').read_text())
            self.assertNotIn('hn-2', (root / 'three/hn-top-videos/feed.json').read_text())


if __name__ == '__main__':
    unittest.main()
