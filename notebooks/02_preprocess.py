"""
02_preprocess.py
Step 2: Preprocess & clean data, scoped to the FIFA World Cup 2022.

Produces clean, integrated tables in data/processed/ that the KG-builder
(Step 3) will turn into RDF triples:

  Entity tables (filtered to WC-2022):
    tournament_2022.csv, teams_2022.csv, players_2022.csv, squads_2022.csv,
    matches_2022.csv, goals_2022.csv, stadiums_2022.csv

  Enrichment:
    player_stats_2022_clean.csv   (cleaned Kaggle per-player stats)
    image_index.csv               (one row per player photo folder)
    player_master_2022.csv        (squad players linked to stats + images)

Run from the worldcup-kg folder:
    python notebooks\02_preprocess.py
"""

import os
import re
import glob
import unicodedata
import pandas as pd

# --------------------------------------------------------------------------
# Paths & config
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
RAW = os.path.join(PROJECT, "data", "raw")
PROCESSED = os.path.join(PROJECT, "data", "processed")
WC = os.path.join(RAW, "worldcup", "data-csv")
IMG_ROOT = os.path.join(RAW, "player-images", "Images", "Images")
STATS_FILE = os.path.join(RAW, "player-stats-fifa-22", "FIFA WC 2022 Players Stats.csv")
STANDINGS_FILE = os.path.join(RAW, "tournament-standings-history", "FIFA - 2022.csv")

TID = "WC-2022"          # tournament id for the 2022 men's World Cup
os.makedirs(PROCESSED, exist_ok=True)


def save(df, name):
    out = os.path.join(PROCESSED, name)
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"  saved {name:<32} ({len(df):,} rows, {len(df.columns)} cols)")


def read_csv_smart(path):
    """Detect encoding at the byte level: if the file is valid utf-8 use it,
    otherwise fall back to latin-1 (many of these source files are latin-1).
    Byte-level detection avoids pandas silently inserting replacement chars."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        raw.decode("utf-8")
        enc = "utf-8"
    except UnicodeDecodeError:
        enc = "latin-1"
    return pd.read_csv(path, encoding=enc, low_memory=False)


def fix_mojibake(s):
    """The image zip was extracted with the wrong code page, so accented
    filenames became mojibake (e.g. 'Mart├¡nez'). Recover by re-encoding to
    cp437/cp850 bytes and decoding as utf-8. ASCII names pass through."""
    if not isinstance(s, str):
        return s
    for cp in ("cp437", "cp850"):
        try:
            return s.encode(cp).decode("utf-8")
        except (UnicodeError, UnicodeDecodeError):
            continue
    return s


def norm_name(s):
    """Normalize a person/team name for matching: strip accents, lowercase,
    remove punctuation, collapse whitespace."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))  # drop accents
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)     # punctuation -> space
    s = re.sub(r"\s+", " ", s).strip()
    return s


# --------------------------------------------------------------------------
# PART 1 - Filter the worldcup (GitHub) tables to WC-2022
# --------------------------------------------------------------------------
def part1_worldcup_entities():
    print("\n[1] Filtering worldcup tables to WC-2022 ...")

    tournaments = read_csv_smart(os.path.join(WC, "tournaments.csv"))
    save(tournaments[tournaments.tournament_id == TID], "tournament_2022.csv")

    squads = read_csv_smart(os.path.join(WC, "squads.csv"))
    squads22 = squads[squads.tournament_id == TID].copy()
    save(squads22, "squads_2022.csv")

    # players: keep only those in the 2022 squads, join bio from players.csv
    players = read_csv_smart(os.path.join(WC, "players.csv"))
    pids = squads22.player_id.unique()
    players22 = players[players.player_id.isin(pids)].copy()
    save(players22, "players_2022.csv")

    # teams: the 32 teams present in 2022, with full team metadata
    teams = read_csv_smart(os.path.join(WC, "teams.csv"))
    tids = squads22.team_id.unique()
    teams22 = teams[teams.team_id.isin(tids)].copy()
    save(teams22, "teams_2022.csv")

    matches = read_csv_smart(os.path.join(WC, "matches.csv"))
    matches22 = matches[matches.tournament_id == TID].copy()
    save(matches22, "matches_2022.csv")

    goals = read_csv_smart(os.path.join(WC, "goals.csv"))
    save(goals[goals.tournament_id == TID], "goals_2022.csv")

    # stadiums used in 2022 matches
    stadiums = read_csv_smart(os.path.join(WC, "stadiums.csv"))
    used = matches22.stadium_id.unique()
    save(stadiums[stadiums.stadium_id.isin(used)], "stadiums_2022.csv")

    return squads22, players22, teams22


