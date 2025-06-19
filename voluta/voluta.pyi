from typing import List, Optional, Tuple

class TextMatcher:
    """A high-performance text pattern matcher using Aho-Corasick algorithm."""

    overlapping: bool
    """Whether to find overlapping matches."""

    case_insensitive: bool
    """Whether the pattern matching is case insensitive."""

    whole_word: bool
    """Whether to match only whole words at word boundaries."""

    def __init__(
        self,
        patterns: List[str],
        overlapping: Optional[bool] = True,
        case_insensitive: Optional[bool] = True,
        whole_word: Optional[bool] = False,
    ) -> None:
        """
        Create a new TextMatcher instance.

        Args:
            patterns: List of string patterns to match
            overlapping: Whether to find overlapping matches (default: True)
            case_insensitive: Whether the pattern matching is case insensitive (default: True)
            whole_word: Whether to match only whole words at word boundaries (default: False)

        Raises:
            ValueError: If pattern set is empty after filtering
        """
        ...

    def match_file(self, path: str) -> List[Tuple[int, int, int, str]]:
        """
        Match patterns in a file.

        Args:
            path: Path to the file to match

        Returns:
            List of (line_number, start_idx, end_idx, matched_pattern) tuples

        Raises:
            IOError: If the file cannot be read
        """
        ...

    def match_file_memmap(
        self, path: str, chunk_size: Optional[int] = None
    ) -> List[Tuple[int, int, str]]:
        """
        Faster file matching using memory mapping for large files.

        Args:
            path: Path to the file to match
            chunk_size: Size of chunks to process (default: 8MB)

        Returns:
            List of (byte_offset, start_index, matched_pattern) tuples

        Raises:
            IOError: If the file cannot be read
        """
        ...

    def match_file_memmap_parallel(
        self,
        path: str,
        chunk_size: Optional[int] = None,
        n_threads: Optional[int] = None,
    ) -> List[Tuple[int, int, str]]:
        """
        Parallel matching of large files with memory mapping.
        Splits the file into chunks and processes them in parallel.

        Args:
            path: Path to the file to match
            chunk_size: Size of chunks to process (default: 8MB)
            n_threads: Number of threads to use (default: automatic)

        Returns:
            List of (byte_offset, start_index, matched_pattern) tuples

        Raises:
            IOError: If the file cannot be read
        """
        ...

    def match_bytes(self, data: bytes) -> List[Tuple[int, int, str]]:
        """
        Raw byte matching on provided byte data.
        This allows for maximum performance by avoiding file I/O overhead.

        Args:
            data: Bytes to match against

        Returns:
            List of (start_index, end_index, matched_pattern) tuples
        """
        ...

    def match_file_stream(
        self, path: str, buffer_size: Optional[int] = None
    ) -> List[Tuple[int, int, str]]:
        """
        Stream-based file matching that processes the file in chunks.
        Useful for very large files or when memory efficiency is important.

        Args:
            path: Path to the file to match
            buffer_size: Size of the buffer to use for streaming (default: 8MB)

        Returns:
            List of (byte_offset, start_index, matched_pattern) tuples

        Raises:
            IOError: If the file cannot be read
        """
        ...

    def match_stream(
        self, stream: bytes, buffer_size: Optional[int] = None
    ) -> List[Tuple[int, int, str]]:
        """
        Stream-based matching from any byte data source.
        Useful for processing data from network streams, memory buffers, etc.

        Args:
            stream: Bytes to match against
            buffer_size: Size of chunks to process (default: 8MB)

        Returns:
            List of (start_index, end_index, matched_pattern) tuples

        Raises:
            IOError: If there is an error processing the stream
        """
        ...
