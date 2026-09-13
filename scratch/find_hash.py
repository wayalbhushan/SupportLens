import hashlib
import json
import itertools

target = "7395f9e8ac7cd5dde3c3f1c419e025f8851bb4155b17a47089e8dc4190da0246"

# Let's check all models and temperatures and variations
with open('data/cache/llm_cache.json', encoding='utf-8') as f:
    cache = json.load(f)

val = cache[target]
print("Target value:", val)

# We know the prompt must contain something related to tweet 2838817 or another tweet!
# Wait, could target key belong to a DIFFERENT tweet and not 2838817?
target = "7395f9e8ac7cd5dde3c3f1c419e025f8851bb4155b17a47089e8dc4190da0246"
import pandas as pd
from src.agent_path_b import SYSTEM_PROMPT_PATH_B

df_post = pd.read_csv('data/processed/agent_eval_predictions.csv')
row = df_post[df_post['tweet_id'] == 2838817].iloc[0]
t_text = row['text_clean']

found = False
for sp in [SYSTEM_PROMPT_PATH_B, SYSTEM_PROMPT_PATH_B.replace('\r\n', '\n'), SYSTEM_PROMPT_PATH_B.replace('\n', '\r\n')]:
    up_raw = f'CUSTOMER MESSAGE TO EVALUATE FOR SEVERITY OVERRIDE:\n"{t_text.strip()}"\n\nExtract severity in strict JSON format:'
    for up in [up_raw, up_raw.replace('\r\n', '\n'), up_raw.replace('\n', '\r\n')]:
        for m in ['gemini-3.5-flash-lite', 'gemini-3.6-flash', 'gemini-3.7-flash', 'gemini-3.8-flash', 'qwen/qwen3.6-27b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-120b']:
            content = f'{m}|0.0|{sp}|{up}'
            h = hashlib.sha256(content.encode('utf-8')).hexdigest()
            if h == target:
                print(f'MATCH FOUND! Model: {m}')
                found = True
                break
print("Found:", found)

