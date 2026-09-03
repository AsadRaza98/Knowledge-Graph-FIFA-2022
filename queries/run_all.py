"""
run_all.py
Executes every queries/q*.rq file against kg/worldcup_full.ttl, prints the
result table and the wall-clock time. This is the Task 4 retrieval demo.

    python queries\run_all.py
"""

import os
import sys
import glob
import time
import io

from rdflib import Graph

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
GRAPH_FILE = os.path.join(PROJECT, "kg", "worldcup_full.ttl")


def main():
    print(f"loading {os.path.relpath(GRAPH_FILE, PROJECT)} ...")
    g = Graph()
    t0 = time.perf_counter()
    g.parse(GRAPH_FILE, format="turtle")
    print(f"  {len(g):,} triples in {time.perf_counter()-t0:.2f}s\n")

    for rq in sorted(glob.glob(os.path.join(HERE, "q*.rq"))):
        name = os.path.basename(rq)
        q = open(rq, encoding="utf-8").read()
        title = q.splitlines()[0].lstrip("# ").strip()
        print("=" * 78)
        print(f"{name}  |  {title}")
        print("=" * 78)
        t0 = time.perf_counter()
        res = g.query(q)
        rows = list(res)
        dt = (time.perf_counter() - t0) * 1000

        cols = [str(v) for v in res.vars]
        print("  " + " | ".join(cols))
        print("  " + "-" * 74)
        for r in rows[:25]:
            print("  " + " | ".join("" if r[v] is None else str(r[v]) for v in res.vars))
        extra = f"  ... (+{len(rows)-25} more)" if len(rows) > 25 else ""
        print(f"\n  {len(rows)} row(s){extra}   |   {dt:.1f} ms\n")


if __name__ == "__main__":
    main()
