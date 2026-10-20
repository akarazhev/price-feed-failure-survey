# Who notices when a price feed goes wrong

1,163 commits matching six feed-failure terms, across 48 crypto organisations, collected on 25 August 2026.
The dataset is in [`data/commits.csv`](data/commits.csv), and every row links to its commit.

> **Correction, 23 September 2026.** This page first said "1,163 commits that repair feed handling". That was
> wrong. I read the diffs of 100 random commits: about 17% repair feed handling (95% interval 11–26%, roughly
> 200 of the 1,163), about 41% touch feed handling at all, and 59% have nothing to do with feeds. Most of those
> use `stale` in another sense: a query cache, an expired order, UI state, an old link. An outside reader
> pointed at the first false match on 14 September, and I should have checked then. Everything below counts
> matches, not repairs; the check itself is in [Precision](#precision-checked-23-september-2026).

Software that consumes market data can fail without any alarm: the feed keeps answering, and the answers stop
being true. A reconnect quietly loses its place in the sequence, or a stale window looks like a quiet market.
I wanted to know whether this keeps coming back or gets fixed once, and public code can answer that, because
the people who fix it commit the fix. So I counted.

## Method and limits

I searched the commits of 56 organisations through the GitHub API for six terms: `stale`, `reconnect`,
`heartbeat`, `backfill`, `desync`, `resubscribe` (the API allows no more than five `OR`s). 48 organisations
returned matches, and each contributes at most its newest 40 commits.

Each organisation is classified by the role a feed plays for it:

| | |
|---|---|
| **PUBLISHER** | the feed is the product: oracles and data providers |
| **CONSUMER** | the feed is consumed so that money can move on it |
| **INDEXER** | ingests and republishes derived data |
| **TOOLING** | open-source client libraries whose product is connection handling |

The comparison that matters is publishers against consumers. Indexers and tooling are published but kept out of
it: for a library like `ccxt`, a reconnect commit is planned work, not the trace of an incident.

What to keep in mind before using any number here:

- The sample skews recent: with the newest 40 per organisation, 733 of the 1,163 commits are from 2026.
- 19 of the 48 organisations hit the cap, so their real totals are higher. Without the cap, one organisation
  would outweigh the other nine publishers together.
- Six words are not the whole vocabulary. "Fix price feed" without any of them is invisible here, and `desync`
  turned out to be almost unused.
- The classification is my judgement. It is in [`orgs.txt`](orgs.txt), line by line.
- A match is not a repair (see the correction above).

## The sample

| class | organisations | repositories | commits |
|---|--:|--:|--:|
| PUBLISHER | 10 | 67 | 267 |
| CONSUMER | 27 | 142 | 601 |
| INDEXER | 6 | 24 | 150 |
| TOOLING | 5 | 11 | 145 |

Eight organisations returned nothing. They stay in `orgs.txt` so the denominator is honest.

## The terms come back

Among repositories with at least one match, the share with two or more:

| class | repositories | with ≥2 | share | median | max |
|---|--:|--:|--:|--:|--:|
| PUBLISHER | 67 | 43 | **64%** | 2 | 40 |
| CONSUMER | 142 | 83 | **58%** | 2 | 40 |
| INDEXER | 24 | 12 | 50% | 2 | 38 |
| TOOLING | 11 | 7 | 64% | 3 | 40 |

In organisations under the cap, where nothing is cut off: publishers 63%, consumers 51%. The cap can only hide
recurrence, so these are floors. Because most matches are not repairs, this table shows that the vocabulary
recurs, not the faults. Whether repairs recur needs a larger checked sample.

## Publishers and consumers write about different things

Share of commits whose first 120 characters, the subject a reviewer reads, name each term:

| class | n | stale | backfill | heartbeat | resubscribe | reconnect |
|---|--:|--:|--:|--:|--:|--:|
| PUBLISHER | 267 | 22% | 6% | **18%** | 0% | **1%** |
| CONSUMER | 601 | 34% | 8% | **6%** | 1% | **13%** |
| INDEXER | 150 | 26% | 3% | 2% | 0% | 2% |
| TOOLING | 145 | 17% | 3% | 6% | 0% | 12% |

Reconnect shows up in consumers' subjects thirteen times as often as in publishers' (13% against 1%), and
heartbeat three times as often the other way (18% against 6%). A publisher's job is to emit a signal that
proves it is alive, so its feed work is about that signal; a consumer finds out about a failing transport when
the connection drops. Tooling looks like consumers (reconnect 12%, heartbeat 6%), as it should: a client library
connects to somebody else's feed. Counting whole messages changes the levels but not the split.

This split is in the words, not necessarily in the faults. In the checked sample, publishers' `heartbeat`
commits were features and liveness logs, and publishers had one repair among 25 checked commits.

A commit shows that engineering time went into something. It doesn't show that anyone would buy a tool, and it
doesn't show severity: a one-line timeout bump and a week rebuilding a bad window are one commit each.

## Precision, checked 23 September 2026

I drew 100 of the 1,163 commits at random (`random.seed(20260923)`), in proportion to the six terms: `stale` 63,
`backfill` 12, `heartbeat` 12, `reconnect` 11, `resubscribe` 1, `desync` 1. Two could no longer be fetched, so
the base is 98. I read the diff of each and put it in one of three buckets, written down before the first diff:

- **R**: fixes wrong behaviour in code that receives, checks or recovers a market-data stream or price feed;
- **F**: the same code, but a feature, refactor, tuning or test;
- **N**: not about feeds (docs, CI, dependencies, bots, or the term in another sense).

Doubt between R and F went to F, between F and N to N. One rule was tightened at the 16th commit:
request-response caches and an application's own data count as N.

| | share of 98 | 95% Wilson interval | of 1,163, weighted by term |
|---|--:|--:|--:|
| R: repairs feed handling | 17.3% | 11.1–26.0% | ≈ 199 |
| R + F: touches feed handling | 40.8% | 31.6–50.7% | ≈ 473 |
| N: not about feeds | 59.2% | | ≈ 690 |

| term | R | F | N |
|---|--:|--:|--:|
| `stale` | 9 | 9 | 43 |
| `backfill` | 2 | 4 | 6 |
| `heartbeat` | 3 | 4 | 5 |
| `reconnect` | 2 | 6 | 3 |
| `resubscribe` | 1 | 0 | 0 |
| `desync` | 0 | 0 | 1 |

Counting caches and application data as feeds would raise R to at most 23.5% and R + F to 46.9%; the conclusion
stays the same. Every classification, with a one-line reason, is in
[`data/precision-sample.csv`](data/precision-sample.csv).

## Reproducing this

Python 3 and a `GITHUB_TOKEN` (commit search doesn't work anonymously):

```sh
export GITHUB_TOKEN=...
python3 collect.py orgs.txt   # -> raw.json
python3 analyse.py            # -> data/commits.csv, prints the tables above
```

`collect.py` asks for the newest 40 matches per organisation, keeps whole commit messages and pauses between
requests. `analyse.py` gives each commit one failure type, by the first term it matches. Running it on the committed `raw.json`
reproduces `data/commits.csv` byte for byte; running `collect.py` today won't reproduce the dataset, because
repositories move on.

## Data

- [`data/commits.csv`](data/commits.csv): 1,163 rows with class, organisation, repository, date, failure type,
  author login, subject and a link to the commit.
- [`raw.json`](raw.json): what the collector saw, with whole messages.

Author logins are kept where GitHub publishes them; email addresses are not collected. If an organisation is in
the wrong class or a commit is misassigned, tell me and I'll fix it.

---

*Andrey Karazhev · [minihub.app](https://minihub.app)*
