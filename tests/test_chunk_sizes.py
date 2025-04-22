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

def test_optional_params(temp_test_file, search_patterns):
    """Test that optional parameters work correctly for memory-mapped functions."""
    matcher = voluta.TextMatcher(search_patterns)
    
    # Test match_file_memmap with default parameters
    default_matches = matcher.match_file_memmap(temp_test_file)
    assert len(default_matches) > 0
    
    # Test match_file_memmap_parallel with default parameters
    parallel_default_matches = matcher.match_file_memmap_parallel(temp_test_file)
    assert len(parallel_default_matches) > 0
    
    # Test match_file_memmap_parallel with custom chunk size
    custom_chunk_matches = matcher.match_file_memmap_parallel(temp_test_file, chunk_size=1024)
    assert len(custom_chunk_matches) > 0
    
    # Test match_file_memmap_parallel with custom thread count
    custom_thread_matches = matcher.match_file_memmap_parallel(temp_test_file, n_threads=2)
    assert len(custom_thread_matches) > 0
    
    # Test match_file_memmap_parallel with all parameters
    all_params_matches = matcher.match_file_memmap_parallel(
        temp_test_file,
        chunk_size=1024,
        n_threads=2
    )
    assert len(all_params_matches) > 0
    
    # Verify that all methods found the same number of matches
    assert len(default_matches) == len(parallel_default_matches)
    assert len(default_matches) == len(custom_chunk_matches)
    assert len(default_matches) == len(custom_thread_matches)
    assert len(default_matches) == len(all_params_matches)
