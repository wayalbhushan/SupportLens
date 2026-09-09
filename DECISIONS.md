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
