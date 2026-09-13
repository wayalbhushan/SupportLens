# SupportLens: Evaluation & Architecture Report

**System:** Customer Support Inbound Routing & Grounded Response Agent  
**Domain:** Verizon Support (FiOS / Wireline Home Services)  
**Evaluation Set:** 200 Golden Labeled Items (Stratum A: 120 Unbiased Natural; Stratum B: 80 Targeted Oversample)  
**Date:** September 2026  

---

## 1. Problem Framing

### 1.1 What "Good" Means for VerizonSupport: The Asymmetry of Routing Cost
In customer support automation for a major telecommunications provider like Verizon, evaluating an agent purely on classification accuracy is dangerous. The operational reality of inbound social customer care is governed by a severe **cost asymmetry**:

$$\text{Cost}(\text{False Auto-Handle}) \gg \text{Cost}(\text{False Escalate})$$

* **False Auto-Handle (Missed Escalation / False Negative):** When a customer experiencing a multi-day internet outage, an unfulfilled regulatory promise, or an active billing ledger dispute is mistakenly classified into an auto-handled intent (such as general advice or canned troubleshooting), the customer receives an ungrounded macro or a generic inquiry. The issue remains unresolved, leading to rapid escalation, brand churn, and potential regulatory fines (e.g., FCC/PUC complaints).
* **False Escalate (Unnecessary Escalation / False Positive):** When a customer who merely needs public diagnostic guidance is routed to a human engineering or billing queue, the company incurs a routing overhead cost (human agent time). While inefficient, the customer's issue is not dropped.

Consequently, a "good" system cannot simply optimize for overall accuracy; it must achieve high **Escalation Recall** on genuine human-intervention tickets while keeping **Escalation Precision** high enough to prevent queue flooding.

### 1.2 Deliberate System Boundaries: What We Chose Not to Build
To preserve engineering focus and protect evaluation rigor under fixed time and hardware constraints (16GB RAM, CPU-only local environment), five deliberate architectural boundaries were established:

1. **Wireless Domain Excluded (Decision 13):** Upstream analysis of the raw Twitter Customer Support (TWCS) corpus revealed a **5:1 product imbalance** favoring mobile/cellular over wireline. Filtering out wireless-only queries (SIM cards, mobile data, cellular tower reception) dropped exactly 397 candidate messages (4.78% of the usable candidate pool). Including wireless would have diluted a 200-item golden evaluation set across two completely divergent operational architectures. FiOS was selected because it possesses coherent, verifiable diagnostic paths (optical network terminal [ONT] light sequences, router power cycles, speed tier validation).
2. **Multi-Turn Dialogue Excluded (Decision 4):** SupportLens enforces a strict single-turn scope: exactly one inbound message maps to one routing and drafting decision. Managing conversational state, thread recovery, and user session timeouts was declared out of scope.
3. **No Model Fine-Tuning (Decision 3):** Prompt augmentation with historical retrieval was chosen over fine-tuning. Fine-tuning on historical tweets bakes in obsolete URLs, discontinued promotional packages, and conversational drift.
4. **Off-the-Shelf Vector Retrieval (Decision 6):** Standard TF-IDF vectorization and nearest-neighbor search were deployed rather than building a custom indexing engine, freeing resources for evaluation harness development and rubric calibration.
5. **Secondary Reply Quality Excluded (Decision 2):** Agent replies are evaluated strictly on three operational dimensions: Groundedness, Actionability, and Brand Appropriateness. Conversational humor, pleasantries, and open-ended chit-chat were discarded as irrelevant to resolution quality.

### 1.3 The Non-Actionable and Out-of-Scope Volume Reality
Analysis of the frozen golden evaluation set (Stratum A, $n=120$) reveals that a substantial portion of inbound traffic requires no technical troubleshooting or human escalation:
* Combined, `complaint_no_request` (15.8%, 19/120) and `praise_thanks` (7.5%, 9/120) — traffic with no actionable request at all — represent **23.3% of natural volume** (Stratum A).
* An additional 11.7% (14/120) falls into `other`, which includes both off-topic noise and legitimate but out-of-scope requests (e.g. coverage inquiries from prospective customers).
* Together, **35.0% of volume requires no operational routing action from this specific agent, though the reasons differ**.