# --------------------------------------------------------------------------
# PART 2 - Clean the Kaggle 2022 per-player stats
# --------------------------------------------------------------------------
def part2_clean_stats():
    print("\n[2] Cleaning 2022 player stats ...")
    df = read_csv_smart(STATS_FILE)
    # strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]
    # strip whitespace from string cells
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()
    # percentage columns -> float
    for c in ["Save Percentage", "Clean Sheets"]:
        if c in df.columns:
            df[c] = (df[c].astype(str).str.replace("%", "", regex=False)
                     .replace({"nan": None}))
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # normalized name for joining
    name_col = "Player Name" if "Player Name" in df.columns else df.columns[7]
    df["name_norm"] = df[name_col].apply(norm_name)
    save(df, "player_stats_2022_clean.csv")
    return df


# --------------------------------------------------------------------------
# PART 2b - Clean the WC-2022 final standings (Kaggle FIFA - 2022.csv)
# --------------------------------------------------------------------------
def part2b_standings():
    print("\n[2b] Cleaning 2022 final standings ...")
    df = read_csv_smart(STANDINGS_FILE)
    df.columns = [c.strip() for c in df.columns]
    # align team names to the worldcup source spelling (only USA differs)
    alias = {"USA": "United States"}
    df["Team"] = df["Team"].astype(str).str.strip()
    df["team_name"] = df["Team"].replace(alias)
    df["team_norm"] = df["team_name"].apply(norm_name)
    for c in ["Position", "Games Played", "Win", "Draw", "Loss",
              "Goals For", "Goals Against", "Goal Difference", "Points"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    save(df, "standings_2022.csv")
    return df


# --------------------------------------------------------------------------
# PART 3 - Build an index of the player image folders
# --------------------------------------------------------------------------
def part3_image_index():
    print("\n[3] Building image index ...")
    exts = (".jpg", ".jpeg", ".png")
    rows = []
    if not os.path.isdir(IMG_ROOT):
        print("  !! image root not found")
        return pd.DataFrame()
    for group in sorted(os.listdir(IMG_ROOT)):
        gpath = os.path.join(IMG_ROOT, group)
        if not os.path.isdir(gpath):
            continue
        for teamdir in sorted(os.listdir(gpath)):
            tpath = os.path.join(gpath, teamdir)
            if not os.path.isdir(tpath):
                continue
            # "Argentina Players" -> "Argentina"; handle 'Netherland'
            teamdir = fix_mojibake(teamdir)
            team = re.sub(r"\s+players$", "", teamdir, flags=re.I).strip()
            if team.lower() == "netherland":
                team = "Netherlands"
            for pdir in sorted(os.listdir(tpath)):
                ppath = os.path.join(tpath, pdir)
                if not os.path.isdir(ppath):
                    continue
                # fix mojibake, drop 'Images_' prefix and '(captain)' suffix
                player = fix_mojibake(pdir)
                player = re.sub(r"^Images_", "", player)
                player = re.sub(r"\(.*?\)", "", player).strip()
                imgs = [f for f in os.listdir(ppath)
                        if f.lower().endswith(exts)]
                rel = os.path.relpath(ppath, PROJECT)
                rows.append({
                    "group": group,
                    "image_team": team,
                    "image_player": player,
                    "name_norm": norm_name(player),
                    "team_norm": norm_name(team),
                    "image_count": len(imgs),
                    "folder_path": rel,
                })
    idx = pd.DataFrame(rows)
    save(idx, "image_index.csv")
    return idx


# --------------------------------------------------------------------------
# PART 4 - Link squad players -> stats + images (by normalized name)
# --------------------------------------------------------------------------
def part4_link(squads22, stats, images):
    print("\n[4] Linking players across sources ...")
    sq = squads22.copy()
    # some players go by one name; given/family may be 'not applicable'
    placeholders = {"not applicable", "not available", "n/a", "na", "nan"}
    gn = sq["given_name"].fillna("").where(
        ~sq["given_name"].fillna("").str.lower().isin(placeholders), "")
    fn = sq["family_name"].fillna("").where(
        ~sq["family_name"].fillna("").str.lower().isin(placeholders), "")
    sq["full_name"] = (gn + " " + fn).str.strip()
    sq["name_norm"] = sq["full_name"].apply(norm_name)
    sq["team_norm"] = sq["team_name"].apply(norm_name)

    # link to stats (name only - stats has no reliable team key formatting)
    stats_small = stats[["name_norm"]].copy()
    stats_small["has_stats"] = True
    stats_small = stats_small.drop_duplicates("name_norm")
    m = sq.merge(stats_small, on="name_norm", how="left")

    # link to images (name + team to disambiguate)
    if not images.empty:
        img_small = (images[["name_norm", "team_norm", "image_count",
                             "folder_path"]]
                     .drop_duplicates(["name_norm", "team_norm"]))
        m = m.merge(img_small, on=["name_norm", "team_norm"], how="left")
        # fallback: match on name only if team-based match failed
        miss = m["folder_path"].isna()
        if miss.any():
            img_name_only = (images.sort_values("image_count", ascending=False)
                             .drop_duplicates("name_norm")
                             [["name_norm", "image_count", "folder_path"]]
                             .rename(columns={"image_count": "ic2",
                                              "folder_path": "fp2"}))
            m = m.merge(img_name_only, on="name_norm", how="left")
            m.loc[miss, "folder_path"] = m.loc[miss, "fp2"]
            m.loc[miss, "image_count"] = m.loc[miss, "ic2"]
            m = m.drop(columns=["fp2", "ic2"])

    m["has_stats"] = m["has_stats"].fillna(False)
    m["has_image"] = m["folder_path"].notna()
    save(m, "player_master_2022.csv")

    # report match rates
    n = len(m)
    print("\n  ---- LINKING REPORT ----")
    print(f"  squad players (2022) : {n}")
    print(f"  linked to stats      : {int(m.has_stats.sum())}  "
          f"({m.has_stats.mean()*100:.1f}%)")
    print(f"  linked to images     : {int(m.has_image.sum())}  "
          f"({m.has_image.mean()*100:.1f}%)")
    # show a few unmatched (for later fuzzy-matching refinement)
    no_img = m[~m.has_image][["full_name", "team_name"]].head(10)
    if len(no_img):
        print("\n  sample players with NO image match (name spelling diffs):")
        for _, r in no_img.iterrows():
            print(f"      {r.full_name}  ({r.team_name})")
    return m


def main():
    print("=" * 70)
    print("PREPROCESSING  |  scope: FIFA World Cup 2022")
    print("=" * 70)
    squads22, players22, teams22 = part1_worldcup_entities()
    stats = part2_clean_stats()
    part2b_standings()
    images = part3_image_index()
    part4_link(squads22, stats, images)
    print("\n" + "=" * 70)
    print(f"DONE. Clean tables written to: {os.path.relpath(PROCESSED, PROJECT)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
