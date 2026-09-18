"""Tests for the indexer module."""

from __future__ import annotations

from pathlib import Path

from mcp_for_agents.indexer import (
    DEFAULT_ACRONYMS,
    Doc,
    Index,
    build_index,
    corpus_label,
    index_directory,
    score,
    term_frequency,
    title_from_body,
    tokenize,
)


class TestTokenize:
    def test_lowercases_and_splits(self) -> None:
        """Lowercase, alphanumeric, 3+ chars only."""
        # Given
        text = "Hello World! Foo bar."
        # When
        result = tokenize(text)
        # Then
        assert result == ["hello", "world", "foo", "bar"]

    def test_skips_short_tokens(self) -> None:
        # Given
        text = "a ab abc abcd"
        # When
        result = tokenize(text)
        # Then
        assert result == ["abc", "abcd"]

    def test_empty_string(self) -> None:
        # Given / When / Then
        assert tokenize("") == []


class TestTermFrequency:
    def test_counts_occurrences(self) -> None:
        # Given
        tokens = ["foo", "bar", "foo", "baz", "foo"]
        # When
        result = term_frequency(tokens)
        # Then
        assert result == {"foo": 3, "bar": 1, "baz": 1}

    def test_empty_input(self) -> None:
        # Given / When / Then
        assert term_frequency([]) == {}


class TestTitleFromBody:
    def test_extracts_from_frontmatter(self) -> None:
        # Given
        body = '---\ntitle: "My Title"\n---\n\n# Heading\n\nBody.'
        # When
        result = title_from_body(body, "any.mdx")
        # Then
        assert result == "My Title"

    def test_extracts_from_h1(self) -> None:
        # Given
        body = "Some preamble.\n\n# Real Title\n\nMore text."
        # When
        result = title_from_body(body, "any.mdx")
        # Then
        assert result == "Real Title"

    def test_falls_back_to_filename(self) -> None:
        # Given
        body = "No frontmatter, no heading.\nJust text."
        # When
        result = title_from_body(body, "my-cool-doc.mdx")
        # Then
        assert result == "my cool doc"

    def test_extracts_from_rst_equals_underline(self) -> None:
        # Given
        body = "Decision Trees\n==============\n\nBody text."
        # When
        result = title_from_body(body, "tree.rst")
        # Then
        assert result == "Decision Trees"

    def test_extracts_from_rst_dash_underline(self) -> None:
        # Given
        body = "Random Forest\n-------------\n\nBody text."
        # When
        result = title_from_body(body, "forest.rst")
        # Then
        assert result == "Random Forest"

    def test_skips_rst_directives_before_title(self) -> None:
        # Given
        body = ".. currentmodule:: sklearn\n\n.. _user_guide:\n\nUser Guide\n==========\n\nBody."
        # When
        result = title_from_body(body, "index.rst")
        # Then
        assert result == "User Guide"

    def test_ignores_short_underline(self) -> None:
        # Given - "Title" is 5 chars but underline is only 3, so not a title.
        body = "Title\n---\n\nBody."
        # When
        result = title_from_body(body, "page.rst")
        # Then
        assert result == "page"


class TestIndexDirectory:
    def test_indexes_markdown_files(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "a.md").write_text("# Title A\n\nContent of A.")
        (tmp_path / "b.mdx").write_text("# Title B\n\nContent of B.")
        (tmp_path / "ignored.txt").write_text("not markdown")
        # When
        result = index_directory(tmp_path)
        # Then
        assert len(result) == 2
        rel_paths = sorted(d.rel_path for d in result)
        assert rel_paths == ["a.md", "b.mdx"]

    def test_indexes_rst_files(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "tree.rst").write_text("Decision Trees\n==============\n\nContent about trees.")
        (tmp_path / "ignored.txt").write_text("not a doc")
        # When
        result = index_directory(tmp_path)
        # Then
        assert len(result) == 1
        assert result[0].rel_path == "tree.rst"
        assert result[0].title == "Decision Trees"

    def test_skips_hidden_and_node_modules(self, tmp_path: Path) -> None:
        # Given
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.md").write_text("# Hidden")
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "dep.md").write_text("# Dep")
        (tmp_path / "real.md").write_text("# Real")
        # When
        result = index_directory(tmp_path)
        # Then
        assert len(result) == 1
        assert result[0].rel_path == "real.md"


