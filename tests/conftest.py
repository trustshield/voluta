import os
import random
import tempfile
from typing import List

import pytest
import voluta


@pytest.fixture
def text_matcher():
    """Fixture that provides a basic TextMatcher instance with common patterns."""
    patterns = ["fox", "jump", "quick"]
    return voluta.TextMatcher(patterns)


@pytest.fixture
def sample_text():
    """Fixture that provides a sample text for testing."""
    return "The fox jumped over the fence. The fox is quick."


@pytest.fixture
def book_sample():
    """Fixture that provides a larger text sample from a book."""
    return """
    It was the best of times, it was the worst of times, it was the age of wisdom,
    it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity,
    it was the season of Light, it was the season of Darkness, it was the spring of hope,
    it was the winter of despair, we had everything before us, we had nothing before us,
    we were all going direct to Heaven, we were all going direct the other way.
    """


@pytest.fixture
def search_patterns():
    """Fixture that provides common search patterns for tests."""
    return [
        "important",
        "critical",
        "error",
        "warning",
        "info",
        "fox",
        "jump",
        "quick",
    ]


@pytest.fixture
def temp_test_file(search_patterns):
    """Fixture that creates a temporary test file with patterns."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name

    # Create the test file with a default size of 1MB
    create_test_file(tmp_path, size_mb=1, patterns=search_patterns)

    yield tmp_path

    # Clean up the file after the test is done
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


def create_test_file(
    file_path: str, size_mb: int, patterns: List[str], pattern_frequency: float = 0.01
) -> None:
    """Create a test file with random content and specified patterns"""
    bytes_per_mb = 1024 * 1024
    total_bytes = size_mb * bytes_per_mb

    # Create a list of words to randomly select from
    word_list = [
        "the",
        "quick",
        "brown",
        "fox",
        "jumps",
        "over",
        "lazy",
        "dog",
        "hello",
        "world",
        "rust",
        "python",
        "programming",
        "language",
        "search",
        "algorithm",
        "performance",
        "testing",
        "memory",
        "file",
    ]

    with open(file_path, "w") as f:
        bytes_written = 0

        # Add content until we reach the desired size
        while bytes_written < total_bytes:
            # Occasionally add one of our target patterns
            if random.random() < pattern_frequency:
                text = random.choice(patterns) + " "
            else:
                text = random.choice(word_list) + " "

            f.write(text)
            bytes_written += len(text)

            # Add newline occasionally
            if random.random() < 0.1:
                f.write("\n")
                bytes_written += 1
