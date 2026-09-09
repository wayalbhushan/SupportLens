"""
src/clean.py
------------
Phase 0 â€” Step 2: Sign-off stripping, language tagging, deduplication.

Sign-off patterns handled (user-confirmed present in real data):
  - ^JK, ^AA, ^HSB          (caret + initials, no space)
  - ^Tanuj, ^Jools           (caret + full name, no space)
  - - Mike, - Lee, - Becky   (hyphen-space + first name)
  - - Lee 2/2                (hyphen-space + name + page marker)
  - Lines with just the sign-off after a literal \n inside the cell

The corrected regex handles all of the above:
  \\s*  [\\^\\-]  \\s*  [A-Za-z]{1,15}  (?:\\s+[A-Za-z]{1,15})?  \\s*  (?:\\d+/\\d+)?  \\s*  $

NOT handled (accepted residual noise):
  - Multiword sign-offs beyond two words (extremely rare).
  - Names with hyphens or apostrophes (e.g. "O'Brien") â€” rare enough to ignore.
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from src.ingest import load_raw

PROCESSED_DIR = Path("data/processed")

# â”€â”€ Sign-off pattern â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Breakdown:
#   \\s*           â€” strip any leading whitespace/newlines before the signoff
#   [\^\-]         â€” literal caret or hyphen (the signoff delimiter)
#   \\s*           â€” optional space after delimiter (handles "- Mike")
#   [A-Za-z]{1,15} â€” first name or initials (1-15 chars)
#   (?:\\s+[A-Za-z]{1,15})? â€” optional second word (two-word names)
#   \\s*           â€” trailing whitespace
#   (?:\d+/\d+)?  â€” optional page marker like "2/2"
#   \s*$          â€” end of string (with any trailing whitespace)
SIGNOFF_PATTERN = re.compile(
    r"\s*[\^\-]\s*[A-Za-z]{1,15}(?:\s+[A-Za-z]{1,15})?\s*(?:\d+/\d+)?\s*$"
)


def strip_signoffs(text: str) -> Tuple[str, Optional[str]]:
    """
    Detect and strip an agent sign-off from the end of `text`.

    Returns:
        (cleaned_text, signoff) where signoff is the matched suffix or None.

    Examples:
        "Thanks for this. ^JK"         â†’ ("Thanks for this.", "^JK")
        "Apologies for that. - Mike"   â†’ ("Apologies for that.", "- Mike")
        "We'll look into it. - Lee 2/2"â†’ ("We'll look into it.", "- Lee 2/2")
        "No sign-off here."            â†’ ("No sign-off here.", None)
    """
    if not isinstance(text, str):
        return ("", None)

    match = SIGNOFF_PATTERN.search(text)
    if match:
        signoff = match.group(0).strip()
        cleaned = text[: match.start()].rstrip()
        return (cleaned, signoff if signoff else None)
    return (text, None)


def tag_language(df: pd.DataFrame, sample_n: int = 50_000) -> pd.DataFrame:
    """
    Add a `lang` column with ISO 639-1 language codes from langdetect.

    Performance: runs detection on a random sample of up to `sample_n` rows
    (default 50k). Running langdetect on all 2.8M rows would take hours.
    Remaining rows are labelled "unknown_unsampled". Filtering happens in
    Phase 1; the sampled fraction is sufficient to report the non-English
    rate honestly.

    Very short strings (single emoji, whitespace-only) raise LangDetectException
    â€” caught and labelled "unknown" rather than crashing.

    langdetect is non-deterministic by default; seed is set for reproducibility.
    """
    try:
        from langdetect import detect, DetectorFactory
        from langdetect.lang_detect_exception import LangDetectException
        DetectorFactory.seed = 42  # make langdetect deterministic
    except ImportError:
        print("[clean] WARNING: langdetect not installed. `lang` column set to 'unknown'.")
        df = df.copy()
        df["lang"] = "unknown"
        return df

    def _detect(text) -> str:
        if not isinstance(text, str) or len(text.strip()) < 3:
            return "unknown"
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"

    df = df.copy()
    df["lang"] = "unknown_unsampled"

    actual_n = min(sample_n, len(df))
    sample_idx = df.sample(n=actual_n, random_state=42).index

    print(
        f"[clean] Tagging languages on {actual_n:,} sampled rows "
        f"(out of {len(df):,} total) ..."
    )
    df.loc[sample_idx, "lang"] = df.loc[sample_idx, "text"].apply(_detect)

    sampled = df.loc[sample_idx]
    counts = sampled["lang"].value_counts()
    non_en_count = (sampled["lang"] != "en").sum()
    non_en_pct = non_en_count / actual_n * 100

    print("[clean] Language distribution in sample (top 10):")
    print(counts.head(10).to_string())
    print(
        f"[clean] Estimated non-English rows in sample: {non_en_count:,} "
        f"({non_en_pct:.1f}%) â€” NOT dropped (tagged only, filter in Phase 1)"
    )
    print(
        f"[clean] NOTE: {len(df) - actual_n:,} rows labelled 'unknown_unsampled' "
        "(not processed for speed; will be tagged in Phase 1 if needed)"
    )
    return df



def dedup(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop exact duplicate tweet_id rows. Reports the count before dropping.
    There should be none, but verify explicitly rather than assuming.
    """
    before = len(df)
    df = df.drop_duplicates(subset=["tweet_id"])
    dropped = before - len(df)
    if dropped == 0:
        print(f"[clean] Dedup: no duplicate tweet_ids found (as expected). Rows: {len(df):,}")
    else:
        print(
            f"[clean] Dedup: dropped {dropped} duplicate tweet_id rows. "
            f"Rows remaining: {len(df):,}"
        )
    return df


def run_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all cleaning steps and add text_clean + agent_signoff columns.
    Keeps original `text` column intact.
    """
    print("\n[clean] â”€â”€ Cleaning Pipeline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")

    # Dedup first (cheap, no side-effects)
    df = dedup(df)

    # Sign-off stripping
    print("[clean] Stripping agent sign-offs ...")
    results = df["text"].apply(
        lambda t: strip_signoffs(t) if isinstance(t, str) else ("", None)
    )
    df = df.copy()
    df["text_clean"] = results.apply(lambda r: r[0])
    df["agent_signoff"] = results.apply(lambda r: r[1])

    n_signoffs = df["agent_signoff"].notna().sum()
    print(f"[clean] Sign-offs detected: {n_signoffs:,} rows")

    # Print 20 random stripped examples so failures are visible
    signoff_rows = df[df["agent_signoff"].notna()].copy()
    if len(signoff_rows) > 0:
        sample_n = min(20, len(signoff_rows))
        sample = signoff_rows.sample(n=sample_n, random_state=42)
        print(f"\n[clean] -- {sample_n} random signoff-stripping examples -----------")
        for i, (_, row) in enumerate(sample.iterrows(), 1):
            print(f"  [{i:02d}] original  : {repr(row['text'][:120])}")
            print(f"        text_clean: {repr(row['text_clean'][:120])}")
            print(f"        signoff   : {repr(row['agent_signoff'])}")
            print()
        print("--------------------------------------------------------------------")

    # Language tagging
    df = tag_language(df)

    return df


# â”€â”€ CLI entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_raw = load_raw()
    df_clean = run_cleaning(df_raw)

    out_path = PROCESSED_DIR / "tweets_clean.parquet"
    df_clean.to_parquet(out_path, index=False)
    print(f"[clean] Saved cleaned data â†’ {out_path}")
    print("[clean] Done.")

