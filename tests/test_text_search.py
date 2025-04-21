import voluta


def test_text_search(book_sample):
    """Test searching for patterns in a larger text sample."""
    patterns = ["times", "age", "season", "hope", "despair", "Heaven"]
    matcher = voluta.TextMatcher(patterns)

    matches = matcher.match_bytes(book_sample.encode())

    assert len(matches) > 0

    found_patterns = {match[2] for match in matches}
    for pattern in patterns:
        assert pattern in found_patterns

    for start, end, pattern in matches:
        assert book_sample[start:end] == pattern

        context_start = max(0, start - 10)
        context_end = min(len(book_sample), end + 10)
        context = book_sample[context_start:context_end]
        assert pattern in context