This reframes the entire task: an inbound support agent does not need to troubleshoot or escalate all of its traffic. It must provide empathetic de-escalation for venting, acknowledge praise, and cleanly filter out-of-scope chatter without congesting human support queues.

### 1.4 Golden Evaluation Set: Sampling Strategy & Labeling Consistency
To evaluate both natural conversational volume and safety-critical edge cases, the 200-item golden evaluation set (`golden_labeled.csv`) was constructed via a two-stratum sampling protocol:
* **Stratum A (Natural Distribution, $n=120$):** Drawn via unbiased random sampling from the 7,626 in-scope VerizonSupport threads. Reflects real-world intent prevalence: `connectivity_issue` (28.3%, 34/120), `tv_content_access` (18.3%, 22/120), `complaint_no_request` (15.8%, 19/120), `other` (11.7%, 14/120), `billing_dispute` (10.8%, 13/120), `praise_thanks` (7.5%, 9/120), `account_access` (6.7%, 8/120), and `appointment_installation` (0.8%, 1/120). Natural human escalation demand is 22.5% (27/120). All headline benchmarks are evaluated on Stratum A.
* **Stratum B (Targeted Oversample, $n=80$):** Purposefully enriched with rare operational intents (`appointment_installation` $n=18$, `account_access` $n=15$, `billing_dispute` $n=15$) and acute safety/legal severity overrides (`physical_hazard` $n=4$, `medical` $n=1$, `business_critical` $n=2$, `prolonged_outage` $n=8$, `legal_regulatory` $n=6$) to ensure statistically meaningful per-class signal.
* **Labeling Consistency:** All items were hand-annotated in a single session under frozen `LABELING_GUIDE.md` v1.2. Annotator reliability was verified via an independent blind relabel of 40 shuffled, unlabelled items (`relabel_blind_sample.csv`) after a 24-hour delay, yielding **$\kappa = 0.705$ for intent** (75.0% raw match, 30/40) and **$\kappa = 0.747$ for escalation** (87.5% raw match, 35/40), demonstrating substantial inter-temporal agreement under Landis & Koch (1977) criteria.

---

## 2. Results vs. Two Baselines

### 2.1 Benchmark Comparison Table
The SupportLens agent was evaluated against two frozen baselines across the 200-item golden dataset (`golden_labeled.csv`). Stratum A ($n=120$) provides unbiased, natural distribution metrics; the Full Blended set ($N=200$) includes Stratum B's targeted oversample of rare intents and acute severity triggers.

| Metric | Baseline 1<br>*(Trivial Keyword)* | Baseline 2<br>*(TF-IDF + LogReg)* | Phase 4 Agent<br>*(Decoupled Dual-Path)* | Target Bar | Bar Met? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stratum A Intent Accuracy** | 48.3% | 47.5% | **77.5%** | > 48.3% | **✅ YES** |
| **Stratum A Macro-F1** | 0.466 | 0.433 | **0.710** | > 0.466 | **✅ YES** |
| **Stratum A Escalation Precision** | 0.225 | 0.706 | **0.950** | > 0.700 | **✅ YES** |
| **Stratum A Escalation Recall** | **1.000** | 0.444 | **0.704** | > 0.850 | **❌ NO** |
| **Stratum A Escalation F1** | 0.367 | 0.545 | **0.809** | — | — |
| **Simultaneous Escalation Bar** | ❌ *(P=0.225)* | ❌ *(R=0.444)* | **P=0.950, R=0.704** | P>70% & R>85% | **❌ NO** |
| | | | | | |
| **Full Blended Intent Accuracy** | 58.0% | 52.5% | **78.0%** | — | — |
| **Full Blended Macro-F1** | 0.558 | 0.509 | **0.732** | — | — |
| **Full Blended Escalation Precision** | 0.405 | 0.768 | **0.928** | — | — |
| **Full Blended Escalation Recall** | **1.000** | 0.531 | **0.790** | — | — |
| **Full Blended Escalation F1** | 0.577 | 0.628 | **0.853** | — | — |

*Data sources: `data/processed/baseline_results.md` and `data/processed/agent_results.md`.*

