"""
src/agent_path_a.py
-------------------
Phase 4: Path A — Intent Classification + Retrieval-Grounded Reply Drafting.

Architecture:
  - Input: Raw inbound customer message + top-5 retrieved paired historical replies from Part A.
  - Single LLM call (Gemini).
  - System prompt includes verbatim Stated-Defect Test and 8 intent class operational
    definitions from LABELING_GUIDE.md v1.3.
  - Output: Strict JSON schema:
    {
      "intent": "connectivity_issue" | "tv_content_access" | "billing_dispute" |
                "account_access" | "appointment_installation" | "complaint_no_request" |
                "praise_thanks" | "other",
      "reply_draft": string,
      "evidence_used": list of tweet_ids actually referenced from retrieved evidence,
      "reasoning": short string
    }
  - Persistent disk caching via LLMClient (Decision 8).
"""

from typing import Dict, List, Optional
from src.retrieval import VerizonSupportRetriever
from src.llm_client import LLMClient, clean_json_response

SYSTEM_PROMPT_PATH_A = """You are SupportLens Path A: an expert Verizon FiOS Customer Support AI.
Your task is to classify the customer's intent into exactly one of the 8 canonical taxonomy classes and draft a professional, grounded customer reply.

### OPERATIONAL TAXONOMY DEFINITIONS (LABELING_GUIDE.md v1.3 VERBATIM)

Apply the mechanical Stated-Defect Operational Test first:
"Does the message describe a specific, observable malfunction or account state that an engineer, billing specialist, or technician could investigate or verify?
- If YES: Classify by the stated defect, ignoring venting, insults, or emotional tone.
- If NO: Classify by emotional tone, sentiment, or out-of-scope status."

THE 8 CANONICAL INTENT CLASSES:
1. connectivity_issue:
   - Scope: Complete loss of internet access, slow broadband throughput, Wi-Fi router / ONT optical terminal / gateway equipment issues, intermittent connection drops, DNS failures, or physical utility cable/pole issues.
   - Core inclusions: outage, slow, down, wifi, wi-fi, internet, speed, speeds, router, ont, gateway, red globe, blinking, disconnect, disconnecting, packet loss, broadband, dns, wire down, wires down, cable down, no connection, cant connect, gigabit, fiber.

2. tv_content_access:
   - Scope: Inability to view television broadcasts, missing channels, cable set-top box (STB) errors, DVR recording failures, On Demand or Pay-Per-View access issues, channel contract blackouts, interactive guide/widget errors.

3. billing_dispute:
   - Scope: Disagreements over monthly invoice charges, unreturned equipment fees, promotional discounts dropping off, unexpected price increases, payment processing failures, refund or account credit requests.
   - Rule 3b Addendum: If a customer states an explicit, affirmative billing action (withholding payment, refusing to pay bill until service restored, demanding refund/credit) tied to a technical defect (e.g. "not paying my damn bill to you actually offer the internet speed you advertise"), classify as billing_dispute.

4. account_access:
   - Scope: Inability to log into customer portal or My Fios mobile app, password reset or credential recovery failures, two-factor authentication loops, locked accounts.
   - Rule 3a: Authentication / credential access blockers take precedence over technical issues (e.g., "Can't log into My Verizon to reset my router").

5. appointment_installation:
   - Scope: Scheduling, rescheduling, technician arrival windows, technician no-shows, delayed dispatches, or incomplete physical installation visits for EXISTING customers.
   - Near-Miss 2: Strictly for existing customers managing appointments/orders. Prospective coverage buildout inquiries belong in 'other'.

6. complaint_no_request:
   - Scope: Pure emotional venting, customer service dissatisfaction, long wait or hold times, threats to switch providers, without naming an actionable technical or billing defect.
   - Fails the Stated-Defect Test.

7. praise_thanks:
   - Scope: Genuine expressions of gratitude, appreciation, or positive feedback regarding customer service or technician support.
   - Note: Sarcastic praise belongs in complaint_no_request.

8. other:
   - Scope: Off-topic inquiries, non-customer network availability / regional buildout inquiries, competitor discussions, third-party promotional broadcasts, residual wireless mobile leaks.

---

### GROUNDED REPLY DRAFTING RULES
1. You are provided with top-5 retrieved historical customer messages and their official VerizonSupport replies.
2. Ground your reply_draft in the provided evidence where relevant. Cite the tweet_id(s) of any evidence you actually use in the "evidence_used" array.
3. If no retrieved evidence is a good match, state so explicitly in "reasoning" and draft a helpful, empathetic, policy-consistent reply without fabricating specific corporate URLs or commitments not seen in evidence.
4. Keep the reply concise, professional, and within standard customer support tone.

OUTPUT FORMAT:
Respond with a strict JSON object with no markdown formatting around it, matching this schema:
{
  "intent": "one of the 8 canonical classes above",
  "reply_draft": "the response to the customer",
  "evidence_used": ["tweet_id_1", "tweet_id_2"],
  "reasoning": "brief explanation of classification and reply grounding"
}
"""

class PathAAgent:
    """Path A Agent: Intent classification and retrieval-grounded reply drafting."""

    def __init__(self, retriever: Optional[VerizonSupportRetriever] = None, client: Optional[LLMClient] = None):
        self.retriever = retriever or VerizonSupportRetriever()
        self.client = client or LLMClient()

    def process_message(self, text: str, k: int = 5) -> Dict:
        """
        Process inbound message:
          1. Retrieve top-k grounding evidence.
          2. Query LLM for intent + grounded reply draft.
          3. Return parsed structured response.
        """
        evidence = self.retriever.retrieve(text, k=k)

        # Format evidence for prompt
        evidence_lines = []
        for i, ev in enumerate(evidence, 1):
            evidence_lines.append(
                f"[Evidence #{i} | Tweet ID: {ev['brand_tweet_id']} | Sim: {ev['similarity']:.3f}]\n"
                f"  Historical Customer: \"{ev['customer_text']}\"\n"
                f"  VerizonSupport Reply: \"{ev['brand_reply']}\""
            )
        evidence_block = "\n\n".join(evidence_lines) if evidence_lines else "No historical evidence found."

        user_prompt = f"""CUSTOMER MESSAGE TO CLASSIFY & ANSWER:
"{text}"

RETRIEVED HISTORICAL EVIDENCE FOR GROUNDING:
{evidence_block}

Classify the intent and generate the grounded reply draft in JSON format:"""

        raw_resp = self.client.generate(
            system_prompt=SYSTEM_PROMPT_PATH_A,
            user_prompt=user_prompt,
            temperature=0.0,
        )

        try:
            parsed = clean_json_response(raw_resp)
            intent = str(parsed.get("intent", "other")).strip().lower()
            valid_intents = {
                "connectivity_issue",
                "tv_content_access",
                "billing_dispute",
                "account_access",
                "appointment_installation",
                "complaint_no_request",
                "praise_thanks",
                "other",
            }
            if intent not in valid_intents:
                intent = "other"
            parsed["intent"] = intent
        except Exception as e:
            # Fallback if model output is malformed
            parsed = {
                "intent": "other",
                "reply_draft": "We'd like to help. Please reach out to us with your account details so we can investigate.",
                "evidence_used": [],
                "reasoning": f"JSON parsing failed: {e}. Raw: {raw_resp[:100]}",
            }

        return parsed
