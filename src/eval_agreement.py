"""
src/eval_agreement.py
---------------------
Phase 5: Run LLM Judge against the 60-item calibration sample, merge with
human blind scores, compute agreement metrics (Raw % and Quadratic Weighted Kappa),
score distributions, verbosity correlation, and extract side-by-side disagreements.
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
from sklearn.metrics import cohen_kappa_score
from scipy.stats import pearsonr, spearmanr

from src.judge import LLMJudge

CALIBRATION_SAMPLE_PATH = Path("data/golden/judge_calibration_sample.csv")
HUMAN_SCORES_PATH = Path("data/golden/human_calibration_scores.csv")
OUTPUT_COMPARISON_PATH = Path("data/golden/calibration_agreement_results.csv")


def run_evaluation():
    if not CALIBRATION_SAMPLE_PATH.exists():
        raise FileNotFoundError(f"Missing {CALIBRATION_SAMPLE_PATH}")
    if not HUMAN_SCORES_PATH.exists():
        raise FileNotFoundError(f"Missing {HUMAN_SCORES_PATH}")

    df_sample = pd.read_csv(CALIBRATION_SAMPLE_PATH)
    df_human = pd.read_csv(HUMAN_SCORES_PATH)

    # Merge on tweet_id
    merged = pd.merge(df_sample, df_human[[
        "tweet_id",
        "human_groundedness",
        "human_groundedness_reason",
        "human_actionability",
        "human_actionability_reason",
        "human_brand",
        "human_brand_reason",
    ]], on="tweet_id")

    assert len(merged) == 60, f"Expected 60 merged items, got {len(merged)}"

    judge = LLMJudge()

    print(f"Starting LLM Judge evaluation for 60 items using model: {judge.model}")
    results = []

    for idx, row in merged.iterrows():
        tid = row["tweet_id"]
        msg = str(row["message"])
        reply = str(row["reply_draft"])
        ev_str = str(row["retrieval_evidence_texts"]) if pd.notna(row["retrieval_evidence_texts"]) else ""
        brand_str = str(row["sample_brand_replies"]) if pd.notna(row["sample_brand_replies"]) else ""

        ev_texts = [x.strip() for x in ev_str.split(" || ") if x.strip() and x.strip() != "None"]
        brand_samples = [x.strip() for x in brand_str.split(" | ") if x.strip()]

        print(f"[{idx+1}/60] Judging tweet_id {tid}...", end=" ", flush=True)

        # 1. Groundedness
        g_res = judge.score_groundedness(msg, ev_texts, reply)
        # 2. Actionability
        a_res = judge.score_actionability(msg, reply)
        # 3. Brand Appropriateness
        b_res = judge.score_brand_appropriateness(reply, brand_samples)

        print(f"G:{g_res['score']} A:{a_res['score']} B:{b_res['score']}")

        rec = dict(row)
        rec["judge_groundedness"] = g_res["score"]
        rec["judge_groundedness_reason"] = g_res["reasoning"]
        rec["judge_actionability"] = a_res["score"]
        rec["judge_actionability_reason"] = a_res["reasoning"]
        rec["judge_brand"] = b_res["score"]
        rec["judge_brand_reason"] = b_res["reasoning"]
        rec["reply_word_count"] = len(reply.split())

        results.append(rec)

    res_df = pd.DataFrame(results)
    res_df.to_csv(OUTPUT_COMPARISON_PATH, index=False, encoding="utf-8")
    print(f"\nSaved full evaluation comparisons to {OUTPUT_COMPARISON_PATH}")

    # Compute Analysis
    print("\n" + "=" * 60)
    print("CALIBRATION AGREEMENT RESULTS & STATISTICS")
    print("=" * 60)

    dims = [
        ("Groundedness", "human_groundedness", "judge_groundedness", "human_groundedness_reason", "judge_groundedness_reason"),
        ("Actionability", "human_actionability", "judge_actionability", "human_actionability_reason", "judge_actionability_reason"),
        ("Brand Appropriateness", "human_brand", "judge_brand", "human_brand_reason", "judge_brand_reason"),
    ]

    summary_rows = []

    for dim_name, h_col, j_col, h_reas, j_reas in dims:
        h_scores = res_df[h_col].astype(int).values
        j_scores = res_df[j_col].astype(int).values

        raw_match = np.mean(h_scores == j_scores) * 100.0
        qw_kappa = cohen_kappa_score(h_scores, j_scores, weights="quadratic")
        lin_kappa = cohen_kappa_score(h_scores, j_scores, weights="linear")
        unw_kappa = cohen_kappa_score(h_scores, j_scores)

        # Pearson & Spearman between human and judge
        pr, _ = pearsonr(h_scores, j_scores)
        sr, _ = spearmanr(h_scores, j_scores)

        summary_rows.append({
            "Dimension": dim_name,
            "Raw Agreement (%)": f"{raw_match:.1f}%",
            "Quadratic Kappa": f"{qw_kappa:.3f}",
            "Linear Kappa": f"{lin_kappa:.3f}",
            "Unweighted Kappa": f"{unw_kappa:.3f}",
            "Pearson r": f"{pr:.3f}",
            "Spearman rho": f"{sr:.3f}",
        })

    summary_table = pd.DataFrame(summary_rows)
    print("\n--- Agreement Metrics Summary ---")
    print(summary_table.to_string(index=False))

    print("\n--- Score Distribution Comparison (Counts per anchor 1-4) ---")
    for dim_name, h_col, j_col, _, _ in dims:
        print(f"\nDimension: {dim_name}")
        dist_df = pd.DataFrame({
            "Score": [1, 2, 3, 4],
            "Human": [(res_df[h_col] == s).sum() for s in [1, 2, 3, 4]],
            "Judge": [(res_df[j_col] == s).sum() for s in [1, 2, 3, 4]],
        })
        print(dist_df.to_string(index=False))

    print("\n--- Verbosity Bias Check (Word Count vs Scores) ---")
    wc = res_df["reply_word_count"].values
    for dim_name, h_col, j_col, _, _ in dims:
        j_scores = res_df[j_col].values
        h_scores = res_df[h_col].values
        j_corr_p, _ = pearsonr(wc, j_scores)
        j_corr_s, _ = spearmanr(wc, j_scores)
        h_corr_p, _ = pearsonr(wc, h_scores)
        h_corr_s, _ = spearmanr(wc, h_scores)
        print(f"{dim_name:22s} | Judge r: {j_corr_p:+.3f} (rho: {j_corr_s:+.3f}) | Human r: {h_corr_p:+.3f} (rho: {h_corr_s:+.3f})")

    print("\n--- Key Disagreement Samples (|Human - Judge| >= 1) ---")
    for dim_name, h_col, j_col, h_reas, j_reas in dims:
        disagreements = res_df[abs(res_df[h_col] - res_df[j_col]) >= 1].copy()
        disagreements["delta"] = abs(disagreements[h_col] - disagreements[j_col])
        top_dis = disagreements.sort_values(by="delta", ascending=False).head(3)

        print(f"\n>>> Disagreements for {dim_name} (Total: {len(disagreements)}/60)")
        for _, d_row in top_dis.iterrows():
            print(f"  Tweet ID: {d_row['tweet_id']} | Human: {d_row[h_col]} vs Judge: {d_row[j_col]} (Delta: {d_row['delta']})")
            print(f"  Customer Message: \"{d_row['message'][:90]}...\"")
            print(f"  Reply Draft: \"{d_row['reply_draft'][:100]}...\"")
            print(f"  Human Reason: {d_row[h_reas]}")
            print(f"  Judge Reason: {d_row[j_reas]}")
            print("  " + "-" * 50)


if __name__ == "__main__":
    run_evaluation()
