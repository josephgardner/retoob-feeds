# Retoob Feed Profile 1

**Status:** Draft. Describes profile 1 as implemented by Retoob TV and the
publishers in this repository. Not an IETF standard.

**Schemas:** [Feed](https://algoplay.com/retoob-feeds/schemas/retoob-feed-v1.schema.json)
([reference](https://algoplay.com/retoob-feeds/schemas/retoob-feed-v1.schema.html)) ·
[Collection](https://algoplay.com/retoob-feeds/schemas/retoob-directory-v1.schema.json)
([reference](https://algoplay.com/retoob-feeds/schemas/retoob-directory-v1.schema.html))

A Retoob feed is a public JSON document listing playable videos. Anyone can
publish one from any source, and any reader can follow one without an account,
a central service or source-specific code. Feeds carry links, attribution and
playback hints, never video bytes; playback stays with the original provider.

This document defines the feed format, the feed collection format, how
publishers serve them, and what readers do with them. The JSON Schemas check
structure; this document adds the rules a schema cannot express. A conforming
document satisfies both.

## 1. Conventions and terms

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when, and only when, they appear in all
capitals.

- **Publisher** (or connector): produces a feed from a source.
- **Source**: the publisher's upstream input, such as a hand-curated list, a
  community or an API.
- **Feed**: a profile-1 document describing the complete current contents of
  one list.
- **Card**: one item in a feed. A card is one video, with every recommendation
  of it.
- **Recommendation**: one save or mention of a video by a curator or source.
- **Collection**: a document listing feed URLs.
- **Reader**: software that follows feeds and hands playback to a provider.

## 2. Feed document

A feed is a [JSON Feed 1.1](https://www.jsonfeed.org/version/1.1/) document.
Generic JSON Feed readers can display its titles, links, text and images.
Retoob data lives in `_retoob` extension objects on the feed and on each item.

### 2.1 Data types

| Type | Rule |
| --- | --- |
| ID | Opaque string of 1–256 characters. Readers MUST NOT parse IDs. |
| Revision | Integer from 1 to 9007199254740991 (2^53 − 1). |
| Instant | RFC 3339 UTC timestamp ending in `Z`. |
| Seconds | Integer from 0 to 2147483647. |
| HTTPS URL | Absolute `https://` URL without credentials. |
| Partial date | `{value, precision}`, where `precision` is `exact` (an instant), `day` (`YYYY-MM-DD`), `month` (`YYYY-MM`) or `year` (`YYYY`). |
| Person | `{name, url?}`. An attributed claim, not a verified identity. |

Optional fields whose value is unknown MUST be omitted, except `sortAt`, which
is `null` when unknown.

### 2.2 Feed object

| Field | Required | Meaning |
| --- | --- | --- |
| `version` | yes | `https://jsonfeed.org/version/1.1` |
| `title` | yes | Nonempty list title. |
| `home_page_url` | yes | HTTPS URL of an HTML page for this list. |
| `feed_url` | yes | HTTPS URL of this feed. |
| `items` | yes | Cards, possibly empty (`[]`). |
| `_retoob` | yes | Feed profile (2.3). |
| `next_url` | no | Next page; omitted on the last page (5.3). |
| `description`, `authors` | no | As in JSON Feed. |

### 2.3 Feed `_retoob`

| Field | Required | Meaning |
| --- | --- | --- |
| `version` | yes | `1` |
| `listId` | yes | Stable ID of the list. |
| `revision` | yes | Publication revision (3.2). |
| `publicationEpoch` | yes | ID of this publication lifetime (3.3). |
| `semantics` | yes | `"snapshot"`: the feed is the complete current list. |
| `itemCount` | yes | Number of distinct cards in the complete feed, 0–1,000. Every page carries the total. |
| `schema` | no | Canonical schema URI (9). |

### 2.4 Item

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Stable card permalink. MUST equal `url`. |
| `url` | yes | Same as `id`. |
| `external_url` | yes | Canonical URL of the video's page. |
| `title` | yes | Nonempty. |
| `content_text` | yes | Plain text that keeps curator or source notes distinct from video metadata. |
| `image` | no | HTTPS thumbnail URL. |
| `date_published` | no | Only a trusted exact recommendation or publication time (4). |
| `date_modified` | no | Instant. |
| `_retoob` | yes | Card profile (2.5). |

A provider's watch page is never a JSON Feed `attachment`.

### 2.5 Item `_retoob`

| Field | Required | Meaning |
| --- | --- | --- |
| `version` | yes | `1` |
| `itemId` | yes | Stable card ID. |
| `revision` | yes | Card revision (3.2). |
| `contentKey` | yes | Canonical media identity (3.1). |
| `sortAt` | yes | Instant used for ordering, or `null` (4). |
| `dateBasis` | yes | `recommendation`, `publication`, `import` or `unknown` (4). |
| `playback` | yes | Playback descriptor (6). |
| `recommendations` | yes | One or more recommendations (2.6). |
| `mediaPublishedAt` | no | When the media was uploaded. Never replaces the recommendation date. |
| `durationSeconds` | no | Seconds. |
| `creator` | no | Person who made the media. |

### 2.6 Recommendation

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Stable recommendation ID. |
| `kind` | yes | `manual`, `feed`, `playlist`, `community` or `catalogue`. |
| `recommendationBasis` | yes | `explicit`, `mention`, `inferred` or `unknown`. |
| `createdAt` | no | When a manual save was made. |
| `recommendedAt` | no | Trusted exact time of the recommendation. |
| `upstreamPublishedAt` | no | Partial date reported by the source. |
| `dateUntrusted` | no | `true` when the source's claimed time is in the future (4). |
| `publisher` | no | Person who made the recommendation. |
| `sourceUrl` | no | HTTPS URL of the source entry. |
| `discussionUrl` | no | HTTPS URL of a discussion of the video. |
| `upstreamItemId` | no | The source's own ID for the entry. |
| `note` | no | Plain-text curator or source note. |
| `startSeconds` | no | Start offset for this recommendation. |

A source mention is not a verified endorsement.

## 3. Identity and revisions

### 3.1 Cards and media

A feed MUST contain at most one card per media item. Every recommendation of a
video belongs to that video's card and keeps its own ID, note, provenance and
start offset. A card's playback descriptor, start offset and date come from its
newest recommendation.

Within a feed, card `id`s, `itemId`s, `contentKey`s and recommendation `id`s
MUST each be unique. Card IDs come from durable input, never from titles or
timestamps, and MUST survive metadata edits.

Publishers SHOULD normalize YouTube watch, `youtu.be`, shorts and live URLs to
the `contentKey` `youtube:<videoId>` and the `external_url`
`https://www.youtube.com/watch?v=<videoId>`, carrying any start offset in
`startSeconds`. An explicit offset, including zero, takes precedence over an
offset in a URL. For other URLs, `contentKey` SHOULD be a hash of the normalized
URL that keeps result-affecting query parameters and drops only known tracking
parameters.

URLs MUST NOT contain credentials, unsafe schemes, local or reserved literal
hosts, or authentication or signature query parameters.

### 3.2 Revisions

Revisions start at 1. A material change to a card increments that card's
`revision` and the feed's `revision`. A change to the list title or to which
cards are in the list increments the feed's `revision`.

Regenerating unchanged input, including equivalent input in a different order,
MUST produce identical bytes, and so the same revision, ETag and modification
time. A metadata change MUST NOT create a new recommendation date.

Publishers SHOULD keep a content-free record of card revisions, so a card that
leaves the feed and later returns continues from its previous revision. That
record MUST NOT retain removed notes or other removed content.

### 3.3 Epochs

`publicationEpoch` separates publication lifetimes. A withdrawn list that is
published again MUST use a new epoch. A withdrawn epoch MUST NOT be reused.

## 4. Dates and ordering

Cards are ordered by `sortAt` descending, with `null` last, then by `itemId`
descending. `sortAt` is `null` exactly when `dateBasis` is `unknown`.

| Source date | What to publish |
| --- | --- |
| Manual save | `createdAt` is the recommendation time. Metadata refreshes MUST NOT change it. |
| Trusted exact recommendation or publication time | Order by it and export it as `date_published`. |
| Partial upstream date (day, month or year) | Keep `{value, precision}` in `upstreamPublishedAt`, order at the start of the period in UTC, and omit `date_published`. |
| Undated historical import | `sortAt: null` and `dateBasis: "unknown"`. Sorts after dated cards. |
| Undated entry first seen live | The ingestion time, with `dateBasis: "import"`. |
| Source time in the future | Keep the claimed value with `dateUntrusted: true`, and cap `sortAt` at the ingestion time. |

Media upload time belongs only in `mediaPublishedAt`. Readers MUST NOT display a
period-start `sortAt` as an exact day, and MUST NOT present import or check
times as the time a link was shared.

## 5. Publishing over HTTP

### 5.1 Requests

Feeds are served over HTTPS. `GET` on a feed URL returns the feed with media
type `application/feed+json`; `HEAD` returns the same headers without a body.
Section 8 covers static hosts that cannot set this media type.

`home_page_url` SHOULD serve HTML that shows the same publication and carries
an alternate-feed discovery link. Card permalinks SHOULD resolve while the card
is in the feed. HTML MUST render feed text as escaped plain text.

### 5.2 Bounds

| Bound | Value |
| --- | --- |
| Cards in a complete feed | At most 1,000. Publishers SHOULD default to 200. |
| Complete feed size | 10 MiB decompressed, across all pages, including repeated page metadata. |
| Page size | Default 50 cards, maximum 100. |

A feed or card that exceeds a bound fails with `feed_too_large`. Publishers
MUST NOT silently truncate provenance to fit.

### 5.3 Pagination

A feed MAY be split into pages linked by `next_url`. The last page omits
`next_url`, and `next_url` MUST stay on the feed's origin. Every page MUST carry
the same `listId`, `publicationEpoch`, `revision` and `itemCount`.

Cursors are opaque to readers. Servers SHOULD authenticate each cursor and bind
it to the list, epoch, revision, page size, position and an expiry. The
reference server uses HMAC and a 15-minute lifetime. When the publication
changes during a read, the server responds `409` with code `snapshot_changed`;
an expired cursor gets `410` with code `cursor_expired`.

### 5.4 Caching and validators

The ETag of every response MUST be derived from its exact body bytes; the
reference publishers use the quoted SHA-256 of the body. Responses SHOULD send
`Cache-Control: public, max-age=60, must-revalidate` and `Last-Modified`.
Servers MUST support `If-None-Match`, MUST check publication status before
answering `304`, and MUST NOT send a body with `304`. Rotating an expired
cursor changes the bytes, and so the validators, of pages that link to it,
without a new revision. Wildcard CORS is allowed only on anonymous responses.

### 5.5 Errors and withdrawal

Errors are JSON problem documents with at least a numeric `status` and a string
`code`, sent with `Cache-Control: no-store`.

A withdrawn feed's URL responds `404` or `410` with `Cache-Control: no-store`.
Publishers MUST NOT report a withdrawal as a retryable error, since that would
keep withdrawn content visible in readers.

## 6. Playback descriptors

| `mode` | Required fields | Meaning |
| --- | --- | --- |
| `external` | `provider`, `url` | Hand off to the provider, such as `provider: "youtube"` with a canonical HTTPS watch URL. |
| `direct` | `url`, `mimeType` | Media the reader plays itself: DASH, HLS or MP4. |
| `web` | `url` | A web page for the viewer to open, for example on a phone. |
| `unavailable` | `reason` | A stable reason the video can't be played. |

Descriptors MAY also carry `startSeconds`, `durationSeconds` and `expiresAt`.
Publishers MUST NOT infer `direct` from a URL's file extension alone.

Readers MUST treat an unknown `mode` or `provider` as an unsupported card and
keep the rest of the feed usable. A feed cannot supply executable schemes, app
packages, request headers, DRM keys or credentials; the reader decides how to
hand off. A successful handoff does not mean the video was watched.

## 7. Readers

### 7.1 Refresh

A reader replaces a list only with a complete, consistent snapshot. It reads
every page; checks that origin, `listId`, `publicationEpoch`, `revision` and
`itemCount` agree across pages; checks that the number of unique cards equals
`itemCount` and that pagination ends; and treats conflicting duplicate IDs as
malformed.

| Response or event | Reader behavior |
| --- | --- |
| Complete, consistent `200` | Atomically replace the list, including removals. |
| Root `304` with a complete matching cache | Keep the snapshot and renew its validation time. |
| `409 snapshot_changed` | Restart from the root, within a restart budget (the reference reader allows two). |
| `410 cursor_expired` | Restart from the root. This is not a withdrawal. |
| Root `404` or `410` | Remove the content and validators at once, and keep the subscription, marked unavailable. |
| Invalid page, conflicting duplicates, loop, count mismatch, oversize or deadline | Keep the previous complete snapshot. Never replace it with partial content. |
| Timeout, `429` or `5xx` | Keep the content, marked stale, and back off, honoring `Retry-After`. |
| Origin, `listId` or epoch changes | Discard the old copy. Old cursors and selection state don't carry over. |

A known withdrawal overrides every rule that retains old content. Readers
SHOULD put a ceiling on how long stale content stays visible; the reference
reader uses 24 hours.

Readers MUST scope caches to the validated effective root origin plus `listId`.
Feed-supplied `feed_url` and `home_page_url` MUST NOT choose the cache namespace
or a privileged request origin.

### 7.2 Transport and safety

Feed, page, redirect, thumbnail and media requests MUST be anonymous: no
cookies, credentials, authentication headers or shared authenticated caches.
Readers MUST validate DNS answers and every redirect destination before
connecting, and refuse local and reserved networks.

Readers MUST bound their work. Reference values: 60 seconds per refresh across
all pages and redirects, five redirects per request, the 10 MiB feed bound, and
2 MiB per thumbnail.

Readers MUST render feed text as plain text, never as HTML, MUST ignore unknown
fields, and MUST NOT fetch `_retoob.schema`.

## 8. Feed collections

A collection lists feeds for a reader to follow:

```json
{
  "version": 1,
  "title": "My video feeds",
  "feeds": [
    {"title": "Software", "url": "https://algoplay.com/retoob-feeds/hackertube-software/feed.json"},
    "https://another.example/feed.json"
  ]
}
```

- New publishers MUST set `version: 1`. Readers SHOULD still accept older
  collections without it.
- `feeds` holds up to 200 entries. Each is a URL string or `{url, title?}`.
  URLs MUST be absolute HTTPS, without credentials or a fragment, and at most
  2,048 characters.
- Entries are feed references only, never merged items or provider
  configuration. Readers MUST NOT expand nested collections.
- A collection is at most 2 MiB. Readers MUST reject an oversized collection
  entirely.
- `feeds.json` is a naming convention. Readers identify a collection by its
  contents, and ignore unknown fields.

A complete, changed collection replaces the membership it governs. A malformed,
truncated or failed read keeps the previous membership. A root `404` or `410`
marks the collection unavailable and removes its references, without affecting
feeds the reader also follows directly.

## 9. Static hosting

A static host can serve a feed as one complete, unpaginated snapshot. Deploy
all of a publication's files together, and remove obsolete card pages along
with their feed entries. On a Git-backed host, history is public: never commit
private or revocable material.

**Known deviation:** GitHub Pages serves feeds as `application/json` with cache
lifetimes of about 10 minutes, not `application/feed+json` with `max-age=60`.
Retoob TV accepts this. Whether profile 1 should allow ordinary JSON media types
and host-controlled cache lifetimes is an open question; until it's decided,
such hosting is a documented deviation, not full conformance. Long cache
lifetimes also delay how soon readers see removals and withdrawals.

## 10. Versioning

Both `_retoob.version` fields are `1`. A breaking change requires a new profile
version. Profile 1 can gain additive fields, which readers MUST ignore when they
don't recognize them.

`_retoob.schema` is an optional HTTPS pointer. New publishers SHOULD set it to
the feed schema's canonical `$id`,
`https://algoplay.com/retoob-feeds/schemas/retoob-feed-v1.schema.json`. Feeds
without it remain valid. Validators SHOULD pin a reviewed local copy of the
schema and flag unknown pointers for review.

The canonical schema URIs are permanent. They stay reachable even if example
feeds move, and a feed's host has no authority over the schema.

## 11. Conformance

[`scripts/check-protocol.py`](https://github.com/josephgardner/retoob-feeds/blob/main/scripts/check-protocol.py)
validates complete local feeds:

```sh
python3 -m pip install -r scripts/requirements-protocol.txt
python3 scripts/check-protocol.py docs/tech-night/feed.json
```

It checks the schema, the 10 MiB bound, that the feed is unpaginated,
`itemCount`, unique identities, `id` equal to `url`, the `sortAt`/`dateBasis`
pairing, and that `_retoob.schema` is absent or canonical. It does not check
network destinations, provider permission or paginated publications.
Conformance doesn't establish permission to publish: publishers are responsible
for the right to export each source's metadata.
