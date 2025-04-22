from io import BytesIO
from voluta import TextMatcher


def test_sync_http_streaming():
    """Test synchronous HTTP streaming with requests."""
    patterns = ["error", "warning", "critical"]
    matcher = TextMatcher(patterns)

    # Create a mock response with test data
    test_data = b"error in system\nwarning: disk full\ncritical: server down"
    buffer = BytesIO()

    # Simulate streaming by writing in chunks
    chunks = [test_data[i : i + 10] for i in range(0, len(test_data), 10)]
    all_matches = []

    for chunk in chunks:
        buffer.write(chunk)
        # Process the entire buffer content
        matches = matcher.match_stream(buffer.getvalue())
        all_matches.extend(matches)
        # Don't clear the buffer, keep accumulating
        buffer.seek(0, 2)  # Seek to end

    # Verify we found all patterns
    found_patterns = {pattern for _, _, pattern in all_matches}
    assert found_patterns == set(patterns)

    # Verify match positions
    for start, end, pattern in all_matches:
        assert end > start
        assert pattern in patterns


def test_streaming_with_overlapping_patterns():
    """Test streaming with overlapping patterns."""
    patterns = ["abc", "bcd", "cde"]
    matcher = TextMatcher(patterns, overlapping=True)

    # Create test data with overlapping patterns
    test_data = b"abcde"
    buffer = BytesIO()
    all_matches = set()  # Use a set to deduplicate matches

    # Simulate streaming in small chunks
    chunks = [test_data[i : i + 2] for i in range(0, len(test_data), 2)]

    for chunk in chunks:
        buffer.write(chunk)
        # Process the entire buffer content
        matches = matcher.match_stream(buffer.getvalue())
        # Add all matches to the set
        all_matches.update(matches)
        buffer.seek(0, 2)  # Seek to end

    # Verify we found all patterns
    found_patterns = {pattern for _, _, pattern in all_matches}
    assert found_patterns == set(patterns)

    # Verify we found all overlapping matches
    assert len(all_matches) == 3  # Should find all three patterns


def test_streaming_large_data():
    """Test streaming with large amounts of data."""
    patterns = ["test", "pattern"]
    matcher = TextMatcher(patterns)

    # Create a large test data (1MB)
    test_data = b"test pattern " * 100000
    buffer = BytesIO()
    all_matches = set()  # Use a set to deduplicate matches

    # Process in chunks
    chunk_size = 8192
    chunks = [
        test_data[i : i + chunk_size] for i in range(0, len(test_data), chunk_size)
    ]

    for chunk in chunks:
        buffer.write(chunk)
        # Process the entire buffer content
        matches = matcher.match_stream(buffer.getvalue())
        # Add all matches to the set
        all_matches.update(matches)
        buffer.seek(0, 2)  # Seek to end

    # Verify we found all expected matches
    assert len(all_matches) == 200000  # 2 matches per line * 100000 lines

    # Verify match positions
    for start, end, pattern in all_matches:
        assert end > start
        assert pattern in patterns


def test_streaming_empty_data():
    """Test streaming with empty data."""
    patterns = ["test"]
    matcher = TextMatcher(patterns)

    buffer = BytesIO()
    matches = matcher.match_stream(buffer.getvalue())

    assert len(matches) == 0
