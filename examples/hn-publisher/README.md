# Hacker News → playable video feeds

A Python standard-library connector consumes the [official HN API](https://github.com/HackerNews/API)
and uses the independent static publisher to generate two JSON Feed 1.1 plus
Retoob profile-1 feeds:

- `hn-top-videos/feed.json`: YouTube links among up to 500 current top stories.
- `hn-new-videos/feed.json`: YouTube links among up to 500 current newest stories.

Both are ordered by HN submission date, not score. These are bounded current
windows, not all HN videos or a complete historical archive. An item leaving a
window leaves the generated snapshot; that does not assert an upstream deletion.
An explicit dead/deleted story contributes nothing on the next successful run.
If a video has two live submissions, it remains one card with two provenance
records. Story dates are upstream publication dates, never claimed media-upload
or verified recommendation dates. HN story titles are used as labels; neither
video availability nor canonical YouTube metadata is verified. Images use the
YouTube thumbnail CDN, and playback is delegated to the existing YouTube handler.
Other video hosts and article pages containing embedded video are skipped.

## Generate

From the repository root:

```sh
python3 examples/hn-publisher/publish.py \
  --initialize --state /tmp/hn-ledger.json --output /tmp/hn-site \
  --schema docs/schemas/retoob-feed-v1.schema.json
python3 scripts/check-protocol.py /tmp/hn-site/hn-*-videos/feed.json
```

Use Python 3.11+ and install the validator requirements for the second command.
For updates retain the ledger, omit `--initialize`, and use a fresh empty output
directory. The existing `tech-night` producer/ledger is independent. Do not reset
an established publication's epoch or revision state. These inputs contain public
HN metadata, not private Family data or private RFC documents.

Only internally constructed HTTPS paths on `hacker-news.firebaseio.com` are
fetched. Redirects are refused. Story links are parsed, never requested. Fetching
is bounded to two windows, at most 1000 distinct item requests, six workers,
15 seconds per request, and 1 MiB per response. The two streams share item
requests, but each refresh rechecks current items so known deletions are not
hidden by a long item cache. No provider credential or Retoob account is used.
Any transport/identity/parse failure aborts before the output and ledger are
replaced. A successful empty window can legitimately publish an empty feed.
Deploy only after generation **and validation** succeed; retain the previous
site on failure. Publish an observable last-success time separately rather than
changing card dates on every poll. HN does not document a rate limit; this is
not permission for unbounded fetching. A six-hour schedule is adequate to start.

The CLI output is a fresh **HN-only staging site**. For a multi-producer site,
replace only the owned `hn-top-videos` and `hn-new-videos` directories (removing
obsolete card pages), retain the manual feed, and generate a combined index.
Keep ledgers outside the published directory. GitHub Pages' JSON MIME/cache
hosting deviations documented in `docs/independent-publishing.md` still apply;
cache expiry delays removals and freshness discovery.

## Checks

```sh
python3 scripts/test-hn-publisher.py
python3 scripts/test-static-publisher.py
```

Tests cover URL canonicalization, duplicates, source/date semantics, explicit
removals, failed fetch isolation, deterministic revisions and schema conformance.
A live initial fetch on 2026-11-05 yielded 6 top-window and 17 newest-window
YouTube cards. Those counts will change. A physical-TV run is not claimed.

## Reddit follow-up

No Reddit crawler is activated. The user has no Reddit API approval. Evaluated
alternatives include Arctic Shift's free archive API and the advertised free
plans of RedditAPIs and Weir. These providers' access/pricing claims do not prove
permission to redistribute Reddit data through a public feed. RedditAPIs' terms
explicitly leave compliance with Reddit's rules with the customer. Verify the
permitted use and removal obligations before activating an adapter. Metadata
removal must propagate through live feeds, stored pages, caches and history as
applicable; a public Git archive may be unsuitable for revocable source content.

At RedditAPIs' advertised 1000 free reads/month and $0.0015/additional read,
assuming one 100-post page per subreddit per hour in a 30-day month:
1 subreddit = 720 calls ($0); 5 = 3600 ($3.90); 10 = 7200 ($9.30);
25 = 18000 ($25.50). Pagination and additional sort windows add calls. Poll once
per configured source, not per TV. These costs are separate from the Google Cloud
budget. Prices and upstream availability must be rechecked before activation.
