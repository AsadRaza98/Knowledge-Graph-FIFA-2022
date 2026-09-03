"""
03_build_kg.py
Step 3 (a): Knowledge Graph construction.

Reads the clean tables in data/processed/ and emits the ABox (instance data)
as RDF triples that conform to ontology/worldcup_tbox.ttl.

Outputs (in kg/):
    worldcup_abox.ttl   - instances only
    worldcup_full.ttl   - TBox + ABox merged (load this into the graph DB)

Multimedia note: PlayerImage nodes get folderPath + imageCount here.
The featureVector literal is added later by 04_image_features.py.

Run from the worldcup-kg folder:
    python notebooks\03_build_kg.py
"""

import os
import re
import math
import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

# --------------------------------------------------------------------------
# Paths & namespace
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
PROC = os.path.join(PROJECT, "data", "processed")
KG = os.path.join(PROJECT, "kg")
TBOX = os.path.join(PROJECT, "ontology", "worldcup_tbox.ttl")
os.makedirs(KG, exist_ok=True)

WC = Namespace("http://www.semanticweb.org/worldcup2022#")

POSITION_IND = {
    "GK": WC.Goalkeeper,
    "DF": WC.Defender,
    "MF": WC.Midfielder,
    "FW": WC.Forward,
}

PLACEHOLDERS = {"", "not applicable", "not available", "n/a", "na", "nan", "none"}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def uid(prefix, raw):
    """A safe URI local-name: keep [A-Za-z0-9_], turn everything else into _."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", str(raw)).strip("_")
    return WC[f"{prefix}_{s}"]


def slug(raw):
    s = re.sub(r"[^A-Za-z0-9]+", "_", str(raw).lower()).strip("_")
    return re.sub(r"_+", "_", s)


def clean(v):
    """Return a stripped string, or None for NaN / placeholder values."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    s = str(v).strip()
    if s.lower() in PLACEHOLDERS:
        return None
    return s


def as_int(v):
    s = clean(v)
    if s is None:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def as_float(v):
    s = clean(v)
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def as_bool(v):
    s = clean(v)
    if s is None:
        return None
    return s in {"1", "1.0", "true", "True", "yes"}


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def as_date(v):
    s = clean(v)
    if s is None or not DATE_RE.match(s):
        return None
    return Literal(s, datatype=XSD.date)


