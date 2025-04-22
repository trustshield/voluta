"""
Stress test for Voluta library.
Tests performance on very large files with random data and random patterns.

Usage:
    python stress_test_voluta.py [--size SIZE_GB] [--patterns N] [--chunk CHUNK_MB] [--threads N]

Options:
    --size SIZE_GB     Size of the test file in GB (default: 1)
    --patterns N       Number of patterns to search for (default: 100)
    --chunk CHUNK_MB   Chunk size in MB (default: 8)
    --threads N        Number of threads for parallel processing (default: available cores)
"""

import voluta
import os
import random
import string
import time
import tempfile
import argparse
import sys
from typing import List


def generate_random_pattern(min_len=3, max_len=15):
    """Generate a random pattern with the given length range"""
    length = random.randint(min_len, max_len)
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def generate_test_patterns(num_patterns=100, min_len=3, max_len=15):
    """Generate random test patterns"""
    return [generate_random_pattern(min_len, max_len) for _ in range(num_patterns)]


def create_large_test_file(
    file_path: str, size_gb: float, patterns: List[str], pattern_frequency: float = 0.01
):
    """Create a very large test file with random content and the specified patterns inserted randomly"""
    print(
        f"Generating {size_gb:.1f}GB test file with {len(patterns)} search patterns..."
    )

    # Calculate size
    bytes_per_gb = 1024 * 1024 * 1024
    total_bytes = int(size_gb * bytes_per_gb)

    # Buffer size for efficient writing
    buffer_size = 1024 * 1024  # 1MB chunks for writing

    # Track progress
    bytes_written = 0
    last_percent = -1

    # Number of times each pattern has been inserted
    pattern_counts = {pattern: 0 for pattern in patterns}
    pattern_positions = []

    with open(file_path, "w") as f:
        while bytes_written < total_bytes:
            # Decide how much to write in this chunk
            chunk_size = min(buffer_size, total_bytes - bytes_written)
            chunk = []
            chunk_bytes = 0

            # Fill the chunk with random data and patterns
            while chunk_bytes < chunk_size:
                # Occasionally insert one of our patterns
                if random.random() < pattern_frequency:
                    pattern = random.choice(patterns)
                    chunk.append(pattern)
                    pattern_counts[pattern] += 1
                    pattern_positions.append(bytes_written + chunk_bytes)
                    chunk_bytes += len(pattern)
                else:
                    # Add random data
                    random_str = "".join(
                        random.choice(string.ascii_letters + string.digits + " \n\t")
                        for _ in range(random.randint(1, 20))
                    )
                    chunk.append(random_str)
                    chunk_bytes += len(random_str)

                # Ensure we don't exceed the chunk size
                if chunk_bytes > chunk_size:
                    # Truncate the last item
                    excess = chunk_bytes - chunk_size
                    chunk[-1] = chunk[-1][:-excess]
                    chunk_bytes -= excess

            # Write the chunk
            f.write("".join(chunk))
            bytes_written += chunk_bytes

            # Show progress
            percent = int(bytes_written * 100 / total_bytes)
            if percent > last_percent:
                last_percent = percent
                sys.stdout.write(f"\rProgress: {percent}% complete")
                sys.stdout.flush()

    file_size_gb = os.path.getsize(file_path) / bytes_per_gb
    print(f"\nCreated test file at {file_path}, size: {file_size_gb:.2f}GB")
    print(f"Inserted {sum(pattern_counts.values())} pattern instances")

    # Return some statistics
    return {
        "file_size": file_size_gb,
        "pattern_counts": pattern_counts,
        "pattern_positions": pattern_positions[
            :1000
        ],  # Just store a sample of positions
    }


def run_stress_test(
    file_path: str, patterns: List[str], chunk_size_mb: int, threads: int = None
):
    """Run a stress test on the large file"""
    matcher = voluta.TextMatcher(patterns)

    # Convert chunk size to bytes
    chunk_size = chunk_size_mb * 1024 * 1024

    print(f"\nRunning stress test with {len(patterns)} patterns:")
    print(f"  - File size: {os.path.getsize(file_path) / (1024 * 1024 * 1024):.2f}GB")
    print(f"  - Chunk size: {chunk_size_mb}MB")
    print(f"  - Threads: {threads if threads else 'auto'}")

    # Memory-mapped matching
    print("\nTesting memory-mapped matching...")
    start_time = time.time()
    mmap_matches = matcher.match_file_memmap(file_path, chunk_size)
    mmap_time = time.time() - start_time
    print(
        f"Memory-mapped matching: {len(mmap_matches)} matches in {mmap_time:.2f} seconds"
    )
    print(
        f"Processing speed: {os.path.getsize(file_path) / (mmap_time * 1024 * 1024):.2f}MB/s"
    )

    # Parallel memory-mapped matching
    print("\nTesting parallel memory-mapped matching...")
    start_time = time.time()
    mmap_parallel_matches = matcher.match_file_memmap_parallel(
        file_path, chunk_size, threads
    )
    mmap_parallel_time = time.time() - start_time
    print(
        f"Parallel memory-mapped matching: {len(mmap_parallel_matches)} matches in {mmap_parallel_time:.2f} seconds"
    )
    print(
        f"Processing speed: {os.path.getsize(file_path) / (mmap_parallel_time * 1024 * 1024):.2f}MB/s"
    )

    # Speed comparison
    print(
        f"\nParallel processing is {mmap_time / mmap_parallel_time:.2f}x faster than single-threaded"
    )

    # Sample some matches
    if mmap_matches:
        sample_size = min(5, len(mmap_matches))
        print("\nSample matches:")
        for start, end, pattern in random.sample(mmap_matches, sample_size):
            print(f"  • '{pattern}' found at byte positions {start}-{end}")

    return {
        "mmap": (len(mmap_matches), mmap_time),
        "parallel": (len(mmap_parallel_matches), mmap_parallel_time),
    }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Stress test for Voluta text pattern matching library"
    )
    parser.add_argument(
        "--size",
        type=float,
        default=1.0,
        help="Size of the test file in GB (default: 1)",
    )
    parser.add_argument(
        "--patterns",
        type=int,
        default=100,
        help="Number of patterns to search for (default: 100)",
    )
    parser.add_argument(
        "--chunk", type=int, default=8, help="Chunk size in MB (default: 8)"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Number of threads (default: available cores)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Generate random patterns
    print(f"Generating {args.patterns} random search patterns...")
    patterns = generate_test_patterns(num_patterns=args.patterns)

    # Create a temporary file for the stress test
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Create the large test file
        create_large_test_file(
            tmp_path, size_gb=args.size, patterns=patterns
        )

        # Run the stress test
        run_stress_test(
            tmp_path, patterns=patterns, chunk_size_mb=args.chunk, threads=args.threads
        )

        print("\nStress test completed successfully!")

    except KeyboardInterrupt:
        print("\nStress test interrupted by user.")
    finally:
        # Clean up the large file
        if os.path.exists(tmp_path):
            print(f"\nCleaning up temporary test file: {tmp_path}")
            os.unlink(tmp_path)


if __name__ == "__main__":
    main()
