import pytest
import time
import voluta


@pytest.mark.parametrize(
    "chunk_size",
    [
        64 * 1024,  # 64KB
        256 * 1024,  # 256KB
        1 * 1024 * 1024,  # 1MB
        4 * 1024 * 1024,  # 4MB
    ],
)
def test_chunk_sizes(temp_test_file, search_patterns, chunk_size):
    """Test the effect of different chunk sizes on performance."""
    matcher = voluta.TextMatcher(search_patterns)

    # Get baseline with no chunk size specified
    start_time = time.time()
    baseline_matches = matcher.match_file_memmap(temp_test_file, None)
    baseline_time = time.time() - start_time

    # Test with the specific chunk size
    start_time = time.time()
    matches = matcher.match_file_memmap(temp_test_file, chunk_size)
    elapsed = time.time() - start_time

    assert len(matches) == len(baseline_matches), (
        f"Chunk size {chunk_size} should find same matches as baseline"
    )

    if not hasattr(test_chunk_sizes, "results"):
        test_chunk_sizes.results = {}

    test_chunk_sizes.results[chunk_size] = {
        "chunk_size": chunk_size,
        "matches": len(matches),
        "time": elapsed,
        "baseline_time": baseline_time,
    }