class Builder:
    def __init__(self):
        self.g = Graph()
        self.g.bind("wc", WC)
        self.g.bind("owl", OWL)
        self.emitted_players = set()

    # -- tiny triple helpers ---------------------------------------------
    def add(self, s, p, o):
        if o is None:
            return
        self.g.add((s, p, o))

    def s(self, subj, prop, val):
        # plain literal (RDF 1.1 xsd:string) - keeps SPARQL string matching simple
        v = clean(val)
        if v is not None:
            self.g.add((subj, WC[prop], Literal(v)))

    def i(self, subj, prop, val):
        v = as_int(val)
        if v is not None:
            self.g.add((subj, WC[prop], Literal(v, datatype=XSD.integer)))

    def f(self, subj, prop, val):
        v = as_float(val)
        if v is not None:
            self.g.add((subj, WC[prop], Literal(v, datatype=XSD.float)))

    def b(self, subj, prop, val):
        v = as_bool(val)
        if v is not None:
            self.g.add((subj, WC[prop], Literal(v, datatype=XSD.boolean)))

    # -- entity builders ----------------------------------------------------
    def build_tournament(self, df, teams_df):
        r = df.iloc[0]
        t = uid("tournament", r.tournament_id)
        self.add(t, RDF.type, WC.Tournament)
        self.s(t, "tournamentName", r.tournament_name)
        yr = as_int(r.year)
        if yr:
            self.add(t, WC.year, Literal(str(yr), datatype=XSD.gYear))
        self.add(t, WC.startDate, as_date(r.start_date))
        self.add(t, WC.endDate, as_date(r.end_date))
        self.s(t, "hostCountry", r.host_country)
        self.i(t, "numberOfTeams", r.count_teams)
        # wonBy -> match winner name to a team row
        w = clean(r.winner)
        if w is not None:
            hit = teams_df[teams_df.team_name == w]
            if len(hit):
                self.add(t, WC.wonBy, uid("team", hit.iloc[0].team_code))
        self.tournament_uri = t

    def build_confederations_and_teams(self, teams):
        seen_conf = set()
        for _, r in teams.iterrows():
            code = clean(r.confederation_code)
            if code and code not in seen_conf:
                seen_conf.add(code)
                c = uid("conf", code)
                self.add(c, RDF.type, WC.Confederation)
                self.s(c, "confederationName", r.confederation_name)
                self.s(c, "confederationCode", code)
            team = uid("team", r.team_code)
            self.add(team, RDF.type, WC.Team)
            self.s(team, "teamName", r.team_name)
            self.s(team, "teamCode", r.team_code)
            self.s(team, "federationName", r.federation_name)
            self.s(team, "regionName", r.region_name)
            if code:
                self.add(team, WC.belongsToConfederation, uid("conf", code))
            self.add(team, WC.participatesIn, self.tournament_uri)

    def build_team_standings(self, standings, teams):
        """Attach the WC-2022 final-standings figures (Kaggle FIFA - 2022.csv)
        to each Team node. Joined to the worldcup teams by team name."""
        code_by_name = dict(zip(teams.team_name, teams.team_code))
        cols = [("Position", "finalPosition"), ("Games Played", "gamesPlayed"),
                ("Win", "wins"), ("Draw", "draws"), ("Loss", "losses"),
                ("Goals For", "goalsFor"), ("Goals Against", "goalsAgainst"),
                ("Goal Difference", "goalDifference"), ("Points", "points")]
        matched = 0
        for _, r in standings.iterrows():
            tc = code_by_name.get(clean(r.team_name))
            if tc is None:
                print(f"  !! standings team unmatched: {r.team_name}")
                continue
            team = uid("team", tc)
            for src, prop in cols:
                self.i(team, prop, r[src])
            matched += 1
        print(f"  standings attached to {matched}/{len(standings)} teams")

    def build_clubs_players_images(self, pmaster, players_bio, stats):
        # bio: player_id -> birth_date
        bio = players_bio.set_index("player_id")["birth_date"].to_dict()
        # stats: first row per normalized name
        stats_by = {}
        for _, s in stats.iterrows():
            k = clean(s.name_norm)
            if k and k not in stats_by:
                stats_by[k] = s
        clubs_seen = set()

        for _, r in pmaster.iterrows():
            pid = clean(r.player_id)
            p = uid("player", pid)
            self.add(p, RDF.type, WC.Player)
            self.emitted_players.add(pid)
            self.s(p, "givenName", r.given_name)
            self.s(p, "familyName", r.family_name)
            self.s(p, "fullName", r.full_name)
            self.i(p, "shirtNumber", r.shirt_number)
            self.s(p, "nationality", r.team_name)
            self.add(p, WC.birthDate, as_date(bio.get(pid)))
            self.add(p, WC.representsTeam, uid("team", r.team_code))
            pos = POSITION_IND.get(clean(r.position_code))
            if pos is not None:
                self.add(p, WC.hasPosition, pos)

            # ---- enrichment: Kaggle per-player stats -------------------
            nn = clean(r.name_norm)
            st = stats_by.get(nn) if nn else None
            if st is not None:
                self.i(p, "appearances", st.get("Appearances"))
                self.i(p, "goalsScored", st.get("Goals Scored"))
                self.i(p, "assistsProvided", st.get("Assists Provided"))
                self.f(p, "dribblesPer90", st.get("Dribbles per 90"))
                self.f(p, "interceptionsPer90", st.get("Interceptions per 90"))
                self.f(p, "tacklesPer90", st.get("Tackles per 90"))
                self.f(p, "duelsWonPer90", st.get("Total Duels Won per 90"))
                self.f(p, "savePercentage", st.get("Save Percentage"))
                self.f(p, "cleanSheets", st.get("Clean Sheets"))
                club = clean(st.get("Club"))
                if club is not None:
                    cu = uid("club", slug(club))
                    if club not in clubs_seen:
                        clubs_seen.add(club)
                        self.add(cu, RDF.type, WC.Club)
                        self.s(cu, "clubName", club)
                    self.add(p, WC.playsForClub, cu)

            # ---- multimedia: PlayerImage node -------------------------
            if bool(r.has_image) and clean(r.folder_path):
                img = uid("img", pid)
                self.add(img, RDF.type, WC.PlayerImage)
                self.s(img, "folderPath", str(r.folder_path).replace("\\", "/"))
                self.i(img, "imageCount", r.image_count)
                self.add(p, WC.hasImage, img)

    def ensure_player(self, pid, given=None, family=None):
        if pid in self.emitted_players:
            return
        p = uid("player", pid)
        self.add(p, RDF.type, WC.Player)
        self.s(p, "givenName", given)
        self.s(p, "familyName", family)
        self.emitted_players.add(pid)

    def build_stadiums(self, st):
        for _, r in st.iterrows():
            s = uid("stadium", r.stadium_id)
            self.add(s, RDF.type, WC.Stadium)
            self.s(s, "stadiumName", r.stadium_name)
            self.s(s, "city", r.city_name)
            self.s(s, "country", r.country_name)
            self.i(s, "capacity", r.stadium_capacity)

    def build_matches(self, mt):
        for _, r in mt.iterrows():
            m = uid("match", r.match_id)
            self.add(m, RDF.type, WC.Match)
            self.s(m, "matchName", r.match_name)
            self.add(m, WC.matchDate, as_date(r.match_date))
            self.s(m, "stageName", r.stage_name)
            self.s(m, "groupName", r.group_name)
            self.i(m, "homeScore", r.home_team_score)
            self.i(m, "awayScore", r.away_team_score)
            self.b(m, "extraTime", r.extra_time)
            self.b(m, "penaltyShootout", r.penalty_shootout)
            self.s(m, "result", r.result)
            self.add(m, WC.partOfTournament, self.tournament_uri)
            self.add(m, WC.hasHomeTeam, uid("team", r.home_team_code))
            self.add(m, WC.hasAwayTeam, uid("team", r.away_team_code))
            if clean(r.stadium_id):
                self.add(m, WC.playedAt, uid("stadium", r.stadium_id))

    def build_goals(self, gl):
        for _, r in gl.iterrows():
            g = uid("goal", r.goal_id)
            self.add(g, RDF.type, WC.Goal)
            self.s(g, "minuteLabel", r.minute_label)
            self.i(g, "minuteRegulation", r.minute_regulation)
            self.b(g, "isPenalty", r.penalty)
            self.b(g, "isOwnGoal", r.own_goal)
            m = uid("match", r.match_id)
            self.add(g, WC.scoredInMatch, m)
            self.add(m, WC.hasGoal, g)
            pid = clean(r.player_id)
            if pid:
                self.ensure_player(pid, r.given_name, r.family_name)
                self.add(g, WC.scoredBy, uid("player", pid))
            if clean(r.team_code):
                self.add(g, WC.goalForTeam, uid("team", r.team_code))


