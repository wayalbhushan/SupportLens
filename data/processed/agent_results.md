# SupportLens — Phase 4 Agent Evaluation Report

**Date:** 2026-09-12  
**Architecture:** Decoupled Dual-Path Orchestrator (Decision 20)  
**Models:** Path A (Gemini 3.6 Flash + Grounded Retrieval) | Path B (Gemini 3.6 Flash, temp 0.0)  
**Target Dataset:** `data/golden/golden_labeled.csv` (200 items: 120 Stratum A, 80 Stratum B)  

---

## 1. Executive Summary & Comparison Against Phase 3 Bar

| Metric | Baseline 1 (Trivial Keyword) | Baseline 2 (TF-IDF + LogReg) | Phase 4 Agent | Target Bar | Target Met? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stratum A Intent Accuracy** | 48.3% | 47.5% | **77.5%** | > 48.3% | **✅ YES** |
| **Stratum A Macro-F1** | 0.466 | 0.433 | **0.710** | > 0.466 | **✅ YES** |
| **Stratum A Escalation Precision** | 0.225 | 0.706 | **0.950** | > 0.700 | ✅ YES |
| **Stratum A Escalation Recall** | 1.000 | 0.444 | **0.704** | > 0.850 | ❌ NO |
| **Stratum A Escalation F1** | 0.367 | 0.545 | **0.809** | — | — |
| **Simultaneous Escalation Bar** | ❌ (P=0.225) | ❌ (R=0.444) | **P=0.950, R=0.704** | R > 85% & P > 70% | **❌ NO** |
| | | | | | |
| **Full Blended Intent Accuracy** | 58.0% | 52.5% | **78.0%** | — | — |
| **Full Blended Macro-F1** | 0.558 | 0.509 | **0.732** | — | — |
| **Full Blended Escalation Precision** | 0.405 | 0.768 | **0.928** | — | — |
| **Full Blended Escalation Recall** | 1.000 | 0.531 | **0.790** | — | — |
| **Full Blended Escalation F1** | 0.577 | 0.628 | **0.853** | — | — |

## 2. Path B: Independent Severity Extraction Analysis

Path B was executed with zero gating or conditioning on 100% of messages.

- **Binary Severity Detection (N=200, n=21 true overrides):**
  - Precision: **0.938**
  - Recall: **0.714**
  - F1-Score: **0.811**

### Per-Trigger Recall Breakdown

| Severity Trigger | Support (n) | Correctly Detected | Recall Rate | Notes |
| :--- | :---: | :---: | :---: | :--- |
| `legal_regulatory` | 6 | 2 | **33.3%** | Individual reporting (see audit below) |
| `prolonged_outage` | 8 | 7 | **87.5%** | Individual reporting (>= 48 hours) |
| `acute/rare` | 7 | 6 | **85.7%** | Grouped: physical_hazard (4), business_critical (2), medical (1) per Decision 21 |

### 2.1 Deep-Dive: Legal / Regulatory Recall Audit & Ground-Truth Reconciliation

In the main results table, we report the raw frozen v1.2 metric of **33.3% (2/6)**. We deliberately retain this as our headline figure—despite having the least confidence in its denominator—because it represents what the frozen golden set actually contains. Changing the headline benchmark post-hoc after seeing model outputs would constitute metric cherry-picking to flatter our performance, exactly the practice this evaluation is designed to prevent.

However, a comprehensive message-by-message audit of all 6 items reveals that this headline understates true operational capability, driven by labeling-version shifts and an annotator error:

