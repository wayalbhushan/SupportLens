import pandas as pd
from src.agent_orchestrator import SupportLensOrchestrator
from src.llm_client import get_cache_key, _CACHE
from src.agent_path_b import SYSTEM_PROMPT_PATH_B

df = pd.read_csv('data/golden/golden_labeled.csv')
row = df[df['tweet_id'] == 2838817].iloc[0]
text = row['text_clean']

orch = SupportLensOrchestrator()
user_prompt = f'CUSTOMER MESSAGE TO EVALUATE FOR SEVERITY OVERRIDE:\n"{text.strip()}"\n\nExtract severity in strict JSON format:'

for m in ['gemini-3.7-flash', 'gemini-3.5-flash-lite', 'gemini-3.8-flash', 'qwen/qwen3.8-27b']:
    k = get_cache_key(m, SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
    print(f'Model {m} key: {k}, in cache? {k in _CACHE}')
    if k in _CACHE:
        print('  Val:', _CACHE[k])

# Now run extract_severity and see what it returns!
res = orch.path_b.extract_severity(text)
print("\nActual extract_severity output:")
print(res)
