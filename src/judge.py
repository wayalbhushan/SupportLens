"""
src/judge.py
------------
Phase 5: LLM-as-Judge scoring pipeline for SupportLens.

Architecture (per Decision 7 & Decision 8):
  - Model Family: Groq (different model family from Gemini generator to avoid self-preference bias).
  - Scale: Pointwise scoring, 1-4 scale.
  - Three orthogonal dimensions scored in SEPARATE independent calls to avoid cross-dimension anchoring:
      1. Groundedness: Faithfulness to retrieved brand knowledge / evidence.
      2. Actionability: Clarity and feasibility of next steps for customer.
      3. Brand Appropriateness: Tone, empathy, adherence to Verizon support persona.
  - Prompts embed rubric sections from `rubric/judge_rubric.md` verbatim at call time.
  - Persistent disk caching in `data/cache/judge_cache.json` (distinct from generator cache).
  - Evaluation exclusion: Items where predicted intent == "other" are skipped (returns None).
"""

import ast
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Paths
RUBRIC_PATH = Path("rubric/judge_rubric.md")
JUDGE_CACHE_DIR = Path("data/cache")
JUDGE_CACHE_FILE = JUDGE_CACHE_DIR / "judge_cache.json"
CORPUS_CSV_PATH = Path("data/processed/retrieval_corpus.csv")

# In-memory judge cache
_JUDGE_CACHE: Dict[str, str] = {}


def _load_judge_cache():
    global _JUDGE_CACHE
    if JUDGE_CACHE_FILE.exists():
        try:
            with open(JUDGE_CACHE_FILE, "r", encoding="utf-8") as f:
                _JUDGE_CACHE = json.load(f)
        except Exception as e:
            print(f"[judge] Warning: Failed to load judge cache from {JUDGE_CACHE_FILE}: {e}")
            _JUDGE_CACHE = {}


def _save_judge_cache():
    JUDGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(JUDGE_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(_JUDGE_CACHE, f, indent=2, ensure_ascii=False)


_load_judge_cache()


def get_judge_cache_key(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    content = f"{model}|{temperature}|{system_prompt}|{user_prompt}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_rubric_dimension(dimension_name: str) -> str:
    """
    Read rubric/judge_rubric.md and extract the verbatim anchor text for the given dimension.
    Reads file dynamically at call-time so rubric updates require no code changes.
    """
    if not RUBRIC_PATH.exists():
        raise FileNotFoundError(f"Rubric file not found at {RUBRIC_PATH}")

    with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = rf"(##\s+{re.escape(dimension_name)}[\s\S]*?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        raise ValueError(f"Rubric dimension '{dimension_name}' not found in {RUBRIC_PATH}")

    text = match.group(1).strip()
    text = re.sub(r"\n+---+\s*$", "", text).strip()
    return text


_CORPUS_MAP: Optional[Dict[str, str]] = None


def get_evidence_text_map() -> Dict[str, str]:
    """
    Load retrieval corpus mapping tweet_id -> text representation.
    Used to join tweet_ids from evidence_used with actual historical evidence text.
    """
    global _CORPUS_MAP
    if _CORPUS_MAP is None:
        if CORPUS_CSV_PATH.exists():
            df = pd.read_csv(CORPUS_CSV_PATH)
            m = {}
            for _, r in df.iterrows():
                b_tid = str(r["brand_tweet_id"])
                c_tid = str(r["customer_tweet_id"])
                b_reply = str(r["brand_reply"])
                c_text = str(r["customer_text"])
                summary = f"Customer: \"{c_text}\" | VerizonSupport Reply: \"{b_reply}\""
                m[b_tid] = summary
                m[c_tid] = summary
            _CORPUS_MAP = m
        else:
            _CORPUS_MAP = {}
    return _CORPUS_MAP


def resolve_evidence_texts(evidence_field: Any) -> List[str]:
    """
    Convert an evidence_used field (list, string representation of list, or comma-separated IDs)
    into actual retrieved evidence text snippets.
    """
    if not evidence_field or pd.isna(evidence_field):
        return []

    tids = []
    if isinstance(evidence_field, list):
        tids = [str(x) for x in evidence_field]
    elif isinstance(evidence_field, str):
        try:
            parsed = ast.literal_eval(evidence_field)
            if isinstance(parsed, list):
                tids = [str(x) for x in parsed]
        except Exception:
            tids = re.findall(r"\d+", evidence_field)

    ev_map = get_evidence_text_map()
    resolved = []
    for tid in tids:
        if tid in ev_map:
            resolved.append(f"[Tweet {tid}] {ev_map[tid]}")
        else:
            resolved.append(f"[Tweet {tid}] (Evidence text unavailable in corpus)")
    return resolved


class LLMJudge:
    """
    Pointwise LLM judge using Groq to score agent drafts on Groundedness,
    Actionability, and Brand Appropriateness independently on a 1-4 scale.
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.environ.get("GROQ_JUDGE_MODEL", "qwen/qwen3.8-27b")
        self.groq_key = os.environ.get("GROQ_API_KEY")
        self.groq_client = None

        if self.groq_key:
            from groq import Groq
            self.groq_client = Groq(api_key=self.groq_key)

    def _call_judge_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Groq API with disk caching and structured JSON parsing."""
        cache_key = get_judge_cache_key(self.model, system_prompt, user_prompt, temperature=0.0)
        if cache_key in _JUDGE_CACHE:
            raw_text = _JUDGE_CACHE[cache_key]
        else:
            if not self.groq_client:
                if not self.groq_key:
                    raise ValueError("GROQ_API_KEY is not set in environment or .env file.")
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)

            raw_text = None
            for attempt in range(5):
                try:
                    completion = self.groq_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.0,
                        max_tokens=600,
                    )
                    raw_text = completion.choices[0].message.content
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "rate_limit" in err_msg.lower() or "503" in err_msg:
                        sleep_s = 2 ** attempt * 2
                        print(f"[judge] Groq rate limit/server notice. Sleeping {sleep_s}s (attempt {attempt+1}/5)...")
                        time.sleep(sleep_s)
                    else:
                        print(f"[judge] API error on attempt {attempt+1}: {e}")
                        time.sleep(2.0)

            if raw_output_text := raw_text:
                _JUDGE_CACHE[cache_key] = raw_output_text
                _save_judge_cache()
            else:
                raise RuntimeError(f"Failed to get completion from Groq model {self.model} after 5 attempts.")

        # Parse JSON from response
        clean_text = raw_text.strip()
        clean_text = re.sub(r"<think>.*?</think>", "", clean_text, flags=re.DOTALL).strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        start_idx = clean_text.find("{")
        end_idx = clean_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_text = clean_text[start_idx : end_idx + 1]

        try:
            parsed = json.loads(clean_text)
            score = int(parsed.get("score", 1))
            reasoning = str(parsed.get("reasoning", "")).strip()
            # Enforce 1-4 bounds
            score = max(1, min(4, score))
            return {"score": score, "reasoning": reasoning}
        except Exception as e:
            return {
                "score": 1,
                "reasoning": f"Judge JSON parse failure: {e}. Raw response: {raw_text[:120]}",
            }

    def score_groundedness(self, message: str, evidence_texts: List[str], reply: str) -> Dict[str, Any]:
        """Score reply groundedness against retrieved historical evidence on 1-4 scale."""
        rubric_text = load_rubric_dimension("Groundedness")
        evidence_block = "\n".join(evidence_texts) if evidence_texts else "No retrieved evidence provided."

        system_prompt = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the GROUNDEDNESS of a generated customer support reply against the retrieved evidence provided.

