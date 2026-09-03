r"""
image_similarity.py
Multimedia (content-based) retrieval demo for Task 4:
"given a player photo, return the visually most similar players".

Uses the 2048-d ResNet-50 feature vectors from 04_image_features.py
(images/player_features.npy) and ranks by cosine similarity. Each result
is linked back to its KG node (wc:player_<id>).

    python queries\image_similarity.py "Lionel Messi"
    python queries\image_similarity.py            # uses a default query player
"""

import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
IMG = os.path.join(PROJECT, "images")
WC = "http://www.semanticweb.org/worldcup2022#"


def main():
    query_name = sys.argv[1] if len(sys.argv) > 1 else "Kylian Mbappe"

    X = np.load(os.path.join(IMG, "player_features.npy"))
    idx = pd.read_csv(os.path.join(IMG, "player_features_index.csv"))
    ok = idx.ok.values.astype(bool)

    # find the query row (case / accent-insensitive contains)
    key = query_name.lower()
    cand = idx.index[idx.full_name.str.lower().str.contains(key, na=False)]
    cand = [i for i in cand if ok[i]]
    if not cand:
        print(f"no image-feature row matching '{query_name}'")
        print("examples:", ", ".join(idx.full_name[ok].head(8)))
        return
    qi = cand[0]

    # cosine similarity (vectors are already L2-normalised -> dot product)
    sims = X @ X[qi]
    sims[~ok] = -1.0
    order = np.argsort(-sims)

    print(f"query player : {idx.full_name[qi]}  ({idx.team[qi]})")
    print(f"KG node      : wc:player_{idx.player_id[qi].replace('-', '_')}")
    print(f"\n  {'rank':<5}{'similarity':<12}{'player':<26}{'team'}")
    print("  " + "-" * 60)
    shown = 0
    for j in order:
        if j == qi:
            continue
        pid = str(idx.player_id[j]).replace("-", "_")
        print(f"  {shown+1:<5}{sims[j]:<12.4f}{idx.full_name[j]:<26}{idx.team[j]}"
              f"   wc:player_{pid}")
        shown += 1
        if shown >= 10:
            break


if __name__ == "__main__":
    main()
