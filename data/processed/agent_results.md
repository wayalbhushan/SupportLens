# SupportLens — Phase 4 Agent Evaluation Report

**Date:** 2026-09-12  
**Architecture:** Decoupled Dual-Path Orchestrator (Decision 20)  
**Models:** Path A (Gemini 3.6 Flash + Grounded Retrieval) | Path B (Gemini 3.6 Flash, temp 0.0)  
**Target Dataset:** `data/golden/golden_labeled.csv` (200 items: 120 Stratum A, 80 Stratum B)  

---

## 1. Executive Summary & Comparison Against Phase 3 Bar

| Metric | Baseline 1 (Trivial Keyword) | Baseline 2 (TF-IDF + LogReg) | Phase 4 Agent | Target Bar | Target Met? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Stratum A Intent Accuracy** | 48.3% | 47.5% | **76.7%** | > 48.3% | **✅ YES** |
| **Stratum A Macro-F1** | 0.466 | 0.433 | **0.662** | > 0.466 | **✅ YES** |
| **Stratum A Escalation Precision** | 0.225 | 0.706 | **1.000** | > 0.700 | ✅ YES |
| **Stratum A Escalation Recall** | 1.000 | 0.444 | **0.593** | > 0.850 | ❌ NO |
| **Stratum A Escalation F1** | 0.367 | 0.545 | **0.744** | — | — |
| **Simultaneous Escalation Bar** | ❌ (P=0.225) | ❌ (R=0.444) | **P=1.000, R=0.593** | R > 85% & P > 70% | **❌ NO** |
| | | | | | |
| **Full Blended Intent Accuracy** | 58.0% | 52.5% | **78.0%** | — | — |
| **Full Blended Macro-F1** | 0.558 | 0.509 | **0.727** | — | — |
| **Full Blended Escalation Precision** | 0.405 | 0.768 | **0.983** | — | — |
| **Full Blended Escalation Recall** | 1.000 | 0.531 | **0.728** | — | — |
| **Full Blended Escalation F1** | 0.577 | 0.628 | **0.837** | — | — |

## 2. Path B: Independent Severity Extraction Analysis

Path B was executed with zero gating or conditioning on 100% of messages.

- **Binary Severity Detection (N=200, n=21 true overrides):**
  - Precision: **0.938**
  - Recall: **0.714**
  - F1-Score: **0.811**

### Per-Trigger Recall Breakdown

| Severity Trigger | Support (n) | Correctly Detected | Recall Rate | Notes |
| :--- | :---: | :---: | :---: | :--- |
| `legal_regulatory` | 6 | 2 | **33.3%** | Individual reporting |
| `prolonged_outage` | 8 | 7 | **87.5%** | Individual reporting (>= 48 hours) |
| `acute/rare` | 7 | 6 | **85.7%** | Grouped: physical_hazard (4), business_critical (2), medical (1) per Decision 21 |

## 3. Disentangled Failure Attribution (The Decoupled Architecture in Practice)

Because Path A (intent routing) and Path B (severity overrides) operate independently, every escalation error is cleanly attributable to a specific root cause:

| Attribution Root Cause | Count | Impact | Explanation |
| :--- | :---: | :---: | :--- |
| `Path A Intent Miss` | 18 | Under-escalation (FN) | Customer message had an escalating default intent (billing/account/appt) that Path A misclassified as non-escalating. |
| `Path B Severity Miss` | 4 | Under-escalation (FN) | Customer message contained an emergency/regulatory condition that Path B failed to extract. |
| `Path B Severity False Positive` | 1 | Over-escalation (FP) | Path B over-triggered an override on a non-emergency message. |

### Detailed Escalation Miss Audit

