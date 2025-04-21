import os
import pytest
import tempfile
import voluta


@pytest.fixture
def boundary_test_files():
    """Fixture that creates test files with patterns at different boundary positions."""
    chunk_size = 1000
    long_pattern = "THISISALONGPATTERNFORCHUNKBOUNDARYTESTING"

    files = []
    positions = []

    # Pattern exactly at the boundary
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        s1 = (
            "X" * (chunk_size - len(long_pattern) // 2)
            + long_pattern
            + "X" * chunk_size
        )
        tmp.write(s1.encode())
        files.append(tmp.name)
        positions.append(chunk_size - len(long_pattern) // 2)

    # Pattern mostly in the first chunk
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        s2 = "Y" * (chunk_size - 5) + long_pattern + "Y" * chunk_size
        tmp.write(s2.encode())
        files.append(tmp.name)
        positions.append(chunk_size - 5)

    # Pattern mostly in the second chunk
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        s3 = "Z" * (chunk_size - 2) + long_pattern + "Z" * chunk_size
        tmp.write(s3.encode())
        files.append(tmp.name)
        positions.append(chunk_size - 2)

    yield files, positions, chunk_size, long_pattern

    for file_path in files:
        if os.path.exists(file_path):
            os.unlink(file_path)


def test_chunk_boundary_handling(boundary_test_files):
    """Test that patterns spanning chunk boundaries are properly detected."""
    files, positions, chunk_size, long_pattern = boundary_test_files

    # Create a matcher with the long pattern
    matcher = voluta.TextMatcher([long_pattern])

    for i, (file_path, expected_pos) in enumerate(zip(files, positions)):
        # Test with direct bytes (should always find the pattern)
        with open(file_path, "rb") as f:
            file_content = f.read()

        byte_matches = matcher.match_bytes(file_content)

        # Test with memory mapping and the specified chunk size
        mmap_matches = matcher.match_file_memmap(file_path, chunk_size)

        # Check if pattern was found in the expected position
        found_direct = any(start == expected_pos for start, _, _ in byte_matches)
        found_mmap = any(start == expected_pos for start, _, _ in mmap_matches)

        assert found_direct, (
            f"Test {i + 1}: Direct byte matching should find pattern at position {expected_pos}"
        )
        assert found_mmap, (
            f"Test {i + 1}: Memory-mapped matching should find pattern at position {expected_pos}"
        )

        direct_patterns = [match[2] for match in byte_matches]
        mmap_patterns = [match[2] for match in mmap_matches]

        assert long_pattern in direct_patterns, (
            f"Test {i + 1}: Direct matching should find the pattern {long_pattern}"
        )
        assert long_pattern in mmap_patterns, (
            f"Test {i + 1}: Memory-mapped should find the pattern {long_pattern}"
        )
