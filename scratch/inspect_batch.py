import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv('data/golden/judge_calibration_sample.csv')

def show_batch(start, end):
    for i in range(start, end):
        r = df.iloc[i]
        print(f"--- [{i+1}/60] Tweet ID: {r['tweet_id']} ---")
        print(f"MSG: {r['message']}")
        ev_txt = str(r['retrieval_evidence_texts']) if pd.notna(r['retrieval_evidence_texts']) else "None"
        print(f"EV: {ev_txt[:200]}...")
        print(f"REPLY: {r['reply_draft']}")
        print()

if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    show_batch(start, end)
