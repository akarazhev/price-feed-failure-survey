# Who notices when a price feed goes wrong

**1,163 commits that repair feed handling, across 48 crypto organisations.**
Collected 25 August 2026.

Software that consumes market data has a failure mode with no alarm attached:
the feed keeps answering, and the answers stop being true. A reconnect that
silently loses its place in the sequence. A stale window that looks like a
quiet market. Afterwards there is no record of what the feed was doing.

Whether that is a real and recurring problem, or one that gets fixed once and
stays fixed, is answerable from public code — the people who fix it commit the
fix. So I counted.

The dataset is in [`data/commits.csv`](data/commits.csv). Every row links to the
commit.

---

## Method, and four things it does not cover

Fifty-six organisations were queried through the GitHub commit search API for
six terms: `stale`, `reconnect`, `heartbeat`, `backfill`, `desync`,
`resubscribe`. Six is the ceiling — the API allows at most five `OR` operators.
Forty-eight returned matches. Each organisation contributes at most its newest
40 commits.

Organisations are classified by **the role a feed plays for them**:

| | |
|---|---|
| **PUBLISHER** | the feed is the product — oracles and data providers |
| **CONSUMER** | the feed is consumed so that money can move on it |
| **INDEXER** | ingests and republishes derived data |
| **TOOLING** | open-source client libraries whose product *is* connection handling |

The comparison that matters is publisher against consumer. Indexers and tooling
are collected and published but kept out of it: for a library like `ccxt`, a
reconnect commit is planned product work, not the trace of an incident.

**Four limits, before any number below is used:**

- **The sample skews recent.** Newest-40 per organisation means 733 of 1,163
  commits are from 2026, though the range runs back to 2017. Older repair work
  is underrepresented.
- **Nineteen of 48 organisations hit the cap.** Their real totals are higher.
  The cap is not tidiness: one organisation alone returns more matches than the
  other nine publishers together, and without it "publisher" would mean that
  one company.
- **Six words are not the vocabulary.** A commit that says "fix price feed"
  without any of them is invisible here. One of the six, `desync`, turned out
  to be almost unused — it accounts for under 1% everywhere, which is a fact
  about the word, not about the world.
- **The classification is a judgement.** It is in [`orgs.txt`](orgs.txt), line
  by line, and it can be argued with.

## The sample

| class | organisations | repositories | commits |
|---|--:|--:|--:|
| PUBLISHER | 10 | 67 | 267 |
| CONSUMER | 27 | 142 | 601 |
| INDEXER | 6 | 24 | 150 |
| TOOLING | 5 | 11 | 145 |

Eight organisations were queried and returned nothing. They stay in `orgs.txt`,
because a denominator that quietly drops its misses is not a denominator.

## It does not get fixed once

Among repositories with at least one such commit, the share that have **two or
more**:

| class | repositories | with ≥2 | share | median | max |
|---|--:|--:|--:|--:|--:|
| PUBLISHER | 67 | 43 | **64%** | 2 | 40 |
| CONSUMER | 142 | 83 | **58%** | 2 | 40 |
| INDEXER | 24 | 12 | 50% | 2 | 38 |
| TOOLING | 11 | 7 | 64% | 3 | 40 |

Restricted to organisations under the cap, where nothing is truncated:
publishers 63%, consumers 51%.

Truncation can only hide recurrence, never invent it, so these are floors. In
roughly three of five repositories that ever repaired feed handling, it came
back.

## Publishers and consumers do not have the same problem

Share of commits whose **first 120 characters** name each term — the subject
line a reviewer actually reads:

| class | n | stale | backfill | heartbeat | resubscribe | reconnect |
|---|--:|--:|--:|--:|--:|--:|
| PUBLISHER | 267 | 22% | 6% | **18%** | 0% | **1%** |
| CONSUMER | 601 | 34% | 8% | **6%** | 1% | **13%** |
| INDEXER | 150 | 26% | 3% | 2% | 0% | 2% |
| TOOLING | 145 | 17% | 3% | 6% | 0% | 12% |

