"""
src/eval_agreement.py
---------------------
Phase 2: Intra-annotator agreement evaluation (Decision 11).

Calculates Cohen's kappa score on the blind 40-item relabeled sample
against the original golden annotations.
"""

from pathlib import Path
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

GOLDEN_PATH = Path("data/golden/golden_labeled.csv")
RELABEL_PATH = Path("data/golden/relabel_blind_sample.csv")

def evaluate_agreement():
    if not RELABEL_PATH.exists():
        print(f"Error: {RELABEL_PATH} does not exist.")
        return

    df_orig = pd.read_csv(GOLDEN_PATH)
    df_re = pd.read_csv(RELABEL_PATH)

    # Check if relabeling is completed
    if df_re["intent"].isna().any() or (df_re["intent"] == "").any():
        unlabeled = (df_re["intent"].isna() | (df_re["intent"] == "")).sum()
        print(f"[eval_agreement] Relabel sample has {unlabeled}/40 unannotated rows. Run after relabeling.")
        return

    merged = df_re.merge(df_orig, on="tweet_id", suffixes=("_relabel", "_orig"))
    assert len(merged) == len(df_re), "Mismatch in merged tweet_ids"

    # Intent Agreement
    y_orig_intent = merged["intent_orig"].astype(str)
    y_re_intent = merged["intent_relabel"].astype(str)

    raw_intent_acc = (y_orig_intent == y_re_intent).mean()
    kappa_intent = cohen_kappa_score(y_orig_intent, y_re_intent)

    # Escalation Agreement
    y_orig_esc = merged["escalate_orig"].astype(bool)
    y_re_esc = merged["escalate_relabel"].astype(bool)

    raw_esc_acc = (y_orig_esc == y_re_esc).mean()
    kappa_esc = cohen_kappa_score(y_orig_esc, y_re_esc)

    print("\n--- INTRA-ANNOTATOR AGREEMENT REPORT (Decision 11) ---")
    print(f"Sample Size: {len(merged)} items (blind 20% sample)")
    print(f"Intent Raw Agreement:       {raw_intent_acc*100:.1f}%")
    print(f"Intent Cohen's Kappa:       {kappa_intent:.3f}")
    print(f"Escalation Raw Agreement:   {raw_esc_acc*100:.1f}%")
    print(f"Escalation Cohen's Kappa:   {kappa_esc:.3f}")

    # Check discrepancies
    discrepancies = merged[merged["intent_orig"] != merged["intent_relabel"]]
    if not discrepancies.empty:
        print(f"\nDiscrepancies found: {len(discrepancies)} items")
        for _, r in discrepancies.iterrows():
            print(f"[{r['tweet_id']}] Original: {r['intent_orig']} -> Relabel: {r['intent_relabel']} | Text: {r['text_clean_orig'][:80]}")
    else:
        print("\nPerfect agreement: 0 discrepancies across all 40 items.")

if __name__ == "__main__":
    evaluate_agreement()
