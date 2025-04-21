# Voluta

A high-performance Python library for searching text patterns using the Aho-Corasick algorithm.
Built with Rust for blazing fast processing.

## Features

- Memory-mapped file processing for optimal performance with large files
- Parallel processing option for multi-core utilization
- Configurable chunk sizes for memory management and performance tuning
- Direct byte matching for maximum control and performance
- Returns full match information (start and end positions)
- Case insensitive matching
- Support for overlapping pattern matches

## Installation

### Prerequisites

- Rust (latest stable)
- Python 3.13
- uv
- just

### Building from source

```bash
# Clone repository
git clone https://github.com/trustshield/voluta.git && cd voluta

# Setup environment
uv venv
source .venv/bin/activate
uv sync --dev

# Build
just build

# Test
just test
```

### Installing the wheel

After building, you can install the wheel in another project:

```bash
# The wheel file will be in target/wheels/
pip install /path/to/voluta/target/wheels/voluta-*.whl

# Alternatively, install directly from GitHub
pip install git+https://github.com/trustshield/voluta.git
```

## Usage

### Basic usage

```python
import voluta

# Create a TextMatcher with patterns to search for
# Case insensitivity and overlapping matching are enabled by default
matcher = voluta.TextMatcher(["error", "warning", "critical"])

# Match patterns in a file (line-by-line)
# Returns (line_num, start_pos, end_pos, pattern)
matches = matcher.match_file("path/to/large.log")
for line_num, start, end, pattern in matches:
    print(f"Found '{pattern}' on line {line_num}, positions {start}-{end}")

# Using memory-mapped matching (faster for large files)
# Returns (byte_offset, end_offset, pattern)
matches = matcher.match_file_memmap("path/to/large.log", None)  # use default chunk size
for start, end, pattern in matches:
    print(f"Found '{pattern}' at byte positions {start}-{end}")

# Using parallel memory-mapped matching (maximum performance)
matches = matcher.match_file_memmap_parallel("path/to/large.log", None, None)
```

### Advanced usage

```python
# Specify chunk size (in bytes)
chunk_size = 8 * 1024 * 1024  # 8MB
matches = matcher.match_file_memmap("path/to/large.log", chunk_size)

# Specify chunk size and number of threads
chunk_size = 4 * 1024 * 1024  # 4MB
n_threads = 8
matches = matcher.match_file_memmap_parallel("path/to/large.log", chunk_size, n_threads)

# Direct byte matching for maximum performance
with open("path/to/large.log", "rb") as f:
    content = f.read()  # Or load bytes from any source
    matches = matcher.match_bytes(content)
    for start, end, pattern in matches:
        print(f"Found '{pattern}' at positions {start}-{end}")

# Simple example of finding specific text patterns
text = "The fox jumped over the fence. The fox is quick."
matcher = voluta.TextMatcher(["fox", "jump", "quick"])
matches = matcher.match_bytes(text.encode())
for start, end, pattern in matches:
    context = text[max(0, start-5):min(len(text), end+5)]
    print(f"Found '{pattern}' at {start}-{end}: '...{context}...'")

# Finding overlapping patterns
text = "abcdefgh"
# Overlapping matches are enabled by default to find all possible matches
matcher = voluta.TextMatcher(["abcd", "bcde", "cdef"])
matches = matcher.match_bytes(text.encode())
for start, end, pattern in matches:
    print(f"Found '{pattern}' at {start}-{end}")
    
# Disable overlapping matches if needed
matcher = voluta.TextMatcher(["abcd", "bcde", "cdef"], overlapping=False)

# Case sensitivity control
text = "Hello WORLD"
# By default, case insensitivity is enabled
matcher = voluta.TextMatcher(["hello", "world"])  # Will match both Hello and WORLD
# Disable case insensitivity if needed
matcher = voluta.TextMatcher(["hello", "world"], case_insensitive=False)  # Will only match exact case
```

## Performance

The memory-mapped approach is significantly faster than line-by-line processing, especially for large files.
For optimal performance:

- Use `match_file_memmap_parallel` for multi-core systems
- For maximum control and performance, use `match_bytes` with pre-loaded content
- Test different chunk sizes for your specific hardware (typically 4-16MB works well)
- For files under 100MB, the performance difference may be less noticeable
- Note that enabling overlapping matches may impact performance

## Thanks

This library is a wrapper of [BurntSushi/aho-corasick](https://github.com/BurntSushi/aho-corasick).

## License

MIT