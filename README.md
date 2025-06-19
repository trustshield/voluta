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

## Using in your project

```bash
pip install voluta
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

### Whole word matching

The whole word matching feature allows you to find patterns only when they appear as complete words, not as substrings within other words. This is particularly useful for finding specific terms, identifiers, or keywords without false positives.

#### What are Word Boundaries?

Word characters are defined as: `[a-zA-Z0-9_]` (letters, digits, and underscores)

Word boundaries occur at:
- Start/end of text
- Between word and non-word characters  
- Punctuation marks: `. , ; : ! ? ( ) [ ] { } ' "`
- Whitespace: spaces, tabs, newlines
- Special characters: `@ # $ % ^ & * + - = | \ / ~ <>`

#### Basic Example

```python
from voluta import TextMatcher

# Without whole word matching (default behavior)
patterns = ["cat", "test"]
matcher = TextMatcher(patterns, whole_word=False)
data = b"The cat in the scatter test and testing"
matches = matcher.match_bytes(data)
# Finds: "cat" (2 times: in "cat" and "scatter"), "test" (2 times: in "test" and "testing")

# With whole word matching
matcher_word = TextMatcher(patterns, whole_word=True)  
matches_word = matcher_word.match_bytes(data)
# Finds: "cat" (1 time: only the standalone word), "test" (1 time: only the standalone word)
```

#### Programming Use Cases

**Finding function names without false positives:**

```python
patterns = ["malloc", "free", "printf"]
matcher = TextMatcher(patterns, whole_word=True, case_insensitive=False)

code = b"""
void* malloc(size_t size);
char* smalloc_wrapper();  // won't match "malloc"
free(ptr);
printf("Hello");
sprintf(buf, "test");     // won't match "printf"
"""

matches = matcher.match_bytes(code)
# Only finds actual function calls: "malloc", "free", "printf"
```

**Variable name detection:**

```python
patterns = ["user", "config", "data"]
matcher = TextMatcher(patterns, whole_word=True)

code = b"""
user = get_user()         # ✓ matches "user"
user_name = "john"        # ✗ doesn't match (connected by underscore)
configure_data()          # ✗ doesn't match ("config" inside "configure")
process(data)             # ✓ matches "data"
"""
```

#### Natural Language Processing

**Stopword detection:**

```python
stopwords = ["the", "and", "or", "in", "on", "at"]
matcher = TextMatcher(stopwords, whole_word=True, case_insensitive=True)

text = b"The cat and dog are in the garden"
matches = matcher.match_bytes(text)
# Correctly identifies: "The", "and", "are", "in", "the"
# Won't match "the" inside words like "gather" or "other"
```

#### Special Character Handling

**API/technical terms:**

```python
patterns = ["API", "URL", "HTTP"]
matcher = TextMatcher(patterns, whole_word=True)

# These WILL match (special characters create boundaries):
text1 = b"REST API endpoints"          # ✓ "API"
text2 = b"The API-URL mapping"         # ✓ "API" and "URL" 
text3 = b"HTTP/1.1 protocol"          # ✓ "HTTP"
text4 = b"Check API() function"        # ✓ "API"

# These will NOT match (connected by word characters):
text5 = b"RAPID development"           # ✗ "API" inside "RAPID"
text6 = b"The API_VERSION constant"    # ✗ "API" connected by underscore
```

#### Email/Domain matching

```python
patterns = ["com", "org", "net"]
matcher = TextMatcher(patterns, whole_word=True, case_insensitive=True)

text = b"Visit example.com or contact@university.org for info"
matches = matcher.match_bytes(text)
# Finds: "com", "org" as complete domain extensions
# Won't match "com" inside words like "complete" or "common"
```

#### Performance Considerations

Whole word matching adds a small overhead as it checks character boundaries for each match. For maximum performance on large datasets where you don't need word boundaries, keep the default `whole_word=False`.

```python
# Fastest (no boundary checking)
matcher = TextMatcher(patterns, whole_word=False)

# Slightly slower but more precise
matcher = TextMatcher(patterns, whole_word=True)
```

#### Combining with Other Options

Whole word matching works seamlessly with other TextMatcher features:

```python
# Case-insensitive whole word matching
matcher = TextMatcher(
    patterns=["Error", "Warning", "Info"],
    whole_word=True,
    case_insensitive=True,     # Matches "ERROR", "error", "Error"
    overlapping=True
)

# Find overlapping whole words
patterns = ["test", "testing", "est"]
matcher = TextMatcher(patterns, whole_word=True, overlapping=True)
text = b"The test and testing phase includes est methods"
# Finds all three as separate whole words
```



## Installation

### Prerequisites

- Rust (latest stable)
- Python 3.12
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

## Performance

The memory-mapped approach is significantly faster than line-by-line processing, especially for large files.
For optimal performance:

- Use `match_file_memmap_parallel` for multi-core systems
- For maximum control and performance, use `match_bytes` with pre-loaded content
- Test different chunk sizes for your specific hardware (typically 4-16MB works well)
- For files under 100MB, the performance difference may be less noticeable
- Note that enabling overlapping matches may impact performance

### Metrics

On a MacBook Pro M1 Pro with 16GB RAM:

```bash
% just stress 1 50 32 8
python tests/benchmark/stress.py --size 1 --patterns 50 --chunk 32 --threads 8
Generating 50 random search patterns...
Generating 1.0GB test file with 50 search patterns...
Progress: 100% complete
Created test file at /var/folders/65/6343wbc565jcmgj3mpvktl880000gp/T/tmpl0uwzhss.txt, size: 1.00GB
Inserted 1024247 pattern instances

Running stress test with 50 patterns:
  - File size: 1.00GB
  - Chunk size: 32MB
  - Threads: 8

Testing memory-mapped matching...
Memory-mapped matching: 1107062 matches in 4.59 seconds
Processing speed: 223.13MB/s

Testing parallel memory-mapped matching...
Parallel memory-mapped matching: 1107062 matches in 0.63 seconds
Processing speed: 1629.94MB/s

Parallel processing is 7.30x faster than single-threaded

Sample matches:
  • 'b37lBbWUl4u' found at byte positions 790320349-790320360
  • 'OsoI' found at byte positions 619636284-619636288
  • 'KGcWelcw6Awl7d4' found at byte positions 952973106-952973121
  • 'YlvzcXcF' found at byte positions 481316276-481316284
  • 'BvK' found at byte positions 909977231-909977234

Stress test completed successfully!

Cleaning up temporary test file: /var/folders/65/6343wbc565jcmgj3mpvktl880000gp/T/tmpl0uwzhss.txt
```

## Thanks

This library is a wrapper of [BurntSushi/aho-corasick](https://github.com/BurntSushi/aho-corasick).

## License

MIT