{rubric_text}

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification directly referencing the rubric criteria and evidence>"
}}"""

        user_prompt = f"""CUSTOMER INBOUND MESSAGE:
"{message}"

RETRIEVED HISTORICAL EVIDENCE:
{evidence_block}

GENERATED REPLY DRAFT TO EVALUATE:
"{reply}"

Evaluate Groundedness (score 1-4) in JSON:"""

        return self._call_judge_api(system_prompt, user_prompt)

    def score_actionability(self, message: str, reply: str) -> Dict[str, Any]:
        """Score reply actionability on 1-4 scale."""
        rubric_text = load_rubric_dimension("Actionability")

        system_prompt = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the ACTIONABILITY of a generated customer support reply for the customer's stated issue.

{rubric_text}

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification directly referencing the rubric criteria>"
}}"""

        user_prompt = f"""CUSTOMER INBOUND MESSAGE:
"{message}"

GENERATED REPLY DRAFT TO EVALUATE:
"{reply}"

Evaluate Actionability (score 1-4) in JSON:"""

        return self._call_judge_api(system_prompt, user_prompt)

    def score_brand_appropriateness(
        self, reply: str, sample_brand_replies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Score reply brand appropriateness on 1-4 scale."""
        rubric_text = load_rubric_dimension("Brand Appropriateness")

        sample_block = ""
        if sample_brand_replies:
            sample_lines = "\n".join(f"- {s}" for s in sample_brand_replies[:3])
            sample_block = f"\nREFERENCE BRAND REPLIES:\n{sample_lines}\n"

        system_prompt = f"""You are an expert, impartial evaluation judge for customer support AI systems.
You evaluate the BRAND APPROPRIATENESS of a customer support reply (tone, empathy, professionalism, signoff conventions).

{rubric_text}
{sample_block}
OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer from 1 to 4>,
  "reasoning": "<concise justification directly referencing the rubric criteria>"
}}"""

        user_prompt = f"""GENERATED REPLY DRAFT TO EVALUATE:
"{reply}"

Evaluate Brand Appropriateness (score 1-4) in JSON:"""

        return self._call_judge_api(system_prompt, user_prompt)


# Module-level convenience functions
_GLOBAL_JUDGE: Optional[LLMJudge] = None


def _get_global_judge() -> LLMJudge:
    global _GLOBAL_JUDGE
    if _GLOBAL_JUDGE is None:
        _GLOBAL_JUDGE = LLMJudge()
    return _GLOBAL_JUDGE


def score_groundedness(message: str, evidence_texts: List[str], reply: str) -> Dict[str, Any]:
    return _get_global_judge().score_groundedness(message, evidence_texts, reply)


def score_actionability(message: str, reply: str) -> Dict[str, Any]:
    return _get_global_judge().score_actionability(message, reply)


def score_brand_appropriateness(
    reply: str, sample_brand_replies: Optional[List[str]] = None
) -> Dict[str, Any]:
    return _get_global_judge().score_brand_appropriateness(reply, sample_brand_replies)


def judge_item(
    message: str,
    reply: str,
    evidence_texts: List[str],
    predicted_intent: str,
    sample_brand_replies: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluate a single item across all three dimensions.
    EVALUATION EXCLUSION: If predicted intent == 'other', skips judging entirely
    and returns None without calling the judge API (Part B Step 5).
    """
    if str(predicted_intent).strip().lower() == "other":
        return None

    groundedness = score_groundedness(message, evidence_texts, reply)
    actionability = score_actionability(message, reply)
    brand = score_brand_appropriateness(reply, sample_brand_replies)

    return {
        "groundedness": groundedness,
        "actionability": actionability,
        "brand_appropriateness": brand,
    }
