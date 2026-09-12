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
- **Observed Result**: *Pending Phase 5 evaluation.*
