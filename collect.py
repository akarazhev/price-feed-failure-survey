#!/usr/bin/env python3
"""Collect commits that repair feed handling, across a list of organisations.

Reads orgs.txt, asks the GitHub commit search API for the newest matching
commits in each organisation, and writes raw.json.

Needs a token in GITHUB_TOKEN — commit search is not available anonymously.
Standard library only.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Six terms, and six is the ceiling: GitHub allows at most five OR operators
# in a search query. A seventh makes every request fail with 422.
TERMS = ["stale", "reconnect", "heartbeat", "backfill", "desync", "resubscribe"]

# Newest N per organisation. Mandatory, not tidiness: smartcontractkit alone
# returns more matches than the other nine publishers together, and uncapped
# the publisher class would mean Chainlink.
CAP = 40

PAUSE = 3.5          # search allows 30/min, but a stricter secondary
                     # limit trips on sustained bursts well under that
API = "https://api.github.com"


def read_orgs(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#") or "\t" not in line:
            continue
        cls, org = line.split("\t", 1)
        out.append((cls.strip(), org.strip()))
    return out


def get(url, token, tries=5):
    """GET with backoff. The secondary rate limit answers 403 and recovers on
    its own; a first pass without this quietly lost 28 of 51 organisations."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "feed-observability-survey",
        "Authorization": f"Bearer {token}",
    })
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429, 500, 502, 503) or attempt == tries - 1:
                raise
            wait = int(e.headers.get("retry-after") or 0) or 2 ** (attempt + 3)
            print(f"      HTTP {e.code}, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)


def search(org, token):
    q = "org:%s %s" % (org, " OR ".join(TERMS))
    url = "%s/search/commits?%s" % (API, urllib.parse.urlencode({
        "q": q, "sort": "committer-date", "order": "desc", "per_page": CAP,
    }))
    return get(url, token)


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("set GITHUB_TOKEN — commit search needs authentication")

    orgs = read_orgs(sys.argv[1] if len(sys.argv) > 1 else "orgs.txt")
    records, empty, failed = [], [], []

    for i, (cls, org) in enumerate(orgs, 1):
        try:
            data = search(org, token)
        except urllib.error.HTTPError as e:
            # Never swallow these, and never let them scroll away either:
            # they are re-reported at the end and set the exit code.
            print(f"  [{i}/{len(orgs)}] {org}: HTTP {e.code} {e.reason}", file=sys.stderr)
            failed.append((org, f"HTTP {e.code}"))
            time.sleep(PAUSE)
            continue

        items = data.get("items", [])
        if not items:
            empty.append(org)

        # Per organisation, not per run. A shared set silently drops an
        # organisation's commits when an earlier one already returned the same
        # sha - which happens whenever two organisations hold the same fork -
        # and the progress line still prints the count the API returned, so the
        # log says four and the data holds none. That is the same silent loss
        # the retry above exists to prevent, one level down.
        seen = set()
        for it in items:
            sha = it["sha"]
            if sha in seen:                       # forks inside one org
                continue
            seen.add(sha)
            commit = it["commit"]
            author = it.get("author") or {}
            records.append({
                "class": cls,
                "org": org,
                "repo": it["repository"]["full_name"],
                "sha": sha,
                "date": commit["committer"]["date"][:10],
                # login only. Commit metadata carries addresses; we do not take them.
                "author": author.get("login") or "",
                # The whole message, untruncated. Squashed pull requests run
                # to 17,000 characters here and the term that matched can sit
                # at offset 14,000; a 300-character cut put a third of the
                # sample in "other". analyse.py trims it for the CSV.
                "message": " ".join(commit["message"].split()),
                "url": it["html_url"],
            })

        print(f"  [{i}/{len(orgs)}] {cls:<9} {org:<22} {len(items):>3}"
              f"  of {data.get('total_count', 0)}")
        time.sleep(PAUSE)

    with open("raw.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1, sort_keys=True)

    queried = len(orgs) - len(failed)
    print(f"\n{len(records)} commits from {queried - len(empty)} of {queried} organisations")
    if empty:
        print(f"no matches in {len(empty)}: {', '.join(empty)}")
    if failed:
        print(f"\nFAILED {len(failed)} — the sample is incomplete, rerun before using it:")
        for org, why in failed:
            print(f"  {org}: {why}")
        sys.exit(1)


if __name__ == "__main__":
    main()
