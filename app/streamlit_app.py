# -*- coding: utf-8 -*-
"""
streamlit_app.py  -  interactive explorer for the FIFA World Cup 2022 multimedia KG.

One tab per ontology class (Player, Team, Match, Goal, Club, Stadium, Confederation,
Position, Tournament, PlayerImage). Each tab has a search box + dropdown to pick an
entity and shows its facts pulled from the knowledge graph (worldcup_full.ttl), the
entities it links to, and the entities that link back to it. The Player and
PlayerImage tabs also show photos, and Player adds content-based image retrieval
(ResNet-50 cosine) over the stored feature vectors.

Run from the worldcup-kg folder:
    streamlit run app/streamlit_app.py
Needs: streamlit, rdflib, pandas, numpy, pillow  (all in the project env).
"""
import os
import re
import numpy as np
import pandas as pd
import streamlit as st
from rdflib import Graph, Namespace, RDF, URIRef

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(APP_DIR)
TTL = os.path.join(PROJECT, "kg", "worldcup_full.ttl")
FEATS = os.path.join(PROJECT, "images", "player_features.npy")
INDEX = os.path.join(PROJECT, "images", "player_features_index.csv")
WC = Namespace("http://www.semanticweb.org/worldcup2022#")
EXTS = (".jpg", ".jpeg", ".png")

st.set_page_config(page_title="WC-2022 KG by Asad Raza",
                   page_icon="⚽", layout="wide")

# Ordered list of tabs (class, emoji label)
TABS = [("Player", "Players"), ("Team", "Teams"), ("Match", "Matches"),
        ("Goal", "Goals"), ("Club", "Clubs"), ("Stadium", "Stadiums"),
        ("Confederation", "Confederations"), ("Position", "Positions"),
        ("Tournament", "Tournament"), ("PlayerImage", "Player images")]

# Name predicates tried, in order, when labelling any node.
NAME_PREDS = ["fullName", "teamName", "clubName", "stadiumName", "matchName",
              "tournamentName", "confederationName", "label"]

# Per-class "things that point back to this node" -> (predicate, section title).
REVERSE = {
    "Team": [("representsTeam", "Squad players"), ("hasHomeTeam", "Home matches"),
             ("hasAwayTeam", "Away matches"), ("goalForTeam", "Goals for")],
    "Match": [("scoredInMatch", "Goals in this match")],
    "Club": [("playsForClub", "Players at this club")],
    "Stadium": [("playedAt", "Matches at this stadium")],
    "Confederation": [("belongsToConfederation", "Member teams")],
    "Position": [("hasPosition", "Players in this position")],
    "Tournament": [("partOfTournament", "Matches"), ("wonBy", "Winner")],
}


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading knowledge graph ...")
def load_graph():
    g = Graph()
    g.parse(TTL, format="turtle")
    return g


@st.cache_data(show_spinner="Loading image feature vectors ...")
def load_features():
    return np.load(FEATS), pd.read_csv(INDEX)


def local(uri):
    return str(uri).split("#")[-1]


def humanize(pred):
    """finalPosition -> 'Final position'."""
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(pred))
    return s[0].upper() + s[1:]


def nice(g, iri):
    """A human label for any node."""
    if isinstance(iri, str):
        iri = URIRef(iri)
    for np_ in NAME_PREDS:
        v = g.value(iri, WC[np_])
        if v is not None:
            return str(v)
    loc = local(iri)
    if loc.startswith("img_"):
        pl = next(g.subjects(WC.hasImage, iri), None)
        nm = g.value(pl, WC.fullName) if pl else None
        return f"{nm} (image)" if nm else loc
    if loc.startswith("goal_"):
        sc = g.value(iri, WC.scoredBy)
        mn = g.value(iri, WC.minuteLabel)
        nm = g.value(sc, WC.fullName) if sc else "?"
        return f"{mn} {nm}".strip() if mn else str(nm)
    return loc


