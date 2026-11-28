"""Profile B draft exporter and validation for published connector snapshots."""
import copy
from datetime import datetime
from urllib.parse import urlsplit

PROFILE = 'b-draft-1'


CARD_FIELDS = {
    'creator': 'creator', 'sortAt': 'sort_at', 'dateBasis': 'date_basis',
    'durationSeconds': 'duration_seconds', 'mediaPublishedAt': 'media_published_at',
}
RECOMMENDATION_FIELDS = {
    'kind': 'kind', 'note': 'note', 'recommendedAt': 'published_at',
    'createdAt': 'created_at', 'sourceUrl': 'source_url', 'discussionUrl': 'discussion_url',
    'upstreamItemId': 'upstream_id', 'upstreamPublishedAt': 'source_date',
    'dateUntrusted': 'date_untrusted', 'startSeconds': 'start_seconds',
}


def nonnegative_integer(value):
    if type(value) is not int or not 0 <= value <= 2147483647:
        raise ValueError('Expected a bounded nonnegative integer')


def partial_date(value):
    precision, raw = value['precision'], text(value['value'])
    if precision == 'exact':
        date(raw)
    elif precision == 'day':
        datetime.strptime(raw, '%Y-%m-%d')
    elif precision == 'month':
        datetime.strptime(raw, '%Y-%m')
    elif precision == 'year':
        datetime.strptime(raw, '%Y')
    else:
        raise ValueError('Unsupported source date precision')


def https_url(value, allow_fragment=False):
    if not isinstance(value, str):
        raise ValueError('Expected an HTTPS URL')
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or (url.fragment and not allow_fragment):
        raise ValueError('Expected an HTTPS URL without credentials or a fragment')
    return value


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty text')
    return value


def date(value):
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
        if profile.get('creator') is not None:
            text(profile['creator']['name'])
            if 'url' in profile['creator']:
                https_url(profile['creator']['url'])
        for field in ('sort_at', 'media_published_at'):
            if profile.get(field) is not None:
                date(profile[field])
        if 'date_basis' in profile:
            if profile['date_basis'] not in ('publication', 'recommendation', 'import', 'unknown'):
                raise ValueError('Unsupported date basis')
            if (profile.get('sort_at') is None) != (profile['date_basis'] == 'unknown'):
                raise ValueError('Date basis and listed date disagree')
        if 'duration_seconds' in profile:
            nonnegative_integer(profile['duration_seconds'])
        playback = profile['playback']
        if 'start_seconds' in playback:
            nonnegative_integer(playback['start_seconds'])
        if playback['mode'] == 'direct':
            attachments = item['attachments']
            if len(attachments) != 1 or attachments[0]['mime_type'] not in (
                    'video/mp4', 'application/dash+xml', 'application/vnd.apple.mpegurl', 'application/x-mpegurl'):
                raise ValueError('Unsupported direct attachment')
            https_url(attachments[0]['url'])
        elif playback['mode'] in ('external', 'web'):
            if playback['mode'] == 'external':
                text(playback['provider'])
            https_url(item['external_url'])
        elif playback['mode'] == 'unavailable':
            text(playback.get('reason', 'Unavailable'))
        else:
            raise ValueError('Unsupported playback mode')
        occurrences = profile.get('recommendations', [])
        if not isinstance(occurrences, list):
            raise ValueError('Expected recommendation array')
        rec_ids = set()
        for rec in occurrences:
            rec_id = text(rec['id'])
            if rec_id in rec_ids or rec['basis'] not in ('mention', 'explicit', 'inferred', 'unknown'):
                raise ValueError('Invalid recommendation identity or basis')
            rec_ids.add(rec_id)
            for field in ('source_url', 'discussion_url', 'attribution_url'):
                if field in rec:
                    https_url(rec[field], allow_fragment=True)
            for field in ('published_at', 'created_at'):
                if field in rec:
                    date(rec[field])
            if 'source_date' in rec:
                partial_date(rec['source_date'])
            if 'start_seconds' in rec:
                nonnegative_integer(rec['start_seconds'])
            if 'date_untrusted' in rec and type(rec['date_untrusted']) is not bool:
                raise ValueError('Expected a boolean source-date trust marker')
            for field in ('note', 'attributed_to'):
                if field in rec and not isinstance(rec[field], str):
                    raise ValueError('Expected descriptive text')


def convert_feed(source, feed_url):
    """Adapt an accepted publication without collecting another upstream."""
    result = {key: copy.deepcopy(source[key]) for key in ('version', 'title', 'home_page_url', 'description') if key in source}
    result.update(feed_url=feed_url, _retoob={'profile': PROFILE}, items=[])
    for original in source['items']:
        old = original['_retoob']
        playback = old['playback']
        item = {key: copy.deepcopy(original[key]) for key in
                ('title', 'url', 'content_text', 'image', 'date_published', 'date_modified') if key in original}
        item['id'] = old['itemId']
        profile = {'media_id': old['contentKey'], 'playback': {'mode': playback['mode']}, 'recommendations': []}
        item['_retoob'] = profile
        for old_name, new_name in CARD_FIELDS.items():
            if old_name in old:
                profile[new_name] = copy.deepcopy(old[old_name])
        for old_name, new_name in (('startSeconds', 'start_seconds'), ('reason', 'reason')):
            if old_name in playback:
                profile['playback'][new_name] = playback[old_name]
        if playback['mode'] == 'direct':
            item['attachments'] = [{'url': playback['url'], 'mime_type': playback['mimeType']}]
        elif playback['mode'] == 'external':
            profile['playback']['provider'] = playback['provider']
            item['external_url'] = playback['url']
        elif playback['mode'] == 'web':
            item['external_url'] = playback['url']
        elif playback['mode'] != 'unavailable':
            raise ValueError('Cannot export an unsupported playback mode')
        for occurrence in old['recommendations']:
            rec = {'id': occurrence['id'], 'basis': occurrence['recommendationBasis']}
            for old_name, new_name in RECOMMENDATION_FIELDS.items():
                if old_name in occurrence:
                    rec[new_name] = copy.deepcopy(occurrence[old_name])
            if occurrence.get('publisher'):
                rec['attributed_to'] = occurrence['publisher']['name']
                if occurrence['publisher'].get('url'):
                    rec['attribution_url'] = occurrence['publisher']['url']
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
