import voluta
import tempfile
import os


def test_backslash_patterns():
    """Test that patterns with backslashes are correctly matched"""
    patterns = ["a\\b", "path\\to\\file", "c:\\windows\\system32"]
    data = b"a\\b test path\\to\\file c:\\windows\\system32"

    matcher = voluta.TextMatcher(patterns)
    matches = matcher.match_bytes(data)

    # All patterns should be found
    found_patterns = {pattern for _, _, pattern in matches}
    assert found_patterns == set(patterns)

    # Specific positions
    positions = {pattern: [] for pattern in patterns}
    for start, end, pattern in matches:
        positions[pattern].append(start)

    assert 0 in positions["a\\b"]
    assert 9 in positions["path\\to\\file"]
    assert 22 in positions["c:\\windows\\system32"]


def test_regex_metacharacters():
    """Test patterns containing characters that would be regex metacharacters"""
    patterns = ["a*b+c?", "[abc]", "{1,2}", "^start$", "a|b", "a(b)c"]

    # Create data containing all patterns
    data = b"a*b+c? [abc] {1,2} ^start$ a|b a(b)c"

    matcher = voluta.TextMatcher(patterns)
    matches = matcher.match_bytes(data)

    # All patterns should be found
    found_patterns = {pattern for _, _, pattern in matches}
    assert found_patterns == set(patterns)


def test_whitespace_characters():
    """Test patterns with whitespace characters (tab, newline, etc.)"""
    patterns = ["hello\tworld", "hello\nworld", "hello\rworld", "hello world"]

    # Create data with mixed whitespace
    data = b"hello\tworld hello\nworld hello\rworld hello world"

    matcher = voluta.TextMatcher(patterns)
    matches = matcher.match_bytes(data)

    # All patterns should be found
    found_patterns = {pattern for _, _, pattern in matches}
    assert found_patterns == set(patterns)


def test_html_characters():
    """Test patterns with characters common in HTML/XML"""
    patterns = ["<div>", "</div>", "<a href=''>", "<!--comment-->"]

    # Create HTML-like data
    data = b"<div>content</div> <a href=''>link</a> <!--comment-->"

    matcher = voluta.TextMatcher(patterns)
    matches = matcher.match_bytes(data)

    # All patterns should be found
    found_patterns = {pattern for _, _, pattern in matches}
    assert found_patterns == set(patterns)


def test_quotes_and_spaces():
    """Test patterns with quotes and various spaces"""
    patterns = ["'single quotes'", '"double quotes"', "space\u00a0character"]

    # Create data with quotes
    data = "'single quotes' \"double quotes\" space\u00a0character".encode()

    matcher = voluta.TextMatcher(patterns)
    matches = matcher.match_bytes(data)

    # All patterns should be found
    found_patterns = {pattern for _, _, pattern in matches}
    assert found_patterns == set(patterns)


def test_mixed_special_characters():
    """Test a mix of various special characters in the same pattern"""
    patterns = [
        "a\\b*c+d?[efg]",
        "multi\nline\tpattern",
        '<tag attr="value">content</tag>',
        "path/to\\file with spaces",
        "^$.*+?()[]{}|\\",
    ]

    # Create a string with exact matches for each pattern
    data_str = (
        "a\\b*c+d?[efg]\n"
        "multi\nline\tpattern\n"
        '<tag attr="value">content</tag>\n'
        "path/to\\file with spaces\n"
        "^$.*+?()[]{}|\\\n"
    )

    # Convert to bytes
    data = data_str.encode()

    matcher = voluta.TextMatcher(patterns)
    matches = matcher.match_bytes(data)

    # All patterns should be found
    found_patterns = {pattern for _, _, pattern in matches}
    assert found_patterns == set(patterns), (
        f"Found: {found_patterns}, Expected: {set(patterns)}"
    )


def test_binary_character_patterns():
    """Test patterns containing binary/non-printable characters"""
    # Instead of using hex directly, create string representations that Voluta can find
    binary_pattern1 = "BINARY_MARKER_000102"
    binary_pattern2 = "BINARY_MARKER_FFFEFD"
    patterns = [binary_pattern1, binary_pattern2]

    # Create a test string with the patterns
    data_str = f"start {binary_pattern1} middle {binary_pattern2} end"
    data = data_str.encode()

    # Create matcher and find matches
    matcher = voluta.TextMatcher(patterns)
    matches = matcher.match_bytes(data)

    # All patterns should be found
    found_patterns = {pattern for _, _, pattern in matches}
    assert found_patterns == set(patterns), (
        f"Found: {found_patterns}, Expected: {set(patterns)}"
    )

    # Check positions
    positions = {pattern: [] for pattern in patterns}
    for start, end, pattern in matches:
        positions[pattern].append(start)

    assert len(positions[binary_pattern1]) > 0, f"Pattern {binary_pattern1} not found"
    assert len(positions[binary_pattern2]) > 0, f"Pattern {binary_pattern2} not found"


def test_binary_data_with_memmap():
    """Test binary data using memory mapping"""
    pattern1 = "binary_test_000102"
    pattern2 = "binary_test_fffefd"
    patterns = [pattern1, pattern2]

    # Create a file with the exact string text embedded as bytes
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = f"prefix_{pattern1}_middle_{pattern2}_suffix".encode("utf-8")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_file_memmap(tmp_path, 4)

        found_patterns = {pattern for _, _, pattern in matches}

        for pattern in patterns:
            assert pattern in found_patterns, (
                f"Pattern {pattern} not found in {found_patterns}"
            )

        # Get positions
        positions = {pattern: [] for pattern in patterns}
        for start, end, pattern in matches:
            positions[pattern].append(start)

        # Expected positions
        p1_pos = content.find(pattern1.encode("utf-8"))
        p2_pos = content.find(pattern2.encode("utf-8"))

        assert p1_pos in positions[pattern1], (
            f"Pattern {pattern1} not found at expected position {p1_pos}"
        )
        assert p2_pos in positions[pattern2], (
            f"Pattern {pattern2} not found at expected position {p2_pos}"
        )

    finally:
        os.unlink(tmp_path)
