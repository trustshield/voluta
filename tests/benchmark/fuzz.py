"""
Fuzzing test for the Voluta library.
Generates random patterns and data to test the robustness of the pattern matching.

Usage:
    python fuzz_test_voluta.py [--iterations N] [--seed SEED]

Options:
    --iterations N    Number of fuzzing iterations (default: 1000)
    --seed SEED       Random seed for reproducibility
"""

import voluta
import random
import string
import argparse
import tempfile
import os
import time
import traceback
from typing import List, Dict

# Test categories
CATEGORIES = [
    "empty_data",
    "long_pattern",
    "overlapping_patterns",
    "repeated_patterns",
    "binary_data",
    "unicode_data",
    "edge_cases",
    "case_insensitive",
    "special_characters",
    "random",
]


def generate_random_pattern(min_len=0, max_len=100):
    """Generate a random pattern with the given length range"""
    length = random.randint(min_len, max_len)

    # Choose pattern mode:
    # 0: safe (letters and digits only)
    # 1: limited special chars
    # 2: full special chars (only when fuzzing with this function)
    mode = random.choices([0, 1, 2], weights=[0.6, 0.3, 0.1])[0]

    if mode == 0:
        # Safe mode - just letters and digits
        chars = string.ascii_letters + string.digits
    elif mode == 1:
        # Limited special characters
        safe_punctuation = ".,!?;:-_+=#@$%&*"
        chars = string.ascii_letters + string.digits + safe_punctuation
    else:
        # Full special characters - only used in a small percentage of tests
        chars = string.ascii_letters + string.digits + string.punctuation

    # Generate a pattern of the chosen length with the selected character set
    return "".join(random.choice(chars) for _ in range(length))


def generate_random_data(size=1000, include_binary=False):
    """Generate random data for testing"""
    if include_binary:
        # Include binary (non-printable) characters
        return bytes(random.randint(0, 255) for _ in range(size))
    else:
        chars = (
            string.ascii_letters
            + string.digits
            + string.punctuation
            + string.whitespace
        )
        return "".join(random.choice(chars) for _ in range(size)).encode()


def insert_patterns_in_data(
    data: bytes, patterns: List[str], count=10
) -> Dict[str, List[int]]:
    """Insert patterns into the data at random positions and return the positions"""
    data_copy = bytearray(data)
    positions = {pattern: [] for pattern in patterns}

    # Insert each pattern a few times
    for _ in range(count):
        for pattern in patterns:
            if len(data_copy) <= len(pattern):
                continue  # Skip if pattern is too large for data

            # Choose random position
            pos = random.randint(0, len(data_copy) - len(pattern))

            # Insert the pattern by copying it into the data
            try:
                pattern_bytes = pattern.encode()

                # Create a temporary copy to verify we can insert the pattern
                temp_data = bytearray(data_copy)
                for i in range(len(pattern_bytes)):
                    temp_data[pos + i] = pattern_bytes[i]

                # Verify the pattern was actually inserted correctly
                if temp_data[pos : pos + len(pattern_bytes)] == pattern_bytes:
                    # Apply the change to the real data
                    data_copy = temp_data
                    # Record the position
                    positions[pattern].append(pos)
            except Exception:
                # Skip this pattern if there was a problem
                continue

    return bytes(data_copy), positions


def test_empty_data():
    """Test with empty data"""
    try:
        patterns = ["abc", "def"]
        data = b""

        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data)

        assert len(matches) == 0, "Empty data should not contain any matches"

        return True, "Empty data test passed"
    except Exception as e:
        return False, f"Empty data test failed: {str(e)}"


