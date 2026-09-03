"""
make_schema_diagram.py
Renders ontology/schema_diagram.svg  - the illustration required by Task 2.

Pure-Python SVG writer (no graphviz needed). Boxes = OWL classes with their
datatype properties listed; labelled arrows = object properties.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "schema_diagram.svg")

W, H = 1180, 760

# class boxes:  id -> (x, y, w, h, title, [datatype props])
BOXES = {
    "Tournament":   (470, 30, 240, 96, "Tournament",
                     ["tournamentName", "year", "startDate / endDate",
                      "hostCountry", "numberOfTeams"]),
    "Confederation":(40, 40, 210, 66, "Confederation",
                     ["confederationName", "confederationCode"]),
    "Stadium":      (930, 40, 210, 80, "Stadium",
                     ["stadiumName", "city", "country", "capacity"]),
    "Team":         (130, 235, 240, 150, "Team",
                     ["teamName", "teamCode", "federationName", "regionName",
                      "finalPosition", "gamesPlayed", "wins / draws / losses",
                      "goalsFor / goalsAgainst", "goalDifference", "points"]),
    "Match":        (860, 250, 240, 118, "Match",
                     ["matchName", "matchDate", "stageName", "groupName",
                      "homeScore / awayScore", "extraTime", "penaltyShootout",
                      "result"]),
    "Player":       (470, 300, 250, 150, "Player",
                     ["givenName / familyName / fullName", "birthDate",
                      "shirtNumber", "nationality", "appearances",
                      "goalsScored / assistsProvided", "dribblesPer90 ...",
                      "savePercentage / cleanSheets"]),
    "Goal":         (700, 540, 230, 90, "Goal",
                     ["minuteLabel", "minuteRegulation", "isPenalty",
                      "isOwnGoal"]),
    "Club":         (170, 470, 190, 56, "Club", ["clubName"]),
    "Position":     (430, 600, 190, 60, "Position",
                     ["positionName", "positionCode", "(GK/DF/MF/FW)"]),
    "PlayerImage":  (100, 590, 240, 78, "PlayerImage",
                     ["folderPath", "imageCount", "featureVector"]),
}

# object properties: (src, dst, label, curve_offset)
EDGES = [
    ("Team", "Confederation", "belongsToConfederation", 0),
    ("Team", "Tournament", "participatesIn", 0),
    ("Tournament", "Team", "wonBy", 40),
    ("Player", "Team", "representsTeam", 0),
    ("Player", "Club", "playsForClub", 0),
    ("Player", "Position", "hasPosition", 0),
    ("Player", "PlayerImage", "hasImage", 0),
    ("Match", "Tournament", "partOfTournament", 0),
    ("Match", "Team", "hasHomeTeam", 70),
    ("Match", "Team", "hasAwayTeam", 110),
    ("Match", "Stadium", "playedAt", 0),
    ("Match", "Goal", "hasGoal / scoredInMatch", 0),
    ("Goal", "Player", "scoredBy", 0),
    ("Goal", "Team", "goalForTeam", -90),
]

def anchor(box, side):
    x, y, w, h = box[:4]
    return {
        "t": (x + w / 2, y), "b": (x + w / 2, y + h),
        "l": (x, y + h / 2), "r": (x + w, y + h / 2),
        "c": (x + w / 2, y + h / 2),
    }[side]

def best_sides(a, b):
    ax, ay = anchor(a, "c"); bx, by = anchor(b, "c")
    dx, dy = bx - ax, by - ay
    if abs(dx) > abs(dy):
        return ("r", "l") if dx > 0 else ("l", "r")
    return ("b", "t") if dy > 0 else ("t", "b")

parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'font-family="Segoe UI, Arial, sans-serif">')
parts.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
parts.append(
    '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
    'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
    '<path d="M0 0 L10 5 L0 10 z" fill="#555"/></marker></defs>')
parts.append(f'<text x="{W/2}" y="20" text-anchor="middle" font-size="17" '
             f'font-weight="bold" fill="#1a4d5c">FIFA World Cup 2022 - Ontology Schema (TBox)</text>')

# edges first (under boxes)
for src, dst, label, off in EDGES:
    a, b = BOXES[src], BOXES[dst]
    sa, sb = best_sides(a, b)
    x1, y1 = anchor(a, sa)
    x2, y2 = anchor(b, sb)
    mx, my = (x1 + x2) / 2 + off, (y1 + y2) / 2 + off
    parts.append(
        f'<path d="M{x1:.0f},{y1:.0f} Q{mx:.0f},{my:.0f} {x2:.0f},{y2:.0f}" '
        f'fill="none" stroke="#777" stroke-width="1.4" marker-end="url(#arrow)"/>')
    parts.append(
        f'<text x="{mx:.0f}" y="{my-4:.0f}" text-anchor="middle" font-size="11" '
        f'fill="#b03a2e"><tspan dy="0">{label}</tspan></text>')

# boxes
for bid, (x, y, w, h, title, props) in BOXES.items():
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                 f'fill="#eaf2f4" stroke="#1a4d5c" stroke-width="1.8"/>')
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="8" '
                 f'fill="#1a4d5c"/>')
    parts.append(f'<text x="{x+w/2}" y="{y+15}" text-anchor="middle" '
                 f'font-size="12.5" font-weight="bold" fill="#fff">{title}</text>')
    for i, p in enumerate(props):
        parts.append(f'<text x="{x+8}" y="{y+37+i*13}" font-size="10" '
                     f'fill="#333">{p}</text>')

parts.append('</svg>')
open(OUT, "w", encoding="utf-8").write("\n".join(parts))
print("wrote", os.path.relpath(OUT, os.path.dirname(HERE)))
