"""
src/threads.py
--------------
Phase 0 â€” Step 3: Thread reconstruction.

Algorithm:
  1. Build pure-Python dicts from the DataFrame (avoid iterrows on 2.8M rows).
  2. For each tweet with no in_response_to_tweet_id (i.e. a root tweet),
     start a new thread.
  3. Follow the reply chain using in_response_to_tweet_id links (BFS).
  4. Exclude broadcast roots before building threads:
     a broadcast root is a brand-authored tweet whose response_tweet_id
     list has MORE than 15 entries. We do not delete those rows from df â€”
     we simply never create a thread rooted at them.
  5. Sort each thread's tweets chronologically by created_at.

Performance note:
  We convert the DataFrame to dicts once upfront to avoid iterrows() on
  the full 2.8M-row dataset. The BFS itself is O(n) in the number of edges.

Output: one row per thread in a DataFrame with columns:
  thread_id, root_tweet_id, brand, tweet_ids (list), tweet_count

The output is written to data/processed/threads.parquet.
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd

from src.ingest import load_raw

PROCESSED_DIR = Path("data/processed")
BROADCAST_THRESHOLD = 15  # exclusive: > 15 responses â†’ broadcast


def _is_brand_account(author_id: str) -> bool:
    """
    Heuristic: brand accounts have non-numeric author_ids in TWCS
    (e.g. "AppleSupport", "SpotifyCares"). Customer accounts are numeric ids.
    """
    return not str(author_id).isdigit()


def is_broadcast_node(row: pd.Series) -> bool:
    """
    Return True if this tweet should be excluded as a broadcast node.

    Criteria:
      - response_tweet_id list has > BROADCAST_THRESHOLD entries
    """
    return len(row["response_tweet_id"]) > BROADCAST_THRESHOLD


def build_threads(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct conversation threads from the TWCS DataFrame.

    Returns a DataFrame with one row per thread:
        thread_id        : int (sequential)
        root_tweet_id    : str
        brand            : str | None (first brand author found in thread)
        tweet_ids        : List[str] (chronologically ordered)
        tweet_count      : int
    """
    print("[threads] Building lookup structures ...")

    # â”€â”€ Convert to native Python structures (avoid iterrows on 2.8M rows) â”€â”€â”€â”€
    tweet_ids_col     = df["tweet_id"].astype(str).tolist()
    author_ids_col    = df["author_id"].astype(str).tolist()
    created_at_col    = df["created_at"].tolist()
    resp_ids_col      = df["response_tweet_id"].tolist()      # List[List[str]]
    in_resp_ids_col   = df["in_response_to_tweet_id"].tolist() # List[List[str]]

    # Maps for fast lookup
    id_to_author: Dict[str, str] = {}
    id_to_created: Dict[str, pd.Timestamp] = {}
    broadcast_node_ids: Set[str] = set()
    children_of: Dict[str, List[str]] = defaultdict(list)
    all_tweet_ids: Set[str] = set()

    for tid, author, created, resp_list, in_resp_list in zip(
        tweet_ids_col, author_ids_col, created_at_col, resp_ids_col, in_resp_ids_col
    ):
        id_to_author[tid] = author
        id_to_created[tid] = created
        all_tweet_ids.add(tid)

        # Broadcast check: apply per-node, not just at the root/brand level.
        # Any tweet with high fan-out (e.g. a canned response quoted by many,
        # or a CEO broadcast) should cut the thread.
        if len(resp_list) > BROADCAST_THRESHOLD:
            broadcast_node_ids.add(tid)

    # Build parentâ†’children adjacency (for BFS from roots)
    replied_to_ids: Set[str] = set()
    for tid, in_resp_list in zip(tweet_ids_col, in_resp_ids_col):
        for parent_id in in_resp_list:
            children_of[parent_id].append(tid)
            replied_to_ids.add(parent_id)

    print(f"[threads] Broadcast nodes excluded: {len(broadcast_node_ids):,}")

    # Root tweets: a tweet is a root if ALL its in_response_to_tweet_id entries
    # point to tweet IDs that do NOT exist in our dataset (i.e. it has no known
    # parent). This includes:
    #   - Original tweets with no in_response_to at all (empty list)
    #   - Tweets whose parent was deleted / is outside the dataset
    # NOTE: this is the OPPOSITE of replied_to_ids, which is the set of tweets
    # that ARE parents. Do not use (all_tweet_ids - replied_to_ids) — that gives
    # LEAF nodes (tweets nobody replied to), not root nodes.
    root_candidates: Set[str] = set()
    for tid, in_resp_list in zip(tweet_ids_col, in_resp_ids_col):
        if tid in broadcast_node_ids:
            continue
        # Root = no parent OR no parent exists in our dataset
        has_known_parent = any(p in all_tweet_ids for p in in_resp_list)
        if not has_known_parent:
            root_candidates.add(tid)

    print(f"[threads] Root candidates: {len(root_candidates):,}")
    print("[threads] Running BFS to reconstruct threads ...")

    # â”€â”€ BFS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    threads = []
    thread_id = 0
    visited_global: Set[str] = set()

    for root_id in sorted(root_candidates):  # sorted for determinism
        if root_id in visited_global:
            continue

        thread_tweet_ids: List[str] = []
        queue: deque[str] = deque([root_id])

        while queue:
            current = queue.popleft()
            if current in visited_global or current in broadcast_node_ids:
                continue
            visited_global.add(current)
            thread_tweet_ids.append(current)
            queue.extend(children_of.get(current, []))

        if not thread_tweet_ids:
            continue

        # Sort chronologically within the thread
        def _sort_key(tid: str):
            dt = id_to_created.get(tid)
            if dt is None or (isinstance(dt, float) and pd.isna(dt)):
                return pd.Timestamp.min.replace(tzinfo=None)
            # Handle both tz-aware and tz-naive (min is tz-naive)
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt

        thread_tweet_ids.sort(key=_sort_key)

        # Identify brand (first non-numeric author in the thread)
        brand: Optional[str] = None
        for tid in thread_tweet_ids:
            author = id_to_author.get(tid, "")
            if _is_brand_account(author):
                brand = author
                break

        threads.append(
            {
                "thread_id": thread_id,
                "root_tweet_id": root_id,
                "brand": brand,
                "tweet_ids": thread_tweet_ids,
                "tweet_count": len(thread_tweet_ids),
            }
        )
        thread_id += 1

    threads_df = pd.DataFrame(threads)

    # â”€â”€ Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[threads] â”€â”€ Thread Statistics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    print(f"  Total threads reconstructed : {len(threads_df):,}")
    print(f"  Broadcast nodes excluded    : {len(broadcast_node_ids):,}")
    if len(threads_df) > 0:
        avg_len = threads_df["tweet_count"].mean()
        max_len = threads_df["tweet_count"].max()
        print(f"  Average thread length       : {avg_len:.2f}")
        print(f"  Max thread length           : {max_len}")
        print(f"  Single-tweet threads        : {(threads_df['tweet_count'] == 1).sum():,}")
    print("â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€\n")

    return threads_df


# â”€â”€ CLI entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = load_raw()
    threads_df = build_threads(df)
    out_path = PROCESSED_DIR / "threads.parquet"
    threads_df.to_parquet(out_path, index=False)
    print(f"[threads] Saved â†’ {out_path}")
    print("[threads] Done.")

