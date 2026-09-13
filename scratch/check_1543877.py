import pandas as pd
from src.agent_orchestrator import SupportLensOrchestrator
from src.agent_path_b import SYSTEM_PROMPT_PATH_B
from src.llm_client import get_cache_key, _CACHE

df = pd.read_csv('data/golden/golden_labeled.csv')
for tid in [2588515, 2533727]:
    row = df[df['tweet_id'] == tid].iloc[0]
    text = row['text_clean']
    print(f"\nTweet {tid} ({row['sample_id']}): {repr(text)}")
    print("Golden override:", row['severity_override'], "| Notes:", row['notes'])
    user_prompt = f'CUSTOMER MESSAGE TO EVALUATE FOR SEVERITY OVERRIDE:\n"{text.strip()}"\n\nExtract severity in strict JSON format:'
    for m in ['gemini-3.5-flash-lite', 'gemini-3.7-flash']:
        k = get_cache_key(m, SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
        print(f"Model {m}: {k in _CACHE}")
        if k in _CACHE:
            print("  VAL:", _CACHE[k])
