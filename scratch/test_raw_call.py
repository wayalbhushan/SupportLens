from dotenv import load_dotenv
import os
from groq import Groq
load_dotenv()
client = Groq(api_key=os.environ['GROQ_API_KEY'])
from src.judge import load_rubric_dimension
rub = load_rubric_dimension('Actionability')
sys_p = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the ACTIONABILITY of a generated customer support reply for the customer's stated issue.

{rub}

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification directly referencing the rubric criteria>"
}}"""
usr_p = """CUSTOMER INBOUND MESSAGE:
"@115725 why did I receive a text message from you today in reference to an account I don't have and a phone number I don't have?"

GENERATED REPLY DRAFT TO EVALUATE:
"We understand you received an unexpected text regarding an account you don't recognize. To help you verify this safely without sharing personal info publicly, please send us a direct message so we can investigate."

Evaluate Actionability (score 1-4) in JSON:"""

for m in ['qwen/qwen3.8-27b', 'openai/gpt-oss-120b', 'openai/gpt-oss-20b']:
    try:
        c = client.chat.completions.create(model=m, messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': usr_p}], max_tokens=200)
        print(f"{m} SUCCEEDED: {c.choices[0].message.content[:100]}")
    except Exception as e:
        print(f"{m} FAILED: {e}")
