"""
src/ingest.py
-------------
Phase 0 — Step 1: Load the raw twcs.csv and produce a typed DataFrame.

Known data issues handled here:
  - `inbound` is the literal string "True"/"False", not a real bool.
  - `response_tweet_id` and `in_response_to_tweet_id` may contain
    comma-separated lists of ids in a single cell.
  - `created_at` is in Twitter's non-ISO format and must be parsed with
    strptime; do NOT use pd.to_datetime's inference.
  - Multi-line tweet text is handled correctly by pandas' quoting — do
    NOT write a custom line splitter.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

RAW_PATH = Path("data/raw/twcs.csv")
TWITTER_DT_FMT = "%a %b %d %H:%M:%S %z %Y"

# Explicit mapping — do NOT rely on Python truthiness of the string "False".
INBOUND_MAP = {"True": True, "False": False}


def _parse_id_list(cell) -> List[str]:
    """
    Convert a raw id cell to a Python list of stripped id strings.

    Handles:
      - NaN / None          → []
      - Single id "119249"  → ["119249"]
      - Comma-list "119249,119251" → ["119249", "119251"]
    """
    if pd.isna(cell) or str(cell).strip() == "":
        return []
    return [tid.strip() for tid in str(cell).split(",") if tid.strip()]


def _parse_twitter_dt(ts: str) -> Optional[datetime]:
    """
    Parse a Twitter-format timestamp string to a timezone-aware datetime.
    Returns None if parsing fails (unexpected format variant).
    """
    try:
        return datetime.strptime(ts, TWITTER_DT_FMT)
    except (ValueError, TypeError):
        return None


def load_raw(path: str | Path = RAW_PATH) -> pd.DataFrame:
    """
    Load twcs.csv and return a typed DataFrame.

    Column transformations applied:
      - `inbound`               : str "True"/"False"  → bool
      - `created_at`            : Twitter timestamp str → datetime (tz-aware)
      - `response_tweet_id`     : str | NaN            → List[str]
      - `in_response_to_tweet_id`: str | NaN           → List[str]
      - `tweet_id`, `author_id` : kept as str (ids should never be ints)

    Rows are NOT sorted here; chronological sorting happens in threads.py
    where it belongs semantically.
    """
    path = Path(path)
    if not path.exists():
        sys.exit(
            f"[ingest] ERROR: raw data not found at {path}.\n"
            "Place twcs.csv in data/raw/ and try again."
        )

    print(f"[ingest] Loading {path} ...")
    df = pd.read_csv(
        path,
        dtype={
            "tweet_id": str,
            "author_id": str,
            "inbound": str,              # parse manually below
            "text": str,
            "response_tweet_id": str,
            "in_response_to_tweet_id": str,
        },
        # pandas handles embedded newlines in quoted cells correctly by default.
        # Do NOT set lineterminator or a custom reader.
    )

    original_rows = len(df)
    print(f"[ingest] Raw row count: {original_rows:,}")

    # ── 1. inbound: str → bool ────────────────────────────────────────────────
    unmapped = df["inbound"].dropna()[~df["inbound"].dropna().isin(INBOUND_MAP)]
    if len(unmapped) > 0:
        print(
            f"[ingest] WARNING: {len(unmapped)} rows have unexpected `inbound` "
            f"values: {unmapped.unique()[:5]}"
        )
    df["inbound"] = df["inbound"].map(INBOUND_MAP)
    # Rows that didn't map become NaN. Cast to pandas nullable boolean
    # so downstream boolean filters (inbound == False) still work correctly.
    df["inbound"] = df["inbound"].astype("boolean")

    # ── 2. created_at: str → datetime ────────────────────────────────────────
    df["created_at"] = df["created_at"].apply(
        lambda x: _parse_twitter_dt(x) if pd.notna(x) else None
    )
    failed_dt = df["created_at"].isna().sum()
    if failed_dt > 0:
        print(f"[ingest] WARNING: {failed_dt} rows failed datetime parsing.")

    # ── 3. id lists ───────────────────────────────────────────────────────────
    df["response_tweet_id"] = df["response_tweet_id"].apply(_parse_id_list)
    df["in_response_to_tweet_id"] = df["in_response_to_tweet_id"].apply(
        _parse_id_list
    )

    # ── Sanity report ─────────────────────────────────────────────────────────
    valid_dates = df["created_at"].dropna()
    print("\n[ingest] -- Sanity Checks ------------------------------------------")
    print(f"  Rows loaded        : {len(df):,}")
    print(f"  Inbound tweets     : {df['inbound'].sum():,}")
    print(f"  Outbound tweets    : {(~df['inbound']).sum():,}")
    print(f"  Date range         : {valid_dates.min()}  ->  {valid_dates.max()}")
    print(f"  Unique authors     : {df['author_id'].nunique():,}")
    print("\n[ingest] Column dtypes:")
    print(df.dtypes.to_string())
    print("--------------------------------------------------------------------\n")

    return df


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_raw()
    print("[ingest] Done.")
