import pandas as pd
import numpy as np
from sklearn.metrics import precision_recall_fscore_support

df = pd.read_csv('data/processed/agent_eval_predictions.csv')

def eval_df(df_in, label=""):
    print(f"=== EVALUATION METRICS ({label}) ===")
    # Stratum A
    df_a = df_in[df_in['stratum'] == 'A']
    p_a, r_a, f1_a, _ = precision_recall_fscore_support(df_a['true_escalate'], df_a['pred_escalate'], pos_label=True, average='binary')
    acc_a = np.mean(df_a['true_intent'] == df_a['pred_intent'])
    
    # Blended
    p_b, r_b, f1_b, _ = precision_recall_fscore_support(df_in['true_escalate'], df_in['pred_escalate'], pos_label=True, average='binary')
    acc_b = np.mean(df_in['true_intent'] == df_in['pred_intent'])

    # Path B Standalone
    y_true_sev = (df_in['true_severity'] != 'none')
    y_pred_sev = (df_in['pred_severity'] != 'none')
    p_sev, r_sev, f1_sev, _ = precision_recall_fscore_support(y_true_sev, y_pred_sev, pos_label=True, average='binary')
    
    tp_sev = np.sum(y_true_sev & y_pred_sev)
    fp_sev = np.sum(~y_true_sev & y_pred_sev)
    fn_sev = np.sum(y_true_sev & ~y_pred_sev)

    print(f"Stratum A Escalation: P={p_a:.3f}, R={r_a:.3f}, F1={f1_a:.3f}")
    print(f"Stratum A Accuracy: {acc_a:.3f}")
    print(f"Blended Escalation: P={p_b:.3f}, R={r_b:.3f}, F1={f1_b:.3f}")
    print(f"Blended Accuracy: {acc_b:.3f}")
    print(f"Path B Standalone (N=200): P={p_sev:.3f}, R={r_sev:.3f}, F1={f1_sev:.3f} | TP={tp_sev}, FP={fp_sev}, FN={fn_sev}")

eval_df(df, "Current: Tweet 2838817 = prolonged_outage")

df_fixed = df.copy()
idx = df_fixed[df_fixed['tweet_id'] == 2838817].index[0]
df_fixed.at[idx, 'pred_severity'] = 'none'
df_fixed.at[idx, 'severity_correct'] = True
df_fixed.at[idx, 'escalation_reason'] = "Escalated: Dispatch calendar and technician routing required"

eval_df(df_fixed, "Fixed to gemini-3.5-flash-lite cache: Tweet 2838817 = none")
