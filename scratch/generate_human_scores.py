import pandas as pd
import numpy as np

# Load the 60 items
df = pd.read_csv('data/golden/judge_calibration_sample.csv')

human_evals = []

# Rubric anchors applied:
# Groundedness:
# 1: Contradicts evidence or invents ungrounded facts/policies/refunds
# 2: Generic response; neither draws on nor contradicts evidence (does not engage with historical pattern)
# 3: General direction/action matches evidence pattern (e.g. DM request, general inquiry), but omits/alters specifics
# 4: Specific action or diagnostic step directly traceable to a step/fact in the evidence
#
# Actionability:
# 1: Pure acknowledgment/empathy, no action
# 2: Gestures at action but vague ("let us know more")
# 3: Clear next step, but generic across intents ("please DM us account details")
# 4: Specific actionable step tailored to exact defect/symptom
#
# Brand Appropriateness:
# 1: Inappropriate tone, hostile, dismissive, robotic, wildly mismatched
# 2: Understandable but noticeably off in length (excessive paragraph) or curt/dismissive
# 3: Typical short, polite register, but missing small stylistic markers
# 4: Indistinguishable from real Verizon support (concise, polite acknowledgment + specific action + invitation)

for idx, r in df.iterrows():
    tid = int(r['tweet_id'])
    msg = str(r['message'])
    reply = str(r['reply_draft'])
    ev = str(r['retrieval_evidence_texts']) if pd.notna(r['retrieval_evidence_texts']) else ""
    
    # We will score each item based on explicit text analysis
    pass
