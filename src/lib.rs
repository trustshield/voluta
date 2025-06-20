use aho_corasick::{AhoCorasick, AhoCorasickBuilder, AhoCorasickKind, PatternID};
use memmap2::Mmap;
use pyo3::prelude::*;
use rayon::prelude::*;
use std::cmp;
use std::collections::HashSet;
use std::fs::File;
use std::io::{BufRead, BufReader, Read, Result};
use std::path::Path;

#[pyclass]
pub struct TextMatcher {
    patterns: Vec<String>,
    ac: AhoCorasick,
    max_pattern_len: usize,
    #[pyo3(get)]
    overlapping: bool,
    #[pyo3(get)]
    case_insensitive: bool,
    #[pyo3(get)]
    whole_word: bool,
}

#[pymethods]
impl TextMatcher {
    #[new]
    #[pyo3(signature = (patterns, overlapping=None, case_insensitive=None, whole_word=None))]
    pub fn new(
        patterns: Vec<String>,
        overlapping: Option<bool>,
        case_insensitive: Option<bool>,
        whole_word: Option<bool>,
    ) -> PyResult<Self> {
        // Filter out empty patterns
        let filtered_patterns: Vec<String> =
            patterns.into_iter().filter(|p| !p.is_empty()).collect();

        // Check if we have any patterns left after filtering
        if filtered_patterns.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Pattern set cannot be empty",
            ));
        }

        // Calculate the maximum pattern length for overlap handling
        let max_pattern_len = filtered_patterns.iter().map(|p| p.len()).max().unwrap_or(0);

        let overlapping_value = overlapping.unwrap_or(true);
        let case_insensitive_value = case_insensitive.unwrap_or(true);
        let whole_word_value = whole_word.unwrap_or(false);

        let ac = AhoCorasickBuilder::new()
            .kind(Some(AhoCorasickKind::DFA))
            .ascii_case_insensitive(case_insensitive_value)
            .build(&filtered_patterns)
            .unwrap();

        Ok(Self {
            patterns: filtered_patterns,
            ac,
            max_pattern_len,
            overlapping: overlapping_value,
            case_insensitive: case_insensitive_value,
            whole_word: whole_word_value,
        })
    }

    pub fn match_file(&self, path: String) -> PyResult<Vec<(usize, usize, usize, String)>> {
        match self.match_file_impl(&path) {
            Ok(res) => Ok(res),
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
        }
    }

    /// Faster file matching using memory mapping for large files
    /// Returns a list of (byte_offset, start_index, end_index, matched_pattern) tuples
    #[pyo3(signature = (path, chunk_size=None))]
    pub fn match_file_memmap(
        &self,
        path: String,
        chunk_size: Option<usize>,
    ) -> PyResult<Vec<(usize, usize, String)>> {
        match self.match_file_memmap_impl(&path, chunk_size.unwrap_or(8 * 1024 * 1024)) {
            Ok(res) => {
                // Convert the internal pattern indices to actual pattern strings only at the end
                let string_matches = res
                    .into_iter()
                    .map(|(start, end, pattern_idx)| {
                        (start, end, self.patterns[pattern_idx.as_usize()].clone())
                    })
                    .collect();
                Ok(string_matches)
            }
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
        }
    }

    /// Parallel matching of large files with memory mapping
    /// Splits the file into chunks and processes them in parallel
    #[pyo3(signature = (path, chunk_size=None, n_threads=None))]
    pub fn match_file_memmap_parallel(
        &self,
        path: String,
        chunk_size: Option<usize>,
        n_threads: Option<usize>,
    ) -> PyResult<Vec<(usize, usize, String)>> {
        match self.match_file_memmap_parallel_impl(
            &path,
            chunk_size.unwrap_or(8 * 1024 * 1024),
            n_threads,
        ) {
            Ok(res) => {
                // Convert the internal pattern indices to actual pattern strings only at the end
                let string_matches = res
                    .into_iter()
                    .map(|(start, end, pattern_idx)| {
                        (start, end, self.patterns[pattern_idx.as_usize()].clone())
                    })
                    .collect();
                Ok(string_matches)
            }
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
        }
    }

    /// Raw byte matching on provided byte data
    /// This allows for maximum performance by avoiding file I/O overhead
    /// The caller is responsible for loading the bytes
    /// Returns a list of (start_index, end_index, matched_pattern) tuples
    pub fn match_bytes(&self, data: &[u8]) -> Vec<(usize, usize, String)> {
        let mut matches = Vec::new();

        if self.overlapping {
            // Use the overlapping iterator
            for mat in self.ac.find_overlapping_iter(data) {
                let pattern_idx = mat.pattern();
                let start_idx = mat.start();
                let end_idx = mat.end();

                // Check word boundary if whole_word is enabled
                if self.is_word_boundary_match(data, start_idx, end_idx) {
                    matches.push((
                        start_idx,
                        end_idx,
                        self.patterns[pattern_idx.as_usize()].clone(),
                    ));
                }
            }
        } else {
            // Use the standard iterator
            for mat in self.ac.find_iter(data) {
                let pattern_idx = mat.pattern();
                let start_idx = mat.start();
                let end_idx = mat.end();

                // Check word boundary if whole_word is enabled
                if self.is_word_boundary_match(data, start_idx, end_idx) {
                    matches.push((
                        start_idx,
                        end_idx,
                        self.patterns[pattern_idx.as_usize()].clone(),
                    ));
                }
            }
        }

        matches
    }

    /// Stream-based file matching that processes the file in chunks
    /// Useful for very large files or when memory efficiency is important
    /// Returns a list of (byte_offset, start_index, end_index, matched_pattern) tuples
    #[pyo3(signature = (path, buffer_size=None))]
    pub fn match_file_stream(
        &self,
        path: String,
        buffer_size: Option<usize>,
    ) -> PyResult<Vec<(usize, usize, String)>> {
        match self.match_file_stream_impl(&path, buffer_size.unwrap_or(8 * 1024 * 1024)) {
            Ok(res) => {
                // Convert the internal pattern indices to actual pattern strings only at the end
                let string_matches = res
                    .into_iter()
                    .map(|(start, end, pattern_idx)| {
                        (start, end, self.patterns[pattern_idx.as_usize()].clone())
                    })
                    .collect();
                Ok(string_matches)
            }
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
        }
    }

    /// Stream-based matching from any Read implementer (files, network streams, etc.)
    /// Returns a list of (byte_offset, start_index, end_index, matched_pattern) tuples
    #[pyo3(signature = (stream, buffer_size=None))]
    pub fn match_stream(
        &self,
        stream: &[u8],
        buffer_size: Option<usize>,
    ) -> PyResult<Vec<(usize, usize, String)>> {
        match self.match_stream_impl(stream, buffer_size.unwrap_or(8 * 1024 * 1024)) {
            Ok(res) => {
                // Convert the internal pattern indices to actual pattern strings only at the end
                let string_matches = res
                    .into_iter()
                    .map(|(start, end, pattern_idx)| {
                        (start, end, self.patterns[pattern_idx.as_usize()].clone())
                    })
                    .collect();
                Ok(string_matches)
            }
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
        }
    }
}

