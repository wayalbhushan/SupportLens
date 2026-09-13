from src.llm_client import get_cache_key, _CACHE
from src.agent_path_b import SYSTEM_PROMPT_PATH_B
import pandas as pd

df = pd.read_csv('data/golden/golden_labeled.csv')
row = df[df['tweet_id'] == 2838817].iloc[0]
text = row['text_clean']
user_prompt = f'CUSTOMER MESSAGE TO EVALUATE FOR SEVERITY OVERRIDE:\n"{text.strip()}"\n\nExtract severity in strict JSON format:'
k = get_cache_key('openai/gpt-oss-120b', SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
print('Key 120b:', k)
print('In cache?', k in _CACHE)
if k in _CACHE:
    print('Val:', _CACHE[k])
