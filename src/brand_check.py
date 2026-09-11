"""
src/brand_check.py
------------------
Phase 0 â€” Step 4: Brand substance heuristic pre-tagging.

Candidate brands: AppleSupport, SpotifyCares, AdobeCare, VerizonSupport.

For each brand:
  - Sample 300 OUTBOUND replies (inbound==False, author_id==brand), seed=42.
  - Apply heuristic pre-tag:
      "likely_deflection" â€” reply contains a DM/private-message redirect
                            with NO diagnostic question and NO specific
                            technical instruction.
      "likely_substantive" â€” reply contains a real troubleshooting step,
                             a specific setting/version/step reference,
                             or a diagnostic question.
      "likely_social"     â€” acknowledgement, thanks, closing with no
                            informational content.
  - Output: data/processed/brand_check_<brand>.csv
            columns: tweet_id, text_clean, heuristic_tag, manual_tag (empty)

The manual_tag column is intentionally left empty for human review.
The heuristic is a starting point, not a final classification.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.ingest import load_raw
from src.clean import strip_signoffs

PROCESSED_DIR = Path("data/processed")
SAMPLE_SEED = 42
SAMPLE_N = 300

from src.config import CANDIDATE_BRANDS

# â”€â”€ Heuristic patterns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Deflection: DM / private message redirect
_DEFLECT_RE = re.compile(
    r"\b(DM\s+us|send\s+us\s+a\s+DM|direct\s+message|private\s+message|"
    r"DM\s+your|message\s+us|send\s+a\s+message|reach\s+out\s+via\s+DM|"
    r"drop\s+us\s+a\s+DM|please\s+DM|please\s+message\s+us)\b",
    re.IGNORECASE,
)

# Diagnostic question: a question mark (? ) that implies diagnostic intent
_DIAGNOSTIC_Q_RE = re.compile(r"\?")

# Substantive content: references to specific technical steps/settings/versions
_SUBSTANTIVE_RE = re.compile(
    r"\b("
    r"restart|reboot|reinstall|uninstall|update|upgrade|reset|refresh|"
    r"settings|setting|toggle|enable|disable|turn\s+on|turn\s+off|"
    r"version|firmware|iOS|Android|app\s+version|build|"
    r"step\s+\d|step\s+one|step\s+two|first\s+try|next\s+try|"
    r"clear\s+cache|log\s+out|sign\s+out|sign\s+in|re-?log|"
    r"check\s+your|go\s+to|navigate\s+to|open\s+the|click|tap|"
    r"troubleshoot|follow\s+these|instructions|guide|"
    r"within\s+\d+\s+(hours?|days?|minutes?)|ticket|case\s+number|"
    r"error\s+code|error\s+message|screenshot\b"
    r")\b",
    re.IGNORECASE,
)

# Social: pure acknowledgements / thanks / closings
_SOCIAL_RE = re.compile(
    r"^("
    r"(thanks?|thank\s+you|ty|thx)\b[^.!?]*[.!]?\s*$|"
    r"(hi|hello|hey)\b[^.!?]{0,60}[.!]?\s*$|"
    r"(sorry\s+to\s+hear|we\s+understand|we\s+hear\s+you)[^.!?]{0,80}[.!]?\s*$|"
    r"(you'?re?\s+welcome|glad\s+(to\s+help|we\s+could)|no\s+problem)[^.!?]{0,60}[.!]?\s*$|"
    r"(have\s+a\s+(great|nice|good|wonderful)\s+\w+)[^.!?]{0,60}[.!]?\s*$"
    r")",
    re.IGNORECASE,
)


def _heuristic_tag(text: str) -> str:
    """
    Apply rule-based heuristic to classify a single reply text.

    Decision logic:
      1. If it matches a DM-deflection pattern AND has no diagnostic question
         AND has no substantive technical content â†’ likely_deflection
      2. If it has substantive content OR a diagnostic question â†’ likely_substantive
      3. Else if it matches social-only pattern â†’ likely_social
      4. Fallback â†’ likely_social (short/ambiguous replies default to social)
    """
    if not isinstance(text, str) or not text.strip():
        return "likely_social"

    has_deflect = bool(_DEFLECT_RE.search(text))
    has_diagnostic_q = bool(_DIAGNOSTIC_Q_RE.search(text))
    has_substantive = bool(_SUBSTANTIVE_RE.search(text))

    if has_deflect and not has_diagnostic_q and not has_substantive:
        return "likely_deflection"

    if has_substantive or has_diagnostic_q:
        return "likely_substantive"

    return "likely_social"


def run_brand_check(df: pd.DataFrame) -> None:
    """
    For each candidate brand, sample OUTBOUND replies, apply heuristic,
    save CSV, and print a summary table.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-clean text (strip sign-offs) for cleaner classification
    def _clean(text):
        if not isinstance(text, str):
            return ""
        cleaned, _ = strip_signoffs(text)
        return cleaned

    print("\n[brand_check] â”€â”€ Brand Substance Heuristic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    print(f"  Candidate brands : {CANDIDATE_BRANDS}")
    print(f"  Sample size      : {SAMPLE_N} outbound replies each (seed={SAMPLE_SEED})")
    print()

    summary_rows = []

    for brand in CANDIDATE_BRANDS:
        brand_df = df[
            (df["inbound"] == False) &  # noqa: E712
            (df["author_id"] == brand)
        ].copy()

        total_replies = len(brand_df)
        if total_replies == 0:
            print(f"  [{brand}] No outbound replies found â€” skipping.")
            continue

        n = min(SAMPLE_N, total_replies)
        sample = brand_df.sample(n=n, random_state=SAMPLE_SEED).copy()

        # Apply sign-off stripping
        sample["text_clean"] = sample["text"].apply(_clean)

        # Apply heuristic tag
        sample["heuristic_tag"] = sample["text_clean"].apply(_heuristic_tag)

        # Add empty manual_tag column for human review
        sample["manual_tag"] = ""

        # Output CSV
        out_cols = ["tweet_id", "text_clean", "heuristic_tag", "manual_tag"]
        out_path = PROCESSED_DIR / f"brand_check_{brand}.csv"
        sample[out_cols].to_csv(out_path, index=False)

        # Summary
        counts = sample["heuristic_tag"].value_counts()
        deflect = counts.get("likely_deflection", 0)
        substant = counts.get("likely_substantive", 0)
        social = counts.get("likely_social", 0)

        # Substance ratio: fraction of replies that are substantive (not deflect, not social)
        substance_ratio = substant / n if n > 0 else 0.0

        summary_rows.append(
            {
                "brand": brand,
                "total_replies_in_corpus": total_replies,
                "sampled": n,
                "likely_deflection": deflect,
                "likely_substantive": substant,
                "likely_social": social,
                "substance_ratio": f"{substance_ratio:.2%}",
            }
        )
        print(f"  [{brand}] â†’ saved {out_path.name} ({n} rows)")

    # Print summary table
    print()
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        print("[brand_check] â”€â”€ Summary Table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
        print(summary_df.to_string(index=False))
        print()
        print(
            "[brand_check] NOTE: `substance_ratio` = likely_substantive / sampled.\n"
            "  Higher ratio â†’ brand resolves more in public (preferred for Phase 1).\n"
            "  This is a heuristic estimate â€” manual_tag column in each CSV is for\n"
            "  your hand-correction before final brand selection."
        )
    print("â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€\n")


# â”€â”€ CLI entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    df = load_raw()
    run_brand_check(df)
    print("[brand_check] Done.")