impl TextMatcher {
    /// Check if a character is a word character (alphanumeric or underscore)
    fn is_word_char(c: u8) -> bool {
        c.is_ascii_alphanumeric() || c == b'_'
    }

    /// Check if a match is at word boundaries
    fn is_word_boundary_match(&self, data: &[u8], start: usize, end: usize) -> bool {
        if !self.whole_word {
            return true;
        }

        // Check character before the match
        let before_is_word = if start > 0 {
            Self::is_word_char(data[start - 1])
        } else {
            false // Beginning of text is considered a word boundary
        };

        // Check character after the match
        let after_is_word = if end < data.len() {
            Self::is_word_char(data[end])
        } else {
            false // End of text is considered a word boundary
        };

        // Match is at word boundary if neither before nor after are word characters
        !before_is_word && !after_is_word
    }

    fn match_file_impl(&self, path: &str) -> Result<Vec<(usize, usize, usize, String)>> {
        let f = File::open(Path::new(path))?;
        let mut reader = BufReader::new(f);
        let mut buffer = String::new();
        let mut matches = Vec::new();
        let mut line_number = 0;

        while reader.read_line(&mut buffer)? > 0 {
            line_number += 1;

            if self.overlapping {
                for mat in self.ac.find_overlapping_iter(&buffer) {
                    let pattern_idx = mat.pattern();
                    let start_idx = mat.start();
                    let end_idx = mat.end();

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(buffer.as_bytes(), start_idx, end_idx) {
                        matches.push((
                            line_number,
                            start_idx,
                            end_idx,
                            self.patterns[pattern_idx.as_usize()].clone(),
                        ));
                    }
                }
            } else {
                for mat in self.ac.find_iter(&buffer) {
                    let pattern_idx = mat.pattern();
                    let start_idx = mat.start();
                    let end_idx = mat.end();

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(buffer.as_bytes(), start_idx, end_idx) {
                        matches.push((
                            line_number,
                            start_idx,
                            end_idx,
                            self.patterns[pattern_idx.as_usize()].clone(),
                        ));
                    }
                }
            }

            buffer.clear();
        }

        Ok(matches)
    }

