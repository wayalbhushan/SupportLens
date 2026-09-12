# Failure Log & Hypotheses

Tracking predicted and observed failure modes throughout the SupportLens pipeline.
Hypotheses are formulated before evaluation and validated against empirical results.

---

## Pre-Evaluation Failure Hypotheses

### Hypothesis 1: Escalation Trigger Confusion — Surface Anger vs. Buried Severity
- **Formulation Date**: Phase 1 (Intent Taxonomy & Labeling Guide Definition)
- **Mechanism**: 
  1. **False Escalation (Surface Anger)**: The agent escalates customer messages that exhibit intense profanity, sarcasm, or shouting (ALL CAPS) even when there is no actionable request or severe dependency (e.g. pure venting like *"@VerizonSupport you guys are fucking garbage"*). Under the policy, pure venting without severe dependency should be acknowledged with empathy, not escalated to an expensive human engineering/dispatch queue.
  2. **Missed Escalation (Buried Severity)**: The agent fails to escalate high-severity dependencies when they are embedded inside rambling, non-standard rants or stated without explicit keywords (e.g. *"Day 7 without Internet. Elderly mom can't access #LifeAlert"*). The classifier may latch onto the generic venting tone (`complaint_no_request`) and miss the life-safety / multi-day outage override.
- **Evaluation Plan**:
  - Evaluate escalation recall on the golden set specifically for the subset of items tagged with `Severity Override` (medical, life-safety, multi-day outage, hazardous physical infrastructure).
  - Measure false positive escalation rate on high-sentiment-negative items in `complaint_no_request`.
- **Observed Result**: 
  - **Partially Observed in Phase 3 Baselines (2026-09-12)**:
    1. **Baseline 1 (Trivial Floor)** exhibits 100% false-escalation on pure venting because it unconditionally predicts `escalate=True` (Stratum A Escalation Precision is only 22.5%).
    2. **Baseline 2 (Simple TF-IDF + LogReg)** demonstrated the exact **Missed Escalation (Buried Severity)** mechanism, resulting in a severe blindspot:
       - **Sub-case 1.1: Legal / Regulatory Threat Suppression via "Other" Classification**:
         In the keyword dictionary, regulatory terms (`fcc`) were categorized strictly under `other`. In golden set evaluation, messages with explicit regulatory and legal filing threats (`GS-197`: `#BBB #FTC #FILECOMPLAINTS`, `GS-200`: `"on the verge of getting an attorney to blow the whistle"`) were classified as `other`. Because the deterministic policy maps `other` $\rightarrow$ `escalate=False`, Baseline 2 auto-handled both messages, completely suppressing mandatory legal escalation.
       - **Sub-case 1.2: Stated Technical Defect Masking Legal Override (GS-185 vs. Actionable Filings)**:
         In `GS-185` (*"@115722 i think a class action lawsuit is needed for claiming internet speeds that you arent actually receiving!!"*), Baseline 2 correctly classified the technical defect as `connectivity_issue`. However, because `connectivity_issue` deterministically maps to `escalate=False` in the absence of a dedicated severity extraction layer, the legal threat was ignored and the message was auto-handled. Note: `GS-185` represents a border case of rhetorical hyperbole ("a lawsuit is needed") rather than an affirmative declaration of intent to file (like `GS-197`/`GS-200`), surfacing a taxonomy grading distinction formally codified in `LABELING_GUIDE.md` v1.3.
       - **Empirical Baseline 2 Legal Recall**:
         - **0 / 2 (0.0% recall)** on unambiguous, affirmative first-person legal/regulatory filings against Verizon (`GS-197`, `GS-200`).
         - **GS-185** flagged separately as an ambiguous threat-severity grading boundary.
         - **GS-193** (*"The FCC is planning to dismantle Net Neutrality..."*) was correctly auto-handled as general policy commentary (`other` / `escalate=False`), confirming non-first-person commentary should not trigger escalation.
    3. **Taxonomy Boundary Ambiguity Accepted (Item `706604`)**:
       - In blind relabeling, item `706604` (*"Dear @115722 I'm not paying my damn bill to you actually offer the internet speed you advertise."*) moved from `billing_dispute` to `connectivity_issue`.
       - Codified in v1.3 Rule 3b: Stated affirmative billing action (payment withholding) overrides underlying technical defects because the operational queue requires billing ledger access.
       - Accepted as a known boundary limitation in frozen v1.2 golden-set labels without retroactively modifying the dataset.
    4. **Phase 4 Severity Architecture Specification (Decoupled Dual-Path Contract)**:
       - **Independent Dual-Path Inference**:
         - **Path A (Intent Classifier)**: Takes raw cleaned text $x$ and predicts $\hat{y}_{\text{intent}} \in \{C_1, \dots, C_8\}$.
         - **Path B (Severity Extractor)**: Runs as an independent pass over raw text $x$ and extracts $\hat{s} \in \{\text{hazard}, \text{medical}, \text{outage}\ge48\text{h}, \text{legal\_regulatory}, \text{revenue\_stop}, \text{none}\}$.
         - Path B is completely unconditioned on and never gated by Path A. It runs on 100% of messages, including those classified as `other` or `complaint_no_request`.
       - **Deterministic Orchestrator Logic**:
         $$\hat{y}_{\text{escalate}} = (\hat{s} \neq \text{none}) \lor \text{DEFAULT\_ESCALATION\_MAPPING}[\hat{y}_{\text{intent}}]$$
         Strict boolean OR. A positive severity extraction guarantees immediate escalation regardless of predicted intent class.