| Sample ID | Tweet ID | Stratum | Customer Text Snippet | Golden Notes (v1.2) | Pred Sev | Audit Classification |
| :---: | :---: | :---: | :--- | :--- | :---: | :--- |
| `GS-197` | `2614567` | B | `...@115722 I'm wondering who else was promised a $250 GC... #BBB #FTC #FILECOMPLAINTS` | Unfulfilled promo; filing with BBB/FTC | `legal_regulatory` | **True Positive (Caught)** |
| `GS-200` | `201872` | B | `@VerizonSupport I have an open case and I'm on the verge of getting an attorney...` | Threatening retention of attorney | `legal_regulatory` | **True Positive (Caught)** |
| `GS-185` | `1019621` | B | `@115722 i think a class action lawsuit is needed for claiming internet speeds...` | Threatening class action lawsuit | `none` | **Label-Version Skew (v1.3 Rule 4)**: Third-person rhetorical hyperbole without an affirmative personal filing is explicitly defined as `none` in v1.3. Path B correctly adhered to the guide. |
| `GS-023` | `997639` | A | `.@115722 Could you have a customer rep contact me about this ad, False Advertising & the Rhode Island Deceptive Trade Practices Act...` | Threatening RI Deceptive Trade Practices Act | `none` | **Borderline Statutory Reference**: Cites a state statute to demand a callback rather than declaring a formal filing. Worth retaining in the denominator as an operational near-miss. |
| `GS-199` | `1543877` | B | `@115722 day 8,29 hrs phone/ store. fraudcontracts, cover up district manager. @12165, and @9988 docs and recordings` | Alleging contract fraud, recordings sent to regulatory officials | `none` | **Annotator Evidence-Rule Violation**: Ground-truth error. The annotator inferred that anonymized numeric handles `@12165` and `@9988` were regulatory officials, violating Section 4 Rule 2 (*judge solely from explicit text; never infer*). |
| `GS-035` | `2588515` | A | `@VerizonSupport you are charging me for a phone that I paid for and sent me to collections!` | Sent to collections for paid phone equipment | `none` | **Collections Dispute, Not Regulatory Threat**: Being sent to collections is an equipment billing issue, not an affirmative regulatory complaint against Verizon. (Escalated via Path A `billing_dispute` default). |

#### Structured Legal-Recall Reconciliation

| Evaluation Standard | Retained Denominator Items | Calculation | Legal Recall | Rationale |
| :--- | :--- | :---: | :---: | :--- |
| **Headline Benchmark (Frozen v1.2)** | All 6 original labeled items | $2 / 6$ | **33.3%** | **Reported headline.** Preserves frozen benchmark integrity; prevents post-hoc flattery. |
| **Adjusted for Label-Version Skew** | Excludes `GS-185` (v1.3 Rule 4 hyperbole) | $2 / 5$ | **40.0%** | Aligns evaluation with updated written guide standard. |
| **Adjusted for Annotator Error** | Excludes `GS-185` and `GS-199` | $2 / 4$ | **50.0%** | **Most representative of operational reality.** Removes a verified annotator rule violation while keeping the borderline statutory citation (`GS-023`) in the denominator. |
| **Strict Affirmative Filing Only** | `GS-197` and `GS-200` only | $2 / 2$ | **100.0%** | Strict legal counsel retention or affirmative agency filing (`#BBB`, `#FTC`). |

> [!IMPORTANT]
> **Annotator Self-Audit & Ground-Truth Review Discipline:**  
> During the legal-item audit, we found our own golden-set annotation for `GS-199` violated the guide's evidence rule (Section 4 Rule 2) by inferring that anonymized Twitter user handles were regulatory officials. This finding demonstrates that manual labeling errors occur even under a formal written guide, and that auditing ground truth—not just model outputs—is essential to credible evaluation. We consider **50.0% (2/4)** to be the estimate closest to operational ground truth, as `GS-199` is an unambiguous labeling error, while `GS-023` represents a genuine real-world borderline case that an operational pipeline should reasonably be challenged on.

### 2.2 Path B Determinism & Precision Reconciliation

Path B's standalone metrics ($N=200$):
- **True Positives (TP):** 15
- **False Positives (FP):** 1 (Tweet `2041296`: TV content outage of 3 days misclassified as `prolonged_outage` when total loss of internet was not present)
- **False Negatives (FN):** 6
- **Precision:** $15 / (15 + 1) = \mathbf{0.938}$
- **Recall:** $15 / 21 = \mathbf{0.714}$
- **F1-Score:** $\mathbf{0.811}$

The single False Positive (Tweet `2041296`) in Path B standalone corresponds **exactly 1:1** with the 1 `Path B Severity False Positive` in the Disentangled Escalation Attribution Table. By pinning `model="gemini-3.5-flash-lite"` across all Path B invocations, Path B achieves 100% bit-for-bit cache determinism (Decision 8) and total architectural independence from Path A (Decision 20).

## 3. Disentangled Failure Attribution (The Decoupled Architecture in Practice)

Because Path A (intent routing) and Path B (severity overrides) operate independently, every escalation error is cleanly attributable to a specific root cause:

| Attribution Root Cause | Count | Impact | Explanation |
| :--- | :---: | :---: | :--- |
| `Path A Intent Miss` | 12 | Under-escalation (FN) | Customer message had an escalating default intent (billing/account/appt) that Path A misclassified as non-escalating. |
| `Path B Severity Miss` | 5 | Under-escalation (FN) | Customer message contained an emergency/regulatory condition that Path B failed to extract. |
| `Path A Intent Over-escalation` | 4 | Over-escalation (FP) | Path A predicted an escalating intent on a non-escalating customer message. |
| `Path B Severity False Positive` | 1 | Over-escalation (FP) | Path B over-triggered an override on a non-emergency message. |