@st.cache_data(show_spinner=False)
def list_instances(cls):
    """[(iri, label)] for every instance of a class, sorted by label."""
    g = load_graph()
    items = [(str(s), nice(g, s)) for s in g.subjects(RDF.type, WC[cls])]
    items = [it for it in items if it[1] and it[1].strip() != "-"]  # drop placeholder nodes
    items.sort(key=lambda t: t[1].lower())
    return items


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------
def selector(cls):
    """Search box + dropdown. Returns the chosen IRI (or None)."""
    items = list_instances(cls)
    q = st.text_input("Search", key=f"search_{cls}",
                      placeholder=f"type to filter {len(items)} {cls.lower()} entities ...")
    if q:
        ql = q.lower()
        items = [it for it in items if ql in it[1].lower()]
    if not items:
        st.warning("No entity matches that search.")
        return None
    idx = st.selectbox("Select", options=range(len(items)),
                       format_func=lambda i: items[i][1], key=f"pick_{cls}")
    return items[idx][0]


def rep_image(folder):
    full = os.path.join(PROJECT, str(folder))
    if not os.path.isdir(full):
        return None
    files = sorted(f for f in os.listdir(full) if f.lower().endswith(EXTS))
    return os.path.join(full, files[0]) if files else None


def details_table(g, iri, skip=()):
    """Datatype (literal) properties + object links, as a two-column table."""
    rows = []
    for p, o in sorted(g.predicate_objects(URIRef(iri)), key=lambda x: local(x[0])):
        if p == RDF.type or local(p) in skip:
            continue
        pn = local(p)
        if pn == "featureVector":
            n = len(str(o).strip("[]").split(","))
            val = f"{n}-d ResNet-50 vector"
        elif str(o).startswith(str(WC)):
            val = nice(g, o)
        else:
            val = str(o)
        rows.append({"Property": humanize(pn), "Value": val})
    if rows:
        st.table(pd.DataFrame(rows))


def reverse_sections(g, cls, iri):
    for pred, title in REVERSE.get(cls, []):
        subs = list(g.subjects(WC[pred], URIRef(iri)))
        if not subs:
            continue
        labels = sorted(nice(g, s) for s in subs)
        with st.expander(f"{title}  ({len(labels)})", expanded=len(labels) <= 12):
            shown = labels[:60]
            st.write(" · ".join(shown) + (f"  … and {len(labels) - 60} more"
                                          if len(labels) > 60 else ""))


# ---------------------------------------------------------------------------
# Player tab (rich view)
# ---------------------------------------------------------------------------
def iri_to_pid(iri):
    return local(iri).replace("player_", "", 1).replace("_", "-")


