"""
src/run_full_judge_eval.py
--------------------------
Phase 5 Part D: Full Golden-Set LLM Judge Evaluation.
Runs the Groq LLM Judge (Revision 1 rubric) on all valid non-other items
from the Phase 4 Agent output (N=176 valid items out of 200 total).
Items with predicted intent == 'other' are explicitly skipped (returns None).
Computes headline reply-quality metrics, cross-tabulations, similarity band
breakdowns, and contextualizes with calibration kappa reliability statistics.
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr

from src.judge import LLMJudge, resolve_evidence_texts
from src.retrieval import VerizonSupportRetriever
from src.prepare_calibration_sample import load_brand_reference_replies

AGENT_EVAL_PATH = Path("data/processed/agent_eval_predictions.csv")
OUTPUT_FULL_EVAL_PATH = Path("data/processed/agent_full_judge_eval.csv")


def run_full_judge_eval():
    print("=" * 70)
    print("PHASE 5 PART D: FULL GOLDEN-SET AGENT EVALUATION (REVISION 1 RUBRIC)")
    print("=" * 70)

    if not AGENT_EVAL_PATH.exists():
        raise FileNotFoundError(f"Missing {AGENT_EVAL_PATH}")

    df_agent = pd.read_csv(AGENT_EVAL_PATH)
    total_items = len(df_agent)
    print(f"Total golden set evaluation items: {total_items}")

    # Compute top-1 retrieval similarity for all items
    print("Computing top-1 retrieval similarity across candidate items...")
    retriever = VerizonSupportRetriever()
    sims = []
    for _, r in df_agent.iterrows():
        ev = retriever.retrieve(str(r["text_clean"]), k=1)
        sims.append(round(float(ev[0]["similarity"]), 4) if ev else 0.0)
    df_agent["retrieval_similarity"] = sims
    df_agent["sim_band"] = pd.cut(
        df_agent["retrieval_similarity"],
        bins=[-1, 0.49999, 0.59999, 1.0],
        labels=["low (<0.50)", "medium (0.50-0.59)", "high (>=0.60)"],
    )

    # Reference brand replies per intent
    brand_samples_map = load_brand_reference_replies(seed=42)

    judge = LLMJudge()
    print(f"Judge Model: {judge.model}")
    print(f"Rubric: Revision 1 (Frozen)")

    results = []
    evaluated_count = 0
    skipped_count = 0

    print("\nExecuting evaluation across all 200 items (skipping predicted 'other')...\n")

    for idx, row in df_agent.iterrows():
        tid = row["tweet_id"]
        pred_intent = str(row["pred_intent"]).strip()
        msg = str(row["text_clean"])
        reply = str(row["reply_draft"]) if pd.notna(row["reply_draft"]) else ""

        rec = dict(row)

        if pred_intent.lower() == "other":
            rec["is_evaluated"] = False
            rec["judge_groundedness"] = None
            rec["judge_groundedness_reason"] = "Skipped: predicted intent is other"
            rec["judge_actionability"] = None
            rec["judge_actionability_reason"] = "Skipped: predicted intent is other"
            rec["judge_brand"] = None
            rec["judge_brand_reason"] = "Skipped: predicted intent is other"
            rec["reply_word_count"] = len(reply.split()) if reply else 0
            skipped_count += 1
            results.append(rec)
            continue

        evaluated_count += 1
        print(f"[{evaluated_count}/176] Judging Tweet {tid} ({pred_intent})...", end=" ", flush=True)

        ev_texts = resolve_evidence_texts(row["evidence_used"])
        brand_samples_str = brand_samples_map.get(pred_intent, "")
        brand_samples = [x.strip() for x in brand_samples_str.split(" | ") if x.strip()]

        # 1. Groundedness
        g_res = judge.score_groundedness(msg, ev_texts, reply)
        # 2. Actionability
        a_res = judge.score_actionability(msg, reply)
        # 3. Brand Appropriateness
        b_res = judge.score_brand_appropriateness(reply, brand_samples)

        print(f"G:{g_res['score']} A:{a_res['score']} B:{b_res['score']}", flush=True)

        rec["is_evaluated"] = True
        rec["judge_groundedness"] = int(g_res["score"])
        rec["judge_groundedness_reason"] = str(g_res["reasoning"])
        rec["judge_actionability"] = int(a_res["score"])
        rec["judge_actionability_reason"] = str(a_res["reasoning"])
        rec["judge_brand"] = int(b_res["score"])
        rec["judge_brand_reason"] = str(b_res["reasoning"])
        rec["reply_word_count"] = len(reply.split()) if reply else 0

        results.append(rec)

    eval_df = pd.DataFrame(results)
    eval_df.to_csv(OUTPUT_FULL_EVAL_PATH, index=False, encoding="utf-8")
    print(f"\nSaved full evaluation results to {OUTPUT_FULL_EVAL_PATH}")

    # Compute Headline Reply-Quality Statistics on Evaluated Items (N=176)
    valid_df = eval_df[eval_df["is_evaluated"]].copy()
    valid_df["judge_groundedness"] = valid_df["judge_groundedness"].astype(int)
    valid_df["judge_actionability"] = valid_df["judge_actionability"].astype(int)
    valid_df["judge_brand"] = valid_df["judge_brand"].astype(int)

    n_valid = len(valid_df)
    assert n_valid == 176, f"Expected 176 valid items, got {n_valid}"

    print("\n" + "=" * 70)
    print(f"HEADLINE REPLY-QUALITY RESULTS (FULL EVALUATION SET, N={n_valid})")
    print("=" * 70)

    # 1. Headline Means & Distributions
    dims = [
        ("Groundedness", "judge_groundedness", 0.252, "Fair (0.252)"),
        ("Actionability", "judge_actionability", 0.637, "Substantial (0.637)"),
        ("Brand Appropriateness", "judge_brand", 0.273, "Fair (0.273)"),
    ]

    headline_rows = []
    for d_name, col, kappa, kappa_desc in dims:
        scores = valid_df[col]
        headline_rows.append({
            "Dimension": d_name,
            "Mean Score (1-4)": f"{scores.mean():.2f}",
            "Std Dev": f"{scores.std():.2f}",
            "Median": f"{scores.median():.1f}",
            "% Score >= 3": f"{(scores >= 3).mean() * 100:.1f}%",
            "% Score == 4": f"{(scores == 4).mean() * 100:.1f}%",
            "Calibration Reliability (Kappa)": kappa_desc,
        })

    headline_table = pd.DataFrame(headline_rows)
    print("\n--- Summary Headline Metrics Table ---")
    print(headline_table.to_string(index=False))

    # 2. Score Histograms
    print("\n--- Headline Score Distribution (Counts across 176 valid items) ---")
    dist_rows = []
    for s in [1, 2, 3, 4]:
        dist_rows.append({
            "Score": s,
            "Groundedness": f"{(valid_df['judge_groundedness'] == s).sum()} ({(valid_df['judge_groundedness'] == s).mean()*100:.1f}%)",
            "Actionability": f"{(valid_df['judge_actionability'] == s).sum()} ({(valid_df['judge_actionability'] == s).mean()*100:.1f}%)",
            "Brand Appropriateness": f"{(valid_df['judge_brand'] == s).sum()} ({(valid_df['judge_brand'] == s).mean()*100:.1f}%)",
        })
    print(pd.DataFrame(dist_rows).to_string(index=False))

    # 3. Breakdown by Intent
    print("\n--- Headline Scores Breakdown by Intent ---")
    intent_group = valid_df.groupby("pred_intent").agg(
        n=("tweet_id", "count"),
        groundedness_mean=("judge_groundedness", "mean"),
        actionability_mean=("judge_actionability", "mean"),
        brand_mean=("judge_brand", "mean"),
    ).reset_index()
    intent_group["groundedness_mean"] = intent_group["groundedness_mean"].round(2)
    intent_group["actionability_mean"] = intent_group["actionability_mean"].round(2)
    intent_group["brand_mean"] = intent_group["brand_mean"].round(2)
    print(intent_group.to_string(index=False))

    # 4. Breakdown by Similarity Band
    print("\n--- Headline Scores Breakdown by Retrieval Similarity Band ---")
    sim_group = valid_df.groupby("sim_band", observed=False).agg(
        n=("tweet_id", "count"),
        groundedness_mean=("judge_groundedness", "mean"),
        actionability_mean=("judge_actionability", "mean"),
        brand_mean=("judge_brand", "mean"),
    ).reset_index()
    sim_group["groundedness_mean"] = sim_group["groundedness_mean"].round(2)
    sim_group["actionability_mean"] = sim_group["actionability_mean"].round(2)
    sim_group["brand_mean"] = sim_group["brand_mean"].round(2)
    print(sim_group.to_string(index=False))

    # 5. Breakdown by Prediction Correctness
    print("\n--- Headline Scores Breakdown by Intent Prediction Correctness ---")
    corr_group = valid_df.groupby("intent_correct").agg(
        n=("tweet_id", "count"),
        groundedness_mean=("judge_groundedness", "mean"),
        actionability_mean=("judge_actionability", "mean"),
        brand_mean=("judge_brand", "mean"),
    ).reset_index()
    corr_group["groundedness_mean"] = corr_group["groundedness_mean"].round(2)
    corr_group["actionability_mean"] = corr_group["actionability_mean"].round(2)
    corr_group["brand_mean"] = corr_group["brand_mean"].round(2)
    print(corr_group.to_string(index=False))

    # 6. Word count correlation
    print("\n--- Verbosity Correlation (Word Count vs Scores, N=176) ---")
    wc = valid_df["reply_word_count"].values
    for d_name, col, _, _ in dims:
        sc = valid_df[col].values
        pr, _ = pearsonr(wc, sc)
        sr, _ = spearmanr(wc, sc)
        print(f"{d_name:22s} | Pearson r: {pr:+.3f} | Spearman rho: {sr:+.3f}")


if __name__ == "__main__":
    run_full_judge_eval()