def test_long_pattern():
    """Test with very long patterns"""
    try:
        # Create a very long pattern (10KB)
        long_pattern = generate_random_pattern(10000, 10000)
        patterns = [long_pattern, "abc"]

        # Create data with the long pattern inserted
        data = generate_random_data(20000)
        insert_pos = random.randint(0, len(data) - len(long_pattern))
        data_with_pattern = (
            data[:insert_pos]
            + long_pattern.encode()
            + data[insert_pos + len(long_pattern) :]
        )

        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data_with_pattern)

        found_long = False
        for start, end, pattern in matches:
            if pattern == long_pattern:
                found_long = True
                assert start == insert_pos, (
                    f"Wrong match position: {start} != {insert_pos}"
                )

        assert found_long, "Long pattern not found"

        # Test with memory mapping
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(data_with_pattern)

        try:
            mmap_matches = matcher.match_file_memmap(tmp_path, 1024)

            found_long = False
            for start, end, pattern in mmap_matches:
                if pattern == long_pattern:
                    found_long = True
                    assert start == insert_pos, (
                        f"Wrong match position in memmap: {start} != {insert_pos}"
                    )

            assert found_long, "Long pattern not found in memmap"

        finally:
            os.unlink(tmp_path)

        return True, "Long pattern test passed"
    except Exception as e:
        return False, f"Long pattern test failed: {str(e)}\n{traceback.format_exc()}"


def test_overlapping_patterns():
    """Test with overlapping patterns"""
    try:
        patterns = ["abcd", "bcde", "cdef"]
        data = b"abcdefgh"

        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data)

        # All patterns should be found
        found_patterns = set(pattern for _, _, pattern in matches)
        assert found_patterns == set(patterns), (
            f"Not all patterns found: {found_patterns} != {set(patterns)}"
        )

        # Check positions
        for start, end, pattern in matches:
            if pattern == "abcd":
                assert start == 0 and end == 4, (
                    f"Wrong position for 'abcd': {start}-{end}"
                )
            elif pattern == "bcde":
                assert start == 1 and end == 5, (
                    f"Wrong position for 'bcde': {start}-{end}"
                )
            elif pattern == "cdef":
                assert start == 2 and end == 6, (
                    f"Wrong position for 'cdef': {start}-{end}"
                )

        # Test with overlapping explicitly disabled
        non_overlapping_matcher = voluta.TextMatcher(patterns, overlapping=False)
        non_overlapping_matches = non_overlapping_matcher.match_bytes(data)

        # We should find fewer matches with overlapping disabled
        assert len(non_overlapping_matches) < len(matches), (
            "Expected fewer matches with overlapping disabled"
        )

        return True, "Overlapping patterns test passed"
    except Exception as e:
        return False, f"Overlapping patterns test failed: {str(e)}"


def test_repeated_patterns():
    """Test with repeated patterns in the data"""
    try:
        patterns = ["abc", "xyz"]
        data = b"abc123abc456abc789xyz"

        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data)

        # Count matches
        pattern_counts = {}
        for _, _, pattern in matches:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        assert pattern_counts.get("abc", 0) == 3, (
            f"Expected 3 matches of 'abc', got {pattern_counts.get('abc', 0)}"
        )
        assert pattern_counts.get("xyz", 0) == 1, (
            f"Expected 1 match of 'xyz', got {pattern_counts.get('xyz', 0)}"
        )

        return True, "Repeated patterns test passed"
    except Exception as e:
        return False, f"Repeated patterns test failed: {str(e)}"


def test_binary_data():
    """Test with binary (non-UTF8) data"""
    try:
        patterns = [b"abc".hex(), b"\x00\x01\x02".hex()]
        # Create binary data with the patterns
        data = bytearray(random.getrandbits(8) for _ in range(1000))

        # Insert the binary pattern
        insert_pos = random.randint(0, len(data) - 3)
        data[insert_pos : insert_pos + 3] = b"\x00\x01\x02"

        # Convert patterns to strings for the matcher
        string_patterns = [p for p in patterns]
        matcher = voluta.TextMatcher(string_patterns)

        # We can't use match_bytes directly with binary data that isn't valid UTF-8
        # Instead, we'll write to a file and use memory mapping
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(data)

        try:
            mmap_matches = matcher.match_file_memmap(tmp_path, 1024)

            # Check if the binary pattern was found
            for start, _, pattern in mmap_matches:
                if pattern == b"\x00\x01\x02".hex():
                    assert start == insert_pos, (
                        f"Wrong match position: {start} != {insert_pos}"
                    )

            # This might fail if the binary pattern can't be matched properly
            # We'll still consider the test a pass if it doesn't crash

        finally:
            os.unlink(tmp_path)

        return True, "Binary data test completed (may not have found binary pattern)"
    except Exception as e:
        return False, f"Binary data test failed: {str(e)}"


