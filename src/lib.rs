use std::fs::File;
use std::io::{BufReader, BufRead, Result};
use std::path::Path;
use pyo3::prelude::*;
use aho_corasick::{AhoCorasick, AhoCorasickBuilder, AhoCorasickKind, PatternID};
use memmap2::Mmap;
use std::cmp;
use rayon::prelude::*;
use std::collections::HashSet;

#[pyclass]
pub struct TextMatcher {
    patterns: Vec<String>,
    ac: AhoCorasick,
    max_pattern_len: usize,
    #[pyo3(get)]
    overlapping: bool,
    #[pyo3(get)]
    case_insensitive: bool,
}

#[pymethods]
impl TextMatcher {
    #[new]
    #[pyo3(signature = (patterns, overlapping=None, case_insensitive=None))]
    pub fn new(patterns: Vec<String>, overlapping: Option<bool>, case_insensitive: Option<bool>) -> PyResult<Self> {
        // Filter out empty patterns
        let filtered_patterns: Vec<String> = patterns.into_iter()
            .filter(|p| !p.is_empty())
            .collect();
            
        // Check if we have any patterns left after filtering
        if filtered_patterns.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err("Pattern set cannot be empty"));
        }
        
        // Calculate the maximum pattern length for overlap handling
        let max_pattern_len = filtered_patterns.iter()
            .map(|p| p.len())
            .max()
            .unwrap_or(0);
            
        let overlapping_value = overlapping.unwrap_or(true);
        let case_insensitive_value = case_insensitive.unwrap_or(true);
        
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
    pub fn match_file_memmap(&self, path: String, chunk_size: Option<usize>) -> PyResult<Vec<(usize, usize, String)>> {
        match self.match_file_memmap_impl(&path, chunk_size.unwrap_or(8 * 1024 * 1024)) {
            Ok(res) => {
                // Convert the internal pattern indices to actual pattern strings only at the end
                let string_matches = res.into_iter()
                    .map(|(start, end, pattern_idx)| (start, end, self.patterns[pattern_idx.as_usize()].clone()))
                    .collect();
                Ok(string_matches)
            },
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
        }
    }

    /// Parallel matching of large files with memory mapping
    /// Splits the file into chunks and processes them in parallel
    pub fn match_file_memmap_parallel(&self, path: String, chunk_size: Option<usize>, n_threads: Option<usize>) -> PyResult<Vec<(usize, usize, String)>> {
        match self.match_file_memmap_parallel_impl(&path, chunk_size.unwrap_or(8 * 1024 * 1024), n_threads) {
            Ok(res) => {
                // Convert the internal pattern indices to actual pattern strings only at the end
                let string_matches = res.into_iter()
                    .map(|(start, end, pattern_idx)| (start, end, self.patterns[pattern_idx.as_usize()].clone()))
                    .collect();
                Ok(string_matches)
            },
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
                matches.push((start_idx, end_idx, self.patterns[pattern_idx.as_usize()].clone()));
            }
        } else {
            // Use the standard iterator
            for mat in self.ac.find_iter(data) {
                let pattern_idx = mat.pattern();
                let start_idx = mat.start();
                let end_idx = mat.end();
                matches.push((start_idx, end_idx, self.patterns[pattern_idx.as_usize()].clone()));
            }
        }
        
        matches
    }
}

impl TextMatcher {
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
                    matches.push((line_number, start_idx, end_idx, self.patterns[pattern_idx.as_usize()].clone()));
                }
            } else {
                for mat in self.ac.find_iter(&buffer) {
                    let pattern_idx = mat.pattern();
                    let start_idx = mat.start();
                    let end_idx = mat.end();
                    matches.push((line_number, start_idx, end_idx, self.patterns[pattern_idx.as_usize()].clone()));
                }
            }
            
            buffer.clear();
        }

        Ok(matches)
    }

    fn match_file_memmap_impl(&self, path: &str, chunk_size: usize) -> Result<Vec<(usize, usize, PatternID)>> {
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
                    
                    // Insert into set to deduplicate
                    let match_tuple = (start_idx, end_idx, pattern_idx);
                    if match_set.insert(match_tuple) {
                        matches.push(match_tuple);
                    }
                }
            } else {
                for mat in self.ac.find_iter(chunk) {
                    let pattern_idx = mat.pattern();
                    let start_idx = offset + mat.start();
                    let end_idx = offset + mat.end();
                    
                    // Insert into set to deduplicate
                    let match_tuple = (start_idx, end_idx, pattern_idx);
                    if match_set.insert(match_tuple) {
                        matches.push(match_tuple);
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
    
    fn match_file_memmap_parallel_impl(&self, path: &str, chunk_size: usize, n_threads: Option<usize>) -> Result<Vec<(usize, usize, PatternID)>> {
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
        
        // Process chunks in parallel and collect all matches with per-thread deduplication
        // Each thread returns a pre-deduplicated set of matches, which reduces the final deduplication work
        let thread_local_results: Vec<HashSet<(usize, usize, PatternID)>> = chunks.par_iter()
            .map(|(start, end)| {
                let chunk = &mmap[*start..*end];
                let mut local_match_set = HashSet::new();
                
                if overlapping {
                    for mat in ac.find_overlapping_iter(chunk) {
                        let pattern_idx = mat.pattern();
                        let start_idx = start + mat.start();
                        let end_idx = start + mat.end();
                        
                        local_match_set.insert((start_idx, end_idx, pattern_idx));
                    }
                } else {
                    for mat in ac.find_iter(chunk) {
                        let pattern_idx = mat.pattern();
                        let start_idx = start + mat.start();
                        let end_idx = start + mat.end();
                        
                        local_match_set.insert((start_idx, end_idx, pattern_idx));
                    }
                }
                
                local_match_set
            })
            .collect();
            
        // Merge all thread-local HashSets into a single result
        let estimated_total_capacity = thread_local_results.iter()
            .map(|set| set.len())
            .sum();
            
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
}

#[pymodule]
fn voluta(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TextMatcher>()?;
    Ok(())
}
