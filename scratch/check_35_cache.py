import pandas as pd
import json
from src.agent_path_b import SYSTEM_PROMPT_PATH_B
from src.llm_client import get_cache_key

df = pd.read_csv('data/golden/golden_labeled.csv')
with open('data/cache/llm_cache.json', encoding='utf-8') as f:
    cache = json.load(f)

cached_count = 0
missing = []
for idx, row in df.iterrows():
    text = row['text_clean']
    user_prompt = f'CUSTOMER MESSAGE TO EVALUATE FOR SEVERITY OVERRIDE:\n"{text.strip()}"\n\nExtract severity in strict JSON format:'
    k = get_cache_key('gemini-3.5-flash-lite', SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
    if k in cache:
        cached_count += 1
    else:
        missing.append(row['tweet_id'])

print(f"Cached gemini-3.5-flash-lite entries for Path B: {cached_count} / {len(df)}")
if missing:
    print("Missing tweet_ids:", missing)
