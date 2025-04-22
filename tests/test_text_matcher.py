import voluta

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

def test_case_insensitive():
    """Test the case_insensitive property and matching behavior."""
    # Create matchers with different case sensitivity settings
    case_insensitive_matcher = voluta.TextMatcher(["fox"], case_insensitive=True)
    case_sensitive_matcher = voluta.TextMatcher(["fox"], case_insensitive=False)
    
    # Check the property values are correct
    assert case_insensitive_matcher.case_insensitive is True
    assert case_sensitive_matcher.case_insensitive is False
    
    # Test matching behavior
    text = "The Fox and the fox are different cases."
    
    # Case insensitive matcher should find both "Fox" and "fox"
    insensitive_matches = case_insensitive_matcher.match_bytes(text.encode())
    assert len(insensitive_matches) == 2
    
    # Case sensitive matcher should only find "fox"
    sensitive_matches = case_sensitive_matcher.match_bytes(text.encode())
    assert len(sensitive_matches) == 1
    assert text[sensitive_matches[0][0]:sensitive_matches[0][1]] == "fox"

def test_overlapping():
    """Test the overlapping property and matching behavior."""
    # Create matchers with different overlapping settings
    overlapping_matcher = voluta.TextMatcher(["ana"], overlapping=True)
    non_overlapping_matcher = voluta.TextMatcher(["ana"], overlapping=False)
    
    # Check the property values are correct
    assert overlapping_matcher.overlapping is True
    assert non_overlapping_matcher.overlapping is False
    
    # Test matching behavior
    text = "banana"  # contains overlapping "ana" patterns
    
    # Overlapping matcher should find both occurrences of "ana"
    overlapping_matches = overlapping_matcher.match_bytes(text.encode())
    assert len(overlapping_matches) == 2
    
    # Non-overlapping matcher should find only one occurrence
    non_overlapping_matches = non_overlapping_matcher.match_bytes(text.encode())
    assert len(non_overlapping_matches) == 1
    
    # Verify the match positions
    if len(overlapping_matches) == 2:
        # First match at "banana" (positions 1-4)
        assert text[overlapping_matches[0][0]:overlapping_matches[0][1]] == "ana"
        # Second match at "banana" (positions 3-6)
        assert text[overlapping_matches[1][0]:overlapping_matches[1][1]] == "ana"
    
    if len(non_overlapping_matches) == 1:
        # Should find the first occurrence at "banana" (positions 1-4)
        assert text[non_overlapping_matches[0][0]:non_overlapping_matches[0][1]] == "ana"