# --------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("KNOWLEDGE GRAPH CONSTRUCTION  |  ABox from data/processed")
    print("=" * 70)

    read = lambda n: pd.read_csv(os.path.join(PROC, n))
    tournament = read("tournament_2022.csv")
    teams = read("teams_2022.csv")
    players_bio = read("players_2022.csv")
    pmaster = read("player_master_2022.csv")
    stats = read("player_stats_2022_clean.csv")
    stadiums = read("stadiums_2022.csv")
    matches = read("matches_2022.csv")
    goals = read("goals_2022.csv")
    standings = read("standings_2022.csv")

    bld = Builder()
    bld.build_tournament(tournament, teams)
    bld.build_confederations_and_teams(teams)
    bld.build_team_standings(standings, teams)
    bld.build_clubs_players_images(pmaster, players_bio, stats)
    bld.build_stadiums(stadiums)
    bld.build_matches(matches)
    bld.build_goals(goals)

    abox_path = os.path.join(KG, "worldcup_abox.ttl")
    bld.g.serialize(destination=abox_path, format="turtle")
    print(f"\n  ABox triples        : {len(bld.g):,}")
    print(f"  wrote               : {os.path.relpath(abox_path, PROJECT)}")

    # ---- merge TBox + ABox (+ image features if already extracted) -------
    full = Graph()
    full.parse(TBOX, format="turtle")
    n_tbox = len(full)
    full.parse(abox_path, format="turtle")
    img_ttl = os.path.join(KG, "worldcup_images.ttl")
    if os.path.exists(img_ttl):
        full.parse(img_ttl, format="turtle")
        print(f"  + merged existing worldcup_images.ttl")
    full_path = os.path.join(KG, "worldcup_full.ttl")
    full.serialize(destination=full_path, format="turtle")
    print(f"  TBox triples        : {n_tbox:,}")
    print(f"  full graph triples  : {len(full):,}")
    print(f"  wrote               : {os.path.relpath(full_path, PROJECT)}")

    # ---- instance counts per class -------------------------------------
    print("\n  ---- instances per class ----")
    q = """
        PREFIX wc: <http://www.semanticweb.org/worldcup2022#>
        SELECT ?c (COUNT(DISTINCT ?x) AS ?n) WHERE {
            ?x a ?c . FILTER(STRSTARTS(STR(?c), STR(wc:)))
        } GROUP BY ?c ORDER BY DESC(?n)
    """
    for row in bld.g.query(q):
        name = str(row.c).split("#")[-1]
        print(f"      {name:<16} {int(row.n):>5}")

    print("\n" + "=" * 70)
    print("DONE.")
    print("=" * 70)


if __name__ == "__main__":
    main()
