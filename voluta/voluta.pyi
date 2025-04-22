from typing import List, Tuple, Optional

class TextMatcher:
    """A high-performance text pattern matcher using Aho-Corasick algorithm."""

    overlapping: bool
    """Whether to find overlapping matches."""

    case_insensitive: bool
    """Whether the pattern matching is case insensitive."""

    def __init__(
        self,
        patterns: List[str],
        overlapping: Optional[bool] = True,
        case_insensitive: Optional[bool] = True,
    ) -> None:
        """
        Create a new TextMatcher instance.

        Args:
            patterns: List of string patterns to match
            overlapping: Whether to find overlapping matches (default: True)
            case_insensitive: Whether the pattern matching is case insensitive (default: True)

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
