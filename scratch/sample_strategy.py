import pandas as pd
import numpy as np

# Load data
from src.retrieval import VerizonSupportRetriever
df_agent = pd.read_csv('data/processed/agent_eval_predictions.csv')
valid = df_agent[df_agent['pred_intent'] != 'other'].copy()

retriever = VerizonSupportRetriever()
sims = []
for idx, r in valid.iterrows():
    ev = retriever.retrieve(r['text_clean'], k=1)
    sims.append(ev[0]['similarity'] if ev else 0.0)

valid['retrieval_similarity'] = sims
valid['sim_band'] = pd.cut(valid['retrieval_similarity'], bins=[-1, 0.49999, 0.59999, 1.0], labels=['low', 'medium', 'high'])

# Target quotas per intent class (sum = 60)
# praise_thanks: 6 (all available)
# appointment_installation: 8 (out of 12)
# account_access: 8 (out of 17)
# billing_dispute: 10 (out of 28)
# complaint_no_request: 10 (out of 29)
# tv_content_access: 9 (out of 34)
# connectivity_issue: 9 (out of 50)
intent_quotas = {
    'praise_thanks': 6,
    'appointment_installation': 8,
    'account_access': 8,
    'billing_dispute': 10,
    'complaint_no_request': 10,
    'tv_content_access': 9,
    'connectivity_issue': 9,
}

rng = np.random.RandomState(42)

# Within each intent class, prioritize high and medium sim_band, and ensure a mix of intent_correct
selected_indices = []

for intent, quota in intent_quotas.items():
    sub = valid[valid['pred_intent'] == intent].copy()
    if len(sub) <= quota:
        selected_indices.extend(sub.index.tolist())
        continue
    
    # Stratify by (sim_band, intent_correct)
    # Give priority to high and medium similarity, and intent_correct == False
    sub['priority_score'] = 0
    # Add priority for rare similarity bands
    sub.loc[sub['sim_band'] == 'high', 'priority_score'] += 3
    sub.loc[sub['sim_band'] == 'medium', 'priority_score'] += 2
    # Add priority for incorrect predictions to test low-quality reply detection
    sub.loc[~sub['intent_correct'], 'priority_score'] += 1
    
    # Sort by priority_score descending, with random tie-breaker
    sub['rand'] = rng.rand(len(sub))
    sub = sub.sort_values(by=['priority_score', 'rand'], ascending=[False, True])
    
    chosen = sub.head(quota)
    selected_indices.extend(chosen.index.tolist())

sample_df = valid.loc[selected_indices].copy()
assert len(sample_df) == 60, f"Expected 60 items, got {len(sample_df)}"

print("=== FINAL 60-ITEM CALIBRATION SAMPLE COMPOSITION ===")
print("\n1. By Intent Class:")
print(sample_df['pred_intent'].value_counts())

print("\n2. By Similarity Band:")
print(sample_df['sim_band'].value_counts())

print("\n3. By Prediction Correctness:")
print(sample_df['intent_correct'].value_counts())

print("\n4. By Escalation Flag:")
print(sample_df['pred_escalate'].value_counts())

print("\nCross-tab Intent x Sim Band:")
print(pd.crosstab(sample_df['pred_intent'], sample_df['sim_band']))

print("\nCross-tab Intent x Correctness:")
print(pd.crosstab(sample_df['pred_intent'], sample_df['intent_correct']))

print("\nCross-tab Intent x Escalation:")
print(pd.crosstab(sample_df['pred_intent'], sample_df['pred_escalate']))