    fn match_file_memmap_impl(
        &self,
        path: &str,
        chunk_size: usize,
    ) -> Result<Vec<(usize, usize, PatternID)>> {
        let file = File::open(path)?;
        let mmap = unsafe { Mmap::map(&file)? };
        let mut matches = Vec::new();
        let total_size = mmap.len();

        // Use a set to deduplicate matches that might be found in overlapping regions
        let mut match_set = HashSet::new();

        // Calculate overlap size based on max pattern length
        // We need to use the max pattern length as overlap to ensure we don't miss any patterns
        let overlap = self.max_pattern_len.saturating_sub(1);

        // Process file in chunks with overlap
        let mut offset = 0;
        while offset < total_size {
            // Calculate the end of this chunk (including overlap)
            let end = cmp::min(offset + chunk_size + overlap, total_size);

            // Get this chunk (with potential overlap into the next chunk)
            let chunk = &mmap[offset..end];

            // Find all matches in this chunk
            if self.overlapping {
                for mat in self.ac.find_overlapping_iter(chunk) {
                    let pattern_idx = mat.pattern();
                    let start_idx = offset + mat.start();
                    let end_idx = offset + mat.end();

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(&mmap, start_idx, end_idx) {
                        // Insert into set to deduplicate
                        let match_tuple = (start_idx, end_idx, pattern_idx);
                        if match_set.insert(match_tuple) {
                            matches.push(match_tuple);
                        }
                    }
                }
            } else {
                for mat in self.ac.find_iter(chunk) {
                    let pattern_idx = mat.pattern();
                    let start_idx = offset + mat.start();
                    let end_idx = offset + mat.end();

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(&mmap, start_idx, end_idx) {
                        // Insert into set to deduplicate
                        let match_tuple = (start_idx, end_idx, pattern_idx);
                        if match_set.insert(match_tuple) {
                            matches.push(match_tuple);
                        }
                    }
                }
            }

            // Move to next chunk (without overlap)
            // We subtract the overlap so the next chunk will include the overlapped region
            offset = if end >= total_size {
                // If we've reached the end of the file
                total_size
            } else {
                // Otherwise, move by chunk_size (not chunk_size + overlap)
                offset + chunk_size
            };
        }

        Ok(matches)
    }

