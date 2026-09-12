"""
tests/test_pipeline.py
----------------------
Phase 0 unit tests. Real assertions, not placeholders.

Coverage:
  1. Multi-id string splitting (including single-id and empty cases)
  2. "True"/"False" string → actual bool mapping (not Python truthiness)
  3. Broadcast-root exclusion rule (>15 threshold)
  4. Sign-off stripping on multiple real-world patterns
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.ingest import _parse_id_list, INBOUND_MAP
from src.clean import strip_signoffs
from src.threads import is_broadcast_node


# ── 1. Multi-id splitting ─────────────────────────────────────────────────────

class TestParseIdList:
    def test_comma_separated_two_ids(self):
        result = _parse_id_list("119249,119251")
        assert result == ["119249", "119251"], (
            "Comma-separated pair must split into a list of two strings."
        )

    def test_comma_separated_three_ids(self):
        result = _parse_id_list("1,2,3")
        assert result == ["1", "2", "3"]

    def test_single_id(self):
        result = _parse_id_list("119249")
        assert result == ["119249"], "Single id must be wrapped in a list."

    def test_nan_returns_empty_list(self):
        assert _parse_id_list(float("nan")) == []

    def test_none_returns_empty_list(self):
        assert _parse_id_list(None) == []

    def test_empty_string_returns_empty_list(self):
        assert _parse_id_list("") == []

    def test_whitespace_string_returns_empty_list(self):
        assert _parse_id_list("   ") == []

    def test_ids_are_stripped(self):
        # Spaces around commas must be stripped
        result = _parse_id_list(" 119249 , 119251 ")
        assert result == ["119249", "119251"]


# ── 2. Boolean parsing ────────────────────────────────────────────────────────

class TestInboundBoolParsing:
    def test_string_true_maps_to_true(self):
        result = INBOUND_MAP["True"]
        assert result is True
        assert isinstance(result, bool)

    def test_string_false_maps_to_false(self):
        result = INBOUND_MAP["False"]
        # Critical: Python evaluates bool("False") as True (truthy non-empty string).
        # Our explicit map must return the bool False, not the string.
        assert result is False
        assert isinstance(result, bool)

    def test_false_string_is_not_truthy(self):
        """Verify the naive Python truthiness trap would give wrong answer."""
        naive = bool("False")  # This is True — the bug we're preventing.
        correct = INBOUND_MAP["False"]
        assert naive is True, "Sanity: naive bool('False') really is True."
        assert correct is False, "INBOUND_MAP must return False for 'False'."

    def test_map_applied_via_pandas(self):
        """End-to-end: map applied to a small Series."""
        s = pd.Series(["True", "False", "True", "False"])
        mapped = s.map(INBOUND_MAP)
        assert list(mapped) == [True, False, True, False]
        # Ensure the dtype isn't accidentally object/string
        assert mapped.dtype == bool or str(mapped.dtype) == "boolean"


# ── 3. Broadcast-root exclusion ───────────────────────────────────────────────

def _make_row(author_id: str, response_ids: list) -> pd.Series:
    """Helper to construct a minimal row Series for is_broadcast_node."""
    return pd.Series(
        {
            "author_id": author_id,
            "response_tweet_id": response_ids,
            "in_response_to_tweet_id": [],
            "inbound": False,
        }
    )


class TestBroadcastNodeExclusion:
    def test_brand_with_exactly_15_responses_is_not_broadcast(self):
        row = _make_row(
            author_id="AppleSupport",
            response_ids=[str(i) for i in range(15)],
        )
        assert is_broadcast_node(row) is False, (
            "A brand tweet with 20 response ids must be classified as broadcast."
        )

    def test_brand_with_3_responses_is_not_broadcast(self):
        row = _make_row(
            author_id="AppleSupport",
            response_ids=["1", "2", "3"],
        )
        assert is_broadcast_node(row) is False

    def test_brand_with_16_responses_is_broadcast(self):
        """One over the threshold must trigger exclusion."""
        row = _make_row(
            author_id="SpotifyCares",
            response_ids=[str(i) for i in range(16)],
        )
        assert is_broadcast_node(row) is True

    def test_numeric_author_id_IS_broadcast_if_high_fanout(self):
        """
        Broadcast exclusion applies per-node. Customer accounts with numeric
        author_ids are excluded if they broadcast (>15 responses).
        """
        row = _make_row(
            author_id="1234567890",  # numeric → customer
            response_ids=[str(i) for i in range(20)],
        )
        assert is_broadcast_node(row) is True

    def test_empty_response_list_is_not_broadcast(self):
        row = _make_row(
            author_id="AppleSupport",
            response_ids=[],
        )
        assert is_broadcast_node(row) is False


# ── 4. Sign-off stripping ─────────────────────────────────────────────────────

class TestStripSignoffs:
    def test_caret_initials_no_space(self):
        text = "Thanks for this. ^JK"
        cleaned, signoff = strip_signoffs(text)
        assert cleaned == "Thanks for this."
        assert signoff == "^JK"

    def test_caret_full_name_no_space(self):
        text = "We'll look into this right away. ^Tanuj"
        cleaned, signoff = strip_signoffs(text)
        assert cleaned == "We'll look into this right away."
        assert signoff == "^Tanuj"

    def test_hyphen_space_name(self):
        """The original naive regex r'[\\^\\-]\\w+$' would fail this case."""
        text = "Apologies for the trouble. - Mike"
        cleaned, signoff = strip_signoffs(text)
        assert cleaned == "Apologies for the trouble."
        assert signoff == "- Mike"

    def test_hyphen_space_name_with_page_marker(self):
        """'- Lee 2/2' — name followed by a page marker."""
        text = "We are looking into it. - Lee 2/2"
        cleaned, signoff = strip_signoffs(text)
        assert cleaned == "We are looking into it."
        assert signoff is not None
        assert "Lee" in signoff

    def test_no_signoff_unchanged(self):
        text = "Please try restarting your device and let us know."
        cleaned, signoff = strip_signoffs(text)
        assert cleaned == text
        assert signoff is None

    def test_caret_uppercase_initials(self):
        text = "We appreciate your patience. ^HSB"
        cleaned, signoff = strip_signoffs(text)
        assert signoff == "^HSB"
        assert "^HSB" not in cleaned

    def test_caret_after_newline(self):
        """Sign-off on its own line (embedded newline in tweet cell)."""
        text = "Please check your settings.\n^AA"
        cleaned, signoff = strip_signoffs(text)
        assert signoff == "^AA"
        assert "^AA" not in cleaned

    def test_non_string_input_returns_empty(self):
        cleaned, signoff = strip_signoffs(None)  # type: ignore[arg-type]
        assert cleaned == ""
        assert signoff is None

    def test_hyphen_becky(self):
        text = "Hope that helps! -Becky"
        cleaned, signoff = strip_signoffs(text)
        assert signoff is not None
        assert "Becky" in signoff
        assert "Becky" not in cleaned


# -- 5. Thread root-vs-leaf regression test -----------------------------------

class TestThreadRootLogic:
    """
    Regression test for the root-candidate bug: the algorithm must identify
    tweets with NO KNOWN PARENT as roots, not tweets with no children (leaves).

    A 3-tweet chain T0 -> T1 -> T2 should produce 1 thread of length 3.
    The old (all_tweet_ids - replied_to_ids) logic produced 3 single-tweet
    threads because it was selecting LEAF nodes not ROOT nodes.
    """

    def _make_chain_df(self):
        import pandas as pd
        rows = [
            {"tweet_id": "T0", "author_id": "BrandCo", "inbound": False,
             "created_at": pd.Timestamp("2017-01-01 10:00:00", tz="UTC"),
             "text": "Hello!", "response_tweet_id": ["T1"],
             "in_response_to_tweet_id": []},
            {"tweet_id": "T1", "author_id": "123456", "inbound": True,
             "created_at": pd.Timestamp("2017-01-01 10:01:00", tz="UTC"),
             "text": "I have an issue.", "response_tweet_id": ["T2"],
             "in_response_to_tweet_id": ["T0"]},
            {"tweet_id": "T2", "author_id": "BrandCo", "inbound": False,
             "created_at": pd.Timestamp("2017-01-01 10:02:00", tz="UTC"),
             "text": "We can help!", "response_tweet_id": [],
             "in_response_to_tweet_id": ["T1"]},
        ]
        return pd.DataFrame(rows)

    def test_three_tweet_chain_is_one_thread(self):
        from src.threads import build_threads
        df = self._make_chain_df()
        threads_df = build_threads(df)
        assert len(threads_df) == 1, (
            f"Expected 1 thread for a 3-tweet chain, got {len(threads_df)}. "
            "Root-candidate logic is computing leaf nodes instead of root nodes."
        )
        assert threads_df.iloc[0]["tweet_count"] == 3
        assert threads_df.iloc[0]["root_tweet_id"] == "T0"

    def test_thread_is_sorted_chronologically(self):
        from src.threads import build_threads
        df = self._make_chain_df()
        threads_df = build_threads(df)
        ids = threads_df.iloc[0]["tweet_ids"]
        assert ids == ["T0", "T1", "T2"], f"Not chronological: {ids}"

    def test_two_independent_roots_give_two_threads(self):
        import pandas as pd
        from src.threads import build_threads
        rows = [
            {"tweet_id": "A0", "author_id": "Brand", "inbound": False,
             "created_at": pd.Timestamp("2017-01-01", tz="UTC"),
             "text": "Hi", "response_tweet_id": ["A1"],
             "in_response_to_tweet_id": []},
            {"tweet_id": "A1", "author_id": "111", "inbound": True,
             "created_at": pd.Timestamp("2017-01-02", tz="UTC"),
             "text": "Problem", "response_tweet_id": [],
             "in_response_to_tweet_id": ["A0"]},
            {"tweet_id": "B0", "author_id": "Brand", "inbound": False,
             "created_at": pd.Timestamp("2017-02-01", tz="UTC"),
             "text": "Hello", "response_tweet_id": ["B1"],
             "in_response_to_tweet_id": []},
            {"tweet_id": "B1", "author_id": "222", "inbound": True,
             "created_at": pd.Timestamp("2017-02-02", tz="UTC"),
             "text": "Issue", "response_tweet_id": [],
             "in_response_to_tweet_id": ["B0"]},
        ]
        df = pd.DataFrame(rows)
        threads_df = build_threads(df)
        assert len(threads_df) == 2
        assert all(threads_df["tweet_count"] == 2)


# ── 8. Golden evaluation set verification ─────────────────────────────────────

class TestGoldenEvaluationSet:
    def test_golden_file_exists_and_row_count(self):
        from pathlib import Path
        import pandas as pd
        path = Path("data/golden/golden_labeled.csv")
        assert path.exists(), "golden_labeled.csv does not exist"
        df = pd.read_csv(path)
        assert len(df) == 200, f"Expected 200 items, found {len(df)}"

    def test_stratum_sizes_and_disjointness(self):
        from pathlib import Path
        import pandas as pd
        df = pd.read_csv(Path("data/golden/golden_labeled.csv"))
        assert (df["stratum"] == "A").sum() == 120, "Stratum A must have 120 items"
        assert (df["stratum"] == "B").sum() == 80, "Stratum B must have 80 items"

        tids_a = set(df[df["stratum"] == "A"]["tweet_id"])
        tids_b = set(df[df["stratum"] == "B"]["tweet_id"])
        assert len(tids_a.intersection(tids_b)) == 0, "Stratum A and B must be disjoint"
        assert len(set(df["tweet_id"])) == 200, "Duplicate tweet IDs in golden set"

    def test_taxonomy_conformity(self):
        from pathlib import Path
        import pandas as pd
        df = pd.read_csv(Path("data/golden/golden_labeled.csv"))
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
        found_intents = set(df["intent"])
        assert found_intents.issubset(valid_intents), f"Invalid intents found: {found_intents - valid_intents}"

    def test_escalation_boolean_integrity(self):
        from pathlib import Path
        import pandas as pd
        df = pd.read_csv(Path("data/golden/golden_labeled.csv"))
        assert df["escalate"].dtype == bool or set(df["escalate"]).issubset({True, False})

    def test_no_nulls_in_required_fields(self):
        from pathlib import Path
        import pandas as pd
        df = pd.read_csv(Path("data/golden/golden_labeled.csv"))
        assert df["sample_id"].isna().sum() == 0, "Nulls found in sample_id"
        assert df["text_clean"].isna().sum() == 0, "Nulls found in text_clean"
        assert df["intent"].isna().sum() == 0, "Nulls found in intent"
        assert df["escalate"].isna().sum() == 0, "Nulls found in escalate"

    def test_relabel_blind_sample_integrity(self):
        from pathlib import Path
        import pandas as pd
        relabel_path = Path("data/golden/relabel_blind_sample.csv")
        golden_path = Path("data/golden/golden_labeled.csv")

        assert relabel_path.exists(), "relabel_blind_sample.csv does not exist"
        df_relabel = pd.read_csv(relabel_path)
        df_golden = pd.read_csv(golden_path)

        assert len(df_relabel) == 40, f"Expected 40 blind items, found {len(df_relabel)}"
        assert set(df_relabel["tweet_id"]).issubset(set(df_golden["tweet_id"])), "Relabel tweet_ids not in golden set"
        # Verify relabel sample is completed and conforms to taxonomy
        assert len(df_relabel) == 40, "Relabel sample must contain 40 items"
        assert df_relabel["intent"].isna().sum() == 0, "Relabel sample must have no null intents"
        assert df_relabel["escalate"].isna().sum() == 0, "Relabel sample must have no null escalations"
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
        assert set(df_relabel["intent"]).issubset(valid_intents), "Invalid intents in relabel sample"
        assert set(df_relabel["escalate"]).issubset({True, False})


# -- 8. Baselines and Data Leakage Regression Tests (Phase 3) -----------------

class TestBaselinesAndLeakage:
    """
    Validation for Phase 3 baselines:
      - Leakage Check (Decision 1): Assert zero golden-set tweet_ids appear
        in the weak-label training pool.
      - Keyword dictionary integrity: All 8 taxonomy classes defined.
      - Deterministic escalation mapping integrity: matches Section 4.
    """

    def test_weak_label_pool_zero_golden_leakage(self):
        from pathlib import Path
        import pandas as pd
        from src.baseline_simple import load_clean_pool_and_sample

        weak_df, golden_df = load_clean_pool_and_sample(sample_size=2500, random_state=42)
        golden_ids = set(golden_df["tweet_id"].astype(str))
        
        id_col = "root_tweet_id" if "root_tweet_id" in weak_df.columns else "tweet_id"
        weak_ids = set(weak_df[id_col].astype(str))

        overlap = weak_ids.intersection(golden_ids)
        assert len(overlap) == 0, f"LEAKAGE: {len(overlap)} golden IDs found in weak-label pool!"
        assert len(weak_df) == 2500, f"Expected 2,500 samples, got {len(weak_df)}"

    def test_keyword_dict_contains_all_taxonomy_classes(self):
        from src.keyword_dict import KEYWORD_DICT, PRIORITY_ORDER
        expected_classes = {
            "connectivity_issue",
            "tv_content_access",
            "billing_dispute",
            "account_access",
            "appointment_installation",
            "complaint_no_request",
            "praise_thanks",
            "other",
        }
        assert set(KEYWORD_DICT.keys()) == expected_classes
        assert set(PRIORITY_ORDER) == expected_classes
        assert len(PRIORITY_ORDER) == 8

    def test_deterministic_escalation_mapping_conformity(self):
        from src.baseline_simple import ESCALATION_DEFAULT_MAPPING
        assert ESCALATION_DEFAULT_MAPPING["billing_dispute"] is True
        assert ESCALATION_DEFAULT_MAPPING["account_access"] is True
        assert ESCALATION_DEFAULT_MAPPING["appointment_installation"] is True
        assert ESCALATION_DEFAULT_MAPPING["connectivity_issue"] is False
        assert ESCALATION_DEFAULT_MAPPING["tv_content_access"] is False
        assert ESCALATION_DEFAULT_MAPPING["complaint_no_request"] is False
        assert ESCALATION_DEFAULT_MAPPING["praise_thanks"] is False
        assert ESCALATION_DEFAULT_MAPPING["other"] is False

    def test_retrieval_index_zero_golden_leakage(self):
        from pathlib import Path
        import pandas as pd
        from src.retrieval import build_or_load_corpus

        golden_df = pd.read_csv(Path("data/golden/golden_labeled.csv"))
        golden_tids = set(golden_df["tweet_id"].astype(str))

        corpus_df = build_or_load_corpus()
        assert len(corpus_df) > 0, "Corpus must not be empty"

        cust_tids = set(corpus_df["customer_tweet_id"].astype(str))
        brand_tids = set(corpus_df["brand_tweet_id"].astype(str))
        all_corpus_tids = cust_tids.union(brand_tids)

        overlap = all_corpus_tids.intersection(golden_tids)
        assert len(overlap) == 0, f"RETRIEVAL LEAKAGE: {len(overlap)} golden IDs found in retrieval index!"


class TestOrchestratorDecoupledLogic:
    """Unit tests for the Decision 20 Decoupled Dual-Path Orchestrator OR-gate logic (no LLM required)."""

    class MockPathA:
        def __init__(self, intent: str):
            self.intent = intent
        def process_message(self, text: str, k: int = 5):
            return {"intent": self.intent, "reply_draft": "test reply", "evidence_used": [], "reasoning": "test reasoning"}

    class MockPathB:
        def __init__(self, severity_label: str):
            self.severity_label = severity_label
        def extract_severity(self, text: str):
            return {"severity_label": self.severity_label, "rationale": "test severity rationale"}

    def test_severity_override_escalates_regardless_of_intent(self):
        from src.agent_orchestrator import SupportLensOrchestrator
        # intent is 'other' (which defaults to False), but severity is 'legal_regulatory'
        orch = SupportLensOrchestrator(
            path_a=self.MockPathA(intent="other"),
            path_b=self.MockPathB(severity_label="legal_regulatory")
        )
        res = orch.process("some text", tweet_id="123")
        assert res["escalate"] is True
        assert res["severity_override_triggered"] is True
        assert "legal_regulatory override detected" in res["escalation_reason"]

    def test_default_intent_escalates_when_severity_is_none(self):
        from src.agent_orchestrator import SupportLensOrchestrator
        # intent is 'billing_dispute' (defaults to True), severity is 'none'
        orch = SupportLensOrchestrator(
            path_a=self.MockPathA(intent="billing_dispute"),
            path_b=self.MockPathB(severity_label="none")
        )
        res = orch.process("some text", tweet_id="456")
        assert res["escalate"] is True
        assert res["severity_override_triggered"] is False
        assert res["default_intent_escalation"] is True
        assert "billing ledger access required" in res["escalation_reason"]

    def test_neither_triggers_yields_false(self):
        from src.agent_orchestrator import SupportLensOrchestrator
        # intent is 'connectivity_issue' (defaults to False), severity is 'none'
        orch = SupportLensOrchestrator(
            path_a=self.MockPathA(intent="connectivity_issue"),
            path_b=self.MockPathB(severity_label="none")
        )
        res = orch.process("some text", tweet_id="789")
        assert res["escalate"] is False
        assert res["severity_override_triggered"] is False
        assert res["default_intent_escalation"] is False
        assert "Auto-handled" in res["escalation_reason"]

    def test_both_trigger_preserves_severity_reason(self):
        from src.agent_orchestrator import SupportLensOrchestrator
        # intent is 'account_access' (defaults to True) AND severity is 'physical_hazard'
        orch = SupportLensOrchestrator(
            path_a=self.MockPathA(intent="account_access"),
            path_b=self.MockPathB(severity_label="physical_hazard")
        )
        res = orch.process("some text", tweet_id="999")
        assert res["escalate"] is True
        assert res["severity_override_triggered"] is True
        # Deliverable 3 requirement: explicit severity trigger takes priority in escalation_reason
        assert "physical_hazard override detected" in res["escalation_reason"]