### 2.2 Why the Simple Baseline Failed to Beat the Trivial Baseline
On Stratum A raw accuracy, Baseline 2 (TF-IDF + Logistic Regression) actually underperformed Baseline 1 (47.5% vs. 48.3%). This is not an anomaly; it is an inevitable consequence of **weak supervision**:
* Baseline 2 was trained on 2,500 messages weak-labeled exclusively by Baseline 1's keyword heuristic dictionary.
* A statistical machine learning model trained on heuristic pseudo-labels cannot outperform the rule set that created its training signal when evaluated against clean, human-curated ground truth.
* Baseline 2 learned a smoothed linear approximation of the keyword rules. In boundary cases where keywords were ambiguous or absent, it defaulted to the majority class (`other`, 35.6% of weak training data), dragging down overall accuracy.

### 2.3 Cost-Asymmetry Analysis: "Safe in the Wrong Direction"
The escalation metrics reveal a critical trade-off:
* **Baseline 1** achieved 100% recall by predicting `escalate=True` for every single inbound message. This guarantees zero missed escalations, but at an operational precision of 22.5% on Stratum A (77.5% false alarm rate), completely overwhelming human tiers.
* **Baseline 2** raised precision to 70.6% by mapping predicted intents to escalation rules, but recall collapsed to 44.4%, dropping more than half of genuine customer issues.
* **The Phase 4 Agent** achieved an outstanding Escalation Precision of **95.0%** (19/20) on Stratum A and **92.8%** on the blended set. However, its Escalation Recall reached **70.4%** on Stratum A (19/27 caught, 8 missed), missing the target bar of >85%.

The agent is **safe in the wrong direction**: it protects Verizon's human agents from noisy tickets with 95% precision, but allows 29.6% of customers requiring human intervention to slip into automated auto-handling.

---

## 3. Top 5 Failure Modes

Our failure analysis surfaced five primary systemic failure mechanisms across baselines and the agent:

### Failure 1: `other` and `complaint_no_request` as an Escalation Sink
* **Mechanism:** Customers who describe legitimate, actionable account, billing, or appointment issues without using polite imperative verbs (e.g., *"How long does it take @VerizonSupport to remove my card from auto pay?"* or *"When are you going to wake up and realize you need to fix your billing"*) are frequently classified by the LLM as `complaint_no_request` or `other`. Because these intents deterministically route to `escalate=False`, the customer is trapped in an automated response loop.
* **Impact:** Path A intent-routing misses accounted for **12 of the 17 total under-escalation (false-negative) errors** on the blended golden set.
* **Representative Examples:**
  * `Tweet 1635027` (*"How long does it take @115725, @VerizonSupport to remove my card from auto pay?!"*): True intent `account_access` (Escalate=True); predicted `complaint_no_request` (Escalate=False).
  * `Tweet 2892866` (*"@115722 when are you going to wake up and realize that you need to fix your billing..."*): True intent `billing_dispute` (Escalate=True); predicted `complaint_no_request` (Escalate=False).

### Failure 2: Legal / Regulatory Severity Recall Shortfall & Annotator Self-Audit
* **Mechanism:** Baseline 2 suffered complete suppression of regulatory threats (0.0% recall on affirmative legal filings), because legal terms like `fcc` were mapped to `other` (auto-handled). To resolve this, Phase 4 implemented Path B: a zero-gated, independent severity extractor.
* **Empirical Result:** Frozen v1.2 headline recall on `legal_regulatory` was **33.3% (2/6)**.
* **The GS-199 Annotator Self-Audit:** A message-by-message ground-truth audit of all 6 legal items revealed critical insights:
  * `GS-197` (`#BBB #FTC #FILECOMPLAINTS`) and `GS-200` (*"on the verge of getting an attorney"*): Correctly caught by Path B (**True Positives**).
  * `GS-185` (*"i think a class action lawsuit is needed..."*): Path B predicted `none`. This aligns with `LABELING_GUIDE.md` v1.3 Rule 4 (third-person rhetorical hyperbole is not an affirmative first-person filing).
  * `GS-199` (*"@115722 day 8,29 hrs phone/ store. fraudcontracts... @12165, and @9988 docs and recordings"*): The human annotator had inferred that numeric user IDs `@12165` and `@9988` were regulatory officials, violating Section 4 Rule 2 of the guide (*judge strictly from explicit text; never infer*).
