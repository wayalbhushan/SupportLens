import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import time
import pandas as pd
from src.judge import LLMJudge, resolve_evidence_texts

print("1. Loading predictions...", flush=True)
df = pd.read_csv('data/processed/agent_eval_predictions.csv')
r = df[df['tweet_id'] == 903382].iloc[0]

print("2. Resolving evidence...", flush=True)
t0 = time.time()
ev = resolve_evidence_texts(r['evidence_used'])
print(f"Evidence resolved in {time.time()-t0:.2f}s: {len(ev)} items", flush=True)

print("3. Initializing judge...", flush=True)
j = LLMJudge()

print("4. Calling score_groundedness...", flush=True)
t0 = time.time()
res = j.score_groundedness(r['text_clean'], ev, r['reply_draft'])
print(f"score_groundedness finished in {time.time()-t0:.2f}s: {res}", flush=True)
