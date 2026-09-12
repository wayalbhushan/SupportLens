import pandas as pd
import re
from pathlib import Path
from langdetect import detect

PROCESSED_DIR = Path("data/processed")

def get_lang(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

def main():
    print("[extract_sample] Loading threads and clean tweets...")
    df_threads = pd.read_parquet(PROCESSED_DIR / "threads.parquet")
    df_tweets = pd.read_parquet(
        PROCESSED_DIR / "tweets_clean.parquet", 
        columns=["tweet_id", "author_id", "text_clean"]
    )

    # 1. Filter to VerizonSupport threads
    v_threads = df_threads[df_threads["brand"] == "VerizonSupport"].copy()
    print(f"[extract_sample] Initial VerizonSupport threads: {len(v_threads):,}")

    tweet_map = df_tweets.set_index("tweet_id")[["author_id", "text_clean"]].to_dict("index")

    # Known corporate / support accounts in Verizon threads
    # Discovered by analyzing high-frequency agent signoffs (^XYZ)
    known_corp = {"115722", "115725", "115990", "125004", "125005", "116655", "VerizonSupport"}

    # 2. Re-rooting brand-initiated threads instead of naive pruning
    usable_threads = []
    re_rooted_count = 0
    dropped_brand_monologues = 0

    for _, row in v_threads.iterrows():
        tids = row["tweet_ids"]
        root_id = row["root_tweet_id"]
        if root_id not in tweet_map:
            continue
        root_author = str(tweet_map[root_id]["author_id"])

        if (not root_author.isnumeric()) or (root_author in known_corp):
            # Brand root: search for the first genuine customer tweet downstream
            new_root_id = None
            new_tids = []
            for i, tid in enumerate(tids):
                if tid in tweet_map:
                    auth = str(tweet_map[tid]["author_id"])
                    if auth.isnumeric() and auth not in known_corp:
                        new_root_id = tid
                        new_tids = tids[i:]
                        break
            if new_root_id is not None:
                usable_threads.append({
                    "thread_id": row["thread_id"],
                    "root_tweet_id": new_root_id,
                    "tweet_ids": new_tids,
                    "re_rooted": True
                })
                re_rooted_count += 1
            else:
                dropped_brand_monologues += 1
        else:
            usable_threads.append({
                "thread_id": row["thread_id"],
                "root_tweet_id": root_id,
                "tweet_ids": tids,
                "re_rooted": False
            })

    df_usable = pd.DataFrame(usable_threads)
    print(f"[extract_sample] Usable threads after re-rooting: {len(df_usable):,}")
    print(f"  - Customer roots preserved: {(~df_usable['re_rooted']).sum():,}")
    print(f"  - Re-rooted support threads recovered: {re_rooted_count:,}")
    print(f"  - Dropped brand monologues (zero customer replies): {dropped_brand_monologues:,}")

    # Attach opening text
    df_usable["text_clean"] = [tweet_map[rid]["text_clean"] for rid in df_usable["root_tweet_id"]]
    df_usable["author_id"] = [tweet_map[rid]["author_id"] for rid in df_usable["root_tweet_id"]]

    # 3. Wireless-only Filter (Scope Decision 13)
    # Exclude messages that are purely about mobile/cellular products and have no home/FiOS product reference
    fios_kw = r"\b(fios|router|wifi|wi-fi|internet|broadband|optical|fiber|ont|tv|channel|cable|dvr|set top|stb|landline|on demand|hbo)\b"
    wireless_kw = r"\b(cell|cellular|mobile|iphone|android|galaxy|pixel|sim|simcard|data plan|unlimited data|lte|4g|5g|tower|reception|signal|bars|mms|sms|text message|voicemail|hotspot|roaming|travel pass|travelpass|byod|trade in|upgrade phone|phone upgrade|carrier)\b"

    has_fios = df_usable["text_clean"].str.contains(fios_kw, case=False, na=False)
    has_wireless = df_usable["text_clean"].str.contains(wireless_kw, case=False, na=False)
    is_wireless_only = has_wireless & (~has_fios)

    wireless_dropped_count = int(is_wireless_only.sum())
    wireless_dropped_pct = (wireless_dropped_count / len(df_usable)) * 100
    print(f"[extract_sample] Wireless-only filter: dropped {wireless_dropped_count:,} messages ({wireless_dropped_pct:.2f}%)")

    df_in_scope = df_usable[~is_wireless_only].copy()
    print(f"[extract_sample] In-scope (FiOS / Home + General) threads: {len(df_in_scope):,}")

    # 4. English Language Filter
    print("[extract_sample] Running language filter (langdetect)...")
    english_rows = []
    non_english_count = 0
    for _, row in df_in_scope.iterrows():
        text = str(row["text_clean"]).strip()
        if text and get_lang(text) == "en":
            english_rows.append(row)
        else:
            non_english_count += 1

    df_english = pd.DataFrame(english_rows)
    non_en_pct = (non_english_count / len(df_in_scope)) * 100
    print(f"[extract_sample] Language filter: dropped {non_english_count:,} non-English ({non_en_pct:.2f}%)")
    print(f"[extract_sample] English in-scope opening messages pool: {len(df_english):,}")

    # Persist pool for fast, reproducible golden set sampling
    pool_path = PROCESSED_DIR / "verizon_in_scope_pool.parquet"
    df_english.to_parquet(pool_path, index=False)
    print(f"[extract_sample] Saved in-scope pool -> {pool_path}")

    # 5. Draw 500-item Sample
    sample_df = df_english.sample(n=min(500, len(df_english)), random_state=42)
    print(f"[extract_sample] Sampled {len(sample_df)} tweets.")

    # 6. Save outputs
    txt_path = PROCESSED_DIR / "taxonomy_reading_sample.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for _, row in sample_df.iterrows():
            text = str(row["text_clean"]).replace("\n", " ").replace("\r", " ").strip()
            f.write(f"[{row['root_tweet_id']}] {text}\n")

    csv_path = PROCESSED_DIR / "taxonomy_reading_sample.csv"
    sample_df[["root_tweet_id", "author_id", "text_clean"]].rename(
        columns={"root_tweet_id": "tweet_id"}
    ).to_csv(csv_path, index=False)

    print(f"[extract_sample] Written {len(sample_df)} rows to {txt_path} and {csv_path}")

if __name__ == "__main__":
    main()
