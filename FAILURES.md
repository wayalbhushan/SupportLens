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
       - **Sub-case 1.2: Stated Technical Defect Masking Legal Override**:
         In `GS-185` (*"@115722 i think a class action lawsuit is needed for claiming internet speeds that you arent actually receiving!!"*), Baseline 2 correctly classified the technical defect as `connectivity_issue`. However, because `connectivity_issue` deterministically maps to `escalate=False` in the absence of a dedicated severity extraction layer, the legal threat was ignored and the message was not escalated.
       - **Empirical Baseline 2 Result**: 0 / 3 (0.0% recall) on legal-regulatory escalation in the golden evaluation set.
    3. **Phase 4 Agent Verification Target**: The LLM agent architecture must decouple intent classification from severity override extraction so that legal, regulatory, medical, and physical hazards trigger `escalate=True` regardless of whether the underlying intent is `connectivity_issue`, `billing_dispute`, or `other`.
