"""
src/baseline_simple.py
----------------------
Phase 3: Baseline 2 — Simple Weak-Supervision Baseline (TF-IDF + Logistic Regression).

Architecture:
  1. Weak-label ~2,500 messages from the clean in-scope Verizon pool using KEYWORD_DICT,
     strictly excluding all 200 golden set tweet_ids (asserted with zero leakage check).
  2. Sample with fixed seed 42.
  3. Print class distribution and flag any class with < 50 examples.
  4. Train TF-IDF (max_features=5000, English stopwords, 1-2 ngrams) +
     Logistic Regression (class_weight='balanced') on an 80/20 train/val split.
  5. Print validation metrics (accuracy, macro-F1, confusion matrix, per-class report).
  6. Evaluate on the 200-item golden evaluation set (Stratum A and full blended set).
  7. Escalation: Deterministic default mapping from predicted intent per Section 4 of
     LABELING_GUIDE.md v1.2 (not a separate classifier).
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.keyword_dict import KEYWORD_DICT, PRIORITY_ORDER

# Paths
GOLDEN_PATH = Path("data/golden/golden_labeled.csv")
POOL_CSV_PATH = Path("data/processed/verizon_in_scope_pool.csv")
POOL_PARQUET_PATH = Path("data/processed/verizon_in_scope_pool.parquet")

# Deterministic escalation mapping per Section 4 of LABELING_GUIDE.md v1.2.
# Escalation is a deterministic function of intent per the taxonomy design,
# not a separately learned behavior: billing_dispute, account_access, and
# appointment_installation require backend ledger, credential, or technician
# dispatch systems and thus deterministically escalate.
ESCALATION_DEFAULT_MAPPING: Dict[str, bool] = {
    "account_access": True,
    "appointment_installation": True,
    "billing_dispute": True,
    "tv_content_access": False,
    "connectivity_issue": False,
    "praise_thanks": False,
    "complaint_no_request": False,
    "other": False,
}

def compile_patterns() -> Dict[str, re.Pattern]:
    """Pre-compile regex patterns for each intent class."""
    compiled = {}
    for intent, terms in KEYWORD_DICT.items():
        escaped_terms = [re.escape(t) for t in terms]
        pattern_str = r"\b(?:" + "|".join(escaped_terms) + r")\b"
        compiled[intent] = re.compile(pattern_str, flags=re.IGNORECASE)
    return compiled

PATTERNS = compile_patterns()

def weak_label_message(text: str) -> str:
    """Assign weak label via keyword dictionary in priority order."""
    text_clean = str(text).lower()
    for intent in PRIORITY_ORDER:
        if PATTERNS[intent].search(text_clean):
            return intent
    return "other"

def load_clean_pool_and_sample(
    sample_size: int = 2500, random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load in-scope pool, strictly exclude all golden set tweet_ids, and sample.
    Asserts zero data leakage.
    """
    if POOL_CSV_PATH.exists():
        df_pool = pd.read_csv(POOL_CSV_PATH)
    elif POOL_PARQUET_PATH.exists():
        df_pool = pd.read_parquet(POOL_PARQUET_PATH)
    else:
        raise FileNotFoundError("In-scope pool file not found (.csv or .parquet)")

    golden_df = pd.read_csv(GOLDEN_PATH)
    golden_ids = set(golden_df["tweet_id"].astype(str))
    assert len(golden_ids) == 200, f"Expected 200 golden tweet IDs, got {len(golden_ids)}"

    id_col = "root_tweet_id" if "root_tweet_id" in df_pool.columns else "tweet_id"

    # Leakage check: exclude all golden tweet_ids from pool
    df_pool_clean = df_pool[~df_pool[id_col].astype(str).isin(golden_ids)].copy()

    # Explicit assertion: Zero golden IDs in remaining pool
    remaining_pool_ids = set(df_pool_clean[id_col].astype(str))
    overlap = remaining_pool_ids.intersection(golden_ids)
    assert len(overlap) == 0, f"LEAKAGE DETECTED: {len(overlap)} golden IDs found in pool!"
    print(f"[Leakage Check PASS] 0 / {len(golden_ids)} golden tweet_ids found in candidate pool.")

    # Sample 2,500 messages
    weak_df = df_pool_clean.sample(n=sample_size, random_state=random_state).copy()
    sample_overlap = set(weak_df[id_col].astype(str)).intersection(golden_ids)
    assert len(sample_overlap) == 0, f"LEAKAGE DETECTED in sampled set: {len(sample_overlap)} items!"
    print(f"[Leakage Check PASS] 0 golden tweet_ids found in sampled weak-label pool (n={len(weak_df)}).")

    return weak_df, golden_df