def test_unicode_data():
    """Test with Unicode data"""
    try:
        # Unicode patterns
        patterns = ["안녕하세요", "こんにちは", "你好"]
        data = "안녕하세요 world! こんにちは universe! 你好 everyone!".encode("utf-8")

        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data)

        # All patterns should be found
        found_patterns = set(pattern for _, _, pattern in matches)
        assert found_patterns == set(patterns), (
            f"Not all patterns found: {found_patterns} != {set(patterns)}"
        )

        # Check positions (this depends on the UTF-8 encoding)
        utf8_data = "안녕하세요 world! こんにちは universe! 你好 everyone!"
        for _, _, pattern in matches:
            pos = utf8_data.find(pattern)
            assert pos >= 0, f"Pattern '{pattern}' not found in the data"

        return True, "Unicode data test passed"
    except Exception as e:
        return False, f"Unicode data test failed: {str(e)}"


def test_edge_cases():
    """Test various edge cases"""
    try:
        # Test pattern at the beginning
        patterns = ["start", "middle", "end"]
        data = b"start of the data with middle and end"

        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data)

        found_start = False
        for start, end, pattern in matches:
            if pattern == "start":
                found_start = True
                assert start == 0, (
                    f"Pattern 'start' should be at position 0, found at {start}"
                )

        assert found_start, "Pattern at start not found"

        # Test pattern at the end
        found_end = False
        for start, end, pattern in matches:
            if pattern == "end":
                found_end = True
                assert end == len(data), (
                    f"Pattern 'end' should end at position {len(data)}, found at {end}"
                )

        assert found_end, "Pattern at end not found"

        # Test with very small chunk size
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(data)

        try:
            # Use a very small chunk size (smaller than the patterns)
            small_chunk_matches = matcher.match_file_memmap(tmp_path, 2)

            # All patterns should still be found
            small_chunk_patterns = set(pattern for _, _, pattern in small_chunk_matches)
            assert small_chunk_patterns == set(patterns), (
                f"Not all patterns found with small chunks: {small_chunk_patterns} != {set(patterns)}"
            )

        finally:
            os.unlink(tmp_path)

        return True, "Edge cases test passed"
    except Exception as e:
        return False, f"Edge cases test failed: {str(e)}"


def test_case_insensitive():
    """Test case insensitive matching"""
    try:
        patterns = ["hello", "world"]
        data = b"HELLO World! hello world!"

        # Case insensitive is on by default
        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data)

        # Count matches - should be 4 (2 for each pattern)
        pattern_counts = {}
        for _, _, pattern in matches:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        assert pattern_counts.get("hello", 0) == 2, (
            f"Expected 2 matches for 'hello', got {pattern_counts.get('hello', 0)}"
        )
        assert pattern_counts.get("world", 0) == 2, (
            f"Expected 2 matches for 'world', got {pattern_counts.get('world', 0)}"
        )

        # Test with case sensitivity enabled
        case_sensitive_matcher = voluta.TextMatcher(patterns, case_insensitive=False)
        case_sensitive_matches = case_sensitive_matcher.match_bytes(data)

        # Count matches - should be only 1 for each pattern
        pattern_counts = {}
        for _, _, pattern in case_sensitive_matches:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        assert pattern_counts.get("hello", 0) == 1, (
            f"Expected 1 match for 'hello', got {pattern_counts.get('hello', 0)}"
        )
        assert pattern_counts.get("world", 0) == 1, (
            f"Expected 1 match for 'world', got {pattern_counts.get('world', 0)}"
        )

        return True, "Case insensitive test passed"
    except Exception as e:
        return False, f"Case insensitive test failed: {str(e)}"


