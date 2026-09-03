r"""
run_all_endpoint.py
Run every queries/q*.rq against a live SPARQL endpoint (default: the local
GraphDB repository) and time each one. Use this once the KG is loaded in
GraphDB to get realistic triplestore latencies for evaluation/results.md.

    python queries\run_all_endpoint.py
    python queries\run_all_endpoint.py http://localhost:7200/repositories/worldcup2022

No extra dependencies - plain urllib POST, JSON results.
"""

import os
import sys
import glob
import time
import json
import io
import urllib.request
import urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ENDPOINT = (sys.argv[1] if len(sys.argv) > 1
            else "http://localhost:7200/repositories/worldcup2022")


def run(query):
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(
        ENDPOINT, data=data,
        headers={"Accept": "application/sparql-results+json",
                 "Content-Type": "application/x-www-form-urlencoded"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    dt = (time.perf_counter() - t0) * 1000
    res = payload["results"]["bindings"]
    cols = payload["head"]["vars"]
    return cols, res, dt


def main():
    print(f"endpoint: {ENDPOINT}\n")
    total = 0.0
    for rq in sorted(glob.glob(os.path.join(HERE, "q*.rq"))):
        name = os.path.basename(rq)
        q = open(rq, encoding="utf-8").read()
        title = q.splitlines()[0].lstrip("# ").strip()
        try:
            cols, rows, dt = run(q)
        except Exception as e:
            print(f"{name:<40} ERROR  {e}")
            continue
        total += dt
        print("=" * 78)
        print(f"{name}  |  {title}")
        print(f"  {' | '.join(cols)}")
        print("  " + "-" * 74)
        for b in rows[:15]:
            print("  " + " | ".join(b.get(c, {}).get("value", "") for c in cols))
        more = f"  (+{len(rows)-15} more)" if len(rows) > 15 else ""
        print(f"  {len(rows)} row(s){more}   |   {dt:.1f} ms\n")
    print(f"TOTAL query time: {total:.0f} ms across all queries")


if __name__ == "__main__":
    main()
