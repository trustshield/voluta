from voluta import TextMatcher


def test_whole_word_matching():
    """Test that whole word matching works correctly."""
    patterns = ["cat", "dog", "a"]

    # Test with whole_word=True
    matcher_whole = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # Test with whole_word=False
    matcher_partial = TextMatcher(patterns, whole_word=False, case_insensitive=False)

    # Test data that contains both whole words and partial matches
    test_data = b"The cat is fast and ask the dog about a task"

    # Whole word matches should only find complete words
    whole_matches = matcher_whole.match_bytes(test_data)

    # Partial matches should find substrings too
    partial_matches = matcher_partial.match_bytes(test_data)

    # Check that whole word matching finds fewer matches
    assert len(whole_matches) <= len(partial_matches)

    # Verify specific expected matches for whole word
    whole_words_found = [match[2] for match in whole_matches]
    assert "cat" in whole_words_found  # "cat" should be found as whole word
    assert "dog" in whole_words_found  # "dog" should be found as whole word
    assert "a" in whole_words_found  # "a" should be found as whole word

    # Verify that partial matches include more occurrences
    partial_words_found = [match[2] for match in partial_matches]
    assert "cat" in partial_words_found  # "cat" in "cat"
    assert "dog" in partial_words_found  # "dog" in "dog"
    assert "a" in partial_words_found  # "a" in multiple places

    # Count occurrences
    whole_a_count = whole_words_found.count("a")
    partial_a_count = partial_words_found.count("a")

    # "a" appears as whole word once, but as substring multiple times
    assert whole_a_count == 1  # Only the standalone "a"
    assert partial_a_count > 1  # "a" in "fast", "and", "ask", "task", etc.


