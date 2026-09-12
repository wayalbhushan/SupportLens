"""
src/retrieval.py
----------------
Phase 4: Retrieval Index for Grounding Evidence in SupportLens Agent.

Architecture:
  - Retrieval corpus: 7,426 paired (customer message, brand reply) records extracted
    from the clean in-scope VerizonSupport thread pool.
  - Zero-Leakage Constraint (Decision 1): All 200 golden_labeled.csv tweet_ids AND
    their entire thread contexts are strictly excluded from the corpus.
  - Vector search: Off-the-shelf NearestNeighbors (Decision 6) with cosine metric.
  - Returns top-k (default k=5) paired historical customer messages and VerizonSupport
    replies to ground Path A reply drafting.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

CORPUS_PATH = Path("data/processed/retrieval_corpus.csv")
POOL_CSV_PATH = Path("data/processed/verizon_in_scope_pool.csv")
TWEETS_PARQUET_PATH = Path("data/processed/tweets_clean.parquet")
GOLDEN_PATH = Path("data/golden/golden_labeled.csv")

def build_or_load_corpus() -> pd.DataFrame:
    """
    Ensure the retrieval corpus exists, is strictly leak-free, and return it.
    If not already generated, extracts it from in-scope threads excluding golden threads.
    """
    if CORPUS_PATH.exists():
        df_corpus = pd.read_csv(CORPUS_PATH)
    else:
        print("[retrieval] Building retrieval corpus from in-scope threads...")
        pool = pd.read_csv(POOL_CSV_PATH)
        tweets = pd.read_parquet(TWEETS_PARQUET_PATH)
        golden = pd.read_csv(GOLDEN_PATH)
        golden_tids = set(golden["tweet_id"].astype(str))

        # Identify threads containing any golden tweet_id
        golden_thread_ids = set()
        for _, row in pool.iterrows():
            th_id = row["thread_id"]
            tids = re.findall(r"\d+", str(row["tweet_ids"]))
            if set(tids).intersection(golden_tids):
                golden_thread_ids.add(th_id)

        clean_pool = pool[~pool["thread_id"].isin(golden_thread_ids)].copy()

        # Collect candidate tweet IDs
        clean_tids = set()
        for _, row in clean_pool.iterrows():
            clean_tids.update(re.findall(r"\d+", str(row["tweet_ids"])))

        sub_tweets = tweets[tweets["tweet_id"].isin(clean_tids)].copy()
        sub_tweets_by_id = sub_tweets.set_index("tweet_id")

        records = []
        for _, row in clean_pool.iterrows():
            root_tid = str(row["root_tweet_id"])
            th_id = row["thread_id"]
            cust_text = str(row["text_clean"]).strip()
            tids_in_thread = re.findall(r"\d+", str(row["tweet_ids"]))

            brand_reply = None
            brand_tid = None

            if root_tid in sub_tweets_by_id.index:
                root_row = sub_tweets_by_id.loc[root_tid]
                resp_ids = root_row["response_tweet_id"] if isinstance(root_row["response_tweet_id"], list) else []
                for rid in resp_ids:
                    if str(rid) in sub_tweets_by_id.index:
                        resp_row = sub_tweets_by_id.loc[str(rid)]
                        if str(resp_row["author_id"]).lower() == "verizonsupport" and str(resp_row["text_clean"]).strip():
                            brand_reply = str(resp_row["text_clean"]).strip()
                            brand_tid = str(rid)
                            break

            if not brand_reply:
                for tid in tids_in_thread:
                    if tid in sub_tweets_by_id.index and tid != root_tid:
                        r_row = sub_tweets_by_id.loc[tid]
                        if str(r_row["author_id"]).lower() == "verizonsupport" and str(r_row["text_clean"]).strip():
                            brand_reply = str(r_row["text_clean"]).strip()
                            brand_tid = tid
                            break

            if brand_reply and cust_text:
                records.append({
                    "thread_id": th_id,
                    "customer_tweet_id": root_tid,
                    "customer_text": cust_text,
                    "brand_tweet_id": brand_tid,
                    "brand_reply": brand_reply,
                })

        df_corpus = pd.DataFrame(records)
        CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_corpus.to_csv(CORPUS_PATH, index=False, encoding="utf-8")

    # Strict Leakage Assertion (Decision 1)
    golden = pd.read_csv(GOLDEN_PATH)
    golden_tids = set(golden["tweet_id"].astype(str))
    corpus_all_tids = set(df_corpus["customer_tweet_id"].astype(str)).union(
        set(df_corpus["brand_tweet_id"].astype(str))
    )
    overlap = corpus_all_tids.intersection(golden_tids)
    assert len(overlap) == 0, f"DATA LEAKAGE: {len(overlap)} golden IDs found in retrieval index!"

    return df_corpus

class VerizonSupportRetriever:
    """Vector search retrieval index for grounding support agent responses."""

    def __init__(self, max_features: int = 5000, n_neighbors: int = 5):
        self.max_features = max_features
        self.n_neighbors = n_neighbors
        self.corpus_df = build_or_load_corpus()
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.neighbors import NearestNeighbors

        # Build Vectorizer & Index
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.X_index = self.vectorizer.fit_transform(
            self.corpus_df["customer_text"].fillna("").astype(str)
        )
        self.index = NearestNeighbors(n_neighbors=self.n_neighbors, metric="cosine", algorithm="brute")
        self.index.fit(self.X_index)

    @property
    def index_size(self) -> int:
        return self.X_index.shape[0]

    @property
    def embedding_dim(self) -> int:
        return self.X_index.shape[1]

    def retrieve(self, query_text: str, k: int = 5) -> List[Dict]:
        """
        Retrieve top-k most similar historical customer interactions and their paired brand replies.
        Returns list of dicts with:
          - customer_tweet_id
          - customer_text
          - brand_tweet_id
          - brand_reply
          - similarity_score (1.0 - cosine_distance)
        """
        q_clean = str(query_text).strip()
        if not q_clean:
            return []

        q_vec = self.vectorizer.transform([q_clean])
        distances, indices = self.index.kneighbors(q_vec, n_neighbors=k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            row = self.corpus_df.iloc[idx]
            similarity = float(max(0.0, 1.0 - dist))
            results.append({
                "customer_tweet_id": str(row["customer_tweet_id"]),
                "customer_text": str(row["customer_text"]),
                "brand_tweet_id": str(row["brand_tweet_id"]),
                "brand_reply": str(row["brand_reply"]),
                "similarity": similarity,
            })
        return results

def sanity_check_retrieval():
    print("=" * 70)
    print("PHASE 4: RETRIEVAL INDEX INITIALIZATION & SANITY CHECK")
    print("=" * 70)

    retriever = VerizonSupportRetriever(max_features=5000, n_neighbors=5)
    print(f"Retrieval Corpus Size : {retriever.index_size:,} paired historical interactions")
    print(f"Embedding Dimension   : {retriever.embedding_dim:,} features (TF-IDF 1-2 ngrams)")
    print("Index Algorithm       : Scikit-learn NearestNeighbors (Metric: Cosine, Decision 6)")
    print("Leakage Status        : VERIFIED (0 / 200 golden tweet_ids in corpus)\n")

    test_queries = [
        ("connectivity", "My wifi is completely down and router blinking red globe"),
        ("billing", "Why did my bill go up $40 this month without any notice?"),
        ("tv_content", "HBO and Univision channels are showing black screen on my cable box"),
    ]

    for category, query in test_queries:
        print("-" * 65)
        print(f"TEST QUERY [{category.upper()}]: '{query}'")
        evidence = retriever.retrieve(query, k=3)
        for rank, ev in enumerate(evidence, 1):
            print(f"  [Top {rank}] (Cosine Similarity: {ev['similarity']:.3f})")
            print(f"    Historical Customer [{ev['customer_tweet_id']}]: {ev['customer_text'][:90]}...")
            print(f"    VerizonSupport Reply [{ev['brand_tweet_id']}]: {ev['brand_reply'][:110]}...")
        print()

if __name__ == "__main__":
    sanity_check_retrieval()
