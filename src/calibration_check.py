"""
src/calibration_check.py
------------------------
Phase 4 Part E: Calibration Check for Path B (Severity Extraction).

Pulls 8 messages from the clean in-scope candidate pool (strictly excluding golden-set threads)
that match loose legal/regulatory keywords (lawyer, sue, legal, agency, complaint, report you, FCC, FTC, BBB, PUC).
Runs Path B independently on all 8, printing:
  - Tweet ID
  - Raw Customer Message
  - Predicted severity_label
  - Rationale

Requirements:
  - Requires GEMINI_API_KEY or GROQ_API_KEY in .env.
  - Caches results to data/cache/llm_cache.json (Decision 8).
"""

import os
import re
import sys
from pathlib import Path
import pandas as pd

from src.agent_path_b import PathBAgent

# Ensure utf-8 stdout on Windows
sys.stdout.reconfigure(encoding="utf-8")

POOL_PATH = Path("data/processed/verizon_in_scope_pool.csv")
GOLDEN_PATH = Path("data/golden/golden_labeled.csv")

def select_calibration_samples(n: int = 8, random_state: int = 42) -> pd.DataFrame:
    """Select 8 candidate messages matching loose legal/regulatory keywords from clean non-golden pool."""
    pool = pd.read_csv(POOL_PATH)
    golden = pd.read_csv(GOLDEN_PATH)
    golden_tids = set(golden["tweet_id"].astype(str))

    # Identify threads containing any golden tweet_id
    golden_threads = set()
    for _, r in pool.iterrows():
        tids = re.findall(r"\d+", str(r["tweet_ids"]))
        if set(tids).intersection(golden_tids):
            golden_threads.add(r["thread_id"])

    clean_pool = pool[~pool["thread_id"].isin(golden_threads)].copy()
    clean_pool = clean_pool[~clean_pool["root_tweet_id"].astype(str).isin(golden_tids)].copy()

    # Search for loose legal/regulatory keywords
    pat = r"(?i)\b(lawyer|sue|legal|agency|complaint|report you|fcc|ftc|bbb|puc)\b"
    matches = clean_pool[clean_pool["text_clean"].str.contains(pat, na=False)].copy()

    assert len(matches) >= n, f"Insufficient candidate matches in clean pool: {len(matches)}"
    sample_df = matches.sample(n=n, random_state=random_state).copy()
    return sample_df

def run_calibration():
    print("=" * 70)
    print("PHASE 4 PART E: PATH B SEVERITY EXTRACTION CALIBRATION CHECK")
    print("=" * 70)

    # Check API key availability
    has_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_groq = bool(os.environ.get("GROQ_API_KEY"))

    if not (has_gemini or has_groq):
        print("\n[!] API KEY NOT CONFIGURED IN .env:")
        print("    Please set GEMINI_API_KEY (or GROQ_API_KEY) in the .env file at the workspace root:")
        print("    c:\\Users\\wayal\\Desktop\\supportlens\\.env")
        print("    Then re-run this calibration script.")
        return None

    samples_df = select_calibration_samples(n=8, random_state=42)
    print(f"Selected 8 candidate messages from non-golden pool (n={len(samples_df)}).\n")

    agent_b = PathBAgent()
    results = []

    for i, (_, row) in enumerate(samples_df.iterrows(), 1):
        tid = str(row["root_tweet_id"])
        text = str(row["text_clean"]).strip()

        print("-" * 70)
        print(f"[{i}/8] TWEET ID: {tid}")
        print(f"RAW MESSAGE:\n  \"{text}\"")

        res = agent_b.extract_severity(text)
        sev_label = res.get("severity_label", "none")
        rationale = res.get("rationale", "")

        print(f"PREDICTED SEVERITY : {sev_label.upper()}")
        print(f"RATIONALE          : {rationale}")

        results.append({
            "index": i,
            "tweet_id": tid,
            "text": text,
            "severity_label": sev_label,
            "rationale": rationale,
        })

    print("\n" + "=" * 70)
    print("CALIBRATION SUMMARY TABLE")
    print("=" * 70)
    for r in results:
        flag = "🚨 OVERRIDE" if r["severity_label"] != "none" else "✅ NONE"
        print(f"[{r['index']}] Tweet {r['tweet_id']:<10} | {flag:<12} ({r['severity_label']:<17}) | Text: {r['text'][:55]}...")

    return results

if __name__ == "__main__":
    run_calibration()
