import pytest
import os
import tempfile
from voluta import TextMatcher

def test_streaming_basic():
    """Test basic streaming functionality with a small file."""
    patterns = ["hello", "world"]
    matcher = TextMatcher(patterns)
    
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("hello world\nhello world")
            temp_path = f.name
        
        # Test with default buffer size
        matches = matcher.match_file_stream(temp_path)
        assert len(matches) == 4  # 2 matches per line
        
        # Test with small buffer size
        matches = matcher.match_file_stream(temp_path, buffer_size=4)
        assert len(matches) == 4
        
        # Verify match positions
        for match in matches:
            start, end, pattern = match
            assert pattern in patterns
            assert end > start
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

def test_streaming_large_file():
    """Test streaming with a large file."""
    patterns = ["test", "pattern"]
    matcher = TextMatcher(patterns)
    
    # Create a large file (1MB)
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        content = "test pattern " * 100000
        f.write(content)
        temp_path = f.name
    
    try:
        # Test with different buffer sizes
        for buffer_size in [1024, 8192, 32768]:
            matches = matcher.match_file_stream(temp_path, buffer_size=buffer_size)
            assert len(matches) == 200000  # 2 matches per line * 100000 lines
            
            # Verify all matches are correct
            for match in matches:
                start, end, pattern = match
                assert pattern in patterns
                assert end > start
    finally:
        os.unlink(temp_path)

def test_streaming_overlapping_patterns():
    """Test streaming with overlapping patterns."""
    patterns = ["abc", "bcd", "cde"]
    matcher = TextMatcher(patterns, overlapping=True)
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("abcde")
        temp_path = f.name
    
    try:
        matches = matcher.match_file_stream(temp_path, buffer_size=2)
        assert len(matches) == 3  # Should find all three patterns
        
        # Verify all patterns are found
        found_patterns = {pattern for _, _, pattern in matches}
        assert found_patterns == set(patterns)
    finally:
        os.unlink(temp_path)

def test_streaming_chunk_boundary():
    """Test that patterns spanning chunk boundaries are found correctly."""
    patterns = ["abcdefgh"]
    matcher = TextMatcher(patterns)
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("abcdefgh")
        temp_path = f.name
    
    try:
        # Use a small buffer size to force chunk boundaries
        matches = matcher.match_file_stream(temp_path, buffer_size=4)
        assert len(matches) == 1
        assert matches[0][2] == "abcdefgh"
    finally:
        os.unlink(temp_path)

def test_streaming_consistency():
    """Test that streaming results match other methods."""
    patterns = ["test", "pattern"]
    matcher = TextMatcher(patterns)
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        content = "test pattern " * 100
        f.write(content)
        temp_path = f.name
    
    try:
        # Compare results with other methods
        streaming_matches = matcher.match_file_stream(temp_path)
        memmap_matches = matcher.match_file_memmap(temp_path)
        basic_matches = matcher.match_file(temp_path)
        
        # Convert to sets for comparison
        streaming_set = {(start, end, pattern) for start, end, pattern in streaming_matches}
        memmap_set = {(start, end, pattern) for start, end, pattern in memmap_matches}
        
        # All methods should find the same matches
        assert streaming_set == memmap_set
        # Note: basic_matches includes line numbers, so we only compare positions and patterns
        assert {(start, end, pattern) for _, start, end, pattern in basic_matches} == streaming_set
    finally:
        os.unlink(temp_path)

def test_streaming_empty_file():
    """Test streaming with an empty file."""
    patterns = ["test"]
    matcher = TextMatcher(patterns)
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_path = f.name
    
    try:
        matches = matcher.match_file_stream(temp_path)
        assert len(matches) == 0
    finally:
        os.unlink(temp_path)

def test_streaming_invalid_path():
    """Test streaming with invalid file path."""
    patterns = ["test"]
    matcher = TextMatcher(patterns)
    
    with pytest.raises(IOError):
        matcher.match_file_stream("nonexistent_file.txt") 