def evaluate_metrics(
    y_true_intent: np.ndarray,
    y_pred_intent: np.ndarray,
    y_true_esc: np.ndarray,
    y_pred_esc: np.ndarray,
    labels: List[str],
) -> Dict:
    """Compute comprehensive accuracy, macro-F1, per-class, escalation, and confusion matrix."""
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
    )

    acc = accuracy_score(y_true_intent, y_pred_intent)
    macro_f1 = f1_score(y_true_intent, y_pred_intent, average="macro", zero_division=0)

    p, r, f, s = precision_recall_fscore_support(
        y_true_intent, y_pred_intent, labels=labels, zero_division=0
    )
    per_class = {}
    for label, prec, rec, f1_val, supp in zip(labels, p, r, f, s):
        per_class[label] = {
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1_val),
            "support": int(supp),
        }

    # Binary escalation metrics (target class: True)
    esc_p, esc_r, esc_f, _ = precision_recall_fscore_support(
        y_true_esc, y_pred_esc, pos_label=True, average="binary", zero_division=0
    )

    cm = confusion_matrix(y_true_intent, y_pred_intent, labels=labels)

    return {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "per_class": per_class,
        "escalation": {"precision": float(esc_p), "recall": float(esc_r), "f1": float(esc_f)},
        "confusion_matrix": cm,
    }

