# SupportLens

AI customer support agent, evaluation-first build.
**Take-home assignment for Hiver SDE Intern role.**

> "Whether you can turn a messy real-world dataset into a working AI system and prove it works. The proof is worth more than the system."

---

## Project Phases

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Data ingest, cleaning, thread reconstruction, brand selection | 🔄 In Progress |
| Phase 1 | Intent taxonomy derivation from real data | ⏳ Pending |
| Phase 2 | Golden evaluation set (150–250 hand-labelled examples) | ⏳ Pending |
| Phase 3 | Trivial + simple baselines | ⏳ Pending |
| Phase 4 | Agent (LLM classify + retrieval-grounded reply + escalate decision) | ⏳ Pending |
| Phase 5 | Evaluation harness + LLM-as-judge + judge-human agreement | ⏳ Pending |
| Phase 6 | Report + decision log + README reproducibility | ⏳ Pending |

---

## Reproducing Phase 0

### Prerequisites

```bash
pip install -r requirements.txt
```

Place `twcs.csv` (Kaggle: `thoughtvector/customer-support-on-twitter`) at `data/raw/twcs.csv`.

### Running the pipeline

```bash
make phase0          # full Phase 0 pipeline
make ingest          # data load and type parsing only
make clean-data      # signoff stripping + language tagging
make threads         # thread reconstruction
make brand-check     # brand substance heuristic
```

### Running tests

```bash
pytest tests/ -v
```

---

## Repo Structure

```
supportlens/
├── README.md
├── ASSIGNMENT.md       — original Hiver assignment
├── DECISIONS.md        — decision log (grows across phases)
├── LABELING_GUIDE.md   — labelling spec (filled in Phase 1)
├── data/
│   ├── raw/            — twcs.csv (NOT committed)
│   ├── processed/      — cleaned outputs
│   └── golden/         — Phase 2 hand-labelled set
├── src/
│   ├── ingest.py
│   ├── clean.py
│   ├── threads.py
│   └── brand_check.py
├── tests/
│   └── test_pipeline.py
├── Makefile
└── requirements.txt
```
