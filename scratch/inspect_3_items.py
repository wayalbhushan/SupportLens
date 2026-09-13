import pandas as pd

df = pd.read_csv('data/golden/golden_labeled.csv')
for s_id in ['GS-023', 'GS-185', 'GS-198']:
    sub = df[df['sample_id'] == s_id]
    if len(sub) == 0:
        print(f"Not found: {s_id}")
        continue
    row = sub.iloc[0]
    print(f"=== {s_id} ===")
    print("Tweet ID:", row['tweet_id'])
    print("Stratum:", row['stratum'])
    print("Text:", repr(row['text_clean']))
    print("Intent:", row['intent'])
    print("Severity:", row['severity_override'])
    print("Escalate:", row['escalate'])
    print("Notes:", repr(row['notes']))
    print()