Two columns separate cleanly, and they separate in opposite directions.

**Reconnect is a consumer problem: 13% against 1%.** Thirteen times more common
in the subject lines of organisations that consume feeds than of those that
publish them.

**Heartbeat is a publisher problem: 18% against 6%.** Three times the other way.

The reading is not complicated. A publisher's job is to emit a signal that
proves it is alive and current, so its repair work is about that signal. A
consumer's problem is that the transport underneath fails, and it finds out
when the connection drops.

**Tooling behaves like consumers** — reconnect 12%, heartbeat 6% — which is
what should happen if the classification means anything: a client library
connects to somebody else's feed and hits the consumer's side of the problem.

Counting whole messages rather than subjects moves the levels but not the
split: reconnect 14% for consumers against 4% for publishers, heartbeat 10%
against 22%.

## What this does not show

**A commit proves engineering time was spent. It does not prove anyone would
buy a tool.** Those are different claims and this dataset only supports the
first. Nothing here says the work is unwelcome, mispriced, or worth
outsourcing — only that it recurs, and that where it recurs depends on which
side of the feed you sit.

**Nor does it show severity.** A one-line timeout bump and a week reconstructing
a bad window are one commit each.

## Reproducing this

No dependencies beyond Python 3. A token is needed in `GITHUB_TOKEN` — commit
search is not available anonymously.

```sh
export GITHUB_TOKEN=...
python3 collect.py orgs.txt   # -> raw.json
python3 analyse.py            # -> data/commits.csv, prints the tables above
```

Duplicate commits are dropped **within** an organisation, not across the run.
Two organisations holding the same fork both legitimately contain that commit,
and a set shared across the whole run gives it to whichever was queried first
while the second silently loses it — with the progress line still printing the
count the API returned. That defect was found on 8 September while running the
same collector over a larger list, where it cost one organisation four commits.
It did not affect this dataset: the eight organisations here that produced no
rows were re-queried and all eight genuinely return nothing.

`collect.py` reads the 56 organisations in [`orgs.txt`](orgs.txt), asks for the
newest 40 matches in each, and stores whole commit messages. It pauses 3.5
seconds between requests and retries on the secondary rate limit — a first pass
without that quietly lost 28 organisations and reported success.

`analyse.py` assigns each commit one fault by first match against the patterns
at the top of the file. Those patterns are the six search terms and their
spellings and nothing else: the sample was selected by those terms, so a bucket
for a synonym would count something the query never asked for. The order only
decides 47 of 1,163 commits — 4% — because the rest carry exactly one term.

Whole messages are kept in `raw.json` because that is where the term often is.
Squashed pull requests here run to 64,000 characters and the matching word can
sit at offset 14,000; an earlier 300-character cut put a third of the sample in
an "other" bucket that should not have existed.

Run `analyse.py` against the committed `raw.json` and you get
[`data/commits.csv`](data/commits.csv) byte for byte, so a disagreement is with
a rule you can read rather than a number you have to trust.

Cells opening with `=`, `+`, `-` or `@` are prefixed with a quote before being
written. Commit subjects are whatever someone typed, and a spreadsheet would
treat such a cell as a formula.

Re-running `collect.py` today will not reproduce this dataset — repositories
move on. `raw.json` is committed so the analysis stays checkable regardless.

## Data

[`data/commits.csv`](data/commits.csv) — 1,163 rows: class, organisation,
repository, date, fault, author login, subject, and a link to the commit.

[`raw.json`](raw.json) — what the collector saw, with whole commit messages.
Faults are derived from these, so this is what to look at if a classification
seems wrong.

Author logins are recorded where GitHub publishes them. Commit metadata also
carries email addresses; those are not collected.

Corrections are welcome. If an organisation is in the wrong class or a fault is
misassigned, the link is right there and I would rather fix it.

---

*Andrey Karazhev · [minihub.app](https://minihub.app)*
