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


## Known Issues Caught During Development

1. **Sign-off Regex Failure**: The initial regex for agent sign-offs `r'[\^\-]\w+$'` failed on real-world data (e.g. `"Thanks - Mike"` and `"- Lee 2/2"`) because it didn't account for spacing between delimiters and names, nor for multi-word signoffs or trailing page markers. This was caught by sampling real data and updated to `r'\s*[\^\-]\s*[A-Za-z]{1,15}(?:\s+[A-Za-z]{1,15})?\s*(?:\d+/\d+)?\s*$'`.

2. **Thread Root/Leaf Inversion**: The BFS logic originally calculated `root_candidates = all_tweet_ids - replied_to_ids`. This incorrectly selected *leaf* nodes (tweets with no children) instead of *root* nodes (tweets with no known parent). This resulted in all threads having a length of 1. Caught by evaluating the average thread length output (`1.00`), the logic was inverted to check `in_response_to_tweet_id`, and explicit regression tests were added to prevent re-inversion.

3. **Per-Node Broadcast Exclusion**: The broadcast exclusion rule (`>15` replies) was originally only applied to brand account root nodes. Mid-conversation high-fanout nodes (e.g., a CEO broadcasting to millions from a non-brand numeric ID) were bypassing this and causing absurdly long threads (up to 974 tweets). The rule was updated to apply to *any* node, pruning all broadcast subtrees and reducing max thread length to a realistic contiguous 650 tweets.

4. **Marketing Tweet Contamination via Anonymized Brand Roots**: In TWCS, corporate brand handles (`@Verizon`, `@VerizonWireless`, `@VerizonFios`) were anonymized as numeric user IDs (`115722`, `115725`, `115990`, etc.) and erroneously tagged with `inbound=True`. Broadcast marketing campaigns (e.g. disaster relief pledges, premiere ticket giveaways) entered thread reconstruction as roots. When customers replied to ads and `VerizonSupport` intervened, threads were assigned to `VerizonSupport`, and naive `inbound=True` queries pulled corporate ad copy directly into the customer reading sample. Fixed by identifying anonymized corporate accounts (matching agent signoff patterns and known corporate IDs) and strictly enforcing customer-initiated thread roots (`root_author not in BRAND_ACCOUNTS`), eliminating 100% of marketing copy from the customer pool.