    fn match_file_memmap_parallel_impl(
        &self,
        path: &str,
        chunk_size: usize,
        n_threads: Option<usize>,
    ) -> Result<Vec<(usize, usize, PatternID)>> {
        // Configure thread pool if specified
        if let Some(threads) = n_threads {
            rayon::ThreadPoolBuilder::new()
                .num_threads(threads)
                .build_global()
                .unwrap_or(());
        }

        let file = File::open(path)?;
        let mmap = unsafe { Mmap::map(&file)? };
        let total_size = mmap.len();

        // Calculate overlap size based on max pattern length
        let overlap = self.max_pattern_len.saturating_sub(1);

        // Calculate chunks with overlap
        let mut chunks = Vec::new();
        let mut offset = 0;
        while offset < total_size {
            let end = cmp::min(offset + chunk_size + overlap, total_size);
            chunks.push((offset, end));

            // Move by chunk_size, not including the overlap
            offset = if end >= total_size {
                total_size
            } else {
                offset + chunk_size
            };
        }

        // Get references to instance fields for the closure
        let ac = &self.ac;
        let overlapping = self.overlapping;
        let whole_word = self.whole_word;

        // Process chunks in parallel and collect all matches with per-thread deduplication
        // Each thread returns a pre-deduplicated set of matches, which reduces the final deduplication work
        let thread_local_results: Vec<HashSet<(usize, usize, PatternID)>> = chunks
            .par_iter()
            .map(|(start, end)| {
                let chunk = &mmap[*start..*end];
                let mut local_match_set = HashSet::new();

                if overlapping {
                    for mat in ac.find_overlapping_iter(chunk) {
                        let pattern_idx = mat.pattern();
                        let start_idx = start + mat.start();
                        let end_idx = start + mat.end();

                        // Check word boundary if whole_word is enabled
                        let is_word_match = if whole_word {
                            // Check character before the match
                            let before_is_word = if start_idx > 0 {
                                Self::is_word_char(mmap[start_idx - 1])
                            } else {
                                false
                            };

                            // Check character after the match
                            let after_is_word = if end_idx < mmap.len() {
                                Self::is_word_char(mmap[end_idx])
                            } else {
                                false
                            };

                            !before_is_word && !after_is_word
                        } else {
                            true
                        };

                        if is_word_match {
                            local_match_set.insert((start_idx, end_idx, pattern_idx));
                        }
                    }
                } else {
                    for mat in ac.find_iter(chunk) {
                        let pattern_idx = mat.pattern();
                        let start_idx = start + mat.start();
                        let end_idx = start + mat.end();

                        // Check word boundary if whole_word is enabled
                        let is_word_match = if whole_word {
                            // Check character before the match
                            let before_is_word = if start_idx > 0 {
                                Self::is_word_char(mmap[start_idx - 1])
                            } else {
                                false
                            };

                            // Check character after the match
                            let after_is_word = if end_idx < mmap.len() {
                                Self::is_word_char(mmap[end_idx])
                            } else {
                                false
                            };

                            !before_is_word && !after_is_word
                        } else {
                            true
                        };

                        if is_word_match {
                            local_match_set.insert((start_idx, end_idx, pattern_idx));
                        }
                    }
                }

                local_match_set
            })
            .collect();

        // Merge all thread-local HashSets into a single result
        let estimated_total_capacity = thread_local_results.iter().map(|set| set.len()).sum();

        let mut final_result_set = HashSet::with_capacity(estimated_total_capacity);

        // Fast path: if we only have one thread-local result, just convert it directly
        if thread_local_results.len() == 1 {
            final_result_set = thread_local_results.into_iter().next().unwrap();
        } else {
            // Merge all thread-local results
            for local_set in thread_local_results {
                final_result_set.extend(local_set);
            }
        }

        let unique_matches = final_result_set.into_iter().collect();

        Ok(unique_matches)
    }

