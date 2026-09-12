"""
src/llm_client.py
-----------------
Shared LLM client with persistent disk caching (Decision 8).
Supports Gemini (via google-genai) and Groq (via groq) as fallback.

Features:
  - Loads API keys from .env via python-dotenv.
  - Computes SHA256 hash of (model, prompt) to cache responses on disk.
  - Committed cache in `data/cache/llm_cache.json` guarantees fast, deterministic
    reproduction without hitting rate limits.
  - Strict JSON extraction from model outputs.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path("data/cache")
CACHE_FILE = CACHE_DIR / "llm_cache.json"

_CACHE: Dict[str, str] = {}

def _load_cache():
    global _CACHE
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
        except Exception as e:
            print(f"[llm_client] Warning: Failed to load cache from {CACHE_FILE}: {e}")
            _CACHE = {}

def _save_cache():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(_CACHE, f, indent=2, ensure_ascii=False)

_load_cache()

def get_cache_key(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    content = f"{model}|{temperature}|{system_prompt}|{user_prompt}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extract and parse JSON from LLM output, handling markdown fences if present."""
    text = raw_text.strip()
    # Strip markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Find the outermost JSON object if surrounded by preamble
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx : end_idx + 1]

    return json.loads(text)

class LLMClient:
    """Unified client for Gemini and Groq with disk caching."""

    def __init__(self, default_provider: str = "gemini"):
        self.default_provider = default_provider
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.groq_key = os.environ.get("GROQ_API_KEY")

        self.gemini_client = None
        self.groq_client = None

        if self.gemini_key:
            from google import genai
            self.gemini_client = genai.Client(api_key=self.gemini_key)

        if self.groq_key:
            from groq import Groq
            self.groq_client = Groq(api_key=self.groq_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        provider: Optional[str] = None,
    ) -> str:
        """
        Generate completion with disk caching.
        Returns the raw string output from the LLM.
        """
        provider = provider or self.default_provider

        # Default model selection
        if not model:
            if provider == "gemini":
                model = "gemini-3.6-flash"
            else:
                model = "llama-3.3-70b-versatile"

        cache_key = get_cache_key(model, system_prompt, user_prompt, temperature)
        if cache_key in _CACHE:
            return _CACHE[cache_key]

        # Call provider
        if provider == "gemini":
            if not self.gemini_client:
                if not self.gemini_key:
                    raise ValueError(
                        "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in environment or .env file."
                    )
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_key)

            full_prompt = f"{system_prompt}\n\nUser Input:\n{user_prompt}"
            import time
            raw_output = None
            for attempt in range(6):
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model,
                        contents=full_prompt,
                        config={"temperature": temperature},
                    )
                    raw_output = response.text
                    break
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        sleep_s = 8 + attempt * 2
                        print(f"[llm_client] Free-tier rate limit (429) encountered. Sleeping {sleep_s}s before retry {attempt+1}/6...")
                        time.sleep(sleep_s)
                    else:
                        raise e
            if raw_output is None:
                raise RuntimeError("Failed to generate content after 6 rate-limit retries.")

        elif provider == "groq":
            if not self.groq_client:
                if not self.groq_key:
                    raise ValueError("GROQ_API_KEY is not set in environment or .env file.")
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)

            completion = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            raw_output = completion.choices[0].message.content

        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Store in cache
        _CACHE[cache_key] = raw_output
        _save_cache()

        return raw_output
