"""
04_image_features.py
Step 3 (b): Multimedia feature extraction for the player-image dataset.

For each player that has an image folder (from player_master_2022.csv):
  * pick one representative photo
  * run it through an ImageNet-pretrained ResNet-50 (penultimate layer)
    -> a 2048-d visual feature vector
  * L2-normalize it

Outputs (in images/):
  player_features.npy         float32 [N, 2048]  - full vectors (for retrieval)
  player_features_index.csv   player_id, full_name, team, folder, ok
  player_features_pca.npy     float32 [N, 128]   - PCA-reduced (compact)

Outputs (in kg/):
  worldcup_images.ttl         adds wc:featureVector (128-d JSON) to PlayerImage
  worldcup_full.ttl           re-merged TBox + ABox + image features

Run from the worldcup-kg folder (CPU is fine, a few minutes):
    python notebooks\04_image_features.py
"""

import os
import re
import json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
PROC = os.path.join(PROJECT, "data", "processed")
IMG_OUT = os.path.join(PROJECT, "images")
KG = os.path.join(PROJECT, "kg")
TBOX = os.path.join(PROJECT, "ontology", "worldcup_tbox.ttl")
os.makedirs(IMG_OUT, exist_ok=True)

EXTS = (".jpg", ".jpeg", ".png")
PCA_DIM = 128


def representative_image(folder_abs):
    if not os.path.isdir(folder_abs):
        return None
    files = sorted(f for f in os.listdir(folder_abs) if f.lower().endswith(EXTS))
    return os.path.join(folder_abs, files[0]) if files else None


def build_extractor():
    import torch
    import torchvision.models as models
    from torchvision.models import ResNet50_Weights

    weights = ResNet50_Weights.IMAGENET1K_V2
    net = models.resnet50(weights=weights)
    net.fc = torch.nn.Identity()          # keep the 2048-d pooled features
    net.eval()
    preprocess = weights.transforms()
    return net, preprocess, torch


def main():
    from PIL import Image

    pm = pd.read_csv(os.path.join(PROC, "player_master_2022.csv"))
    pm = pm[pm.has_image & pm.folder_path.notna()].copy()
    print(f"players with an image folder: {len(pm)}")

    net, preprocess, torch = build_extractor()

    vecs, rows = [], []
    with torch.no_grad():
        for k, (_, r) in enumerate(pm.iterrows(), 1):
            folder_abs = os.path.join(PROJECT, str(r.folder_path))
            img_path = representative_image(folder_abs)
            ok = img_path is not None
            v = np.zeros(2048, dtype=np.float32)
            if ok:
                try:
                    im = Image.open(img_path).convert("RGB")
                    x = preprocess(im).unsqueeze(0)
                    v = net(x).squeeze(0).cpu().numpy().astype(np.float32)
                    n = np.linalg.norm(v)
                    if n > 0:
                        v = v / n
                except Exception as e:
                    ok = False
                    print(f"  !! {r.full_name}: {e}")
            vecs.append(v)
            rows.append({
                "player_id": r.player_id,
                "full_name": r.full_name,
                "team": r.team_name,
                "folder": str(r.folder_path).replace("\\", "/"),
                "ok": ok,
            })
            if k % 100 == 0:
                print(f"  {k}/{len(pm)} ...")

    X = np.vstack(vecs)
    idx = pd.DataFrame(rows)
    np.save(os.path.join(IMG_OUT, "player_features.npy"), X)
    idx.to_csv(os.path.join(IMG_OUT, "player_features_index.csv"), index=False)
    print(f"\n  saved player_features.npy  {X.shape}")
    print(f"  extracted OK: {int(idx.ok.sum())} / {len(idx)}")

    # ---- PCA-reduce for a compact KG literal ---------------------------
    from sklearn.decomposition import PCA

    mask = idx.ok.values
    pca = PCA(n_components=PCA_DIM, random_state=0)
    Xr = np.zeros((len(idx), PCA_DIM), dtype=np.float32)
    Xr[mask] = pca.fit_transform(X[mask]).astype(np.float32)
    np.save(os.path.join(IMG_OUT, "player_features_pca.npy"), Xr)
    print(f"  saved player_features_pca.npy  {Xr.shape}  "
          f"(explained var {pca.explained_variance_ratio_.sum():.2f})")

    # ---- write feature triples --------------------------------------------
    from rdflib import Graph, Namespace, Literal
    WC = Namespace("http://www.semanticweb.org/worldcup2022#")

    g = Graph()
    g.bind("wc", WC)

    def uid(prefix, raw):
        s = re.sub(r"[^A-Za-z0-9_]+", "_", str(raw)).strip("_")
        return WC[f"{prefix}_{s}"]

    added = 0
    for i, r in idx.iterrows():
        if not r.ok:
            continue
        img = uid("img", r.player_id)
        payload = json.dumps([round(float(x), 5) for x in Xr[i]])
        g.add((img, WC.featureVector, Literal(payload)))
        added += 1
    img_ttl = os.path.join(KG, "worldcup_images.ttl")
    g.serialize(destination=img_ttl, format="turtle")
    print(f"  wrote {os.path.relpath(img_ttl, PROJECT)}  ({added} featureVector triples)")

    # ---- re-merge the full graph ----------------------------------------
    full = Graph()
    full.parse(TBOX, format="turtle")
    full.parse(os.path.join(KG, "worldcup_abox.ttl"), format="turtle")
    full.parse(img_ttl, format="turtle")
    full.serialize(destination=os.path.join(KG, "worldcup_full.ttl"), format="turtle")
    print(f"  re-merged worldcup_full.ttl  ({len(full):,} triples)")
    print("\nDONE.")


if __name__ == "__main__":
    main()
