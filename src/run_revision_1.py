"""
src/run_revision_1.py
---------------------
Phase 5: Rubric Revision 1 (of 2 permitted).
Re-runs ONLY Groundedness and Brand Appropriateness on the same 60-item calibration set.
Actionability is preserved untouched from Revision 0.
Merges with updated human scores (including Tweet 399679 URL oversight correction).
Computes full side-by-side comparative analysis (Rev 0 vs Rev 1).
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

REV0_RESULTS_PATH = Path("data/golden/calibration_agreement_results.csv")
HUMAN_SCORES_PATH = Path("data/golden/human_calibration_scores.csv")
REV1_OUTPUT_PATH = Path("data/golden/calibration_agreement_results_rev1.csv")


def run_revision_1():
    print("=" * 65)
    print("PHASE 5: RUBRIC REVISION 1 (GROUNDEDNESS & BRAND APPROPRIATENESS)")
    print("=" * 65)

    df_rev0 = pd.read_csv(REV0_RESULTS_PATH)
    df_human = pd.read_csv(HUMAN_SCORES_PATH)

    # Merge fresh human scores
    merged = pd.merge(
        df_rev0[[c for c in df_rev0.columns if not c.startswith("human_")]],
        df_human[[
            "tweet_id",
            "human_groundedness",
            "human_groundedness_reason",
            "human_actionability",
            "human_actionability_reason",
            "human_brand",
            "human_brand_reason",
        ]],
        on="tweet_id"
    )

    judge = LLMJudge()
    print(f"Model: {judge.model}")
    print("Actionability: PRESERVED untouched from Revision 0.")
    print("Re-evaluating Groundedness and Brand Appropriateness with Revision 1 rubric...\n")

    results = []

    for idx, row in merged.iterrows():
        tid = row["tweet_id"]
        msg = str(row["message"])
        reply = str(row["reply_draft"])
        ev_str = str(row["retrieval_evidence_texts"]) if pd.notna(row["retrieval_evidence_texts"]) else ""
        brand_str = str(row["sample_brand_replies"]) if pd.notna(row["sample_brand_replies"]) else ""

        ev_texts = [x.strip() for x in ev_str.split(" || ") if x.strip() and x.strip() != "None"]
        brand_samples = [x.strip() for x in brand_str.split(" | ") if x.strip()]

        print(f"[{idx+1}/60] Re-judging tweet_id {tid}...", end=" ", flush=True)

        # 1. Groundedness (revised rubric)
        g_res = judge.score_groundedness(msg, ev_texts, reply)
        # 2. Actionability (untouched, preserve rev0)
        a_score = int(row["judge_actionability"])
        a_reason = str(row["judge_actionability_reason"])
        # 3. Brand Appropriateness (revised rubric)
        b_res = judge.score_brand_appropriateness(reply, brand_samples)

        print(f"G:{g_res['score']} (was {row['judge_groundedness']}) | B:{b_res['score']} (was {row['judge_brand']})")

        rec = dict(row)
        # Save previous Rev 0 judge scores
        rec["judge_groundedness_rev0"] = row["judge_groundedness"]
        rec["judge_groundedness_reason_rev0"] = row["judge_groundedness_reason"]
        rec["judge_brand_rev0"] = row["judge_brand"]
        rec["judge_brand_reason_rev0"] = row["judge_brand_reason"]

        # Update with Rev 1 judge scores
        rec["judge_groundedness"] = g_res["score"]
        rec["judge_groundedness_reason"] = g_res["reasoning"]
        rec["judge_actionability"] = a_score
        rec["judge_actionability_reason"] = a_reason
        rec["judge_brand"] = b_res["score"]
        rec["judge_brand_reason"] = b_res["reasoning"]

        results.append(rec)

    res_df = pd.DataFrame(results)
    res_df.to_csv(REV1_OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"\nSaved Revision 1 evaluation results to {REV1_OUTPUT_PATH}")

    # Compute Comparative Metrics
    print("\n" + "=" * 65)
    print("REVISION 0 VS. REVISION 1 AGREEMENT COMPARISON")
    print("=" * 65)

    comp_dims = [
        ("Groundedness", "human_groundedness", "judge_groundedness_rev0", "judge_groundedness", "human_groundedness_reason", "judge_groundedness_reason"),
        ("Actionability", "human_actionability", "judge_actionability", "judge_actionability", "human_actionability_reason", "judge_actionability_reason"),
        ("Brand Appropriateness", "human_brand", "judge_brand_rev0", "judge_brand", "human_brand_reason", "judge_brand_reason"),
    ]

    metrics_rows = []
    for name, h_col, j_rev0_col, j_rev1_col, _, _ in comp_dims:
        h = res_df[h_col].astype(int).values
        j0 = res_df[j_rev0_col].astype(int).values
        j1 = res_df[j_rev1_col].astype(int).values

        raw0 = np.mean(h == j0) * 100.0
        raw1 = np.mean(h == j1) * 100.0

        qw0 = cohen_kappa_score(h, j0, weights="quadratic")
        qw1 = cohen_kappa_score(h, j1, weights="quadratic")

        lin0 = cohen_kappa_score(h, j0, weights="linear")
        lin1 = cohen_kappa_score(h, j1, weights="linear")

        p0, _ = pearsonr(h, j0)
        p1, _ = pearsonr(h, j1)

        s0, _ = spearmanr(h, j0)
        s1, _ = spearmanr(h, j1)

        metrics_rows.append({
            "Dimension": name,
            "Raw Match (Rev0)": f"{raw0:.1f}%",
            "Raw Match (Rev1)": f"{raw1:.1f}%",
            "Quad Kappa (Rev0)": f"{qw0:.3f}",
            "Quad Kappa (Rev1)": f"{qw1:.3f}",
            "Linear Kappa (Rev1)": f"{lin1:.3f}",
            "Pearson r (Rev1)": f"{p1:.3f}",
            "Spearman rho (Rev1)": f"{s1:.3f}",
        })

    comp_table = pd.DataFrame(metrics_rows)
    print("\n--- Summary Comparison Table ---")
    print(comp_table.to_string(index=False))

    print("\n--- Score Histograms (Counts per anchor 1-4) ---")
    for name, h_col, j_rev0_col, j_rev1_col, _, _ in comp_dims:
        print(f"\nDimension: {name}")
        h = res_df[h_col].astype(int).values
        j0 = res_df[j_rev0_col].astype(int).values
        j1 = res_df[j_rev1_col].astype(int).values

        hist_df = pd.DataFrame({
            "Score": [1, 2, 3, 4],
            "Human": [(h == s).sum() for s in [1, 2, 3, 4]],
            "Judge (Rev0)": [(j0 == s).sum() for s in [1, 2, 3, 4]],
            "Judge (Rev1)": [(j1 == s).sum() for s in [1, 2, 3, 4]],
        })
        print(hist_df.to_string(index=False))

    print("\n--- Verbosity Correlation (Word Count vs Judge Score) ---")
    wc = res_df["reply_word_count"].values
    for name, _, _, j_rev1_col, _, _ in comp_dims:
        j1 = res_df[j_rev1_col].astype(int).values
        p, _ = pearsonr(wc, j1)
        s, _ = spearmanr(wc, j1)
        print(f"{name:22s} | Rev1 Judge r: {p:+.3f} (rho: {s:+.3f})")

    print("\n--- Key Disagreement Samples in Revision 1 ---")
    for name, h_col, _, j_rev1_col, h_reas, j_reas in comp_dims:
        if name == "Actionability":
            continue
        dis = res_df[abs(res_df[h_col] - res_df[j_rev1_col]) >= 1].copy()
        dis["delta"] = abs(dis[h_col] - dis[j_rev1_col])
        print(f"\n>>> Disagreements for {name} (Rev 1 Total: {len(dis)}/60)")
        for _, r in dis.sort_values("delta", ascending=False).head(3).iterrows():
            print(f"  Tweet {r['tweet_id']} | Human: {r[h_col]} vs Judge: {r[j_rev1_col]} (delta: {r['delta']})")
            print(f"  Message: \"{r['message'][:80]}...\"")
            print(f"  Reply: \"{r['reply_draft'][:90]}...\"")
            print(f"  Human Reason: {r[h_reas]}")
            print(f"  Judge Reason: {r[j_reas]}")
            print("  " + "-" * 50)


if __name__ == "__main__":
    run_revision_1()