| Tweet ID | Stratum | True Intent | Pred Intent | True Sev | Pred Sev | True Esc | Pred Esc | Attribution | Customer Text Snippet |
| :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `436040` | A | `billing_dispute` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | @115725 Have this great rep helping me for a while &amp; now... |
| `903382` | A | `account_access` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | @VerizonSupport If I could get someone that can actually pul... |
| `997639` | A | `billing_dispute` | `other` | `legal_regulatory` | `none` | True | False | **Path B Severity Miss** | .@115722 Could you have a customer rep contact me about this... |
| `1635027` | A | `account_access` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | How long does it take @115725, @VerizonSupport to remove my ... |
| `746217` | A | `billing_dispute` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | @115725 @VerizonSupport Got a weird call with someone offeri... |
| `1547388` | A | `connectivity_issue` | `connectivity_issue` | `prolonged_outage` | `none` | True | False | **Path B Severity Miss** | @115722 I’ve never been so felt frustrated about smth like I... |
| `2951002` | A | `billing_dispute` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | @115725 your rewards program was/is a scam. Took my money an... |
| `2892866` | A | `billing_dispute` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | @115722 when are you going to wake up and realize that you n... |
| `2962200` | A | `billing_dispute` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | @VerizonSupport Going to Toronto for a few days. Do I need t... |
| `1468162` | A | `billing_dispute` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | What the hell @VerizonSupport??? I never got a final bill fr... |
| `956106` | A | `account_access` | `tv_content_access` | `none` | `none` | True | False | **Path A Intent Miss** | @115722 fucking garbage. Trying to sign in to watch ESPN on ... |
| `265214` | B | `billing_dispute` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | @VerizonSupport u shut my phone off instead of my moms and u... |
| `377702` | B | `account_access` | `tv_content_access` | `none` | `none` | True | False | **Path A Intent Miss** | @196474 Hi, is there a problem with FiOS subscriptions to HB... |
| `2115187` | B | `account_access` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | @84402 Since yesterday I have been unable to send outgoing e... |
| `1012001` | B | `account_access` | `tv_content_access` | `none` | `none` | True | False | **Path A Intent Miss** | @115722 your support page is a piece of garbage. I'm trying ... |
| `377168` | B | `account_access` | `tv_content_access` | `none` | `none` | True | False | **Path A Intent Miss** | @115722 please help with Starz login issue!!!!!... |
| `2615922` | B | `appointment_installation` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | Hey @115725- I emailed your customer service line with billi... |
| `1981642` | B | `appointment_installation` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | When you see a commercial for @115722 but they refuse to ins... |
| `2507806` | B | `appointment_installation` | `other` | `none` | `none` | True | False | **Path A Intent Miss** | @115722 : How would a working professional get Fios connecti... |
| `894006` | B | `appointment_installation` | `complaint_no_request` | `none` | `none` | True | False | **Path A Intent Miss** | @115725 your five star customer service gets a 0 star will n... |
| `2041296` | B | `tv_content_access` | `tv_content_access` | `none` | `prolonged_outage` | False | True | **Path B Severity False Positive** | So this is the third day without @226184. Thanks @115722 Im ... |
| `1019621` | B | `connectivity_issue` | `connectivity_issue` | `legal_regulatory` | `none` | True | False | **Path B Severity Miss** | @115722 i think a class action lawsuit is needed for claimin... |
| `1543877` | B | `billing_dispute` | `complaint_no_request` | `legal_regulatory` | `none` | True | False | **Path B Severity Miss** | @115722 day 8,29 hrs phone/ store. fraudcontracts, cover up ... |

## 4. Detailed Intent Classification Breakdown

### Stratum A (Unbiased Headline Set, n=120)

| Intent Class | Precision | Recall | F1-Score | Support | Notes |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `account_access` | 1.000 | 0.500 | 0.667 | 8 | OK |
| `appointment_installation` | 0.333 | 1.000 | 0.500 | 1 | ⚠️ **n < 5** (unrepresentative per Decision 18) |
| `billing_dispute` | 0.714 | 0.385 | 0.500 | 13 | OK |
| `tv_content_access` | 0.909 | 0.909 | 0.909 | 22 | OK |
| `connectivity_issue` | 0.886 | 0.912 | 0.899 | 34 | OK |
| `praise_thanks` | 1.000 | 0.222 | 0.364 | 9 | OK |
| `complaint_no_request` | 0.593 | 0.842 | 0.696 | 19 | OK |
| `other` | 0.650 | 0.929 | 0.765 | 14 | OK |

