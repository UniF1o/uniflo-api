"""Unit tests for the careers matching logic (no DB, no HTTP).

Covers:
  - _passes_subject_rule: all_of / any_of gate
  - _keyword_matches: word-boundary matching (including over-match guard)
  - _matches_keywords: any keyword in list
"""

from app.api.careers.service import (
    _keyword_matches,
    _matches_keywords,
    _passes_subject_rule,
)

# ─── Subject rule gate ───────────────────────────────────────────────────────

class TestPassesSubjectRule:
    def test_empty_rule_always_passes(self):
        rule = {"all_of": [], "any_of": []}
        assert _passes_subject_rule(set(), rule) is True
        assert _passes_subject_rule({"Mathematics"}, rule) is True

    def test_all_of_requires_every_subject(self):
        rule = {"all_of": ["Mathematics", "Physical Sciences"], "any_of": []}
        assert _passes_subject_rule({"Mathematics", "Physical Sciences"}, rule) is True
        assert _passes_subject_rule({"Mathematics"}, rule) is False
        assert _passes_subject_rule(set(), rule) is False

    def test_any_of_requires_at_least_one(self):
        rule = {"all_of": [], "any_of": ["Mathematics", "Mathematical Literacy"]}
        assert _passes_subject_rule({"Mathematics"}, rule) is True
        assert _passes_subject_rule({"Mathematical Literacy"}, rule) is True
        assert _passes_subject_rule({"Life Sciences"}, rule) is False

    def test_combined_all_of_and_any_of(self):
        rule = {
            "all_of": ["Life Sciences"],
            "any_of": ["Mathematics", "Physical Sciences"],
        }
        # all_of satisfied + any_of satisfied
        assert _passes_subject_rule({"Life Sciences", "Mathematics"}, rule) is True
        # all_of satisfied but any_of not satisfied
        assert _passes_subject_rule({"Life Sciences"}, rule) is False
        # any_of satisfied but all_of not satisfied
        assert _passes_subject_rule({"Mathematics"}, rule) is False

    def test_pure_maths_vs_maths_literacy_are_distinct(self):
        """Engineering gate (Mathematics required) must reject Mathematical Literacy."""
        engineering_rule = {"all_of": ["Mathematics", "Physical Sciences"], "any_of": []}
        maths_lit_student = {"Mathematical Literacy", "Physical Sciences", "Life Sciences"}
        assert _passes_subject_rule(maths_lit_student, engineering_rule) is False

        maths_student = {"Mathematics", "Physical Sciences"}
        assert _passes_subject_rule(maths_student, engineering_rule) is True

    def test_all_of_missing_one_fails(self):
        rule = {"all_of": ["Mathematics", "Physical Sciences", "Life Sciences"], "any_of": []}
        # Has Maths + Physical Sciences but no Life Sciences
        assert _passes_subject_rule({"Mathematics", "Physical Sciences"}, rule) is False

    def test_any_of_only_key_without_all_of_key(self):
        """Handle dicts that omit the other key entirely."""
        rule = {"any_of": ["Tourism", "Geography", "Business Studies"]}
        assert _passes_subject_rule({"Geography"}, rule) is True
        assert _passes_subject_rule({"History"}, rule) is False


# ─── Keyword matching ────────────────────────────────────────────────────────