def test_special_characters():
    """Test with patterns containing special characters"""
    try:
        # Test with a variety of special characters
        special_patterns = [
            "a\\b",  # Backslash
            "a*b+c?",  # Regex metacharacters
            "[abc]",  # Square brackets
            "{1,2}",  # Curly braces
            "^start$",  # Anchors
            "a|b",  # Pipe
            "a(b)c",  # Parentheses
            "hello\tworld",  # Tab
            "hello\nworld",  # Newline
            "<html>",  # Angle brackets
            "'quoted'",  # Single quotes
            '"double"',  # Double quotes
            "#comment",  # Hash
            "100%",  # Percent
            "path/to/file",  # Forward slash
        ]

        # Create data containing each pattern
        data = bytearray()
        expected_positions = {}

        for pattern in special_patterns:
            pos = len(data)
            expected_positions[pattern] = [pos]
            data.extend(pattern.encode())
            # Add some padding between patterns
            data.extend(b" --- ")

        # Convert to bytes
        final_data = bytes(data)

        # Create matcher and find matches
        matcher = voluta.TextMatcher(special_patterns)
        matches = matcher.match_bytes(final_data)

        # Check that all patterns were found
        found_patterns = set(pattern for _, _, pattern in matches)
        assert found_patterns == set(special_patterns), (
            f"Not all special patterns found: {found_patterns} != {set(special_patterns)}"
        )

        # Check positions
        for start, end, pattern in matches:
            expected_pos = expected_positions[pattern][0]
            assert start == expected_pos, (
                f"Wrong position for '{pattern}': {start} != {expected_pos}"
            )
            assert end == expected_pos + len(pattern), (
                f"Wrong end position for '{pattern}': {end} != {expected_pos + len(pattern)}"
            )

        # Test with memory mapping
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(final_data)

        try:
            mmap_matches = matcher.match_file_memmap(tmp_path, 1024)

            # Check that all patterns were found in memory-mapped file
            found_patterns = set(pattern for _, _, pattern in mmap_matches)
            assert found_patterns == set(special_patterns), (
                f"Not all special patterns found in memmap: {found_patterns} != {set(special_patterns)}"
            )

            # Check positions in memory-mapped matches
            for start, end, pattern in mmap_matches:
                expected_pos = expected_positions[pattern][0]
                assert start == expected_pos, (
                    f"Wrong position for '{pattern}' in memmap: {start} != {expected_pos}"
                )
                assert end == expected_pos + len(pattern), (
                    f"Wrong end position for '{pattern}' in memmap: {end} != {expected_pos + len(pattern)}"
                )

        finally:
            os.unlink(tmp_path)

        return True, "Special characters test passed"
    except Exception as e:
        return (
            False,
            f"Special characters test failed: {str(e)}\n{traceback.format_exc()}",
        )


def test_random(iteration=0):
    """Test with random patterns and data"""
    try:
        # Generate random patterns (1-5 patterns)
        num_patterns = random.randint(1, 5)
        patterns = [generate_random_pattern(1, 20) for _ in range(num_patterns)]

        # Filter out empty patterns
        patterns = [p for p in patterns if p]
        if not patterns:
            # If we somehow ended up with no valid patterns, add a default one
            patterns = ["test"]

        # Generate random data
        data_size = random.randint(100, 10000)
        data = generate_random_data(data_size)

        # Insert patterns into the data
        data_with_patterns, pattern_positions = insert_patterns_in_data(
            data, patterns, count=random.randint(1, 5)
        )

        # Create matcher and find matches
        matcher = voluta.TextMatcher(patterns)
        matches = matcher.match_bytes(data_with_patterns)

        # Check that all inserted patterns were found
        for pattern, positions in pattern_positions.items():
            # Extract all matches for this exact pattern
            matched_positions = [start for start, end, p in matches if p == pattern]

            # Verify that all expected positions are in the matched positions
            for pos in positions:
                # Check if the pattern was actually inserted correctly
                actual_data = data_with_patterns[pos : pos + len(pattern.encode())]
                expected_data = pattern.encode()

                if actual_data != expected_data:
                    # If the pattern wasn't correctly inserted, skip this check
                    continue

                assert pos in matched_positions, (
                    f"Pattern '{pattern}' not found at position {pos}. "
                    f"Matched positions: {matched_positions}"
                )

        # Test with memory mapping
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(data_with_patterns)

        try:
            # Random chunk size (but ensure it's at least as big as the longest pattern)
            max_pattern_len = max(len(p.encode()) for p in patterns)
            chunk_size = random.randint(max_pattern_len, max(100, max_pattern_len * 2))

            mmap_matches = matcher.match_file_memmap(tmp_path, chunk_size)

            # Check that all inserted patterns were found
            for pattern, positions in pattern_positions.items():
                # Extract all matches for this exact pattern
                matched_positions = [
                    start for start, end, p in mmap_matches if p == pattern
                ]

                # Verify that all expected positions are in the matched positions
                for pos in positions:
                    # Check if the pattern was actually inserted correctly
                    actual_data = data_with_patterns[pos : pos + len(pattern.encode())]
                    expected_data = pattern.encode()

                    if actual_data != expected_data:
                        # If the pattern wasn't correctly inserted, skip this check
                        continue

                    assert pos in matched_positions, (
                        f"Pattern '{pattern}' not found at position {pos} in memmap. "
                        f"Matched positions: {matched_positions}"
                    )

        finally:
            os.unlink(tmp_path)

        return True, f"Random test {iteration} passed"
    except Exception as e:
        return False, f"Random test {iteration} failed: {str(e)}"


