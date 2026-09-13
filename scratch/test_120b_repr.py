from dotenv import load_dotenv
import os
from groq import Groq
load_dotenv()
client = Groq(api_key=os.environ['GROQ_API_KEY'])
from src.judge import load_rubric_dimension
rub = load_rubric_dimension('Actionability')
sys_p = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the ACTIONABILITY of a generated customer support reply.

{rub}

OUTPUT FORMAT:
Respond ONLY with valid JSON:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification>"
}}"""
usr_p = """CUSTOMER: "why did I receive a text?"
REPLY: "please DM us so we can investigate."
Evaluate Actionability (score 1-4) in JSON:"""

c = client.chat.completions.create(model='openai/gpt-oss-120b', messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': usr_p}], max_tokens=150)
msg = c.choices[0].message
print("Content:", repr(msg.content))
print("Reasoning:", repr(getattr(msg, 'reasoning', None)))
