"""
src/prepare_calibration_sample.py
---------------------------------
Phase 5 Part 1: Prepare the 60-item calibration sample for LLM-as-judge and human scoring.

Architecture (Decision 24):
  - Source: ONLY Phase 4 Agent outputs from `data/processed/agent_eval_predictions.csv`
    (176 candidate items with predicted_intent != 'other').
  - Exclusion of baselines: As logged in Decision 24, Phase 3 baselines were classification-only;
    fabricating replies breaks calibration validity.
  - Multi-axis quality-proxy stratification (60 items, fixed seed 42):
      1. Intent class: All 7 non-other canonical classes represented, oversampling rare classes.
      2. Retrieval similarity bands:
           - high: >= 0.60 (captures all 8 available items)
           - medium: 0.50 - 0.59 (captures all 13 available items)
           - low: < 0.50 (balanced to 60 items)
      3. Prediction correctness: Balanced mix of correct intent vs. misclassified intent
         (testing judge ability to catch replies answering the wrong question).
      4. Escalation status: Balanced mix of escalate=True vs. escalate=False.
  - Brand Reference Context: 5 real @VerizonSupport replies per predicted intent sampled
    from the retrieval corpus (excluding golden-set threads), pipe-separated.
  - Output: `data/golden/judge_calibration_sample.csv`
      Columns: tweet_id, message, predicted_intent, golden_intent,
               retrieval_evidence_texts, reply_draft, retrieval_similarity,
               escalate_pred, sample_brand_replies
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from src.retrieval import VerizonSupportRetriever
from src.judge import resolve_evidence_texts
from src.baseline_simple import weak_label_message

# Paths
AGENT_PRED_PATH = Path("data/processed/agent_eval_predictions.csv")
CORPUS_PATH = Path("data/processed/retrieval_corpus.csv")
CALIBRATION_OUTPUT_PATH = Path("data/golden/judge_calibration_sample.csv")


def load_brand_reference_replies(seed: int = 42) -> Dict[str, str]:
    """
    Extract 5 real @VerizonSupport replies per intent class from the retrieval corpus
    (which already strictly excludes all golden-set threads per Decision 1).
    Returns a dict mapping intent -> 5 pipe-separated replies.
    """
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"Retrieval corpus not found at {CORPUS_PATH}")

    df_corpus = pd.read_csv(CORPUS_PATH)
    df_corpus["intent"] = df_corpus["customer_text"].fillna("").apply(weak_label_message)

    intents = [
        "billing_dispute",
        "account_access",
        "connectivity_issue",
        "tv_content_access",
        "appointment_installation",
        "complaint_no_request",
        "praise_thanks",
    ]

    brand_samples = {}
    for intent in intents:
        sub = df_corpus[df_corpus["intent"] == intent]
        replies = (
            sub["brand_reply"]
            .dropna()
            .drop_duplicates()
            .sample(min(5, len(sub)), random_state=seed)
            .tolist()
        )
        # Pipe-separated format
        brand_samples[intent] = " | ".join(replies)

    return brand_samples


def build_calibration_sample(seed: int = 42) -> pd.DataFrame:
    """
    Construct the 60-item quality-stratified calibration sample from agent predictions.
    """
    if not AGENT_PRED_PATH.exists():
        raise FileNotFoundError(f"Agent predictions not found at {AGENT_PRED_PATH}")

    df_agent = pd.read_csv(AGENT_PRED_PATH)
    valid = df_agent[df_agent["pred_intent"] != "other"].copy()

    # Compute top-1 retrieval similarity for each candidate
    retriever = VerizonSupportRetriever()
    sims = []
    for _, r in valid.iterrows():
        ev = retriever.retrieve(r["text_clean"], k=1)
        sims.append(round(float(ev[0]["similarity"]), 4) if ev else 0.0)

    valid["retrieval_similarity"] = sims
    valid["sim_band"] = pd.cut(
        valid["retrieval_similarity"],
        bins=[-1, 0.49999, 0.59999, 1.0],
        labels=["low (<0.50)", "medium (0.50-0.59)", "high (>=0.60)"],
    )

    # Intent class quotas (summing exactly to 60)
    intent_quotas = {
        "billing_dispute": 10,
        "complaint_no_request": 10,
        "tv_content_access": 9,
        "connectivity_issue": 9,
        "appointment_installation": 8,
        "account_access": 8,
        "praise_thanks": 6,
    }

    rng = np.random.RandomState(seed)
    selected_indices = []

    for intent, quota in intent_quotas.items():
        sub = valid[valid["pred_intent"] == intent].copy()
        if len(sub) <= quota:
            selected_indices.extend(sub.index.tolist())
            continue

        # Prioritize rare similarity bands (high, medium) and incorrect predictions
        sub["priority_score"] = 0
        sub.loc[sub["sim_band"] == "high (>=0.60)", "priority_score"] += 3
        sub.loc[sub["sim_band"] == "medium (0.50-0.59)", "priority_score"] += 2
        sub.loc[~sub["intent_correct"], "priority_score"] += 1

        sub["rand"] = rng.rand(len(sub))
        sub = sub.sort_values(by=["priority_score", "rand"], ascending=[False, True])

        chosen = sub.head(quota)
        selected_indices.extend(chosen.index.tolist())

    sample_df = valid.loc[selected_indices].copy()
    assert len(sample_df) == 60, f"Expected exactly 60 items, got {len(sample_df)}"

    # Resolve evidence texts
    ev_texts_list = []
    for _, r in sample_df.iterrows():
        ev_resolved = resolve_evidence_texts(r["evidence_used"])
        ev_str = " || ".join(ev_resolved) if ev_resolved else "None"
        ev_texts_list.append(ev_str)
    sample_df["retrieval_evidence_texts"] = ev_texts_list

    # Reference brand replies per intent
    brand_samples = load_brand_reference_replies(seed=seed)
    sample_df["sample_brand_replies"] = sample_df["pred_intent"].map(brand_samples)

    # Rename and select final columns
    sample_df["message"] = sample_df["text_clean"]
    sample_df["predicted_intent"] = sample_df["pred_intent"]
    sample_df["golden_intent"] = sample_df["true_intent"]
    sample_df["escalate_pred"] = sample_df["pred_escalate"]

    final_cols = [
        "tweet_id",
        "message",
        "predicted_intent",
        "golden_intent",
        "retrieval_evidence_texts",
        "reply_draft",
        "retrieval_similarity",
        "escalate_pred",
        "sample_brand_replies",
        # Internal stratification metadata preserved for reporting
        "sim_band",
        "intent_correct",
    ]
    export_df = sample_df[final_cols].copy()

    # Save to CSV
    CALIBRATION_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    export_df.to_csv(CALIBRATION_OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"Saved 60-item calibration sample to {CALIBRATION_OUTPUT_PATH}")

    return export_df


def print_stratification_breakdown(df_sample: pd.DataFrame):
    """Print the final 60-item multi-axis stratification breakdown."""
    print("\n" + "=" * 75)
    print("PHASE 5 JUDGE CALIBRATION SAMPLE STRATIFICATION BREAKDOWN (N=60)")
    print("=" * 75)

    print("\n1. Breakdown by Predicted Intent Class:")
    print("-" * 50)
    for intent, cnt in df_sample["predicted_intent"].value_counts().items():
        print(f"  - {intent:<26}: {cnt:2d} items")

    print("\n2. Breakdown by Retrieval Similarity Band:")
    print("-" * 50)
    for band, cnt in df_sample["sim_band"].value_counts().items():
        print(f"  - {band:<26}: {cnt:2d} items")

    print("\n3. Breakdown by Prediction Correctness (Intent Accuracy Proxy):")
    print("-" * 50)
    for corr, cnt in df_sample["intent_correct"].value_counts().items():
        label = "Correct Intent (pred == golden)" if corr else "Misclassified Intent (pred != golden)"
        print(f"  - {label:<35}: {cnt:2d} items")

    print("\n4. Breakdown by Predicted Escalation Status:")
    print("-" * 50)
    for esc, cnt in df_sample["escalate_pred"].value_counts().items():
        label = "Escalate = True" if esc else "Escalate = False"
        print(f"  - {label:<26}: {cnt:2d} items")

    print("\n5. Cross-Tabulation: Predicted Intent x Similarity Band:")
    print("-" * 50)
    print(pd.crosstab(df_sample["predicted_intent"], df_sample["sim_band"]).to_string())

    print("\n6. Cross-Tabulation: Predicted Intent x Correctness:")
    print("-" * 50)
    print(pd.crosstab(df_sample["predicted_intent"], df_sample["intent_correct"]).to_string())

    print("\n7. Cross-Tabulation: Predicted Intent x Escalation:")
    print("-" * 50)
    print(pd.crosstab(df_sample["predicted_intent"], df_sample["escalate_pred"]).to_string())
    print("=" * 75)


if __name__ == "__main__":
    sample_df = build_calibration_sample(seed=42)
    print_stratification_breakdown(sample_df)
