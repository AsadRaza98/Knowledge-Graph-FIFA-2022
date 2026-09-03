# WC-2022 Knowledge Graph Explorer (Streamlit)

An interactive front-end over the FIFA World Cup 2022 multimedia knowledge graph,
with **one tab per ontology class** (Player, Team, Match, Goal, Club, Stadium,
Confederation, Position, Tournament, PlayerImage). Each tab has a **search box +
dropdown** to pick an entity and shows its facts pulled from the graph, the
entities it links to (resolved to readable names), and the entities that link
back to it (e.g. a team's squad, a match's goals, a club's players).

- The **Player** tab shows the full integrated profile (bio + performance stats +
  team & final standing + club + position), the representative **photo**, and the
  **visually most similar players** (ResNet-50 cosine) — each a linked KG entity.
- The **PlayerImage** tab shows the photo, the player it depicts, and the feature-vector dimension.

It exercises both retrieval modes of the project:
- **Structured retrieval** — queries over `kg/worldcup_full.ttl` (rdflib, in-memory;
  no server needed).
- **Content-based image retrieval** — cosine over `images/player_features.npy`
  (the 2048-d ResNet-50 vectors), reusing the logic of `queries/image_similarity.py`.

## Run

From the `worldcup-kg/` folder:

```bash
streamlit run app/streamlit_app.py
```

Then open the URL it prints (default http://localhost:8501).

## Requirements

`streamlit, rdflib, pandas, numpy, pillow` — see `requirements.txt`
(all already in the project's Anaconda environment).

## Data it reads (read-only)

| File | Purpose |
|------|---------|
| `kg/worldcup_full.ttl` | the 20,023-triple RDF/OWL graph (facts) |
| `images/player_features.npy` | 820 × 2048 ResNet-50 vectors (similarity) |
| `images/player_features_index.csv` | player_id → name / team / photo folder |
| `data/raw/player-images/...` | the actual photo folders (representative image) |

The graph and vectors are loaded once and cached, so switching players is instant.