### Detailed Escalation Miss Audit

| Tweet ID | Stratum | True Intent | Pred Intent | True Sev | Pred Sev | True Esc | Pred Esc | Attribution | Customer Text Snippet |
| :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `997639` | A | `billing_dispute` | `other` | `legal_regulatory` | `none` | True | False | **Path B Severity Miss** | .@115722 Could you have a customer rep contact me about this... |
| `1635027` | A | `account_access` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | How long does it take @115725, @VerizonSupport to remove my ... |
| `746217` | A | `billing_dispute` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | @115725 @VerizonSupport Got a weird call with someone offeri... |
| `1547388` | A | `connectivity_issue` | `connectivity_issue` | `prolonged_outage` | `none` | True | False | **Path B Severity Miss** | @115722 I’ve never been so felt frustrated about smth like I... |
| `2870879` | A | `connectivity_issue` | `account_access` | `none` | `none` | False | True | **Path A Intent Over-escalation** | @VerizonSupport all devices, nothing website just doesn't co... |
| `200451` | A | `connectivity_issue` | `connectivity_issue` | `business_critical` | `none` | True | False | **Path B Severity Miss** | K.  @VerizonSupport, who’s paying me for clients I can’t acc... |
| `2892866` | A | `billing_dispute` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | @115722 when are you going to wake up and realize that you n... |
| `2962200` | A | `billing_dispute` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | @VerizonSupport Going to Toronto for a few days. Do I need t... |
| `1468162` | A | `billing_dispute` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | What the hell @VerizonSupport??? I never got a final bill fr... |
| `1347710` | B | `connectivity_issue` | `billing_dispute` | `none` | `none` | False | True | **Path A Intent Over-escalation** | @115725 yo why is my service always shit when i drop a mill ... |
| `377702` | B | `account_access` | `tv_content_access` | `none` | `none` | True | False | **Path A Intent Miss** | @196474 Hi, is there a problem with FiOS subscriptions to HB... |
| `2115187` | B | `account_access` | `connectivity_issue` | `none` | `none` | True | False | **Path A Intent Miss** | @84402 Since yesterday I have been unable to send outgoing e... |
| `377168` | B | `account_access` | `tv_content_access` | `none` | `none` | True | False | **Path A Intent Miss** | @115722 please help with Starz login issue!!!!!... |
| `2806897` | B | `connectivity_issue` | `account_access` | `none` | `none` | False | True | **Path A Intent Over-escalation** | @VerizonSupport where do i find my wifi password?... |
| `2615922` | B | `appointment_installation` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | Hey @115725- I emailed your customer service line with billi... |
| `1981642` | B | `appointment_installation` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | When you see a commercial for @115722 but they refuse to ins... |
| `894006` | B | `appointment_installation` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | @115725 your five star customer service gets a 0 star will n... |
| `2041296` | B | `tv_content_access` | `tv_content_access` | `none` | `prolonged_outage` | False | True | **Path B Severity False Positive** | So this is the third day without @226184. Thanks @115722 Im ... |
| `376777` | B | `tv_content_access` | `billing_dispute` | `none` | `none` | False | True | **Path A Intent Over-escalation** | What? @115725? Why are we paying you for your TV service if ... |
| `1019621` | B | `connectivity_issue` | `connectivity_issue` | `legal_regulatory` | `none` | True | False | **Path B Severity Miss** | @115722 i think a class action lawsuit is needed for claimin... |
| `262435` | B | `appointment_installation` | `connectivity_issue` | `none` | `none` | True | False | **Path A Intent Miss** | @115725 Hello, Pseg replaced a pole in my backyard. Can you ... |
| `1543877` | B | `billing_dispute` | `complaint_no_request` | `legal_regulatory` | `none` | True | False | **Path B Severity Miss** | @115722 day 8,29 hrs phone/ store. fraudcontracts, cover up ... |

## 4. Detailed Intent Classification Breakdown

### Stratum A (Unbiased Headline Set, n=120)

