"""
src/agent_path_b.py
-------------------
Phase 4: Path B — Independent Severity Extraction.

Architecture:
  - Input: Raw inbound customer message text ONLY (strictly unconditioned on Path A).
  - Enforced via code-level assertion: Path B accepts only string text input, with no access
    to Path A's intent or output object.
  - LLM call (Gemini, temperature 0.0) evaluated on 100% of messages without filtering.
  - Evaluates explicit severity triggers per Section 4 of LABELING_GUIDE.md v1.3:
      1. physical_hazard
      2. medical
      3. prolonged_outage (explicitly >= 48 hours)
      4. legal_regulatory (affirmative first-person filing/retention)
      5. business_critical
      6. none (default if no trigger present)
  - Strict three-way distinction between affirmative filing vs rhetorical hyperbole vs news commentary.
  - Persistent disk caching via LLMClient (Decision 8).
"""

from typing import Dict, Optional
from src.llm_client import LLMClient, clean_json_response

VALID_SEVERITY_LABELS = {
    "none",
    "physical_hazard",
    "medical",
    "prolonged_outage",
    "legal_regulatory",
    "business_critical",
}

SYSTEM_PROMPT_PATH_B = """You are SupportLens Path B: an independent, high-precision Safety and Severity Extraction AI for Verizon customer support.
Your ONLY role is to detect whether an inbound message contains an EXPLICIT, UNAMBIGUOUS high-severity operational emergency trigger that mandates immediate human supervisor or field escalation.

### THE 5 EXPLICIT SEVERITY OVERRIDE TRIGGERS
1. physical_hazard:
   - Downed utility cables or power wires in roads, yards, or sidewalks; snapped or severely leaning utility poles; smoking, sparking, or fire hazard equipment.
2. medical:
   - Explicit medical dependency: life-support devices, home dialysis, in-home oxygen equipment, emergency 911 access loss, or medical alert monitoring systems (LifeAlert).
3. prolonged_outage:
   - Complete loss of service EXPLICITLY stated by the customer as lasting 48 hours or longer (e.g. "Day 3 without internet", "down for 5 days", "offline for 72 hours"). Do not infer multi-day duration unless explicitly stated.
4. legal_regulatory:
   - Formal, affirmative first-person declarations of filing or lodging complaints with the FCC, FTC, Better Business Bureau (BBB), State Public Utility Commission (PUC), or retention of legal counsel/attorneys against Verizon.
5. business_critical:
   - Commercial / business customer explicitly stating ongoing downtime is actively halting business operations, point-of-sale card transactions, or employee payroll.
6. none:
   - No explicit emergency or severe override trigger stated. (Normal connection drops, billing disputes, customer service anger, or long wait times without the above explicit triggers are 'none').

---

### CRITICAL THREAT-SEVERITY GRADING RULES (v1.3 SPECIFICATION)
Apply this rigorous three-way boundary test:
1. Affirmative First-Person Intent -> Mark matching severity:
   - The customer declares an actual, ongoing or imminent complaint filing, regulatory report, or legal retention.
2. Rhetorical / Hyperbolic Legal Language -> Mark "none":
   - Venting emotional anger using legal phrases without an affirmative declaration of personal action. Phrases like "someone should sue", "a lawsuit is needed", or "this should be illegal" are venting hyperbole, NOT actionable legal escalation.
3. Third-Party Policy / News Commentary -> Mark "none":
   - Discussion of regulatory agencies (FCC/FTC) in a public policy, political, or broadcast context (e.g. net neutrality) rather than an individual customer service dispute.

---

### VERBATIM FEW-SHOT BENCHMARK EXAMPLES
- Example 1 (Affirmative Regulatory Filing):
  Text: "@115722 I'm wondering who else was promised a $250 GC, never got it and is disconnected when they call to ask. #BBB #FTC #FILECOMPLAINTS"
  JSON: {"severity_label": "legal_regulatory", "rationale": "Affirmative declaration of filing complaints with the BBB and FTC regarding unfulfilled promotion."}

- Example 2 (Affirmative Attorney Retention):
  Text: "@VerizonSupport I have an open case and I'm on the verge of getting an attorney to blow the whistle on the dirty unethical dealings"
  JSON: {"severity_label": "legal_regulatory", "rationale": "Explicit first-person threat of retaining an attorney regarding an ongoing active dispute."}

- Example 3 (Rhetorical Lawsuit Hyperbole):
  Text: "@115722 i think a class action lawsuit is needed for claiming internet speeds that you arent actually receiving!!"
  JSON: {"severity_label": "none", "rationale": "Rhetorical hyperbole stating a lawsuit is needed, rather than an affirmative declaration of personal legal action."}

- Example 4 (Speculative Venting):
  Text: "You guys should be sued for this terrible customer service, worst company in America."
  JSON: {"severity_label": "none", "rationale": "Hypothetical expression of anger ('should be sued'), not an active or imminent legal proceeding."}

- Example 5 (Policy / News Commentary):
  Text: "The FCC is planning to dismantle Net Neutrality. Imagine having to buy packages for the internet. Get educated on #NetNeutrality now."
  JSON: {"severity_label": "none", "rationale": "Public policy advocacy and news commentary regarding the FCC; not a customer account dispute."}

- Example 6 (Profane-but-Non-Legal-Vocabulary Affirmative Regulatory Threat):
  Text: "You corrupt crooks took $300 from my account. I'm reporting your fraud to the state attorney general and consumer protection bureau tomorrow morning."
  JSON: {"severity_label": "legal_regulatory", "rationale": "Explicit affirmative first-person declaration of filing with state attorney general and consumer protection bureau."}

- Example 7 (Hyperbole Without Legal Vocabulary):
  Text: "This is literally a crime against humanity to leave people without internet on a weekend, you all belong in federal prison."
  JSON: {"severity_label": "none", "rationale": "Extreme rhetorical venting ('crime against humanity', 'federal prison') with no genuine legal or emergency dependency."}

OUTPUT FORMAT:
Respond with a strict JSON object with no markdown formatting around it:
{
  "severity_label": "none" | "physical_hazard" | "medical" | "prolonged_outage" | "legal_regulatory" | "business_critical",
  "rationale": "concise explanation citing the explicit text evidence or lack thereof"
}
"""

