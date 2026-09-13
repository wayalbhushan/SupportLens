import pandas as pd

df = pd.read_csv('data/golden/golden_labeled.csv')
preds = pd.read_csv('data/processed/agent_eval_predictions.csv')
leg = df[df['severity_override'] == 'legal_regulatory']
print(f"Total legal_regulatory items in golden set: {len(leg)}\n")

for idx, r in leg.iterrows():
    p_row = preds[preds['tweet_id'] == r['tweet_id']].iloc[0]
    print(f"=== {r['sample_id']} (Tweet {r['tweet_id']}, Stratum {r['stratum']}) ===")
    print(f"Text: {repr(r['text_clean'])}")
    print(f"Golden Notes: {r['notes']}")
    print(f"Pred Intent: {p_row['pred_intent']}, Pred Severity: {p_row['pred_severity']}")
    print(f"Path B Correct? {p_row['pred_severity'] == 'legal_regulatory'}")
    print()