- **Stratum A Overall Accuracy:** 76.7%
- **Stratum A Macro-F1:** 0.662

#### Stratum A Confusion Matrix
| True \ Pred | acc_acc | appt_inst | bill_disp | tv_cont | conn_iss | praise | complaint | other |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **acc_acc** |   4 |   0 |   1 |   1 |   0 |   0 |   2 |   0 |
| **appt_inst** |   0 |   1 |   0 |   0 |   0 |   0 |   0 |   0 |
| **bill_disp** |   0 |   1 |   5 |   0 |   0 |   0 |   3 |   4 |
| **tv_cont** |   0 |   0 |   0 |  20 |   0 |   0 |   1 |   1 |
| **conn_iss** |   0 |   1 |   1 |   1 |  31 |   0 |   0 |   0 |
| **praise** |   0 |   0 |   0 |   0 |   2 |   2 |   4 |   1 |
| **complaint** |   0 |   0 |   0 |   0 |   2 |   0 |  16 |   1 |
| **other** |   0 |   0 |   0 |   0 |   0 |   0 |   1 |  13 |

### Full Blended Golden Set (N=200)

| Intent Class | Precision | Recall | F1-Score | Support | Notes |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `account_access` | 1.000 | 0.600 | 0.750 | 20 | OK |
| `appointment_installation` | 0.846 | 0.688 | 0.759 | 16 | OK |
| `billing_dispute` | 0.870 | 0.645 | 0.741 | 31 | OK |
| `tv_content_access` | 0.861 | 0.939 | 0.899 | 33 | OK |
| `connectivity_issue` | 0.906 | 0.923 | 0.914 | 52 | OK |
| `praise_thanks` | 1.000 | 0.308 | 0.471 | 13 | OK |
| `complaint_no_request` | 0.485 | 0.800 | 0.604 | 20 | OK |
| `other` | 0.538 | 0.933 | 0.683 | 15 | OK |

- **Full Blended Overall Accuracy:** 78.0%
- **Full Blended Macro-F1:** 0.727

#### Full Blended Confusion Matrix
| True \ Pred | acc_acc | appt_inst | bill_disp | tv_cont | conn_iss | praise | complaint | other |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **acc_acc** |  12 |   0 |   1 |   4 |   0 |   0 |   2 |   1 |
| **appt_inst** |   0 |  11 |   1 |   0 |   0 |   0 |   2 |   2 |
| **bill_disp** |   0 |   1 |  20 |   0 |   0 |   0 |   5 |   5 |
| **tv_cont** |   0 |   0 |   0 |  31 |   0 |   0 |   1 |   1 |
| **conn_iss** |   0 |   1 |   1 |   1 |  48 |   0 |   1 |   0 |
| **praise** |   0 |   0 |   0 |   0 |   2 |   4 |   5 |   2 |
| **complaint** |   0 |   0 |   0 |   0 |   3 |   0 |  16 |   1 |
| **other** |   0 |   0 |   0 |   0 |   0 |   0 |   1 |  14 |

## 5. Grounding Quality & TF-IDF Evidence Analysis

> [!NOTE]
> **What's Misleading About Grounding:**
> 1. **Similarity Score Distribution:** The TF-IDF cosine similarity scores of top-1 retrieved historical brand replies typically cluster between **0.52 and 0.64**. This indicates moderate lexical overlap, not near-duplicate semantic matches.
> 2. **Over-Claiming Safeguard:** When retrieved evidence is loosely related (e.g. general Wi-Fi advice for an ONT hardware issue), Path A is instructed to acknowledge weak matching and fall back to standardized policy-consistent language rather than hallucinating brand claims.
> 3. **Zero Brand Contamination:** Out of 200 items, exactly 0 retrieved evidence replies originated from `@Ask_Spectrum` or `@AsurionCares`, confirming 100% compliance with the retrieval safeguard.
