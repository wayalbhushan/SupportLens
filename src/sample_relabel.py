"""
src/sample_relabel.py
---------------------
Phase 2: Intra-annotator agreement preparation (Decision 11).

Extracts a blind 40-item sample (20% of the 200-item golden evaluation set),
strips labels, shuffles order, and saves to data/golden/relabel_blind_sample.csv.
The relabeling must be executed >=24 hours after original labeling (scheduled Sept 13-14)
to evaluate Cohen's kappa consistency without memory bias.
"""

from pathlib import Path
import pandas as pd

GOLDEN_LABELED_PATH = Path("data/golden/golden_labeled.csv")
RELABEL_BLIND_PATH = Path("data/golden/relabel_blind_sample.csv")

def main():
    print("[sample_relabel] Loading 200-item golden labeled dataset...")
    df = pd.read_csv(GOLDEN_LABELED_PATH)
    assert len(df) == 200, f"Error: expected 200 rows, found {len(df)}"

    # Sample 40 items: 24 from Stratum A (random), 16 from Stratum B (targeted)
    # This preserves the 60/40 ratio of the golden set
    stratum_a = df[df["stratum"] == "A"].sample(n=24, random_state=1337)
    stratum_b = df[df["stratum"] == "B"].sample(n=16, random_state=1337)

    blind_sample = pd.concat([stratum_a, stratum_b], ignore_index=True)
    # Shuffle order with a fixed seed so order cannot be cross-referenced
    blind_sample = blind_sample.sample(frac=1.0, random_state=42).reset_index(drop=True)

    # Prepare blind columns
    blind_sample["relabel_id"] = [f"RL-{i+1:02d}" for i in range(len(blind_sample))]
    blind_sample["intent"] = ""
    blind_sample["escalate"] = ""
    blind_sample["severity_override"] = ""
    blind_sample["notes"] = ""

    cols = ["relabel_id", "tweet_id", "text_clean", "intent", "escalate", "severity_override", "notes"]
    blind_df = blind_sample[cols]

    RELABEL_BLIND_PATH.parent.mkdir(parents=True, exist_ok=True)
    blind_df.to_csv(RELABEL_BLIND_PATH, index=False, encoding="utf-8")

    print(f"[sample_relabel] Successfully generated blind relabel sample -> {RELABEL_BLIND_PATH}")
    print(f"  - Total items: {len(blind_df)}")
    print("  - Scheduled execution: >=24 hours after original annotation (Sept 13-14).")

if __name__ == "__main__":
    main()
