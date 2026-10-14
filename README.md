# SupportLens

AI customer support inbound routing and grounded response agent, built evaluation-first.  
**GitHub Repository:** [https://github.com/wayalbhushan/SupportLens](https://github.com/wayalbhushan/SupportLens)  

> *"Whether you can turn a messy real-world dataset into a working AI system and prove it works. The proof is worth more than the system."*

---

## Project Phases & Deliverable Summary

| Phase | Focus | Status & Key Artifacts |
| :--- | :--- | :--- |
| **Phase 0** | Data Ingest & Cleaning | **Complete** — Cleaned TWCS corpus, reconstructed 7,626 customer threads (up to 650 tweets), filtered corporate broadcasts, selected VerizonSupport based on measured public reply-substance ratio. |
| **Phase 1** | Intent Taxonomy & Labeling Guide | **Complete** — Derived 8-class empirical taxonomy from real reading sample; authored and versioned `LABELING_GUIDE.md` (frozen at v1.2, boundary rule 3b added in v1.3). |
| **Phase 2** | Golden Evaluation Set | **Complete** — Curated 200 hand-labeled items across Stratum A (120 natural random) and Stratum B (80 targeted oversamples of rare intents/overrides) in `data/golden/golden_labeled.csv`. |
| **Phase 3** | Baselines & Leakage Protection | **Complete** — Evaluated Trivial Keyword Floor vs. Weakly Supervised TF-IDF+Logistic Regression; documented weak-supervision ceiling (47.5% test vs 75% val) in `data/processed/baseline_results.md`. |
| **Phase 4** | Decoupled Dual-Path Agent | **Complete** — Implemented Gemini 3.5 Flash pipeline: Path A (intent routing + retrieval grounding) + Path B (zero-gated severity extractor). Results and failure attribution in `data/processed/agent_results.md`. |
| **Phase 5** | LLM-as-Judge Calibration & Full Eval | **Complete** — Calibrated Groq Qwen-2.5-32B judge against blind human ratings ($\kappa_w=0.637$ Actionability, $0.252$ Groundedness, $0.273$ Brand). Evaluated all 176 non-other golden items in `data/processed/agent_full_judge_eval.csv`. |
| **Phase 6** | Synthesis & Technical Report | **Complete** — Comprehensive evaluation report authored in `REPORT.md`, tracking top 5 failure modes, cost-asymmetry analysis, what's misleading about headline numbers, and full 27 decisions in `DECISIONS.md`. |
| **Phase 7** | Reproducibility Verification | **Complete** — Verified cold reproduction in clean checkout under 2 minutes with 100% cache hit determinism and zero API key requirements. |
| **Phase 8** | Interactive Demo UI | **Complete** — Responsive single-page application (FastAPI + Vanilla JS) featuring zero-key cached golden replay and live decoupled pipeline inference. |

---

## Reproducing Headline Results in Under 2 Minutes (Fast Cached Path)

All LLM generator completions (`data/cache/llm_cache.json`) and judge evaluations (`data/cache/judge_cache.json`) are **committed to the repository** (Decision 8). 

> [!IMPORTANT]
> **Zero API Keys & Zero Raw Data Required:**  
> Reproducing the headline results does **NOT** require a `GEMINI_API_KEY`, **NOT** require `GROQ_API_KEYS`, and does **NOT** require downloading the 460MB raw `twcs.csv` dataset. The evaluation runs 100% locally from committed golden data and bit-for-bit cached model outputs.

### 1. Environment Setup

Clone the repository and install the standard dependencies:

```bash
git clone https://github.com/wayalbhushan/SupportLens.git
cd SupportLens

# Create and activate virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run Test Suite

Run the full pytest suite (47 regression and integrity tests):

```bash
pytest tests/ -v
# or: make test
```

### 3. Reproduce All Headline Numbers

Execute the reproduction pipeline via `make` or direct `python -m` module invocation:

```bash
make reproduce
```

*Alternatively, run each evaluation step individually:*

```bash
# Phase 3 Baselines (Trivial Keyword Floor & TF-IDF + LogReg vs Golden Set)
python -m src.baseline_report

# Phase 4 Agent (Stratum A & Blended Intent Accuracy, Escalation Precision/Recall, Error Attribution)
python -m src.eval_agent

# Phase 5 LLM Judge (Headline Reply Quality: Groundedness, Actionability, Brand Appropriateness)
python -m src.run_full_judge_eval
```

**Expected Runtime:** ~30 to 45 seconds total wall-clock time across all three scripts.

### 4. Launch Interactive Demo UI (Phase 8)

SupportLens includes a responsive single-page application featuring an interactive pipeline visualization and results explorer:

```bash
uvicorn app.main:app --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.
* **Live Demo Tab:** Test inbound customer messages. Pre-selected chips replay committed golden-set items with zero API keys. Live inference through the dual-path orchestrator is available when `GEMINI_API_KEY` is configured in `.env`.
* **Results Dashboard Tab:** Explore headline benchmark cards, agreement kappa charts, and a filterable dataset browser across all 200 golden-set predictions.

---

## Headline Results Summary

| Benchmark Metric | Baseline 1 (Trivial) | Baseline 2 (TF-IDF + LogReg) | Phase 4 Agent (Dual-Path) | Target Bar | Result |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stratum A Intent Accuracy** | 48.3% | 47.5% | **77.5%** | > 48.3% | **PASSED** |
| **Stratum A Macro-F1** | 0.466 | 0.433 | **0.710** | > 0.466 | **PASSED** |
| **Stratum A Escalation Precision** | 0.225 | 0.706 | **0.950** | > 0.700 | **PASSED** |
| **Stratum A Escalation Recall** | 1.000 | 0.444 | **0.704** | > 0.850 | Under (FN=8) |
| **Full Blended Intent Accuracy** | 58.0% | 52.5% | **78.0%** | — | — |
| **Full Blended Escalation Precision** | 0.405 | 0.768 | **0.928** | — | — |
| **Full Blended Escalation Recall** | 1.000 | 0.531 | **0.790** | — | — |

### Reply-Quality Benchmarks ($N=176$ Golden Non-Other Items)
* **Groundedness:** Mean **2.82** / 4.00 (Std 0.78, Median 3.0) — 79.5% scored $\ge 3$. Contextualized by calibration $\kappa_w = 0.252$.
* **Actionability:** Mean **2.93** / 4.00 (Std 0.87, Median 3.0) — 69.3% scored $\ge 3$. Contextualized by calibration $\kappa_w = 0.637$.
* **Brand Appropriateness:** Mean **2.44** / 4.00 (Std 0.61, Median 2.0) — 39.8% scored $\ge 3$ (59.1% concentrated at Score 2 due to conversational verbosity). Contextualized by calibration $\kappa_w = 0.273$.

*For deep dives into cost-asymmetry analysis, failure modes, and what is misleading about these numbers, read [REPORT.md](REPORT.md).*

---

## Full Pipeline Reproduction From Raw Data (Slow Cold Path)

If you wish to re-run the entire data ingestion, thread reconstruction, and live model API calls from scratch:

1. **Place Raw Data:**  
   Download `twcs.csv` from Kaggle (`thoughtvector/customer-support-on-twitter`) and place it at:
   ```
   data/raw/twcs.csv
   ```

2. **Configure API Keys:**  
   Copy `.env.example` to `.env` and add your keys:
   ```bash
   cp .env.example .env
   # Add GEMINI_API_KEY=... and GROQ_API_KEYS=key1,key2,...
   ```

3. **Execute Full Pipeline:**
   ```bash
   # Phase 0: Ingest raw data, clean tweets, reconstruct threads, run brand check
   make phase0

   # Phase 3: Train weak-supervision baseline from candidate pool
   python -m src.baseline_simple

   # Phase 4 & 5: Clear caches to force live API calls (WARNING: consumes live rate limits)
   # rm data/cache/llm_cache.json data/cache/judge_cache.json
   python -m src.eval_agent
   python -m src.run_full_judge_eval
   ```

---

## Repository Structure

```
supportlens/
├── README.md               — Project overview and turnkey reproduction guide
├── REPORT.md               — Comprehensive Phase 6 evaluation report
├── DECISIONS.md            — 27 chronological architectural and methodology decisions
├── FAILURES.md             — Hypothesized vs. observed failure modes
├── LABELING_GUIDE.md       — 8-class taxonomy and severity override rules (frozen v1.2)
├── Makefile                — Reproduction and pipeline shortcuts
├── requirements.txt        — Pinned Python dependencies
├── data/
│   ├── raw/                — data/raw/twcs.csv (gitignored; not required for evaluation)
│   ├── processed/          — Cleaned thread corpus, baseline & agent results
│   ├── golden/             — 200 hand-labeled golden set + calibration samples
│   └── cache/              — Committed llm_cache.json & judge_cache.json (Decision 8)
├── rubric/
│   └── judge_rubric.md     — 4-point pointwise rubric for Groundedness, Actionability, Brand
├── src/
│   ├── agent_orchestrator.py — Decoupled Dual-Path orchestrator (Path A + Path B boolean OR)
│   ├── agent_path_a.py       — Intent classifier + retrieval grounding prompt
│   ├── agent_path_b.py       — Independent zero-gated severity override extractor
│   ├── baseline_trivial.py   — Baseline 1: Priority keyword floor + always-escalate
│   ├── baseline_simple.py    — Baseline 2: Weakly supervised TF-IDF + Logistic Regression
│   ├── baseline_report.py    — Phase 3 comparative report generator
│   ├── eval_agent.py         — Phase 4 agent evaluation on golden dataset
│   ├── eval_agreement.py     — Phase 5 human-judge calibration & weighted kappa metrics
│   ├── judge.py              — Groq LLM-as-judge scoring pipeline
│   ├── llm_client.py         — Unified client with SHA256 disk caching
│   ├── retrieval.py          — TF-IDF brand reply retriever
│   └── run_full_judge_eval.py — Phase 5 Part D full 176-item judge benchmark
└── tests/
    └── test_pipeline.py    — 47 pytest assertions verifying pipeline and dataset integrity
```
