"""
src/agent_orchestrator.py
-------------------------
Phase 4: Agent Orchestrator — Decoupled Dual-Path Contract (Decision 20).

Orchestration Logic:
  1. Invokes Path A with raw text: returns predicted intent, grounded reply draft, evidence used.
  2. Invokes Path B independently with raw text: returns severity label and rationale.
     Zero gating: Path B is never conditioned, filtered, or skipped based on Path A.
  3. Escalation Decision:
     final_escalate = (severity_label != "none") OR DEFAULT_ESCALATION_MAPPING[predicted_intent]
  4. Explicit Escalation Reason:
     - If severity_label != "none": States specific severity override trigger.
     - Else if default mapping is True: States default operational requirement reason.
     - Else: "Auto-handled: public troubleshooting script or standard reply available".
  5. Outputs unified record per message:
     {tweet_id, intent, severity_label, reply_draft, escalate, escalation_reason, evidence_used}
"""

from typing import Dict, List, Optional
from src.agent_path_a import PathAAgent
from src.agent_path_b import PathBAgent
from src.baseline_simple import ESCALATION_DEFAULT_MAPPING

DEFAULT_REASONS: Dict[str, str] = {
    "billing_dispute": "Escalated: Account authentication and billing ledger access required",
    "account_access": "Escalated: Secure credential handling and authentication required",
    "appointment_installation": "Escalated: Dispatch calendar and technician routing required",
    "connectivity_issue": "Auto-handled: Public troubleshooting script available",
    "tv_content_access": "Auto-handled: Public troubleshooting script available",
    "complaint_no_request": "Auto-handled: Empathy acknowledgement; no actionable resolution path",
    "praise_thanks": "Auto-handled: Standard closing response",
    "other": "Auto-handled: Out of scope inquiry",
}

class SupportLensOrchestrator:
    """Decoupled Dual-Path Orchestrator for SupportLens."""

    def __init__(
        self,
        path_a: Optional[PathAAgent] = None,
        path_b: Optional[PathBAgent] = None,
    ):
        self.path_a = path_a or PathAAgent()
        self.path_b = path_b or PathBAgent()

    def process(self, text: str, tweet_id: str = "") -> Dict:
        """
        Process inbound customer message through independent Path A and Path B,
        then unify through the deterministic escalation contract.
        """
        raw_text = str(text)

        # Path A: Intent classification + grounded reply draft
        res_a = self.path_a.process_message(raw_text)
        predicted_intent = res_a.get("intent", "other")
        reply_draft = res_a.get("reply_draft", "")
        evidence_used = res_a.get("evidence_used", [])

        # Path B: Independent severity extraction
        # Enforced decoupled contract: Path B receives ONLY raw_text string
        res_b = self.path_b.extract_severity(raw_text)
        severity_label = res_b.get("severity_label", "none")
        severity_rationale = res_b.get("rationale", "")

        # Deterministic Orchestration Rule (Decision 20):
        # final_escalate = (severity_label != "none") OR DEFAULT_ESCALATION_MAPPING[predicted_intent]
        severity_override_triggered = (severity_label != "none")
        default_intent_escalation = ESCALATION_DEFAULT_MAPPING.get(predicted_intent, False)
        final_escalate = severity_override_triggered or default_intent_escalation

        # Determine explicit escalation reason
        if severity_override_triggered:
            escalation_reason = (
                f"Escalated: {severity_label} override detected ({severity_rationale})"
            )
        elif default_intent_escalation:
            escalation_reason = DEFAULT_REASONS.get(
                predicted_intent, "Escalated: Default intent policy requires human queue"
            )
        else:
            escalation_reason = DEFAULT_REASONS.get(
                predicted_intent, "Auto-handled: Standard automated support flow"
            )

        return {
            "tweet_id": str(tweet_id),
            "intent": predicted_intent,
            "severity_label": severity_label,
            "reply_draft": reply_draft,
            "escalate": final_escalate,
            "escalation_reason": escalation_reason,
            "evidence_used": evidence_used,
            "severity_override_triggered": severity_override_triggered,
            "default_intent_escalation": default_intent_escalation,
            "path_a_reasoning": res_a.get("reasoning", ""),
        }