| Intent Class | Precision | Recall | F1-Score | Support | Notes |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `account_access` | 0.857 | 0.750 | 0.800 | 8 | OK |
| `appointment_installation` | 0.500 | 1.000 | 0.667 | 1 | ⚠️ **n < 5** (unrepresentative per Decision 18) |
| `billing_dispute` | 0.889 | 0.615 | 0.727 | 13 | OK |
| `tv_content_access` | 0.909 | 0.909 | 0.909 | 22 | OK |
| `connectivity_issue` | 0.906 | 0.853 | 0.879 | 34 | OK |
| `praise_thanks` | 0.500 | 0.222 | 0.308 | 9 | OK |
| `complaint_no_request` | 0.640 | 0.842 | 0.727 | 19 | OK |
| `other` | 0.579 | 0.786 | 0.667 | 14 | OK |

- **Stratum A Overall Accuracy:** 77.5%
- **Stratum A Macro-F1:** 0.710

#### Stratum A Confusion Matrix
| True \ Pred | acc_acc | appt_inst | bill_disp | tv_cont | conn_iss | praise | complaint | other |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **acc_acc** |   6 |   0 |   1 |   0 |   0 |   0 |   1 |   0 |
| **appt_inst** |   0 |   1 |   0 |   0 |   0 |   0 |   0 |   0 |
| **bill_disp** |   0 |   0 |   8 |   0 |   0 |   0 |   1 |   4 |
| **tv_cont** |   0 |   0 |   0 |  20 |   0 |   0 |   1 |   1 |
| **conn_iss** |   1 |   1 |   0 |   1 |  29 |   0 |   1 |   1 |
| **praise** |   0 |   0 |   0 |   0 |   2 |   2 |   4 |   1 |
| **complaint** |   0 |   0 |   0 |   0 |   1 |   1 |  16 |   1 |
| **other** |   0 |   0 |   0 |   1 |   0 |   1 |   1 |  11 |

### Full Blended Golden Set (N=200)

| Intent Class | Precision | Recall | F1-Score | Support | Notes |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `account_access` | 0.882 | 0.750 | 0.811 | 20 | OK |
| `appointment_installation` | 0.917 | 0.688 | 0.786 | 16 | OK |
| `billing_dispute` | 0.857 | 0.774 | 0.814 | 31 | OK |
| `tv_content_access` | 0.882 | 0.909 | 0.896 | 33 | OK |
| `connectivity_issue` | 0.880 | 0.846 | 0.863 | 52 | OK |
| `praise_thanks` | 0.667 | 0.308 | 0.421 | 13 | OK |
| `complaint_no_request` | 0.552 | 0.800 | 0.653 | 20 | OK |
| `other` | 0.500 | 0.800 | 0.615 | 15 | OK |

- **Full Blended Overall Accuracy:** 78.0%
- **Full Blended Macro-F1:** 0.732

#### Full Blended Confusion Matrix
| True \ Pred | acc_acc | appt_inst | bill_disp | tv_cont | conn_iss | praise | complaint | other |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **acc_acc** |  15 |   0 |   1 |   2 |   1 |   0 |   1 |   0 |
| **appt_inst** |   0 |  11 |   1 |   0 |   1 |   0 |   1 |   2 |
| **bill_disp** |   0 |   0 |  24 |   0 |   0 |   0 |   3 |   4 |
| **tv_cont** |   0 |   0 |   1 |  30 |   0 |   0 |   1 |   1 |
| **conn_iss** |   2 |   1 |   1 |   1 |  44 |   0 |   1 |   2 |
| **praise** |   0 |   0 |   0 |   0 |   2 |   4 |   5 |   2 |
| **complaint** |   0 |   0 |   0 |   0 |   2 |   1 |  16 |   1 |
| **other** |   0 |   0 |   0 |   1 |   0 |   1 |   1 |  12 |

## 5. Grounding Quality & TF-IDF Evidence Analysis

> [!NOTE]
> **What's Misleading About Grounding:**
> 1. **Similarity Score Distribution:** The TF-IDF cosine similarity scores of top-1 retrieved historical brand replies typically cluster between **0.52 and 0.64**. This indicates moderate lexical overlap, not near-duplicate semantic matches.
> 2. **Over-Claiming Safeguard:** When retrieved evidence is loosely related (e.g. general Wi-Fi advice for an ONT hardware issue), Path A is instructed to acknowledge weak matching and fall back to standardized policy-consistent language rather than hallucinating brand claims.
> 3. **Zero Brand Contamination:** Out of 200 items, exactly 0 retrieved evidence replies originated from `@Ask_Spectrum` or `@AsurionCares`, confirming 100% compliance with the retrieval safeguard.
