# Public video feeds

This is an independent, offline Python connector for a Git-tracked manual collection.
It publishes a complete JSON Feed 1.1 / Retoob profile-1 snapshot. It needs no
Retoob service, database, account, or Go generator. It fetches no video bytes or
provider metadata. YouTube supplies playback in the original app.

Subscribe: https://algoplay.com/retoob-feeds/tech-night/feed.json

Browse: https://algoplay.com/retoob-feeds/tech-night/

Schema: https://algoplay.com/retoob-feeds/schemas/retoob-feed-v1.schema.json

The source is `examples/static-publisher/tech-night.json`. Each entry has a stable
recommendation ID, YouTube video ID, title, UTC save time, and optional note/offset.
Labels/notes are curator-authored demonstration text. Multiple saves of one video
produce one card with all recommendations. Newest save wins the card's title and
offset. The source's save time describes the recommendation, never the video's
upload date. Keep IDs and dates stable when editing metadata.

## Update

Use Python 3.11 or newer. Install validation dependencies in a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r scripts/requirements-protocol.txt
```

Edit the collection, then generate into a fresh directory outside the checkout:

```sh
python3 examples/static-publisher/publish.py examples/static-publisher/tech-night.json \
  --state .publisher-state.json --output /tmp/retoob-next-site \
  --schema docs/schemas/retoob-feed-v1.schema.json
python3 scripts/check-protocol.py /tmp/retoob-next-site/tech-night/feed.json
```

Review the output. Replace the **entire `docs/` directory** with this generated
site, including deletion of old card pages, and commit it together with the
collection and `.publisher-state.json`. Push `main` to publish via GitHub Pages
(branch `main`, directory `/docs`). Do not overlay an old site: that can preserve
removed notes in old HTML pages. Git history is public; never put sensitive or
revocable private content into this repository. Remove prohibited content from
history/caches separately when required.

Retain `.publisher-state.json`: it contains hashes and revision numbers, no notes
or titles. It preserves monotonically increasing card revisions after removal and
return. The unchanged input produces identical bytes. For a truly new publication,
choose a fresh `publicationEpoch`, use a new state path and `--initialize`. Never
reset an existing publication's ledger or reuse a withdrawn epoch.

Delete an entry to remove one recommendation; delete all recommendations for a
video to remove its card. Publish an empty collection to deliberately clear a
list. To withdraw the list, remove its feed and HTML/card pages in the same deploy
so a subsequent root fetch returns 404; retain the subscription URL unavailable.
GitHub's caches can delay this change, so use a configurable HTTP origin if prompt
withdrawal is required.

## Hosting and conformance

Only `docs/` is served. This repository's connector source and content-free state
are intentionally public. The site is static and portable; `baseUrl` configures
its location, including a project subdirectory. No custom domain is required.
A later feeds.algoplay.com deployment may use the same connector and a new epoch.
The schema URI identifies the project-owned schema, independently of feed origin;
keep the canonical URI available even if the test publisher moves.

GitHub Pages controls MIME types and caching: `.json` is `application/json`, which
the existing TV reader accepts. The current protocol specifies
`application/feed+json`, so this demonstrates reader interoperability with a
**documented hosting deviation**, not full HTTP conformance. There is no arbitrary
upstream Git crawler, webhook ingestion, scheduled source refresh, or multi-feed
aggregation service in this first connector.

The offline validator uses a pinned local schema, checks complete counts and unique
identities, and never fetches a feed-supplied schema URL. Older profile-1 feeds
without `_retoob.schema` remain valid. Unknown schema identifiers need explicit
review; a reader may ignore additive discovery fields. It is not a network/SSRF,
provider-permission, or cross-page conformance audit.

## Hacker News feeds

- Top-story window: https://algoplay.com/retoob-feeds/hn-top-videos/feed.json
- Newest-story window: https://algoplay.com/retoob-feeds/hn-new-videos/feed.json
- Last successful refresh: https://algoplay.com/retoob-feeds/hn-status.json

These are YouTube links among the official API's current top/new story windows,
ordered by submission date. They are not a complete historical archive. HN
mentions retain discussion provenance and are not verified endorsements. No
YouTube account, Retoob backend, database, browser scraper, or Cloud Run deploy is
needed. See `examples/hn-publisher/README.md` for bounds and failure behavior.

The GitHub Actions workflow refreshes every six hours or on manual dispatch, then
validates and publishes the whole Pages site, preserving the manual Tech Night
feed. `.hn-publisher-state.json` retains only hashes/revisions and must never be
reset. An unsuccessful source fetch or validation prevents publishing. Scheduled
GitHub jobs can be delayed, and public-repository schedules may be disabled after
60 days of repository inactivity. Check the public freshness timestamp and the
Actions page if updates stop. Pages must use the GitHub Actions publishing mode.

The manual update instructions above predate multiple producers: regenerate the
manual feed in a staging directory and replace only `docs/tech-night`, retaining
the two HN directories, then run `scripts/update-hn-site.py` on a fresh HN staging
site to rebuild the combined index. Do not replace the entire `docs` directory
with manual-only output.

No Reddit feed is configured. Third-party API access and public redistribution
requirements remain to be verified before enabling one.