def render_player(g, iri, X, idx):
    d = {local(p): o for p, o in g.predicate_objects(URIRef(iri))}
    team = {}
    if "representsTeam" in d:
        team = {local(p): o for p, o in g.predicate_objects(d["representsTeam"])}
    club = nice(g, d["playsForClub"]) if "playsForClub" in d else "-"
    position = local(d["hasPosition"]) if "hasPosition" in d else "-"
    pid = iri_to_pid(iri)

    left, right = st.columns([1, 2], gap="large")
    with left:
        st.subheader(str(d.get("fullName", local(iri))))
        irow = idx[idx.player_id == pid]
        img = rep_image(irow.iloc[0].folder) if not irow.empty else None
        if img:
            st.image(img, use_column_width=True, caption="representative photo")
        else:
            st.info("No photo folder for this player.")
        st.markdown(
            f"**Nationality:** {d.get('nationality','-')}  \n"
            f"**Team:** {team.get('teamName','-')}  \n"
            f"**Club:** {club}  \n"
            f"**Position:** {position}  \n"
            f"**Shirt #:** {d.get('shirtNumber','-')}  \n"
            f"**Born:** {d.get('birthDate','-')}  \n"
            f"**KG node:** `{local(iri)}`")
    with right:
        st.markdown("#### Tournament performance")
        keys = [("appearances", "Appearances"), ("goalsScored", "Goals"),
                ("assistsProvided", "Assists"), ("dribblesPer90", "Dribbles / 90"),
                ("tacklesPer90", "Tackles / 90"), ("interceptionsPer90", "Interceptions / 90"),
                ("duelsWonPer90", "Duels won / 90"), ("savePercentage", "Save %"),
                ("cleanSheets", "Clean sheets")]
        perf = [{"Metric": lbl, "Value": str(d[k])} for k, lbl in keys if k in d]
        if perf:
            st.table(pd.DataFrame(perf))
        else:
            st.info("No performance-statistics row matched this player "
                    "(one of the 77 unmatched squad members).")
        if team:
            st.markdown(f"#### {team.get('teamName','')} — final standing")
            trow = {"Final position": team.get("finalPosition", "-"),
                    "Points": team.get("points", "-"),
                    "W-D-L": f"{team.get('wins','-')}-{team.get('draws','-')}-{team.get('losses','-')}",
                    "Goals F/A": f"{team.get('goalsFor','-')}/{team.get('goalsAgainst','-')}",
                    "Goal diff": team.get("goalDifference", "-")}
            st.table(pd.DataFrame([{"Attribute": k, "Value": str(v)} for k, v in trow.items()]))

    st.divider()
    st.markdown("#### Visually similar players "
                "<span style='color:#888;font-size:0.8em'>(content-based image "
                "retrieval, ResNet-50 cosine)</span>", unsafe_allow_html=True)
    pos = {p: i for i, p in enumerate(idx.player_id.tolist())}.get(pid)
    if pos is None:
        st.info("This player has no image vector, so no visual neighbours are available.")
        return
    ok = idx.ok.values.astype(bool)
    sims = X @ X[pos]
    sims[~ok] = -1.0
    order = [j for j in np.argsort(-sims) if j != pos][:6]
    cols = st.columns(6)
    for col, j in zip(cols, order):
        with col:
            im = rep_image(idx.folder[j])
            if im:
                st.image(im, use_column_width=True)
            st.caption(f"**{idx.full_name[j]}**  \n{idx.team[j]}  \ncos = {sims[j]:.3f}")
    st.caption("Neighbours share appearance / pose / kit rather than identity, the "
               "limitation of a single global CNN descriptor. Each is still a linked KG entity.")


# ---------------------------------------------------------------------------
# PlayerImage tab
# ---------------------------------------------------------------------------
def render_image_node(g, iri):
    d = {local(p): o for p, o in g.predicate_objects(URIRef(iri))}
    pl = next(g.subjects(WC.hasImage, URIRef(iri)), None)
    left, right = st.columns([1, 2], gap="large")
    with left:
        img = rep_image(d.get("folderPath", ""))
        if img:
            st.image(img, use_column_width=True, caption="representative photo")
        else:
            st.info("Folder not found on disk.")
    with right:
        st.markdown(f"**Depicts:** {nice(g, pl) if pl else '-'}")
        st.markdown(f"**Images in folder:** {d.get('imageCount','-')}")
        st.markdown(f"**Folder path:** `{d.get('folderPath','-')}`")
        if "featureVector" in d:
            n = len(str(d["featureVector"]).strip("[]").split(","))
            st.markdown(f"**Feature vector:** {n}-d PCA-reduced ResNet-50 embedding")
        st.markdown(f"**KG node:** `{local(iri)}`")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
st.title("⚽  FIFA World Cup 2022 — KG by Asad Raza")
st.caption("Browse every class in the ontology. Structured retrieval (SPARQL over the "
           "KG) throughout; the Player tab adds content-based image retrieval.")

g = load_graph()
X, idx = load_features()
tabs = st.tabs([lbl for _, lbl in TABS])

for (cls, lbl), tab in zip(TABS, tabs):
    with tab:
        iri = selector(cls)
        if not iri:
            continue
        st.divider()
        if cls == "Player":
            render_player(g, iri, X, idx)
        elif cls == "PlayerImage":
            render_image_node(g, iri)
        else:
            st.subheader(nice(g, iri))
            details_table(g, iri)
            reverse_sections(g, cls, iri)
            st.caption(f"KG node: `{local(iri)}`")

st.divider()
st.caption("Data: jfjelstul/worldcup + Kaggle (stats, images, standings) · "
           "20,023-triple RDF/OWL graph · features: ResNet-50 (ImageNet) 2048-d, L2-normalised.")
