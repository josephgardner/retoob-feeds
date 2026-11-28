"""Profile B draft exporter and checks for the bounded Reddit pilot."""
import copy
from datetime import datetime
from urllib.parse import urlsplit

PROFILE = 'b-draft-1'


def https_url(value):
    if not isinstance(value, str):
        raise ValueError('Expected an HTTPS URL')
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError('Expected an HTTPS URL without credentials or a fragment')
    return value


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty text')
    return value


def date(value):
    datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset()
    if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Expected an RFC 3339 date with timezone')


def validate(feed):
    if feed.get('version') != 'https://jsonfeed.org/version/1.1' or feed.get('_retoob', {}).get('profile') != PROFILE:
        raise ValueError('Expected Profile B draft')
    text(feed['title'])
    https_url(feed['feed_url'])
    if 'next_url' in feed or not isinstance(feed['items'], list) or len(feed['items']) > 1000:
        raise ValueError('Expected one bounded complete list')
    ids, media_ids = set(), set()
    for item in feed['items']:
        item_id = text(item['id'])
        profile = item['_retoob']
        media_id = text(profile['media_id'])
        if item_id in ids or media_id in media_ids:
            raise ValueError('Duplicate card or media identity')
        ids.add(item_id)
        media_ids.add(media_id)
        text(item['title'])
        if not isinstance(item['content_text'], str):
            raise ValueError('Expected plain text content')
        https_url(item['url'])
        for field in ('date_published', 'date_modified'):
            if field in item:
                date(item[field])
        if 'image' in item:
            https_url(item['image'])
        playback = profile['playback']
        if playback['mode'] == 'direct':
            attachments = item['attachments']
            if len(attachments) != 1 or attachments[0]['mime_type'] not in (
                    'video/mp4', 'application/dash+xml', 'application/vnd.apple.mpegurl', 'application/x-mpegurl'):
                raise ValueError('Unsupported direct attachment')
            https_url(attachments[0]['url'])
        elif playback['mode'] == 'external':
            text(playback['provider'])
            https_url(item['external_url'])
        else:
            raise ValueError('Unsupported playback mode')
        occurrences = profile.get('recommendations', [])
        if not isinstance(occurrences, list):
            raise ValueError('Expected recommendation array')
        rec_ids = set()
        for rec in occurrences:
            rec_id = text(rec['id'])
            if rec_id in rec_ids or rec['basis'] not in ('mention', 'explicit'):
                raise ValueError('Invalid recommendation identity or basis')
            rec_ids.add(rec_id)
            if 'source_url' in rec:
                https_url(rec['source_url'])
            if 'published_at' in rec:
                date(rec['published_at'])
            for field in ('note', 'attributed_to'):
                if field in rec and not isinstance(rec[field], str):
                    raise ValueError('Expected descriptive text')


def reddit_feed(source, feed_url):
    """Adapt existing published Reddit data without collecting another upstream."""
    if source['_retoob']['listId'] != 'reddit-videos':
        raise ValueError('Pilot is limited to the r/videos source')
    result = {key: copy.deepcopy(source[key]) for key in ('version', 'title', 'home_page_url', 'description')}
    result.update(feed_url=feed_url, _retoob={'profile': PROFILE}, items=[])
    for original in source['items']:
        old = original['_retoob']
        playback = old['playback']
        if playback.get('startSeconds', 0) != 0:
            raise ValueError('Draft does not represent playback offsets')
        item = {key: copy.deepcopy(original[key]) for key in
                ('title', 'url', 'content_text', 'image', 'date_published', 'date_modified') if key in original}
        item['id'] = old['itemId']
        profile = {'media_id': old['contentKey'], 'playback': {'mode': playback['mode']}, 'recommendations': []}
        item['_retoob'] = profile
        if playback['mode'] == 'direct':
            item['attachments'] = [{'url': playback['url'], 'mime_type': playback['mimeType']}]
        elif playback['mode'] == 'external':
            profile['playback']['provider'] = playback['provider']
            item['external_url'] = playback['url']
        else:
            raise ValueError('Cannot export an unsupported playback mode')
        for occurrence in old['recommendations']:
            if occurrence.get('startSeconds', 0) != 0:
                raise ValueError('Draft does not represent recommendation offsets')
            rec = {'id': occurrence['id'], 'basis': occurrence['recommendationBasis']}
            for key, field in (('note', 'note'), ('recommendedAt', 'published_at')):
                if key in occurrence:
                    rec[field] = occurrence[key]
            if occurrence.get('publisher', {}).get('name'):
                rec['attributed_to'] = occurrence['publisher']['name']
            source_url = occurrence.get('discussionUrl') or occurrence.get('sourceUrl')
            if source_url:
                rec['source_url'] = source_url
            upstream = occurrence.get('upstreamPublishedAt', {})
            if 'published_at' not in rec and upstream.get('precision') == 'exact':
                rec['published_at'] = upstream['value']
            profile['recommendations'].append(rec)
        result['items'].append(item)
    validate(result)
    return result


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('feeds', nargs='+', type=Path)
    args = parser.parse_args()
    for path in args.feeds:
        document = json.loads(path.read_text())
        validate(document)
        print(f'Validated Profile B {path} ({len(document["items"])} cards)')
