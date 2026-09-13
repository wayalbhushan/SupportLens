import pandas as pd
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv('data/golden/judge_calibration_sample.csv')
print(f"Loaded {len(df)} items to score.")

scores = []

for idx, r in df.iterrows():
    tid = r['tweet_id']
    msg = str(r['message'])
    reply = str(r['reply_draft'])
    ev = str(r['retrieval_evidence_texts'])
    
    # Let's inspect each item systematically
    # We will compute human_groundedness, human_actionability, human_brand and their reasons