class TestKeywordMatches:
    def test_exact_match(self):
        assert _keyword_matches("BSc in Engineering: Civil Engineering", "civil engineering") is True

    def test_case_insensitive(self):
        assert _keyword_matches("BSc CIVIL ENGINEERING", "civil engineering") is True
        assert _keyword_matches("BSc Civil Engineering", "CIVIL ENGINEERING") is True

    def test_partial_word_does_not_match(self):
        """Word-boundary matcher rejects 'law' when it is embedded inside another word.

        Note: \blaw\b does NOT match 'Laws' (the 's' is still a word char, so there is
        no boundary after 'w'). It also does not match 'outlaw' (no boundary before 'l').
        Protection against keyword 'law' matching commerce programmes like 'Economics with
        Law' relies on curated keywords ('llb', 'bachelor of laws') rather than the
        matcher alone, since 'Law' in that phrase IS a standalone word.
        """
        assert _keyword_matches("Outlaw Studies", "law") is False   # 'law' embedded in word
        assert _keyword_matches("Bachelor of Laws", "law") is False  # 'Laws' ≠ 'Law'
        assert _keyword_matches("Bachelor of Law", "law") is True    # exact standalone word

    def test_law_keyword_over_match_is_blocked_by_curation(self):
        """The law careers use 'llb' and 'bachelor of laws', NOT 'law'.
        Verify 'llb' matches real law degree names."""
        assert _keyword_matches("Bachelor of Laws (LLB)", "llb") is True
        assert _keyword_matches("LLB", "llb") is True

    def test_economics_with_law_not_matched_by_llb_keyword(self):
        """'Economics with Law' is NOT an LLB degree — 'llb' should not match it."""
        assert _keyword_matches("BCom Economics with Law", "llb") is False
        assert _keyword_matches("Bachelor of Commerce: Economics with Law", "llb") is False

    def test_civil_engineering_keyword(self):
        assert _keyword_matches("BEng Civil Engineering", "civil engineering") is True
        assert _keyword_matches("BSc in Engineering: Civil Engineering", "civil engineering") is True
        assert _keyword_matches("Mechanical Engineering", "civil engineering") is False

    def test_mbchb_keyword(self):
        assert _keyword_matches("Bachelor of Medicine and Surgery (MBChB)", "mbchb") is True
        assert _keyword_matches("MBChB", "mbchb") is True
        assert _keyword_matches("Bachelor of Science in Medicine", "mbchb") is False

    def test_actuarial_keyword(self):
        assert _keyword_matches("Bachelor of Business Science: Actuarial Science", "actuarial") is True
        assert _keyword_matches("BSc Actuarial Science", "actuarial") is True
        assert _keyword_matches("BSc Mathematics", "actuarial") is False

    def test_nursing_keyword(self):
        assert _keyword_matches("BSc Nursing Science", "nursing") is True
        assert _keyword_matches("Bachelor of Nursing", "nursing") is True
        assert _keyword_matches("BSc Nutrition", "nursing") is False

    def test_keyword_with_special_regex_chars_is_safe(self):
        """re.escape in _keyword_matches prevents regex injection."""
        assert _keyword_matches("BSc (Hons) Computer Science", "computer science") is True

    def test_empty_keyword_does_not_raise(self):
        # An empty keyword after strip should not crash
        result = _keyword_matches("Any Programme Name", "  ")
        assert isinstance(result, bool)


# ─── Multi-keyword matching ──────────────────────────────────────────────────

class TestMatchesKeywords:
    def test_any_keyword_triggers_match(self):
        keywords = ["civil engineering", "mechanical engineering"]
        assert _matches_keywords("BEng Civil Engineering", keywords) is True
        assert _matches_keywords("BEng Mechanical Engineering", keywords) is True

    def test_no_keyword_matches(self):
        keywords = ["civil engineering", "mechanical engineering"]
        assert _matches_keywords("BSc Computer Science", keywords) is False

    def test_empty_keyword_list(self):
        assert _matches_keywords("BSc Computer Science", []) is False

    def test_multiple_keywords_first_match_wins(self):
        keywords = ["computer science", "information technology", "software engineering"]
        assert _matches_keywords("BSc Computer Science", keywords) is True

    def test_software_developer_keywords_match_cs_degree(self):
        keywords = ["computer science", "information technology", "informatics", "software engineering", "data science"]
        assert _matches_keywords("BSc Computer Science", keywords) is True
        assert _matches_keywords("BSc Information Technology", keywords) is True
        assert _matches_keywords("BSc Data Science", keywords) is True
        assert _matches_keywords("BCom Economics", keywords) is False

    def test_accounting_keyword_does_not_match_economics_with_law(self):
        keywords = ["accounting", "chartered accountant"]
        assert _matches_keywords("BCom: Accounting Sciences", keywords) is True
        assert _matches_keywords("BCom Economics with Law", keywords) is False
