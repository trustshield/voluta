import pytest
import voluta

def test_empty_pattern_validation():
    """Test that TextMatcher rejects empty pattern sets with a ValueError."""
    with pytest.raises(ValueError) as excinfo:
        voluta.TextMatcher([])
    
    assert "Pattern set cannot be empty" in str(excinfo.value)

def test_non_empty_pattern_initialization():
    """Test that TextMatcher initializes correctly with valid patterns."""
    # Create with a single pattern
    matcher = voluta.TextMatcher(["pattern"])
    assert matcher is not None
    
    # Create with multiple patterns
    matcher = voluta.TextMatcher(["fox", "jump", "quick"])
    assert matcher is not None 

def test_empty_patterns_filtering():
    """Test that empty patterns are filtered out during initialization."""
    # Create a matcher with a mix of empty and non-empty patterns
    patterns = ["", "valid", "", "another", ""]
    matcher = voluta.TextMatcher(patterns)
    
    # Test match_bytes to verify only non-empty patterns are matched
    data = b"This is a valid test with another valid pattern."
    matches = matcher.match_bytes(data)
    
    # Collect all matched patterns
    matched_patterns = set(pattern for _, _, pattern in matches)
    
    # Verify only non-empty patterns are in the matches
    assert "" not in matched_patterns, "Empty patterns should be filtered out"
    assert "valid" in matched_patterns, "Valid pattern should be matched"
    assert "another" in matched_patterns, "Valid pattern should be matched"
    
    # Try with only empty patterns - should raise an error
    with pytest.raises(ValueError) as excinfo:
        voluta.TextMatcher(["", "", ""])
    
    assert "Pattern set cannot be empty" in str(excinfo.value)

def test_optional_parameters():
    """Test the optional parameters for TextMatcher."""
    # Default parameters (overlapping=True, case_insensitive=True)
    matcher_default = voluta.TextMatcher(["a", "b"])
    assert matcher_default is not None
    
    # Test with explicit overlapping=True
    matcher_overlap = voluta.TextMatcher(["a", "b"], overlapping=True)
    assert matcher_overlap is not None
    
    # Test with overlapping=False
    matcher_no_overlap = voluta.TextMatcher(["a", "b"], overlapping=False)
    assert matcher_no_overlap is not None
    
    # Test with explicit case_insensitive=True
    matcher_case = voluta.TextMatcher(["a", "b"], case_insensitive=True)
    assert matcher_case is not None
    
    # Test with case_insensitive=False
    matcher_case_sensitive = voluta.TextMatcher(["a", "b"], case_insensitive=False)
    assert matcher_case_sensitive is not None
    
    # Test with both parameters explicit
    matcher_both = voluta.TextMatcher(["a", "b"], overlapping=False, case_insensitive=False)
    assert matcher_both is not None 