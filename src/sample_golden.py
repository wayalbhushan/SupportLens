"""
src/sample_golden.py
--------------------
Phase 2: Stratified sampling for the Golden Evaluation Set (200 items).

Sampling Architecture (Decision 9):
  - Stratum A (120 items): Pure random sample from the in-scope pool.
    Represents the unbiased operational distribution; headline metrics are reported
    exclusively on Stratum A.
  - Stratum B (80 items): Targeted oversamples (16 items each across 5 under-represented
    categories / escalation triggers) from the remaining pool:
      1. billing_dispute targeted
      2. account_access targeted
      3. appointment_installation targeted
      4. tv_content_access targeted
      5. severity_override targeted (safety, medical, multi-day outage, hazard, regulatory)

Output:
  data/golden/golden_unlabeled.csv
"""

from pathlib import Path
import pandas as pd

POOL_PATH = Path("data/processed/verizon_in_scope_pool.parquet")
GOLDEN_DIR = Path("data/golden")
OUTPUT_CSV = GOLDEN_DIR / "golden_unlabeled.csv"

def main():
    print("[sample_golden] Loading in-scope Verizon customer pool...")
    df_pool = pd.read_parquet(POOL_PATH)
    print(f"[sample_golden] Total pool size: {len(df_pool):,} messages")

    # Rename tweet ID column if needed
    id_col = "root_tweet_id" if "root_tweet_id" in df_pool.columns else "tweet_id"

    # --- Stratum A: 120 Pure Random Items ---
    stratum_a = df_pool.sample(n=120, random_state=42).copy()
    stratum_a["stratum"] = "A"
    stratum_a["sampling_rule"] = "pure_random"
    print(f"[sample_golden] Drawn Stratum A (pure random): {len(stratum_a)} items")

    # Remaining pool for Stratum B
    remaining_pool = df_pool[~df_pool[id_col].isin(stratum_a[id_col])].copy()
    print(f"[sample_golden] Pool remaining for Stratum B: {len(remaining_pool):,} messages")

    # --- Stratum B: 80 Targeted Items (16 x 5 categories) ---
    b_rules = [
        ("billing_dispute_target", r"\b(bill|billing|charged|overcharge|fee|cost|refund|rate|promo|discount)\b"),
        ("account_access_target", r"\b(login|log in|password|sign in|locked out|portal|reset password)\b"),
        ("appointment_install_target", r"\b(technician|tech|install|installation|appointment|dispatch|setup)\b"),
        ("tv_content_target", r"\b(tv|channel|cable|dvr|stb|set top|hbo|red zone|univision|widgets)\b"),
        ("severity_override_target", r"\b(lifealert|medical|oxygen|911|emergency|wire down|wires down|pole|days without|day [2-9]|fcc|bbb|lawsuit|attorney)\b"),
    ]

    stratum_b_list = []
    used_tids = set(stratum_a[id_col])

    for rule_name, pattern in b_rules:
        candidates = remaining_pool[
            (~remaining_pool[id_col].isin(used_tids)) &
            (remaining_pool["text_clean"].str.contains(pattern, case=False, na=False))
        ]
        sample_size = min(16, len(candidates))
        sampled = candidates.sample(n=sample_size, random_state=42).copy()
        sampled["stratum"] = "B"
        sampled["sampling_rule"] = rule_name
        stratum_b_list.append(sampled)
        used_tids.update(sampled[id_col])
        print(f"[sample_golden] Drawn Stratum B ({rule_name}): {len(sampled)} items (pool: {len(candidates)})")

    stratum_b = pd.concat(stratum_b_list, ignore_index=True)
    assert len(stratum_b) == 80, f"Error: Stratum B has {len(stratum_b)} items instead of 80"

    # Combine Stratum A and Stratum B
    golden_df = pd.concat([stratum_a, stratum_b], ignore_index=True)
    assert len(golden_df) == 200, f"Error: Golden set has {len(golden_df)} items instead of 200"
    assert len(set(golden_df[id_col])) == 200, "Error: Duplicate tweet_ids found in golden set!"

    # Format dataframe for labeling
    golden_df = golden_df.rename(columns={id_col: "tweet_id"})
    golden_df["sample_id"] = [f"GS-{i+1:03d}" for i in range(len(golden_df))]
    golden_df["intent"] = ""
    golden_df["escalate"] = ""
    golden_df["severity_override"] = ""
    golden_df["notes"] = ""

    cols = [
        "sample_id",
        "tweet_id",
        "stratum",
        "sampling_rule",
        "text_clean",
        "intent",
        "escalate",
        "severity_override",
        "notes"
    ]
    golden_df = golden_df[cols]

    # Save to data/golden/
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"\n[sample_golden] Successfully generated golden unlabeled set -> {OUTPUT_CSV}")
    print(f"  - Total items: {len(golden_df)}")
    print(f"  - Stratum A: {(golden_df['stratum'] == 'A').sum()}")
    print(f"  - Stratum B: {(golden_df['stratum'] == 'B').sum()}")

if __name__ == "__main__":
    main()
