"""
src/baseline_trivial.py
-----------------------
Phase 3: Baseline 1 — Trivial Keyword Baseline.

Algorithm:
  1. Lowercase the inbound message.
  2. Match against KEYWORD_DICT in PRIORITY_ORDER (specific categories first,
     complaint_no_request and other last).
  3. First matching category wins. If no match, predicts 'other'.
  4. Escalation: Always predicts escalate=True (trivial baseline floor).
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from src.keyword_dict import KEYWORD_DICT, PRIORITY_ORDER

GOLDEN_PATH = Path("data/golden/golden_labeled.csv")

def compile_patterns() -> Dict[str, re.Pattern]:
    """Pre-compile regex patterns for each intent class."""
    compiled = {}
    for intent, terms in KEYWORD_DICT.items():
        # Escape terms and wrap word boundaries
        escaped_terms = [re.escape(t) for t in terms]
        pattern_str = r"\b(?:" + "|".join(escaped_terms) + r")\b"
        compiled[intent] = re.compile(pattern_str, flags=re.IGNORECASE)
    return compiled

PATTERNS = compile_patterns()

def predict_trivial(text: str) -> Tuple[str, bool]:
    """
    Predict intent and escalation for a single message.
    Returns: (predicted_intent, predicted_escalate)
    """
    text_clean = str(text).lower()
    for intent in PRIORITY_ORDER:
        if PATTERNS[intent].search(text_clean):
            return intent, True  # Trivial escalation: always True
    return "other", True

def evaluate_predictions(y_true_intent, y_pred_intent, y_true_esc, y_pred_esc, labels: List[str]):
    """Compute comprehensive evaluation metrics for intent and escalation."""
    acc = accuracy_score(y_true_intent, y_pred_intent)
    macro_f1 = f1_score(y_true_intent, y_pred_intent, average="macro", zero_division=0)

    # Per-class metrics
    p, r, f, s = precision_recall_fscore_support(
        y_true_intent, y_pred_intent, labels=labels, zero_division=0
    )
    per_class = {}
    for label, prec, rec, f1_val, supp in zip(labels, p, r, f, s):
        per_class[label] = {
            "precision": prec,
            "recall": rec,
            "f1": f1_val,
            "support": supp,
        }

    # Escalation metrics for True class (positive class)
    esc_p, esc_r, esc_f, _ = precision_recall_fscore_support(
        y_true_esc, y_pred_esc, pos_label=True, average="binary", zero_division=0
    )

    # Confusion matrix
    cm = confusion_matrix(y_true_intent, y_pred_intent, labels=labels)

    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "escalation": {"precision": esc_p, "recall": esc_r, "f1": esc_f},
        "confusion_matrix": cm,
    }

def run_trivial_baseline():
    print("=" * 70)
    print("BASELINE 1: TRIVIAL KEYWORD BASELINE")
    print("=" * 70)
    print(f"Priority Order Chosen:\n  {' -> '.join(PRIORITY_ORDER)}\n")
    print("Escalation Rule: Always predict escalate=True (deliberate floor).\n")

    df = pd.read_csv(GOLDEN_PATH)
    all_labels = PRIORITY_ORDER

    # Run predictions
    preds = [predict_trivial(t) for t in df["text_clean"]]
    df["pred_intent"] = [p[0] for p in preds]
    df["pred_escalate"] = [p[1] for p in preds]

    # Evaluate Stratum A
    df_a = df[df["stratum"] == "A"].copy()
    res_a = evaluate_predictions(
        df_a["intent"], df_a["pred_intent"], df_a["escalate"], df_a["pred_escalate"], all_labels
    )

    # Evaluate Full 200 Blended
    res_all = evaluate_predictions(
        df["intent"], df["pred_intent"], df["escalate"], df["pred_escalate"], all_labels
    )

    print("-" * 50)
    print(f"STRATUM A (Pure Random, n={len(df_a)}) RESULTS:")
    print(f"  Overall Intent Accuracy : {res_a['accuracy'] * 100:.1f}%")
    print(f"  Intent Macro-F1         : {res_a['macro_f1']:.3f}")
    print(f"  Escalation (P / R / F1) : {res_a['escalation']['precision']:.3f} / {res_a['escalation']['recall']:.3f} / {res_a['escalation']['f1']:.3f}")

    print("\n  Per-Class Breakdown (Stratum A):")
    for cls in all_labels:
        m = res_a["per_class"][cls]
        flag = " [! n<5 !]" if m["support"] < 5 else ""
        print(f"    {cls:<25} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  (n={m['support']}){flag}")

    print("\n" + "-" * 50)
    print(f"FULL BLENDED GOLDEN SET (N={len(df)}) RESULTS:")
    print(f"  Overall Intent Accuracy : {res_all['accuracy'] * 100:.1f}%")
    print(f"  Intent Macro-F1         : {res_all['macro_f1']:.3f}")
    print(f"  Escalation (P / R / F1) : {res_all['escalation']['precision']:.3f} / {res_all['escalation']['recall']:.3f} / {res_all['escalation']['f1']:.3f}")

    print("\n  Per-Class Breakdown (Full Blended):")
    for cls in all_labels:
        m = res_all["per_class"][cls]
        print(f"    {cls:<25} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  (n={m['support']})")

    return res_a, res_all

if __name__ == "__main__":
    run_trivial_baseline()
