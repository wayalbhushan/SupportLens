# Decision Log

Non-obvious decisions made throughout the project, with rationale.
Append new entries here as they arise — never reconstruct this file.

---

1. Golden set will be excluded from the retrieval index and from any
   few-shot prompt examples, to prevent evaluation leakage.

2. Brand will be chosen by measured reply-substance ratio (how often the
   brand resolves issues in public vs. deflects to DM), not by corpus size.

3. No fine-tuning — hardware constraint (16GB RAM, no GPU) plus retrieval-
   augmented prompting is sufficient for grounding.

4. Single-turn scope only — one inbound message to one decision. Multi-turn
   dialogue state is explicitly out of scope.

5. Non-English messages will be filtered before the golden set and agent
   pipeline; the filtered fraction will be reported as a stated limitation.

6. Off-the-shelf vector search (FAISS or sklearn nearest-neighbours) used
   instead of a custom index implementation, to protect time for evaluation.

7. The LLM judge will be a different model family from the generator model,
   to avoid self-preference bias in reply-quality scoring.

8. All LLM calls are cached to disk (hash of prompt -> response) and the
   cache is committed to the repo, so headline results reproduce from
   committed data in minutes rather than requiring live API calls subject
   to free-tier rate limits.

9. Golden set uses a two-stratum sample: Stratum A (pure random, ~120
   examples) for unbiased headline metrics, Stratum B (targeted oversample
   of rare intents / escalation cases, ~80 examples) for per-class signal.
   Headline numbers are reported on Stratum A only; blended numbers are
   flagged as such wherever shown.

10. A written label guide (LABELING_GUIDE.md) is created and versioned
    before labelling begins; if it changes mid-labelling, the change is
    committed and which examples were labelled under which version is noted.

