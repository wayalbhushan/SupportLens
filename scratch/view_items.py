import pandas as pd

df = pd.read_csv('data/golden/judge_calibration_sample.csv')
for idx in range(0, 10):
    r = df.iloc[idx]
    print(f"=== Item {idx+1}/60 | Tweet ID: {r['tweet_id']} ===")
    print("CUSTOMER MESSAGE:", repr(r['message']))
    print("RETRIEVED EVIDENCE:", repr(r['retrieval_evidence_texts']))
    print("AGENT REPLY DRAFT:", repr(r['reply_draft']))
    print("SAMPLE BRAND REPLIES:", repr(r['sample_brand_replies'][:120]))
    print()
