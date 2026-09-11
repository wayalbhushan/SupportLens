import pandas as pd
import re

from src.config import CANDIDATE_BRANDS

def check_thread_resolution(df_threads, df_tweets):
    brands = CANDIDATE_BRANDS
    
    # Regex heuristics
    # Customer confirms fix
    resolve_pattern = re.compile(r"(?i)\b(fixed|working now|all good|resolved|worked|appreciate it|thank you so much|that did it|all set|perfect now|thanks for the help)\b")
    # Brand asks to DM
    dm_pattern = re.compile(r"(?i)\b(dm us|send us a dm|direct message|private message|message us|dm me)\b")
    
    results = []
    
    for brand in brands:
        brand_threads = df_threads[df_threads['brand'] == brand]
        if len(brand_threads) >= 150:
            sample = brand_threads.sample(150, random_state=42)
        else:
            sample = brand_threads
            
        resolutions = 0
        dm_redirects = 0
        other = 0
        
        for _, thread in sample.iterrows():
            t_ids = thread['tweet_ids']
            # Get tweets in order
            thread_tweets = df_tweets[df_tweets['tweet_id'].isin(t_ids)].copy()
            # Sort chronologically by matching the order in t_ids
            # create categorical type for sorting
            thread_tweets['tweet_id'] = pd.Categorical(thread_tweets['tweet_id'], categories=t_ids, ordered=True)
            thread_tweets = thread_tweets.sort_values('tweet_id')
            
            has_resolution = False
            has_dm = False
            
            for _, tw in thread_tweets.iterrows():
                text = str(tw['text_clean']) if pd.notna(tw['text_clean']) else ""
                if tw['inbound']:
                    # Customer tweet
                    if resolve_pattern.search(text):
                        has_resolution = True
                else:
                    # Brand tweet
                    if dm_pattern.search(text):
                        has_dm = True
                        
            # If the customer confirmed resolution, we count it as resolved
            # Even if there was a DM redirect earlier, a public confirmation of fix is what we want.
            if has_resolution:
                resolutions += 1
            elif has_dm:
                dm_redirects += 1
            else:
                other += 1
                
        results.append({
            'brand': brand,
            'sampled_threads': len(sample),
            'resolutions': resolutions,
            'dm_redirects': dm_redirects,
            'other': other,
            'resolution_pct': f"{(resolutions / len(sample)) * 100:.1f}%"
        })
        
    res_df = pd.DataFrame(results)
    print("\n[thread_check] -- Thread Resolution Analysis -------------------")
    print(res_df.to_string(index=False))
    print("----------------------------------------------------------------\n")

if __name__ == "__main__":
    print("[thread_check] Loading datasets...")
    df_threads = pd.read_parquet('data/processed/threads.parquet')
    df_tweets = pd.read_parquet('data/processed/tweets_clean.parquet')
    
    # Pre-filter tweets to only those in the sampled threads to speed up processing
    brands = CANDIDATE_BRANDS
    sampled_tids = []
    for brand in brands:
        bt = df_threads[df_threads['brand'] == brand]
        if len(bt) >= 150:
            samp = bt.sample(150, random_state=42)
        else:
            samp = bt
        for ids in samp['tweet_ids']:
            sampled_tids.extend(ids)
            
    df_tweets_sub = df_tweets[df_tweets['tweet_id'].isin(set(sampled_tids))]
    
    check_thread_resolution(df_threads, df_tweets_sub)