def test_word_boundary_edge_cases():
    """Test word boundary detection with edge cases."""
    patterns = ["test"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # Test at beginning and end of text
    assert len(matcher.match_bytes(b"test")) == 1
    assert len(matcher.match_bytes(b"test end")) == 1
    assert len(matcher.match_bytes(b"start test")) == 1
    assert len(matcher.match_bytes(b"start test end")) == 1

    # Test with punctuation boundaries
    assert len(matcher.match_bytes(b"test.")) == 1
    assert len(matcher.match_bytes(b".test")) == 1
    assert len(matcher.match_bytes(b"(test)")) == 1
    assert len(matcher.match_bytes(b"test!")) == 1

    # Test non-word boundaries (should not match)
    assert len(matcher.match_bytes(b"testing")) == 0
    assert len(matcher.match_bytes(b"pretest")) == 0
    assert len(matcher.match_bytes(b"pretesting")) == 0


def test_whole_word_with_case_insensitive():
    """Test whole word matching combined with case insensitive matching."""
    patterns = ["Test"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=True)

    test_data = b"This is a Test and testing and TEST case"
    matches = matcher.match_bytes(test_data)

    # Should find "Test" and "TEST" as whole words, but not "testing"
    matched_words = [match[2] for match in matches]
    assert len(matched_words) == 2  # "Test" and "TEST"


def test_whole_word_property():
    """Test that the whole_word property is accessible."""
    matcher_true = TextMatcher(["test"], whole_word=True)
    matcher_false = TextMatcher(["test"], whole_word=False)
    matcher_default = TextMatcher(["test"])

    assert matcher_true.whole_word == True
    assert matcher_false.whole_word == False
    assert matcher_default.whole_word == False  # Default should be False


def test_underscore_as_word_character():
    """Test that underscores are treated as word characters."""
    patterns = ["var", "test"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # Underscores should be word characters, so these should NOT match
    test_data = b"my_var is_test and var_name test_case"
    matches = matcher.match_bytes(test_data)

    # Should find no matches since patterns are connected to underscores
    matched_words = [match[2] for match in matches]
    assert len(matched_words) == 0

    # But these should match (underscore boundaries)
    test_data2 = b"check var and test here"
    matches2 = matcher.match_bytes(test_data2)
    matched_words2 = [match[2] for match in matches2]
    assert "var" in matched_words2
    assert "test" in matched_words2


def test_underscore_patterns():
    """Test patterns that contain underscores."""
    patterns = ["my_var", "test_func", "_private"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    test_data = b"call my_var and test_func but not _private_method"
    matches = matcher.match_bytes(test_data)

    matched_words = [match[2] for match in matches]
    assert "my_var" in matched_words
    assert "test_func" in matched_words
    # "_private" should not match because it's followed by "_method"
    assert "_private" not in matched_words

    # Test proper underscore pattern matching
    test_data2 = b"access _private variable here"
    matches2 = matcher.match_bytes(test_data2)
    matched_words2 = [match[2] for match in matches2]
    assert "_private" in matched_words2


def test_punctuation_boundaries():
    """Test various punctuation marks as word boundaries."""
    patterns = ["word"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # All these should match (punctuation creates word boundaries)
    test_cases = [
        b"word.",
        b"word,",
        b"word;",
        b"word:",
        b"word!",
        b"word?",
        b"(word)",
        b"[word]",
        b"{word}",
        b"'word'",
        b'"word"',
        b"word-end",
        b"word+sign",
        b"word*star",
        b"word/slash",
        b"word\\backslash",
        b"word@email",
        b"word#hash",
        b"word$dollar",
        b"word%percent",
        b"word^caret",
        b"word&ampersand",
        b"word|pipe",
        b"word~tilde",
        b"word`backtick",
    ]

    for test_case in test_cases:
        matches = matcher.match_bytes(test_case)
        assert len(matches) == 1, f"Failed for test case: {test_case}"
        assert matches[0][2] == "word"


def test_whitespace_boundaries():
    """Test various whitespace characters as word boundaries."""
    patterns = ["word"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # All these should match (whitespace creates word boundaries)
    test_cases = [
        b"word ",  # regular space
        b" word",  # leading space
        b"word\t",  # tab
        b"\tword",  # leading tab
        b"word\n",  # newline
        b"\nword",  # leading newline
        b"word\r",  # carriage return
        b"\rword",  # leading carriage return
        b"word\r\n",  # CRLF
        b"\r\nword",  # leading CRLF
        b"word\f",  # form feed
        b"\fword",  # leading form feed
        b"word\v",  # vertical tab
        b"\vword",  # leading vertical tab
    ]

    for test_case in test_cases:
        matches = matcher.match_bytes(test_case)
        assert len(matches) == 1, f"Failed for test case: {test_case!r}"
        assert matches[0][2] == "word"


def test_numeric_boundaries():
    """Test that numbers create word boundaries."""
    patterns = ["test"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # Numbers are word characters, so these should NOT match
    no_match_cases = [
        b"test123",
        b"123test",
        b"test4you",
        b"2test2",
    ]

    for test_case in no_match_cases:
        matches = matcher.match_bytes(test_case)
        assert len(matches) == 0, f"Should not match: {test_case!r}"

    # But these should match (non-alphanumeric boundaries)
    match_cases = [
        b"test-123",
        b"123-test",
        b"test.4",
        b"2.test",
    ]

    for test_case in match_cases:
        matches = matcher.match_bytes(test_case)
        assert len(matches) == 1, f"Should match: {test_case!r}"


def test_unicode_characters():
    """Test whole word matching with unicode characters."""
    patterns = ["café", "naïve", "résumé"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # Unicode letters should be treated as non-word characters in ASCII mode
    # So these should match (unicode creates boundaries)
    test_data = "café is naïve about résumé writing".encode("utf-8")
    matches = matcher.match_bytes(test_data)

    matched_words = [match[2] for match in matches]
    assert "café" in matched_words
    assert "naïve" in matched_words
    assert "résumé" in matched_words


def test_mixed_special_characters():
    """Test complex scenarios with mixed special characters."""
    patterns = ["API", "URL", "HTTP"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    test_data = b"The API-URL uses HTTP/1.1 protocol for API_calls and URL-encoding"
    matches = matcher.match_bytes(test_data)

    matched_words = [match[2] for match in matches]

    # Should find "API", "URL", and "HTTP" as whole words
    assert "API" in matched_words
    assert "URL" in matched_words
    assert "HTTP" in matched_words

    # Count occurrences
    api_count = matched_words.count("API")
    url_count = matched_words.count("URL")

    # "API" appears twice: "API-URL" and standalone, but "API_calls" should not match
    assert api_count == 1  # Only from "API-URL"
    assert url_count == 2  # From "API-URL" and "URL-encoding"


def test_empty_and_single_character_patterns():
    """Test edge cases with very short patterns."""
    patterns = ["a", "I", "x"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    test_data = b"I am a programmer, x marks the spot"
    matches = matcher.match_bytes(test_data)

    matched_words = [match[2] for match in matches]
    assert "I" in matched_words
    assert "a" in matched_words
    assert "x" in matched_words

    # Make sure we don't match inside words
    test_data2 = b"examining taxation maximum"
    matches2 = matcher.match_bytes(test_data2)
    matched_words2 = [match[2] for match in matches2]

    # Should find no matches since all are inside words
    assert len(matched_words2) == 0


def test_overlapping_with_whole_word():
    """Test overlapping matches combined with whole word matching."""
    patterns = ["test", "testing", "est"]
    matcher_overlap = TextMatcher(
        patterns, whole_word=True, overlapping=True, case_insensitive=False
    )
    matcher_no_overlap = TextMatcher(
        patterns, whole_word=True, overlapping=False, case_insensitive=False
    )

    test_data = b"The test and testing phase includes est methods"

    overlap_matches = matcher_overlap.match_bytes(test_data)
    no_overlap_matches = matcher_no_overlap.match_bytes(test_data)

    overlap_words = [match[2] for match in overlap_matches]
    no_overlap_words = [match[2] for match in no_overlap_matches]

    # Should find "test", "testing", and "est" as separate whole words
    assert "test" in overlap_words
    assert "testing" in overlap_words
    assert "est" in overlap_words

    # Non-overlapping behavior: when multiple patterns could match at the same position,
    # it picks one and moves on. Also, shorter patterns found first prevent longer ones.
    assert "test" in no_overlap_words
    assert "est" in no_overlap_words
    # "testing" might not be found if "test" is found first and the matcher moves past it
    # This is expected behavior for non-overlapping mode


def test_whole_word_with_file_methods():
    """Test whole word matching with file-based methods."""
    import os
    import tempfile

    patterns = ["test", "word"]
    matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # Create a temporary file
    test_content = b"This is a test file with word boundaries and testing words"

    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(test_content)
        temp_path = f.name

    try:
        # Test memmap method
        matches = matcher.match_file_memmap(temp_path)
        matched_words = [match[2] for match in matches]
        assert "test" in matched_words
        assert "word" in matched_words

        # Test stream method
        matches_stream = matcher.match_file_stream(temp_path)
        matched_words_stream = [match[2] for match in matches_stream]
        assert "test" in matched_words_stream
        assert "word" in matched_words_stream

        # Results should be consistent
        assert set(matched_words) == set(matched_words_stream)

    finally:
        os.unlink(temp_path)


def test_case_sensitivity_edge_cases():
    """Test case sensitivity combined with whole word matching."""
    patterns = ["Test", "WORD", "CamelCase"]

    # Case sensitive
    matcher_sensitive = TextMatcher(patterns, whole_word=True, case_insensitive=False)

    # Case insensitive
    matcher_insensitive = TextMatcher(patterns, whole_word=True, case_insensitive=True)

    test_data = b"test Test TEST word WORD Word camelcase CamelCase CAMELCASE"

    sensitive_matches = matcher_sensitive.match_bytes(test_data)
    insensitive_matches = matcher_insensitive.match_bytes(test_data)

    sensitive_words = [match[2] for match in sensitive_matches]
    insensitive_words = [match[2] for match in insensitive_matches]

    # Case sensitive should only match exact cases
    assert "Test" in sensitive_words
    assert "WORD" in sensitive_words
    assert "CamelCase" in sensitive_words
    assert len(sensitive_words) == 3

    # Case insensitive should match all variations
    assert len(insensitive_words) >= 6  # At least 6 matches for all variations
