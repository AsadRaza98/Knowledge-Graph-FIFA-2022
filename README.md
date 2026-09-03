# FIFA World Cup 2022 — Multimedia Knowledge Graph for Information Retrieval

IR exam project (Prof. A. M. Rinaldi / C. Russo, UNINA 2025-26). Builds an
RDF/OWL knowledge graph about the 2022 men's World Cup from four mandatory
sources (textual + image), stores it as Turtle, and retrieves information from
it with SPARQL and content-based image similarity.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1. Inventory raw data | `notebooks/01_inventory.py` | console report |
| 2. Clean & integrate (scope = WC-2022) | `notebooks/02_preprocess.py` | `data/processed/*.csv` (11 tables incl. `standings_2022.csv`) |
| 3a. Build the KG (ABox) | `notebooks/03_build_kg.py` | `kg/worldcup_abox.ttl`, `kg/worldcup_full.ttl` |
| 3b. Multimedia feature extraction | `notebooks/04_image_features.py` | `images/player_features*.npy`, `kg/worldcup_images.ttl` |
| —. Schema illustration | `ontology/make_schema_diagram.py` | `ontology/schema_diagram.svg` |
| 4. Retrieval (SPARQL) | `queries/*.rq` + `queries/run_all.py` | console |
| 4. Retrieval (image) | `queries/image_similarity.py` | console |
| 5. Evaluation | `evaluation/benchmark.py` | `evaluation/results.md` |

Run everything from this folder with the Anaconda interpreter:

```bash
python notebooks/02_preprocess.py
python notebooks/03_build_kg.py
python notebooks/04_image_features.py      # downloads ResNet-50 weights once, CPU ~15 min
python ontology/make_schema_diagram.py
python queries/run_all.py
python queries/image_similarity.py "Lionel Messi"
python evaluation/benchmark.py
```

Requires: `pandas`, `rdflib`, `torch`, `torchvision`, `pillow`, `scikit-learn`, `numpy`.

## Data sources → ontology classes

| Source | Feeds |
|---|---|
| github.com/jfjelstul/worldcup | Tournament, Team, Confederation, Player (bio), Match, Goal, Stadium, Position |
| Kaggle *fifa-world-cup-2022-players-statistics* | Player (stats), Club |
| Kaggle *fifa-2022-all-players-image-dataset* | PlayerImage (folder, count, ResNet-50 feature vector) |
| Kaggle *fifa-football-world-cup-dataset* (`FIFA - 2022.csv`) | Team final standings (position, W/D/L, GF/GA, GD, points) |

## Ontology

* Schema (TBox): `ontology/worldcup_tbox.ttl` — 10 classes, 16 object
  properties, ~50 datatype properties, 4 enumerated `Position` individuals.
  Open directly in Protégé; run HermiT to check consistency.
* Design notes: `ontology/ontology_design.md`
* Illustration: `ontology/schema_diagram.svg`
* Namespace: `http://www.semanticweb.org/worldcup2022#` (prefix `wc:`)

## Knowledge graph (current build)

`kg/worldcup_full.ttl` — ~20,000 triples. Instances: 831 Player, 820
PlayerImage (each with a 128-d PCA feature vector), 298 Club, 172 Goal,
64 Match, 32 Team (with final-standings figures), 8 Stadium,
5 Confederation, 1 Tournament.

## Loading into a graph database

The graph is RDF/OWL, so use an RDF-native store:

* **GraphDB Free** — create a repository, *Import → RDF → Upload*
  `kg/worldcup_full.ttl`, query in the Workbench SPARQL tab.
* **Apache Jena Fuseki** — `fuseki-server --file kg/worldcup_full.ttl /worldcup`,
  then POST the `queries/*.rq` to `http://localhost:3030/worldcup/sparql`.

## Report (max 10 pages) — chapter map

1. Introduction to Knowledge Graphs — KGs for IR
2. Data and preprocessing — the 4 sources, scoping to WC-2022, entity
   resolution (`name_norm`), placeholder cleaning, image mojibake fix
3. Retrieval methodologies — SPARQL over the KG, content-based image retrieval
   on ResNet-50 embeddings
4. System implementation and evaluation — TBox/ABox construction, feature
   extraction, `evaluation/results.md` (KG vs per-dataset retrieval)
5. Conclusions and future work — richer multimedia (video highlights),
   embeddings in the store, KG-embedding link prediction