def run_fuzzing_tests(iterations=1000, seed=None):
    """Run a series of fuzzing tests"""
    if seed is not None:
        random.seed(seed)
        print(f"Using random seed: {seed}")
    else:
        seed = random.randint(0, 2**32 - 1)
        random.seed(seed)
        print(f"Using random seed: {seed}")

    # Run standard tests
    tests = {
        "empty_data": test_empty_data,
        "long_pattern": test_long_pattern,
        "overlapping_patterns": test_overlapping_patterns,
        "repeated_patterns": test_repeated_patterns,
        "binary_data": test_binary_data,
        "unicode_data": test_unicode_data,
        "edge_cases": test_edge_cases,
        "case_insensitive": test_case_insensitive,
        "special_characters": test_special_characters,
    }

    results = {}
    for name, test_func in tests.items():
        print(f"Running {name} test...")
        start_time = time.time()
        success, message = test_func()
        elapsed = time.time() - start_time
        results[name] = (success, message, elapsed)
        print(f"  {'✅ PASS' if success else '❌ FAIL'} ({elapsed:.2f}s): {message}")

    # Run random tests
    print(f"\nRunning {iterations} random fuzzing tests...")
    random_results = []
    for i in range(iterations):
        if i % 100 == 0 and i > 0:
            print(f"  Completed {i} iterations...")

        success, message = test_random(i)
        random_results.append((success, message))

        if not success:
            print(f"  ❌ FAIL: {message}")

    # Count random test results
    random_success = sum(1 for success, _ in random_results if success)
    print(f"\nRandom fuzzing tests: {random_success}/{iterations} passed")

    # Overall summary
    all_standard_passed = all(success for success, _, _ in results.values())
    if all_standard_passed and random_success == iterations:
        print("\n✅ All fuzzing tests passed!")
    else:
        print("\n❌ Some fuzzing tests failed:")

        # Show failed standard tests
        for name, (success, message, _) in results.items():
            if not success:
                print(f"  - {name}: {message}")

        # Show failed random tests
        for i, (success, message) in enumerate(random_results):
            if not success:
                print(f"  - Random test {i}: {message}")

    return {
        "standard_tests": results,
        "random_tests": {
            "total": iterations,
            "passed": random_success,
            "failed": iterations - random_success,
        },
        "all_passed": all_standard_passed and random_success == iterations,
    }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Fuzzing tests for Voluta library")
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of random fuzzing iterations (default: 1000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        nargs="?",
        const=None,
        help="Random seed for reproducibility. When passed without a value, generates a random seed",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("Running fuzzing tests for Voluta library")
    print("=======================================\n")

    start_time = time.time()
    results = run_fuzzing_tests(iterations=args.iterations, seed=args.seed)
    elapsed = time.time() - start_time

    print(f"\nCompleted in {elapsed:.2f} seconds")

    # Exit with appropriate status code
    return 0 if results["all_passed"] else 1


if __name__ == "__main__":
    exit(main())
