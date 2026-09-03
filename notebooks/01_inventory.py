"""
01_inventory.py
Step 2 (start): Inventory every dataset in data/raw so we understand the
structure before cleaning and ontology design.

For each CSV: prints row count, column count, column names, dtypes, and a
sample row. Also summarizes the player-images folder (teams + image count).

Run from the worldcup-kg folder:
    python notebooks\01_inventory.py
"""

import os
import glob
import pandas as pd

# --- locate data/raw relative to this script -------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
RAW = os.path.join(PROJECT, "data", "raw")

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


def hr(char="=", n=90):
    print(char * n)


def inventory_csv(path):
    rel = os.path.relpath(path, RAW)
    hr("-")
    print(f"FILE: {rel}")
    try:
        # low_memory=False avoids dtype-guess warnings on big files
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        print(f"  !! could not read: {e}")
        return None
    print(f"  rows: {len(df):,}   columns: {len(df.columns)}")
    print(f"  columns: {list(df.columns)}")
    # show a compact sample (first row) transposed for readability
    if len(df) > 0:
        print("  sample row:")
        first = df.iloc[0]
        for col, val in first.items():
            sval = str(val)
            if len(sval) > 60:
                sval = sval[:57] + "..."
            print(f"      {col:<28} = {sval}")
    return df


def main():
    hr()
    print("DATASET INVENTORY  |  data/raw")
    print(f"path: {RAW}")
    hr()

    # all CSVs under data/raw, sorted, grouped by their top folder
    csvs = sorted(glob.glob(os.path.join(RAW, "**", "*.csv"), recursive=True))
    print(f"\nFound {len(csvs)} CSV files.\n")

    total_rows = 0
    for path in csvs:
        df = inventory_csv(path)
        if df is not None:
            total_rows += len(df)

    # --- image dataset summary --------------------------------------------
    hr()
    print("IMAGE DATASET SUMMARY")
    hr()
    img_root = os.path.join(RAW, "player-images", "Images", "Images")
    if os.path.isdir(img_root):
        exts = (".jpg", ".jpeg", ".png")
        img_count = 0
        team_dirs = set()
        player_dirs = set()
        for root, dirs, files in os.walk(img_root):
            for f in files:
                if f.lower().endswith(exts):
                    img_count += 1
            depth = os.path.relpath(root, img_root).count(os.sep)
            if depth == 1:   # <Group>/<Team>
                team_dirs.add(root)
            if depth == 2:   # <Group>/<Team>/Images_<Player>
                player_dirs.add(root)
        print(f"  image root : {os.path.relpath(img_root, RAW)}")
        print(f"  groups     : {len(os.listdir(img_root))}")
        print(f"  teams      : {len(team_dirs)}")
        print(f"  players    : {len(player_dirs)}")
        print(f"  images     : {img_count:,}")
    else:
        print("  (image folder not found at expected path)")

    hr()
    print(f"DONE. {len(csvs)} CSVs, {total_rows:,} total rows across CSVs.")
    hr()


if __name__ == "__main__":
    main()