* **Transparent Reconciliation:**
  * Frozen v1.2 headline benchmark: **33.3% (2/6)** (retained to prevent post-hoc metric flattery).
  * Adjusted for label guide standard (excluding `GS-185`): **40.0% (2/5)**.
  * Adjusted for verified human annotator error (excluding `GS-199`): **50.0% (2/4)** (closest to operational truth, keeping borderline statutory citation `GS-023`).
  * Strict affirmative filings: **100.0% (2/2)**.

### Failure 3: Path A Intent-Routing Misses Driving Escalation Misses
* **Mechanism:** Even with Path B extracting emergency overrides independently, the bulk of operational escalations are triggered by Path A's default intent mapping (`billing_dispute`, `account_access`, `appointment_installation` $\rightarrow$ Escalate=True). When Path A misclassifies an escalating issue into a technical defect (`connectivity_issue` or `tv_content_access`), escalation fails.
* **Impact:** Clean attribution showed that **12 under-escalation errors** stemmed from Path A intent misses, while Path B severity misses caused only 5.
* **Representative Examples:**
  * `Tweet 377702` (*"@196474 Hi, is there a problem with FiOS subscriptions to HBO GO..."*): True intent `account_access` (Escalate=True); Path A predicted `tv_content_access` (Escalate=False).
  * `Tweet 262435` (*"@115725 Hello, Pseg replaced a pole in my backyard. Can you attach the wires..."*): True intent `appointment_installation` (Escalate=True); Path A predicted `connectivity_issue` (Escalate=False).

### Failure 4: Brand Appropriateness Systematic Verbosity and Formality Mismatch
* **Mechanism:** The agent's generator prompt instructs the model to be polite and helpful. Consequently, the LLM generates well-structured, formal 40-to-80-word corporate paragraphs (*"We apologize for the frustration regarding your bill. Let's get this sorted right away. Could you please send us a direct message with your account number..."*). Authentic `@VerizonSupport` replies in TWCS are radically different: they average under 25 words, use punchy casual empathy openers (*"Oh no!"*, *"Whoa!"*), and ask a single direct question.
* **Judge Scoring Clustering:** Across the 176 valid replies evaluated by the LLM judge, **59.1% (104/176)** were scored at **Score 2**. The judge penalized replies for failing the concise, casual register of real-time social support. On the headline set, reply length correlated negatively with brand score (judge $r = -0.594$, $N=176$); this matches the pattern seen in calibration (judge $r = -0.522$, human $r = -0.729$, $N=60$).

### Failure 5: Groundedness Ceiling from 88% Low-Similarity Retrieval Evidence
* **Mechanism:** TF-IDF retrieval across historical brand replies produced top-1 matches that were lexically distant from customer queries.
* **Evidence Reality:** Across the 176 evaluated agent outputs, **155 items (88.1%) had retrieval similarity < 0.50**. Only 13 items fell in the medium band (0.50–0.59), and only 8 reached high similarity ($\ge 0.60$).
* **Groundedness Plateau:** Despite 88% weak retrieval evidence, agent groundedness remained flat across similarity tiers:
  * Low similarity (< 0.50, $n=155$): Groundedness Mean = **2.83**
  * Medium similarity (0.50–0.59, $n=13$): Groundedness Mean = **2.85**
  * High similarity ($\ge 0.60$, $n=8$): Groundedness Mean = **2.62**
  * Overall correlation between retrieval similarity and judge groundedness was virtually zero ($r = 0.059$).
* **Root Cause:** The agent drafts replies by adhering to prompted procedural rules and domain knowledge embedded in the LLM, rather than by copying specific facts from retrieved tweets. The judge was evaluating policy adherence rather than historical retrieval grounding.

---

## 4. What Is Misleading About My Headline Numbers

A rigorous technical report must scrutinize its own results. Below are five concrete areas where our headline metrics could mislead a superficial reader:

### 4.1 The Weak-Label Validation Mirage (75.0% Val vs. 47.5% Golden Accuracy)
In Phase 3, Baseline 2 achieved **75.0% validation accuracy** and **0.693 Macro-F1** on an 80/20 train/validation split drawn from 2,500 weak-labeled examples. However, when evaluated against the clean, held-out golden test set ($n=120$), accuracy collapsed by **27.5 percentage points to 47.5%**. 
* **Why it misleads:** Had we reported validation accuracy on the weak-label split as proof of model capability, the baseline would have appeared moderately competent. Offline validation on heuristic pseudo-labels measures only consistency with the heuristic, not real-world performance.

### 4.2 Escalation Precision (95.0%) Masks Dangerous Recall (70.4%)
A casual observer looking at the executive summary might see **95.0% Escalation Precision** on Stratum A and conclude the agent is production-ready.
* **Why it misleads:** Precision measures what fraction of escalated tickets actually belonged in the human queue (19/20). It says nothing about how many tickets were dropped. Given the cost asymmetry where false auto-handles are catastrophic, **Recall (70.4%)** is the operational bottleneck. The agent allowed 8 out of 27 genuine escalation cases in Stratum A to be auto-handled. High precision creates a false sense of safety.

### 4.3 Groundedness Scores Plateau Regardless of Retrieval Evidence
The agent achieved a respectable headline Groundedness mean of **2.82 / 4.00**, with **79.5%** of replies scoring $\ge 3$.
* **Why it misleads:** Because 88.1% of items had retrieval similarity $<0.50$ and the correlation between similarity and groundedness was near zero ($r = 0.059$), the groundedness score does not measure whether the RAG pipeline retrieved useful historical solutions. The agent succeeded because the LLM was prompted with standard telecommunications customer care guidelines. Claiming the agent is "well-grounded by historical retrieval" is technically inaccurate; it is well-guided by prompt constraints.

### 4.4 Calibration Kappa Was Measured on a Stress-Test Sample, Not Natural Distribution
In Phase 5, judge-human agreement was measured via quadratic Cohen's kappa:
* **Actionability:** $\kappa_w = \mathbf{0.637}$ (Raw Match 63.3%, Pearson $r = 0.642$) — *Substantial Agreement*
* **Groundedness:** $\kappa_w = \mathbf{0.252}$ (Raw Match 40.0%, Pearson $r = 0.309$) — *Fair Agreement*
* **Brand Appropriateness:** $\kappa_w = \mathbf{0.273}$ (Raw Match 36.7%, Pearson $r = 0.445$) — *Fair Agreement*
* **Why it misleads:** The 60-item calibration sample was intentionally constructed as an adversarial stress-test (55% failure modes, oversampling misclassified intents and low-similarity retrievals). These kappa values reflect the judge's ability to discriminate edge cases under severe skew, not its performance on easy, typical support traffic. Furthermore, the drop in Brand Appropriateness kappa (0.455 $\rightarrow$ 0.273 in Revision 1) revealed a **negative lexical cutoff effect**: the LLM judge treated word-count limits as a hard step-function cutoff (scoring 31 items at Score 2), whereas human raters rewarded polite, customer-centric effort with Score 3.

### 4.5 FiOS/Home Wireline Scope Excludes Cellular/Mobile Realities
All metrics in this report apply exclusively to Verizon FiOS / wireline home services.
* **Why it misleads:** This report's findings are scoped entirely to FiOS/wireline traffic. Within this specific Twitter support corpus, wireless-related messages were a small minority (~7% by keyword match, 4.78% by the enforced filter) — but this dataset's composition should not be assumed to reflect Verizon's overall customer support volume across channels, which is unmeasured here. None of our findings, intent models, or grounding benchmarks generalize to Verizon Wireless.

---

## 5. What I'd Do With One More Week

If granted an additional week of development and evaluation, work would focus on five concrete engineering interventions:

1. **Fix Brand Appropriateness via Prompt Length Constraints & Few-Shot Injectors:**
   * Introduce an explicit system prompt constraint: *"Reply must be between 15 and 28 words. Begin with a short empathetic acknowledgment ('Oh no!', 'We hear you!'). Never write multi-sentence explanatory paragraphs."*
   * Inject 3 real historical short-reply examples directly into Path A. Re-evaluating the 176 golden set items would eliminate the Score 2 clustering (59.1%) and restore brand alignment.