    fn match_file_stream_impl(
        &self,
        path: &str,
        buffer_size: usize,
    ) -> Result<Vec<(usize, usize, PatternID)>> {
        let file = File::open(path)?;
        let mut reader = BufReader::with_capacity(buffer_size, file);
        let mut matches = Vec::new();
        let mut offset = 0;
        let mut buffer = vec![0; buffer_size];

        // Use a set to deduplicate matches that might be found in overlapping regions
        let mut match_set = HashSet::new();

        // Calculate overlap size based on max pattern length
        let overlap = self.max_pattern_len.saturating_sub(1);

        // Keep track of the last chunk to handle overlap
        let mut last_chunk = Vec::new();

        loop {
            let bytes_read = reader.read(&mut buffer)?;
            if bytes_read == 0 {
                break;
            }

            // Process the current chunk
            let chunk = &buffer[..bytes_read];

            // Combine with last chunk's overlap if we have one
            let combined_chunk = if !last_chunk.is_empty() {
                let mut combined = last_chunk.clone();
                combined.extend_from_slice(chunk);
                combined
            } else {
                chunk.to_vec()
            };

            if self.overlapping {
                for mat in self.ac.find_overlapping_iter(&combined_chunk) {
                    let pattern_idx = mat.pattern();
                    let start_idx = offset + mat.start();
                    let end_idx = offset + mat.end();

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(&combined_chunk, mat.start(), mat.end()) {
                        // Insert into set to deduplicate
                        let match_tuple = (start_idx, end_idx, pattern_idx);
                        if match_set.insert(match_tuple) {
                            matches.push(match_tuple);
                        }
                    }
                }
            } else {
                for mat in self.ac.find_iter(&combined_chunk) {
                    let pattern_idx = mat.pattern();
                    let start_idx = offset + mat.start();
                    let end_idx = offset + mat.end();

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(&combined_chunk, mat.start(), mat.end()) {
                        // Insert into set to deduplicate
                        let match_tuple = (start_idx, end_idx, pattern_idx);
                        if match_set.insert(match_tuple) {
                            matches.push(match_tuple);
                        }
                    }
                }
            }

            // Store the overlap for the next iteration
            if bytes_read > overlap {
                last_chunk = chunk[bytes_read - overlap..].to_vec();
            } else {
                last_chunk = chunk.to_vec();
            }

            // Move the offset for the next chunk
            offset += bytes_read;
        }

        Ok(matches)
    }

    fn match_stream_impl(
        &self,
        data: &[u8],
        buffer_size: usize,
    ) -> Result<Vec<(usize, usize, PatternID)>> {
        let mut matches = Vec::new();
        let mut offset = 0;

        // Use a set to deduplicate matches
        let mut match_set = HashSet::new();

        // Calculate overlap size based on max pattern length
        let overlap = self.max_pattern_len.saturating_sub(1);

        // Process data in chunks with overlap
        for chunk in data.chunks(buffer_size) {
            // For overlapping patterns, we need to look at the current chunk plus the overlap
            let search_window = if offset > 0 && chunk.len() > overlap {
                &data[offset - overlap..offset + chunk.len()]
            } else {
                chunk
            };

            if self.overlapping {
                for mat in self.ac.find_overlapping_iter(search_window) {
                    let pattern_idx = mat.pattern();
                    let start_idx = if offset > 0 && chunk.len() > overlap {
                        offset - overlap + mat.start()
                    } else {
                        offset + mat.start()
                    };
                    let end_idx = if offset > 0 && chunk.len() > overlap {
                        offset - overlap + mat.end()
                    } else {
                        offset + mat.end()
                    };

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(data, start_idx, end_idx) {
                        // Insert into set to deduplicate
                        let match_tuple = (start_idx, end_idx, pattern_idx);
                        if match_set.insert(match_tuple) {
                            matches.push(match_tuple);
                        }
                    }
                }
            } else {
                for mat in self.ac.find_iter(search_window) {
                    let pattern_idx = mat.pattern();
                    let start_idx = if offset > 0 && chunk.len() > overlap {
                        offset - overlap + mat.start()
                    } else {
                        offset + mat.start()
                    };
                    let end_idx = if offset > 0 && chunk.len() > overlap {
                        offset - overlap + mat.end()
                    } else {
                        offset + mat.end()
                    };

                    // Check word boundary if whole_word is enabled
                    if self.is_word_boundary_match(data, start_idx, end_idx) {
                        // Insert into set to deduplicate
                        let match_tuple = (start_idx, end_idx, pattern_idx);
                        if match_set.insert(match_tuple) {
                            matches.push(match_tuple);
                        }
                    }
                }
            }

            offset += chunk.len();
        }

        Ok(matches)
    }
}

#[pymodule]
fn voluta(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TextMatcher>()?;
    Ok(())
}
