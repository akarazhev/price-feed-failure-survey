#!/usr/bin/env python3
"""Turn raw.json into data/commits.csv and print the tables in the report.

Standard library only. Deterministic: run it against the committed raw.json
and you get the committed CSV byte for byte.
"""

import csv
import json
import re
import statistics as st
from collections import Counter, defaultdict

# Order is priority: a message mentioning both "stale" and "reconnect" is
# counted as stale, because the staleness is what was wrong and the reconnect
# is how it was handled.
# The patterns are the six search terms and their spellings, nothing more.
# Synonyms were tried and dropped: the sample was selected by these six terms,
# so a bucket for "liveness" or "sequence gap" would count something the query
# never asked for and could not have found evenly.
FAILURES = [
    ("stale",       r"stale"),
    ("desync",      r"desync"),
    ("backfill",    r"back[- ]?fill"),
    ("heartbeat",   r"heart[- ]?beat"),
    ("resubscribe", r"re[- ]?subscrib"),
    ("reconnect",   r"re[- ]?connect"),
]
PATTERNS = [(name, re.compile(rx, re.I)) for name, rx in FAILURES]

CAP = 40  # must match collect.py; used to flag truncated organisations

CLASSES = ("PUBLISHER", "CONSUMER", "INDEXER", "TOOLING")

# A cell starting with any of these is a formula to a spreadsheet. Commit
# messages are written by strangers and this file is meant to be opened.
FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


def defuse(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(FORMULA_LEAD) else text


def classify(message):
    for name, rx in PATTERNS:
        if rx.search(message):
            return name
    return "other"   # unreachable: every commit was found by one of the terms


def median(values):
    return st.median(values) if values else 0


def main():
    records = json.load(open("raw.json", encoding="utf-8"))
    for r in records:
        r["failure"] = classify(r["message"])
    records.sort(key=lambda r: (r["class"], r["org"], r["repo"], r["date"], r["sha"]))

    # raw.json keeps whole messages because that is what the fault is read
    # from; the CSV keeps the subject, because it is meant to be read.
    with open("data/commits.csv", "w", newline="", encoding="utf-8") as f:
        # Explicit LF. The csv module defaults to CRLF, git rewrites it to LF on
        # commit, and the file a cloner regenerates then differs from the file in
        # the repository - which would make the byte-for-byte claim below false
        # for everyone except the author.
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["class", "org", "repo", "date", "failure", "author", "subject", "url"])
        for r in records:
            row = [r["class"], r["org"], r["repo"], r["date"], r["failure"],
                   r["author"], r["message"][:160], r["url"]]
            w.writerow([defuse(v) for v in row])

    by_class = defaultdict(list)
    for r in records:
        by_class[r["class"]].append(r)

    print("## Sample\n")
    print(f"{'class':<10} {'orgs':>5} {'repos':>6} {'commits':>8}")
    for cls in CLASSES:
        rs = by_class[cls]
        print(f"{cls:<10} {len({r['org'] for r in rs}):>5} "
              f"{len({r['repo'] for r in rs}):>6} {len(rs):>8}")

    print("\n## Recurrence — repositories where the same class of fault came back\n")
    print(f"{'class':<10} {'repos':>6} {'>=2':>5} {'share':>7} {'median':>7} {'max':>5}")
    for cls in CLASSES:
        per_repo = Counter(r["repo"] for r in by_class[cls])
        if not per_repo:
            continue
        counts = sorted(per_repo.values())
        rep = sum(1 for c in counts if c >= 2)
        print(f"{cls:<10} {len(counts):>6} {rep:>5} {rep/len(counts)*100:>6.0f}% "
              f"{median(counts):>7.0f} {max(counts):>5}")

    print("\n## Recurrence, organisations under the cap only\n")
    print("Capped organisations are truncated to the newest %d, which can only hide\n"
          "recurrence, never invent it. These are the ones returning everything." % CAP)
    print()
    print(f"{'class':<10} {'orgs':>5} {'repos':>6} {'>=2':>5} {'share':>7}")
    for cls in CLASSES:
        per_org = Counter(r["org"] for r in by_class[cls])
        under = {o for o, n in per_org.items() if n < CAP}
        rs = [r for r in by_class[cls] if r["org"] in under]
        if not rs:
            continue
        per_repo = Counter(r["repo"] for r in rs)
        counts = list(per_repo.values())
        rep = sum(1 for c in counts if c >= 2)
        print(f"{cls:<10} {len(under):>5} {len(counts):>6} {rep:>5} "
              f"{rep/len(counts)*100:>6.0f}%")

    amb = sum(1 for r in records
              if sum(1 for _, rx in PATTERNS if rx.search(r["message"])) > 1)
    print(f"\n## What breaks — share of commits by fault, within each class\n")
    print(f"Exclusive: first pattern in the list above wins. That decides only "
          f"{amb} of\n{len(records)} commits ({amb/len(records)*100:.0f}%) — the rest "
          f"carry exactly one term.\n")
    names = [n for n, _ in FAILURES]
    print(f"{'class':<10} " + " ".join(f"{n:>11}" for n in names))
    for cls in CLASSES:
        rs = by_class[cls]
        if not rs:
            continue
        c = Counter(r["failure"] for r in rs)
        print(f"{cls:<10} " + " ".join(f"{c[n]/len(rs)*100:>10.0f}%" for n in names))

    print("\n## What the commit announces itself as — term in the first 120 characters\n")
    print("Stricter, and it is the subject a reviewer reads. A term buried at offset\n"
          "14,000 of a squashed pull request says less than one in the summary line.\n")
    print(f"{'class':<10} {'n':>5} " + " ".join(f"{n:>11}" for n in names))
    for cls in CLASSES:
        rs = by_class[cls]
        if not rs:
            continue
        line = f"{cls:<10} {len(rs):>5} "
        for n, rx in PATTERNS:
            hit = sum(1 for r in rs if rx.search(r["message"][:120]))
            line += f"{hit/len(rs)*100:>10.0f}%"
            line += " "
        print(line.rstrip())

    print(f"\n{len(records)} commits, {len({r['repo'] for r in records})} repositories, "
          f"{len({r['org'] for r in records})} organisations")


if __name__ == "__main__":
    main()