class PathBAgent:
    """Path B Agent: Independent severity extraction with zero conditioning on Path A."""

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    def extract_severity(self, text: str) -> Dict:
        """
        Extract severity trigger from raw message text.
        CODE-LEVEL ASSERTION: Must accept only raw text string, never Path A output object.
        """
        assert isinstance(text, str), (
            f"VIOLATION OF DECOUPLED CONTRACT: Path B must be invoked with raw text str, "
            f"got {type(text)}. Access to Path A output is strictly prohibited."
        )
        assert not isinstance(text, dict), (
            "VIOLATION OF DECOUPLED CONTRACT: Path B cannot receive a dictionary or Path A result."
        )

        user_prompt = f"""CUSTOMER MESSAGE TO EVALUATE FOR SEVERITY OVERRIDE:
"{text.strip()}"

Extract severity in strict JSON format:"""

        raw_resp = self.client.generate(
            system_prompt=SYSTEM_PROMPT_PATH_B,
            user_prompt=user_prompt,
            model="gemini-3.5-flash-lite",
            temperature=0.0,
        )

        try:
            parsed = clean_json_response(raw_resp)
            label = parsed.get("severity_label", "none")
            if label not in VALID_SEVERITY_LABELS:
                label = "none"
            parsed["severity_label"] = label
        except Exception as e:
            parsed = {
                "severity_label": "none",
                "rationale": f"JSON parsing fallback: {e}. Raw: {raw_resp[:100]}",
            }

        return parsed