class TestBuildIndex:
    def test_avgdl_is_mean_length(self) -> None:
        # Given
        docs = [
            Doc("a.md", "A", "body", {"foo": 1}, length=10),
            Doc("b.md", "B", "body", {"foo": 1}, length=20),
        ]
        # When
        index = build_index(docs)
        # Then
        assert index.avgdl == 15.0

    def test_empty_corpus(self) -> None:
        # Given / When
        index = build_index([])
        # Then
        assert index.avgdl == 0.0
        assert index.idf == {}

    def test_rare_term_gets_higher_idf_than_common_term(self) -> None:
        # Given - "common" appears in both docs, "rare" only in one.
        docs = [
            Doc("a.md", "A", "body", {"common": 1, "rare": 1}, length=5),
            Doc("b.md", "B", "body", {"common": 1}, length=5),
        ]
        # When
        index = build_index(docs)
        # Then
        assert index.idf["rare"] > index.idf["common"]

    def test_term_in_every_doc_gets_near_zero_idf(self) -> None:
        # Given - "common" appears in every one of 10 docs, so it
        # carries almost no discriminative power; "rare" appears in
        # just one and should score much higher.
        docs = [Doc(f"{i}.md", str(i), "body", {"common": 1}, length=5) for i in range(9)]
        docs.append(Doc("9.md", "9", "body", {"common": 1, "rare": 1}, length=5))
        # When
        index = build_index(docs)
        # Then
        assert index.idf["common"] < 0.1
        assert index.idf["rare"] > 1.0


class TestScore:
    def test_zero_for_empty_query(self) -> None:
        # Given
        doc = Doc("a.md", "Title", "body", {"foo": 3}, length=3)
        index = build_index([doc])
        # When / Then
        assert score([], doc, index) == 0.0

    def test_zero_for_empty_corpus(self) -> None:
        # Given - an Index with no documents (avgdl == 0).
        doc = Doc("a.md", "Title", "foo", {"foo": 1}, length=1)
        index = Index(idf={}, avgdl=0.0)
        # When / Then
        assert score(["foo"], doc, index) == 0.0

    def test_zero_when_term_absent(self) -> None:
        # Given
        doc = Doc("a.md", "Title", "foo", {"foo": 1}, length=1)
        index = build_index([doc])
        # When / Then
        assert score(["baz"], doc, index) == 0.0

    def test_rare_query_term_outscores_common_one(self) -> None:
        # Given - two docs, each mentioning its own term once; "rare"
        # appears in only one doc, "common" in both.
        doc_a = Doc("a.md", "A", "body", {"common": 1, "rare": 1}, length=5)
        doc_b = Doc("b.md", "B", "body", {"common": 1}, length=5)
        index = build_index([doc_a, doc_b])
        # When
        rare_score = score(["rare"], doc_a, index)
        common_score = score(["common"], doc_a, index)
        # Then - same tf and length, but "rare" is more discriminative.
        assert rare_score > common_score

    def test_shorter_doc_scores_higher_for_equal_term_frequency(self) -> None:
        # Given - both docs mention "foo" once, but doc_a is shorter,
        # so BM25's length normalization favors it.
        doc_a = Doc("a.md", "A", "body", {"foo": 1}, length=5)
        doc_b = Doc("b.md", "B", "body", {"foo": 1}, length=50)
        index = build_index([doc_a, doc_b])
        # When
        score_a = score(["foo"], doc_a, index)
        score_b = score(["foo"], doc_b, index)
        # Then
        assert score_a > score_b


class TestCorpusLabel:
    def test_known_acronym(self) -> None:
        # Given / When / Then
        assert corpus_label(Path("/some/path/fastapi")) == "FastAPI"

    def test_unknown_title_cased(self) -> None:
        # Given / When / Then
        assert corpus_label(Path("/some/path/awesome-package")) == "Awesome Package"

    def test_custom_acronyms_override(self) -> None:
        # Given / When / Then
        assert corpus_label(Path("/some/path/fastapi"), acronyms={"fastapi": "FAST API"}) == "FAST API"

    def test_root_or_empty_path(self) -> None:
        # Given / When / Then
        assert corpus_label(Path("/")) == "Documentation"

    def test_default_acronyms_constant_shape(self) -> None:
        """Smoke check: every value is a non-empty label."""
        # Given / When / Then
        for key, value in DEFAULT_ACRONYMS.items():
            assert key == key.lower()
            assert value
