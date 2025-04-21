def test_basic_text_matcher(text_matcher, sample_text):
    """Test the TextMatcher with a simple example."""
    # Find matches directly in the bytes
    matches = text_matcher.match_bytes(sample_text.encode())

    # Verify we have the expected number of matches
    assert len(matches) == 4  # "fox" appears twice, plus "jump" and "quick"

    # Check each expected match is found
    match_patterns = [match[2] for match in matches]
    assert "fox" in match_patterns
    assert "jump" in match_patterns
    assert "quick" in match_patterns

    # Check positions of the first 'fox' match
    fox_matches = [match for match in matches if match[2] == "fox"]
    assert len(fox_matches) == 2  # "fox" appears twice in the text
    start, end, pattern = fox_matches[0]
    assert pattern == "fox"
    assert sample_text[start:end] == "fox"

    # Check that the context contains the pattern
    for start, end, pattern in matches:
        context = sample_text[max(0, start - 5) : end + 5]
        assert pattern in context