2. **Measure Inter-Annotator Agreement with a Second Human Rater:**
   * Replace single-annotator intra-agreement (Cohen's $\kappa$) with true dual-annotator inter-rater reliability. A second independent rater on the 60 calibration items would establish an empirical human-human agreement baseline, contextualizing whether $\kappa_w = 0.252$ on Groundedness reflects judge error or inherent human rating ambiguity.
3. **Upgrade Retrieval Corpus Embeddings Beyond Lexical TF-IDF:**
   * Address the 88% low-similarity ceiling by replacing unigram/bigram TF-IDF with a dense bi-encoder embedding model (e.g., `BAAI/bge-small-en-v1.5`). Dense semantic embeddings would retrieve conceptually aligned troubleshooting precedent even when vocabulary diverges (e.g., matching "dropped connection" to "intermittent sync loss").
4. **Implement Outcome-Verified Resolution Grounding:**
   * Ground replies strictly on customer threads where resolution was confirmed (e.g., customer replied *"thank you, that fixed it"*). While only 7.3% of public threads in TWCS contain explicit customer confirmation, restricting retrieval to this subset would ensure the agent grounds only on verified solutions rather than deflection macros.
5. **Formalize the Rhetorical vs. Affirmative Threat Boundary:**
   * Collect and label an expanded sample of 50 customer messages citing regulatory bodies (FCC, FTC, PUC, BBB) and legal threats. Measure whether a dedicated few-shot prompt in Path B can reliably separate hyperbolic venting (*"someone ought to sue you"*) from affirmative personal filings (*"filing with FCC today"*), fully resolving the boundary highlighted by `GS-185` and `GS-197`.

---

## 6. Summary of Architectural & Methodology Decisions

The table below summarizes the 27 chronological decisions recorded throughout development. Detailed rationale, empirical justifications, and change histories are preserved in [DECISIONS.md](DECISIONS.md).

| Decision | Area / Topic | Core Decision & Operational Rationale | Primary File / Metric |
| :--- | :--- | :--- | :--- |
| **D1, D6** | Data Leakage & Search | Golden items strictly excluded from retrieval index; TF-IDF nearest-neighbor retrieval. | `src/retrieval.py` (Assert overlap = 0) |
| **D2, D13** | Scope & Brand | VerizonSupport selected via reply-substance ratio; wireless filtered (5:1 imbalance, 4.78% drop). | `LABELING_GUIDE.md` (FiOS wireline) |
| **D3, D4, D5** | System Bounds | Prompt RAG over fine-tuning; single-turn scope; upstream non-English message filtering. | `REPORT.md` Section 1.2 |
| **D7, D8** | Models & Caching | Disjoint judge (`qwen/qwen3.8-27b`) vs generator (`gemini-3.5-flash-lite`); deterministic prompt hashing. | `data/cache/llm_cache.json` |
| **D9, D17** | Dataset Design | 200 items: Stratum A (120 natural random, headline) + Stratum B (80 rare intent/severity oversamples). | `data/golden/golden_labeled.csv` |
| **D10, D16** | Guide Governance | Written guide versioned before labeling; frozen at v1.2 across all 200 items in single session. | `LABELING_GUIDE.md` v1.2 |
| **D11, D12** | Reliability Protocol | Intra-annotator 40-item blind relabel ($\kappa=0.705$/$0.747$); quadratic weighted judge kappa ($\kappa_w$). | `data/golden/relabel_blind_sample.csv` |
| **D14** | Thread Topology | Re-rooted 240 corporate broadcast trees to preserve legitimate downstream customer discussions. | `src/thread_check.py` |
| **D15, D20** | Dual-Path Routing | Independent Path B zero-gated severity extractor OR-gated with Path A default intent policy. | `src/agent_orchestrator.py` |
| **D18, D21** | Small-Sample Policy | Explicit flagging for $n<5$ classes; grouped acute emergency triggers ($n=7$, 85.7% recall). | `REPORT.md` Section 4 |
| **D19, D22** | Prompt Iteration | Guide v1.3 Rule 3b for billing withholding; bounded prompt rules preventing complaint sinks. | `src/agent_path_a.py` |
| **D23** | Ground-Truth Audit | Audited GS-199 rater error; retained 33.3% headline legal recall to prevent metric cherry-picking. | `REPORT.md` Section 3 (Failure 2) |
| **D24, D25** | Calibration Design | 60-item quality-stratified calibration sample; blind scoring uncovered 88% low-similarity retrieval. | `data/golden/judge_calibration_sample.csv` |
| **D26, D27** | Rubric & Rotation | Revision 1 Groundedness disambiguation (+0.106 $\kappa$); 5-key Groq rotation pool across 176 items. | `src/run_full_judge_eval.py` |

---

## 7. References & AI Assistant Attribution

### References & Citations
1. **Primary Dataset:** Customer Support on Twitter (TWCS), thoughtvector, Kaggle (2017). Reconstructed 7,626 threads scoped to VerizonSupport wireline/FiOS customer care.
2. **Generative Model:** Google DeepMind `gemini-3.5-flash-lite` (Path A intent classifier, Path B severity extractor, and grounded response generator).
3. **Judge Model:** Alibaba Cloud / Qwen team `qwen/qwen3.8-27b` via Groq API (disjoint model family for LLM-as-a-judge evaluation).
4. **LLM-as-a-Judge Methodology:** Zheng, L., Chiang, W. L., Sheng, Y., et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. Advances in Neural Information Processing Systems (NeurIPS 2023).
5. **Inter-Rater Reliability:** Cohen, J. (1960). *A coefficient of agreement for nominal scales*. Educational and Psychological Measurement, 20(1), 37–46.
6. **Agreement Interpretation Standards:** Landis, J. R., & Koch, G. G. (1977). *The measurement of observer agreement for categorical data*. Biometrics, 33(1), 159–174.
7. **Core Software Libraries:** Scikit-learn (Pedregosa et al., 2011), SciPy (Virtanen et al., 2020), Pandas, PyArrow, FastAPI, Uvicorn.

### AI Assistant Attribution & Engineering Review
In accordance with the Hiver take-home guidelines (*"Cite anything you borrowed... we will ask you to explain and modify your own code live"*), **Antigravity (Google DeepMind agentic AI coding assistant)** was used throughout the project for boilerplate generation, scaffolding, regex drafting, and test harness execution. All taxonomy definitions, labeling judgments, operational boundaries, and evaluation designs were directed and reviewed by the author.

During development, manual code audits and unit test assertions caught **six critical engineering issues** introduced during AI-assisted implementation:
1. **Sign-off Regex Failure:** The assistant's initial regex `r'[\^\-]\w+$'` truncated multi-word agent sign-offs (e.g. `"- Lee 2/2"` or `"Thanks - Mike"`). Caught and rewritten with whitespace and page-marker tolerance in `src/clean.py`.
2. **Thread Root/Leaf Inversion:** The assistant inverted parent-child relationships in the BFS thread reconstructor, picking reply leaf nodes instead of conversation roots and collapsing average thread length to 1.00. Caught via metric assertions, inverted, and covered by `TestThreadRootLogic`.
3. **Per-Node Broadcast Exclusion:** Broadcast pruning was initially applied only to root brand nodes; high-fanout marketing nodes appearing mid-thread bypassed the check, generating 900+ tweet runaway threads. Resolved by enforcing per-node degree bounds ($>15$ replies).
4. **Marketing Tweet Contamination via Anonymized Brand Roots:** In TWCS, corporate handles (`@Verizon`, `@VerizonWireless`) were anonymized as numeric user IDs and tagged `inbound=True`, allowing marketing tweets to enter as customer roots. Caught in reading sample and eliminated by enforcing customer-authored thread roots.
5. **Path B Model-Drift and Cache-Key Mismatch:** During prompt iteration on Path B, unpinned model tags and system prompt variations caused non-deterministic cache lookups; resolved by pinning `gemini-3.5-flash-lite`, enforcing `temperature=0.0`, and standardizing SHA256 prompt hashing in `src/llm_client.py`.
6. **Fabricated Confidence Display:** A visual mock-up placeholder for model confidence (`0.88` / `0.90`) was placed in the demo frontend without underlying pipeline support; caught during pre-submission audit and completely removed from all schemas, templates, and UI components to preserve strict empirical truth.
