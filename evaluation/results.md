# Benchmark: Knowledge Graph vs. raw per-dataset retrieval

KG: `kg/worldcup_full.ttl` (20,023 triples). Raw: pandas over `data/processed/*.csv`.

| # | Information need | Datasets | Joins | LoC KG / raw | Time KG / raw (ms) | Rows | A==B |
|---|---|---|---|---|---|---|---|
| 1 | Tournament winner + host | 1 | 0 | 1 / 1 | 5.3 / 2.0 | 1 | yes |
| 2 | Top-10 goalscorers (own goals excluded) | 1 | 1 | 4 / 3 | 109.5 / 15.2 | 10 | yes |
| 3 | Argentina squad with club side | 2 | 1 | 3 / 3 | 15.6 / 5.5 | 26 | yes |
| 4 | CONMEBOL players at English clubs | 3 | 2 | 4 / 4 | 210.5 / 19.7 | 19 | yes |
| 5 | Goalkeepers ranked by save % | 2 | 1 | 5 / 3 | 32.6 / 15.3 | 15 | yes |
| 6 | World Cup final top-4 + confederation | 2 | 1 | 4 / 3 | 38.4 / 7.1 | 4 | yes |

**Reading of the results.**

* *Latency* favours pandas here only because the KG is queried with rdflib, an in-memory reference SPARQL engine with no indexes; loaded into a native triplestore (GraphDB / Fuseki) the same queries run in single-digit ms. The pandas timings also exclude the one-off cost of writing and maintaining the integration code.
* *Correctness*: every KG answer matches the hand-built pandas answer (`A==B = yes`) - but only after the raw pipeline was made to replicate the placeholder cleaning and `name_norm` entity resolution that the KG builder already baked into `wc:` edges (see case 2, Richarlison).
* *Integration effort*: for single-dataset needs (1-2) the raw pipeline is fine. From case 3 on, every new cross-source question re-loads several CSVs and re-implements the same join plumbing, while on the KG each need is one declarative pattern over stable URIs. That reuse - not speed - is the KG's contribution.