11. Labelling consistency will be measured via intra-annotator agreement
    (Cohen's kappa on a blind relabel of a random subset after 24+ hours),
    or inter-annotator agreement if a second labeller is available.

12. Judge-human agreement will be measured with quadratically weighted
    Cohen's kappa on rubric scores, plus plain kappa on intent/escalation
    labels, using a fresh set of items not used to tune the judge rubric.

13. Scope is restricted to FiOS / Home services only. Wireless-only product
    intents (SIM, cellular data, mobile tower signal) are filtered upstream
    prior to sampling (measured exact drop: 397 messages / 4.78% of usable
    corpus) and documented as a stated boundary. Rationale: a 5:1 product
    imbalance makes wireless statistically unmeasurable in a ~200-item golden set;
    FiOS has coherent, publicly groundable diagnostic scripts (ONT lights, router
    resets, speed tests).

14. Corporate-rooted broadcast trees are re-rooted, not pruned. Of 268 threads
    rooted at an anonymized brand handle, 240 (89.6%) contained legitimate
    downstream customer support interactions with @VerizonSupport. Re-rooting
    preserves these grounded customer support conversations for retrieval/evaluation
    while stripping the top-level marketing copy.

15. Escalation policy includes a non-negotiable Severity Override. Regardless of
    the primary intent class (even for `complaint_no_request`), the agent must
    escalate if a message exhibits safety/medical dependencies (LifeAlert),
    hazardous physical infrastructure (downed live wires, broken poles), multi-day
    complete outages (>=48h), legal/regulatory filings (FCC/PUC), or business-critical
    stoppage.

16. LABELING_GUIDE.md is formally frozen at v1.2 before golden set labelling
    begins. All 200 items in the golden evaluation set are annotated under v1.2.
    Any post-hoc adjustments will require an explicit v1.3 version bump, Git
    commit, and documentation of affected rows to safeguard annotation consistency.

17. Golden Evaluation Set (data/golden/golden_labeled.csv) contains exactly 200
    curated items across two strata: Stratum A (120 pure random, unbiased headline
    metric test set; 22.5% natural escalation rate) and Stratum B (80 targeted
    oversamples across rare intents and severity overrides; 67.5% escalation rate).
    Every single item is annotated with intent, boolean escalation decision,
    severity override trigger, and operational notes under guide v1.2.
    Total labeling time spent: 3 hours 45 minutes in a single sustained session.

18. Stratum A per-class metrics are unreliable below n=5 (specifically,
    appointment_installation has n=1 in Stratum A). Top-line headline numbers
    (overall intent accuracy, overall escalation precision/recall/F1) are reported
    exclusively on Stratum A to preserve unbiased evaluation. However, for
    per-class breakdowns, any class with n<5 in Stratum A is explicitly flagged
    as "insufficient sample size for reliable natural estimate", and per-class
    numbers for those classes are reported from the blended set (A+B) with a
    mandatory disclosure that the blended sample reflects targeted oversampling,
    not natural operational frequency.

19. Affirmative Billing Actions Override Underlying Technical Defects (v1.3 Rule 3b):
    Intra-annotator blind relabeling surfaced a boundary contradiction on item 706604
    ("not paying my damn bill to you actually offer the internet speed you advertise"),
    which flipped from billing_dispute to connectivity_issue under a naive stated-defect
    reading. We formally resolved this in LABELING_GUIDE.md v1.3 by establishing Rule 3b:
    when a customer states an explicit, affirmative billing action (payment withholding,
    refusal to pay, refund demand, disputing billed charges) motivated by an underlying
    technical issue, the message is classified as billing_dispute. Rationale: the primary
    human support queue requires financial/account ledger access, which is an operational
    blocker. Golden set labels remain frozen under v1.2; this boundary is logged as an
    accepted taxonomy limitation for the 200 frozen rows.

20. Decoupled Dual-Path Architecture for Severity Escalation (Phase 4 Spec):
    Phase 3 Baseline 2 demonstrated a critical architectural flaw: folding severity
    overrides into the intent classifier caused 0/2 recall on affirmative legal threats
    because legal language was mapped to "other" (auto-handled) or masked by the technical
    defect intent. For Phase 4, the agent must employ a strict dual-path pipeline:
    Path A predicts intent independently; Path B extracts severity independently across
    100% of raw messages (never gated or conditioned on intent). Escalation is determined
    by a strict boolean OR: escalate = (severity != none) OR default_mapping[predicted_intent].

21. Grouping Acute/Rare Severity Classes in Reporting:
    In the golden evaluation set (N=200), acute emergency categories have very low
    natural support (physical_hazard n=4, business_critical n=2, medical n=1).
    Reporting individual recall on n=1 or n=2 leads to extreme variance (0% or 100%
    based on a single item) and uninformative zero-division risks. Therefore, while
    Path B extracts each exact category independently, evaluation aggregates
    acute/rare categories into a unified group (n=7, recall 85.7%), alongside
    dedicated per-class reporting for high-stakes regulatory (legal_regulatory n=6)
    and operational (prolonged_outage n=8) overrides.

22. Bounded Prompt Iteration for Path A Escalation Sink Mitigation:
    Evaluation revealed an escalation sink in Path A: customers stating actionable
    billing or account disputes without a polite imperative verb were disproportionately
    classified as complaint_no_request or other, dropping Stratum A escalation recall
    to 0.704. A single bounded prompt rule was added to Path A's system prompt
    directing the model to prioritize specific operational intent over complaint/other
    whenever operational facts are present. Furthermore, error audit identified
    that GS-185 ("class action lawsuit is needed for claiming speeds...") is an
    artifact of golden-set frozen v1.2 vs. guide v1.3 Rule 4 (rhetorical hyperbole
    classified as none), rather than an operational model miss.

23. Ground-Truth Auditing and Reporting Integrity for Legal / Regulatory Recall:
    During the legal-item audit, we discovered our own golden-set annotation for GS-199
    violated the guide's evidence rule (Section 4 Rule 2) by inferring that anonymized
    Twitter handles were regulatory officials. Despite finding that operational legal
    recall is realistically 50.0% (2/4, or 100% on strict affirmative filings), we
    deliberately retain the frozen v1.2 metric of 33.3% (2/6) as the reported headline
    in all summary tables. Changing the headline benchmark post-hoc would constitute
    metric cherry-picking to flatter results. We reconcile the numbers transparently
    via a four-tier breakdown in the report, affirming 50.0% (2/4) as closest to
    operational truth (removing the annotator rule violation while retaining the
    borderline statutory citation in GS-023).

24. Reversal of Cross-System Calibration Sampling in Favor of Quality-Stratified Agent Output:
    Initial guidance contemplated drawing the 60-item human/judge calibration sample
    equally across Baseline 1, Baseline 2, and the Phase 4 Agent (20 items each).
    However, audit revealed that Phase 3 baselines were implemented strictly as intent
    and escalation classifiers (`text -> (intent, escalate)`) and do not draft replies.
    Fabricating replies post-hoc would break calibration validity: scoring canned macros
    tests template detection rather than reply quality, while retrieving raw top-1
    historical brand replies creates circularity (scoring the ground truth as grounded).
    Furthermore, reopening baseline architecture violates the Phase 3 freeze.
    Instead, calibration validity requires spanning real quality variance, which the 176
    valid agent replies naturally provide across retrieval similarity bands (high >=0.60,
    medium 0.50-0.59, low <0.50), prediction correctness (correct intent vs. misclassification
    answering the wrong question), escalation status, and all 7 non-other intent classes.
    The 60-item calibration sample is drawn strictly from Phase 4 Agent output stratified
    on these quality proxies (seed=42).

25. Human Blind Calibration Protocol and 88% Weak Retrieval Evidence Finding:
    Prior to running the LLM-as-judge scoring pipeline (`src/judge.py`), human blind scoring
    was conducted across all 60 calibration items on Groundedness, Actionability, and Brand
    Appropriateness (180 distinct scores and justifications). Key methodological points and findings:
    - **Weak Retrieval Evidence Reality (88% below 0.50)**: Across the full 176 valid agent outputs,
      only 21 items total had retrieval similarity >= 0.50. 155 of 176 (88%) sat below this threshold.
      Thus, the agent's non-other replies primarily rely on the LLM's prompted policy constraints
      rather than close historical precedent. A judge evaluating "groundedness" against mostly weak
      evidence is measuring policy-consistency rather than close historical grounding.
    - **Calibration Harness vs. Headline Agent Evaluation**: The 60-item calibration set was
      deliberately engineered to be harder than the natural distribution (55% failure modes: wrong-intent
      matches or low similarity) to test whether the judge can discriminate good from bad replies.
      Consequently, calibration scores and kappa agreement statistics reflect judge sensitivity on a
      stress test, and are strictly separated from Part D's headline reply-quality evaluation.
    - **Blind Protocol and Integrity Freeze**: Human scoring was executed blind to retrieval similarity,
      golden vs. predicted intent comparison, and stratum labels. Each score was assigned using the exact
      rubric anchors (`rubric/judge_rubric.md`) accompanied by a specific one-line justification.
      The pass was completed in a single sitting (~45 minutes) and committed to version control
      (`data/golden/human_calibration_scores.csv`) before any call to `src/judge.py` or population
      of `data/cache/judge_cache.json`.





## Known Issues Caught During Development

1. **Sign-off Regex Failure**: The initial regex for agent sign-offs `r'[\^\-]\w+$'` failed on real-world data (e.g. `"Thanks - Mike"` and `"- Lee 2/2"`) because it didn't account for spacing between delimiters and names, nor for multi-word signoffs or trailing page markers. This was caught by sampling real data and updated to `r'\s*[\^\-]\s*[A-Za-z]{1,15}(?:\s+[A-Za-z]{1,15})?\s*(?:\d+/\d+)?\s*$'`.

2. **Thread Root/Leaf Inversion**: The BFS logic originally calculated `root_candidates = all_tweet_ids - replied_to_ids`. This incorrectly selected *leaf* nodes (tweets with no children) instead of *root* nodes (tweets with no known parent). This resulted in all threads having a length of 1. Caught by evaluating the average thread length output (`1.00`), the logic was inverted to check `in_response_to_tweet_id`, and explicit regression tests were added to prevent re-inversion.

3. **Per-Node Broadcast Exclusion**: The broadcast exclusion rule (`>15` replies) was originally only applied to brand account root nodes. Mid-conversation high-fanout nodes (e.g., a CEO broadcasting to millions from a non-brand numeric ID) were bypassing this and causing absurdly long threads (up to 974 tweets). The rule was updated to apply to *any* node, pruning all broadcast subtrees and reducing max thread length to a realistic contiguous 650 tweets.

4. **Marketing Tweet Contamination via Anonymized Brand Roots**: In TWCS, corporate brand handles (`@Verizon`, `@VerizonWireless`, `@VerizonFios`) were anonymized as numeric user IDs (`115722`, `115725`, `115990`, etc.) and erroneously tagged with `inbound=True`. Broadcast marketing campaigns (e.g. disaster relief pledges, premiere ticket giveaways) entered thread reconstruction as roots. When customers replied to ads and `VerizonSupport` intervened, threads were assigned to `VerizonSupport`, and naive `inbound=True` queries pulled corporate ad copy directly into the customer reading sample. Fixed by identifying anonymized corporate accounts (matching agent signoff patterns and known corporate IDs) and strictly enforcing customer-initiated thread roots (`root_author not in BRAND_ACCOUNTS`), eliminating 100% of marketing copy from the customer pool.
