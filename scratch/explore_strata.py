import pandas as pd
import numpy as np
from src.retrieval import VerizonSupportRetriever
from src.baseline_simple import weak_label_message

df_agent = pd.read_csv('data/processed/agent_eval_predictions.csv')
valid = df_agent[df_agent['pred_intent'] != 'other'].copy()

retriever = VerizonSupportRetriever()
sims = []
for idx, r in valid.iterrows():
    ev = retriever.retrieve(r['text_clean'], k=1)
    sims.append(ev[0]['similarity'] if ev else 0.0)

valid['retrieval_similarity'] = sims
valid['sim_band'] = pd.cut(valid['retrieval_similarity'], bins=[-1, 0.49999, 0.59999, 1.0], labels=['low (<0.50)', 'medium (0.50-0.59)', 'high (>=0.60)'])

print("Total candidate pool:", len(valid))
print("\nBy Intent:\n", valid['pred_intent'].value_counts())
print("\nBy Similarity Band:\n", valid['sim_band'].value_counts())
print("\nBy Correctness:\n", valid['intent_correct'].value_counts())
print("\nBy Escalation:\n", valid['pred_escalate'].value_counts())

# Cross-tabulation of available pool
print("\nCross-tab Intent x Sim Band:")
print(pd.crosstab(valid['pred_intent'], valid['sim_band']))

print("\nCross-tab Intent x Intent Correct:")
print(pd.crosstab(valid['pred_intent'], valid['intent_correct']))

print("\nCross-tab Intent x Pred Escalate:")
print(pd.crosstab(valid['pred_intent'], valid['pred_escalate']))
