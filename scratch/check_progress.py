import pandas as pd
import json
from src.judge import LLMJudge, resolve_evidence_texts, load_rubric_dimension, get_judge_cache_key
from src.prepare_calibration_sample import load_brand_reference_replies

df = pd.read_csv('data/processed/agent_eval_predictions.csv')
valid = df[df['pred_intent'] != 'other'].copy()
with open('data/cache/judge_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

rub_g = load_rubric_dimension('Groundedness')
rub_a = load_rubric_dimension('Actionability')
rub_b = load_rubric_dimension('Brand Appropriateness')
brand_map = load_brand_reference_replies(42)

g_done = 0
a_done = 0
b_done = 0
all_done = 0

for _, r in valid.iterrows():
    ev_texts = resolve_evidence_texts(r['evidence_used'])
    ev_block = "\n".join(ev_texts) if ev_texts else "No retrieved evidence provided."
    sys_g = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the GROUNDEDNESS of a generated customer support reply against the retrieved evidence provided.

{rub_g}

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification directly referencing the rubric criteria and evidence>"
}}"""
    usr_g = f"""CUSTOMER INBOUND MESSAGE:
"{r['text_clean']}"

RETRIEVED HISTORICAL EVIDENCE:
{ev_block}

GENERATED REPLY DRAFT TO EVALUATE:
"{r['reply_draft']}"

Evaluate Groundedness (score 1-4) in JSON:"""
    kg = get_judge_cache_key('qwen/qwen3.8-27b', sys_g, usr_g)

    sys_a = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the ACTIONABILITY of a generated customer support reply for the customer's stated issue.

{rub_a}

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification directly referencing the rubric criteria>"
}}"""
    usr_a = f"""CUSTOMER INBOUND MESSAGE:
"{r['text_clean']}"

GENERATED REPLY DRAFT TO EVALUATE:
"{r['reply_draft']}"

Evaluate Actionability (score 1-4) in JSON:"""
    ka = get_judge_cache_key('qwen/qwen3.8-27b', sys_a, usr_a)

    sample_lines = "\n".join(f"- {s}" for s in [x.strip() for x in brand_map.get(str(r['pred_intent']), '').split(' | ') if x.strip()][:3])
    sample_block = f"\nREFERENCE BRAND REPLIES:\n{sample_lines}\n" if sample_lines else ""
    sys_b = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the BRAND APPROPRIATENESS of a customer support reply (tone, empathy, professionalism, signoff conventions).

{rub_b}
{sample_block}
OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification directly referencing the rubric criteria>"
}}"""
    usr_b = f"""GENERATED REPLY DRAFT TO EVALUATE:
"{r['reply_draft']}"

Evaluate Brand Appropriateness (score 1-4) in JSON:"""
    kb = get_judge_cache_key('qwen/qwen3.8-27b', sys_b, usr_b)

    is_g = kg in cache
    is_a = ka in cache
    is_b = kb in cache

    if is_g: g_done += 1
    if is_a: a_done += 1
    if is_b: b_done += 1
    if is_g and is_a and is_b: all_done += 1

print(f"Total valid non-other items: {len(valid)}")
print(f"Fully judged items (all 3 dims): {all_done}/{len(valid)}")
print(f"Groundedness done: {g_done}/{len(valid)}")
print(f"Actionability done: {a_done}/{len(valid)}")
print(f"Brand done: {b_done}/{len(valid)}")
