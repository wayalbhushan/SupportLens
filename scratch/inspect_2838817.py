import subprocess
import io
import json
import pandas as pd
from src.agent_path_b import SYSTEM_PROMPT_PATH_B
from src.llm_client import get_cache_key

res = subprocess.run(['git', 'show', '9719cfd:data/processed/agent_eval_predictions.csv'], capture_output=True, check=True)
df_pre = pd.read_csv(io.BytesIO(res.stdout), encoding='utf-8')
df_post = pd.read_csv('data/processed/agent_eval_predictions.csv', encoding='utf-8')

row_pre = df_pre[df_pre['tweet_id'] == 2838817].iloc[0]
row_post = df_post[df_post['tweet_id'] == 2838817].iloc[0]

print("=== TWEET 2838817 ===")
print("Text:", repr(row_pre['text_clean']))
print("Pre run:")
print("  pred_intent:", row_pre['pred_intent'])
print("  pred_severity:", row_pre['pred_severity'])
print("  pred_escalate:", row_pre['pred_escalate'])
print("  escalation_reason:", row_pre['escalation_reason'])

print("\nPost run:")
print("  pred_intent:", row_post['pred_intent'])
print("  pred_severity:", row_post['pred_severity'])
print("  pred_escalate:", row_post['pred_escalate'])
print("  escalation_reason:", row_post['escalation_reason'])

# Check what was in git cache at 9719cfd vs now
res_c = subprocess.run(['git', 'show', '9719cfd:data/cache/llm_cache.json'], capture_output=True, check=True)
cache_pre = json.loads(res_c.stdout.decode('utf-8'))
with open('data/cache/llm_cache.json', encoding='utf-8') as f:
    cache_post = json.load(f)

text = row_pre['text_clean']
user_prompt = f'CUSTOMER MESSAGE TO EVALUATE FOR SEVERITY OVERRIDE:\n"{text.strip()}"\n\nExtract severity in strict JSON format:'

key_37 = get_cache_key('gemini-3.7-flash', SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
key_38 = get_cache_key('gemini-3.8-flash', SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
key_qwen = get_cache_key('qwen/qwen3.8-27b', SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
key_120 = get_cache_key('openai/gpt-oss-120b', SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)

target = '7395f9e8ac7cd5dde3c3f1c419e025f8851bb4155b17a47089e8dc4190da0246'
print("\nChecking target key:", target)
models = ['gemini-3.5-flash-lite', 'gemini-3.6-flash', 'gemini-3.7-flash', 'gemini-3.8-flash', 'qwen/qwen3.6-27b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-120b']
for m in models:
    k = get_cache_key(m, SYSTEM_PROMPT_PATH_B, user_prompt, 0.0)
    if k == target:
        print(f'MATCH MODEL: {m}')