def run_simple_baseline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    print("=" * 70)
    print("BASELINE 2: SIMPLE WEAK-SUPERVISION BASELINE (TF-IDF + Logistic Regression)")
    print("=" * 70)

    # 1. Sample and weak label
    weak_df, golden_df = load_clean_pool_and_sample(sample_size=2500, random_state=42)
    weak_df["weak_intent"] = [weak_label_message(t) for t in weak_df["text_clean"]]

    # 2. Print class distribution and flag < 50
    print("\nWeak-Labelled Set Class Distribution (n=2,500):")
    counts = weak_df["weak_intent"].value_counts()
    for intent in PRIORITY_ORDER:
        cnt = counts.get(intent, 0)
        pct = cnt / len(weak_df) * 100
        warn = ""
        if cnt < 50:
            warn = " <-- WARNING: <50 examples! Severe under-representation in weak labels."
        print(f"  {intent:<25}: {cnt:>5} ({pct:>5.1f}%){warn}")

    # 3. Train/Val Split (80/20 stratified)
    X = weak_df["text_clean"].fillna("").astype(str).values
    y = weak_df["weak_intent"].values

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"\nTrain split: {len(X_train)} samples | Val split: {len(X_val)} samples")

    # 4. Train TF-IDF + Logistic Regression
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)

    clf = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
    )
    clf.fit(X_train_vec, y_train)

    # 5. Validation Evaluation
    y_val_pred = clf.predict(X_val_vec)
    # Validation escalation: based on predicted vs weak true
    y_val_true_esc = np.array([ESCALATION_DEFAULT_MAPPING.get(lbl, False) for lbl in y_val])
    y_val_pred_esc = np.array([ESCALATION_DEFAULT_MAPPING.get(lbl, False) for lbl in y_val_pred])

    val_metrics = evaluate_metrics(y_val, y_val_pred, y_val_true_esc, y_val_pred_esc, PRIORITY_ORDER)

    print("\n" + "-" * 50)
    print("VALIDATION SET METRICS (Weak Ground-Truth, n=500):")
    print(f"  Val Intent Accuracy : {val_metrics['accuracy'] * 100:.1f}%")
    print(f"  Val Intent Macro-F1 : {val_metrics['macro_f1']:.3f}")
    print("\n  Per-Class Validation Breakdown:")
    for cls in PRIORITY_ORDER:
        m = val_metrics["per_class"][cls]
        print(f"    {cls:<25} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  (n={m['support']})")

    print("\n  Validation Confusion Matrix (labels in PRIORITY_ORDER):")
    print(val_metrics["confusion_matrix"])

    # 6. Evaluate on Golden Set (Held-out Test)
    golden_texts = golden_df["text_clean"].fillna("").astype(str).values
    golden_vec = vectorizer.transform(golden_texts)
    golden_pred_intent = clf.predict(golden_vec)

    # Escalation: Deterministic mapping from model's PREDICTED intent
    golden_pred_esc = np.array([ESCALATION_DEFAULT_MAPPING.get(lbl, False) for lbl in golden_pred_intent])

    golden_df["pred_intent"] = golden_pred_intent
    golden_df["pred_escalate"] = golden_pred_esc

    # Split into Stratum A and Full Blended
    df_a = golden_df[golden_df["stratum"] == "A"].copy()
    y_a_true = df_a["intent"].values
    y_a_pred = df_a["pred_intent"].values
    y_a_true_esc = df_a["escalate"].astype(bool).values
    y_a_pred_esc = df_a["pred_escalate"].astype(bool).values

    metrics_a = evaluate_metrics(y_a_true, y_a_pred, y_a_true_esc, y_a_pred_esc, PRIORITY_ORDER)

    y_full_true = golden_df["intent"].values
    y_full_pred = golden_df["pred_intent"].values
    y_full_true_esc = golden_df["escalate"].astype(bool).values
    y_full_pred_esc = golden_df["pred_escalate"].astype(bool).values

    metrics_full = evaluate_metrics(y_full_true, y_full_pred, y_full_true_esc, y_full_pred_esc, PRIORITY_ORDER)

    print("\n" + "=" * 70)
    print(f"HELD-OUT GOLDEN SET EVALUATION — STRATUM A (Pure Random, n={len(df_a)}):")
    print(f"  Overall Intent Accuracy : {metrics_a['accuracy'] * 100:.1f}%")
    print(f"  Intent Macro-F1         : {metrics_a['macro_f1']:.3f}")
    print(f"  Escalation (P / R / F1) : {metrics_a['escalation']['precision']:.3f} / {metrics_a['escalation']['recall']:.3f} / {metrics_a['escalation']['f1']:.3f}")

    print("\n  Per-Class Breakdown (Stratum A):")
    for cls in PRIORITY_ORDER:
        m = metrics_a["per_class"][cls]
        flag = " [! n<5 !]" if m["support"] < 5 else ""
        print(f"    {cls:<25} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  (n={m['support']}){flag}")

    print("\n" + "=" * 70)
    print(f"HELD-OUT GOLDEN SET EVALUATION — FULL BLENDED SET (N={len(golden_df)}):")
    print(f"  Overall Intent Accuracy : {metrics_full['accuracy'] * 100:.1f}%")
    print(f"  Intent Macro-F1         : {metrics_full['macro_f1']:.3f}")
    print(f"  Escalation (P / R / F1) : {metrics_full['escalation']['precision']:.3f} / {metrics_full['escalation']['recall']:.3f} / {metrics_full['escalation']['f1']:.3f}")

    print("\n  Per-Class Breakdown (Full Blended):")
    for cls in PRIORITY_ORDER:
        m = metrics_full["per_class"][cls]
        print(f"    {cls:<25} P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  (n={m['support']})")

    return {
        "val": val_metrics,
        "stratum_a": metrics_a,
        "full_blended": metrics_full,
        "weak_counts": counts.to_dict(),
        "vectorizer": vectorizer,
        "classifier": clf,
    }

if __name__ == "__main__":
    run_simple_baseline()
