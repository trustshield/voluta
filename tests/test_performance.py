import time
import voluta


def test_matching_methods_performance(temp_test_file, search_patterns):
    """Test the performance of different matching methods."""
    matcher = voluta.TextMatcher(search_patterns)

    # Line-by-line matching
    start_time = time.time()
    line_matches = matcher.match_file(temp_test_file)
    line_time = time.time() - start_time

    # Memory-mapped matching
    start_time = time.time()
    mmap_matches = matcher.match_file_memmap(temp_test_file, None)
    mmap_time = time.time() - start_time

    # Parallel memory-mapped matching
    start_time = time.time()
    mmap_parallel_matches = matcher.match_file_memmap_parallel(
        temp_test_file, None, None
    )
    mmap_parallel_time = time.time() - start_time

    # Direct byte matching
    with open(temp_test_file, "rb") as f:
        file_bytes = f.read()

    start_time = time.time()
    byte_matches = matcher.match_bytes(file_bytes)
    byte_time = time.time() - start_time

    # Check that all methods find the same number of matches
    assert len(line_matches) > 0, "Line matching should find some matches"
    assert len(line_matches) == len(mmap_matches), (
        "Line and mmap should find same number of matches"
    )
    assert len(line_matches) == len(mmap_parallel_matches), (
        "Line and parallel should find same number"
    )
    assert len(line_matches) == len(byte_matches), (
        "Line and byte should find same number"
    )

    # Calculate performance ratios instead of asserting specific speed relationships
    # For small test files, the performance characteristics may vary
    mmap_ratio = line_time / mmap_time if mmap_time > 0 else 0
    parallel_ratio = line_time / mmap_parallel_time if mmap_parallel_time > 0 else 0
    byte_ratio = line_time / byte_time if byte_time > 0 else 0

    test_matching_methods_performance.results = {
        "line": (len(line_matches), line_time),
        "mmap": (len(mmap_matches), mmap_time),
        "parallel": (len(mmap_parallel_matches), mmap_parallel_time),
        "bytes": (len(byte_matches), byte_time),
        "ratios": {
            "mmap_vs_line": mmap_ratio,
            "parallel_vs_line": parallel_ratio,
            "byte_vs_line": byte_ratio,
        },
    }
