#!/usr/bin/env python3
"""Citation Pattern Normalizer Workflow"""

import os
import re
import yaml
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict
from datetime import datetime

from ..shared_modules.exceptions import ProcessingError
from ..status_management_yaml.status_manager import StatusManager


class CitationPatternNormalizerWorkflow:
    """Workflow for normalizing citation patterns across different publishers."""
    
    def __init__(self, config_manager, logger):
        """Initialize Citation Pattern Normalizer Workflow.
        
        Args:
            config_manager: Configuration manager instance
            logger: Logger instance or IntegratedLogger instance
        """
        self.config = config_manager
        # Handle both IntegratedLogger instances and regular logger instances
        if hasattr(logger, 'get_logger'):
            self.logger = logger.get_logger('citation_pattern_normalizer')
        else:
            self.logger = logger
        self.status_manager = StatusManager(config_manager, logger)
        
        # Load publisher patterns configuration
        self.publisher_parsers = self._load_publisher_parsers()
        
        # Get configuration
        self.enabled = self.config.config.get('citation_pattern_normalizer', {}).get('enabled', True)
        self.batch_size = self.config.config.get('citation_pattern_normalizer', {}).get('batch_size', 20)
        self.retry_attempts = self.config.config.get('citation_pattern_normalizer', {}).get('retry_attempts', 3)
        
        # Publisher detection settings
        detection_config = self.config.config.get('citation_pattern_normalizer', {}).get('publisher_detection', {})
        self.auto_detect = detection_config.get('auto_detect', True)
        self.fallback_parser = detection_config.get('fallback_parser', 'generic')
        
        # Notification settings
        notification_config = self.config.config.get('citation_pattern_normalizer', {}).get('notification', {})
        self.unsupported_pattern_alert = notification_config.get('unsupported_pattern_alert', True)
        self.new_parser_suggestion = notification_config.get('new_parser_suggestion', True)
        
        self.logger.info(f"CitationPatternNormalizerWorkflow initialized with {len(self.publisher_parsers)} parsers")
    
    def _load_publisher_parsers(self) -> Dict[str, Any]:
        """Load publisher patterns from configuration file.
        
        Returns:
            Dict containing publisher parser configurations
        """
        try:
            # Get the project root directory more reliably
            current_dir = os.path.dirname(__file__)
            project_root = current_dir
            # Navigate up to find the project root (where config directory is located)
            while not os.path.exists(os.path.join(project_root, 'config')) and project_root != '/':
                project_root = os.path.dirname(project_root)
            
            patterns_file = os.path.join(project_root, 'config', 'publisher_patterns.yaml')
            
            if not os.path.exists(patterns_file):
                self.logger.warning(f"Publisher patterns file not found: {patterns_file}")
                return {}
            
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns_data = yaml.safe_load(f)
            
            return patterns_data.get('parsers', {})
        
        except Exception as e:
            self.logger.error(f"Failed to load publisher patterns: {e}")
            return {}
    
    def process_items(self, input_dir: str, target_items: Optional[List[str]] = None) -> Dict[str, Any]:
        """Process citation pattern normalization for target items.
        
        Args:
            input_dir: Directory containing markdown files
            target_items: List of citation keys to process (None for all)
            
        Returns:
            Dict containing processing results
        """
        if not self.enabled:
            self.logger.info("Citation pattern normalizer is disabled")
            return {"status": "disabled", "processed": 0, "skipped": 0, "failed": 0}
        
        self.logger.info(f"Starting citation pattern normalization in {input_dir}")
        
        processed = 0
        skipped = 0
        failed = 0
        
        try:
            # Get list of markdown files to process
            markdown_files = self._find_markdown_files(input_dir, target_items)
            
            for file_path in markdown_files:
                try:
                    citation_key = os.path.basename(os.path.dirname(file_path))
                    
                    # Check if already processed
                    try:
                        if hasattr(self.status_manager, 'should_skip_processing'):
                            if self.status_manager.should_skip_processing(citation_key, 'citation_pattern_normalizer'):
                                self.logger.info(f"Skipping {citation_key}: already processed")
                                skipped += 1
                                continue
                        else:
                            # Alternative method to check processing status
                            if hasattr(self.status_manager, 'get_processing_status'):
                                status = self.status_manager.get_processing_status(citation_key, 'citation_pattern_normalizer')
                                if status == 'completed':
                                    self.logger.info(f"Skipping {citation_key}: already processed")
                                    skipped += 1
                                    continue
                    except Exception as e:
                        self.logger.debug(f"Status check failed for {citation_key}: {e}, proceeding with processing")
                    
                    # Process the file
                    result = self._process_single_file(file_path, citation_key)
                    
                    if result:
                        processed += 1
                        self.logger.info(f"Successfully normalized citations for {citation_key}")
                    else:
                        failed += 1
                        self.logger.warning(f"Failed to normalize citations for {citation_key}")
                
                except Exception as e:
                    failed += 1
                    self.logger.error(f"Error processing {file_path}: {e}")
            
            self.logger.info(f"Citation pattern normalization completed: {processed} processed, {skipped} skipped, {failed} failed")
            
            return {
                "status": "completed",
                "processed": processed,
                "skipped": skipped,
                "failed": failed
            }
        
        except Exception as e:
            self.logger.error(f"Citation pattern normalization failed: {e}")
            raise ProcessingError(f"Citation pattern normalization failed: {e}")
    
    def _find_markdown_files(self, input_dir: str, target_items: Optional[List[str]] = None) -> List[str]:
        """Find markdown files to process.
        
        Args:
            input_dir: Directory to search for markdown files
            target_items: List of citation keys to process (None for all)
            
        Returns:
            List of markdown file paths
        """
        markdown_files = []
        
        try:
            for root, dirs, files in os.walk(input_dir):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        citation_key = os.path.basename(root)
                        
                        # Filter by target items if specified
                        if target_items is None or citation_key in target_items:
                            markdown_files.append(file_path)
            
            return markdown_files
        
        except Exception as e:
            self.logger.error(f"Error finding markdown files: {e}")
            return []
    
    def _process_single_file(self, file_path: str, citation_key: str) -> bool:
        """Process a single markdown file for citation normalization.
        
        Args:
            file_path: Path to the markdown file
            citation_key: Citation key for the paper
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract YAML header and content
            yaml_header, markdown_content = self._extract_yaml_and_content(content)
            
            # Detect publisher
            publisher = self.detect_publisher(markdown_content, yaml_header)
            
            # Remove links from citations if present
            content_without_links = self._remove_citation_links(markdown_content)
            
            # Normalize citations
            normalized_content, normalization_results = self.normalize_citations(content_without_links, publisher)
            
            # Update YAML header with normalization results
            updated_yaml_header = self._update_yaml_header(yaml_header, publisher, normalization_results)
            
            # Write back the updated content
            updated_content = self._combine_yaml_and_content(updated_yaml_header, normalized_content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            # Update processing status
            try:
                if hasattr(self.status_manager, 'update_processing_status'):
                    self.status_manager.update_processing_status(citation_key, 'citation_pattern_normalizer', 'completed')
                else:
                    self.logger.debug(f"StatusManager does not have update_processing_status method, skipping status update for {citation_key}")
            except Exception as e:
                self.logger.debug(f"Failed to update processing status for {citation_key}: {e}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return False
    
    def _extract_yaml_and_content(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML header and markdown content.
        
        Args:
            content: Full file content
            
        Returns:
            Tuple of (yaml_header_dict, markdown_content)
        """
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            yaml_content = parts[1]
            markdown_content = parts[2]
            try:
                yaml_header = yaml.safe_load(yaml_content) or {}
            except yaml.constructor.ConstructorError as e:
                self.logger.warning(f"YAML parsing error (using unsafe loader): {e}")
                try:
                    # Use unsafe loader for complex YAML with Python objects
                    yaml_header = yaml.load(yaml_content, Loader=yaml.UnsafeLoader) or {}
                except Exception as e2:
                    self.logger.error(f"Failed to parse YAML even with unsafe loader: {e2}")
                    yaml_header = {}
        else:
            yaml_header = {}
            markdown_content = content
        
        return yaml_header, markdown_content
    
    def _combine_yaml_and_content(self, yaml_header: Dict[str, Any], markdown_content: str) -> str:
        """Combine YAML header and markdown content.
        
        Args:
            yaml_header: YAML header dictionary
            markdown_content: Markdown content
            
        Returns:
            Combined content string
        """
        if yaml_header:
            yaml_content = yaml.dump(yaml_header, default_flow_style=False, allow_unicode=True)
            return f"---\n{yaml_content}---\n{markdown_content}"
        else:
            return markdown_content
    
    def detect_publisher(self, content: str, metadata: Dict[str, Any]) -> str:
        """Detect publisher based on content and metadata.
        
        Args:
            content: Markdown content
            metadata: YAML header metadata
            
        Returns:
            Publisher identifier
        """
        # Check if publisher is manually specified in metadata
        if 'publisher' in metadata:
            manual_publisher = metadata['publisher'].lower()
            for parser_name in self.publisher_parsers:
                if parser_name in manual_publisher or manual_publisher in parser_name:
                    self.logger.info(f"Using manually specified publisher: {parser_name}")
                    return parser_name
        
        # Auto-detect publisher if enabled
        if self.auto_detect:
            # Try DOI-based detection
            doi = metadata.get('doi', '')
            if doi:
                for parser_name, parser_config in self.publisher_parsers.items():
                    detection_config = parser_config.get('detection', {})
                    doi_prefixes = detection_config.get('doi_prefixes', [])
                    
                    for prefix in doi_prefixes:
                        if doi.startswith(prefix):
                            self.logger.info(f"Detected publisher from DOI: {parser_name}")
                            return parser_name
            
            # Try journal name-based detection
            title = metadata.get('title', '')
            journal = metadata.get('journal', '')
            
            for parser_name, parser_config in self.publisher_parsers.items():
                detection_config = parser_config.get('detection', {})
                journal_keywords = detection_config.get('journal_keywords', [])
                
                for keyword in journal_keywords:
                    if keyword.lower() in title.lower() or keyword.lower() in journal.lower():
                        self.logger.info(f"Detected publisher from journal: {parser_name}")
                        return parser_name
        
        # Use fallback parser
        self.logger.info(f"Using fallback parser: {self.fallback_parser}")
        return self.fallback_parser
    
    def normalize_citations(self, content: str, publisher: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Normalize citation patterns in content.
        
        Args:
            content: Markdown content
            publisher: Publisher identifier
            
        Returns:
            Tuple of (normalized_content, normalization_results)
        """
        if publisher not in self.publisher_parsers:
            self.logger.warning(f"No parser found for publisher: {publisher}")
            return content, []
        
        parser_config = self.publisher_parsers[publisher]
        patterns = parser_config.get('patterns', [])
        
        normalized_content = content
        normalization_results = []
        
        for pattern_config in patterns:
            regex_pattern = pattern_config.get('regex', '')
            replacement_template = pattern_config.get('replacement', '')
            description = pattern_config.get('description', '')
            
            try:
                # Find all matches
                matches = list(re.finditer(regex_pattern, normalized_content))
                
                for match in reversed(matches):  # Process in reverse to maintain positions
                    original_text = match.group(0)
                    
                    # Create replacement text
                    replacement_text = self._create_replacement_text(match, replacement_template)
                    
                    # Replace in content
                    start_pos = match.start()
                    end_pos = match.end()
                    normalized_content = normalized_content[:start_pos] + replacement_text + normalized_content[end_pos:]
                    
                    # Record normalization
                    normalization_results.append({
                        'original': original_text,
                        'normalized': replacement_text,
                        'position': start_pos,
                        'pattern_description': description
                    })
            
            except re.error as e:
                self.logger.error(f"Invalid regex pattern '{regex_pattern}': {e}")
                continue
        
        # Detect unsupported patterns if enabled
        if self.unsupported_pattern_alert:
            self._detect_unsupported_patterns(content, publisher, normalized_content)
        
        return normalized_content, normalization_results
    
    def _create_replacement_text(self, match: re.Match, template: str) -> str:
        """Create replacement text from regex match and template.
        
        Args:
            match: Regex match object
            template: Replacement template
            
        Returns:
            Replacement text
        """
        # Convert superscript numbers to regular numbers
        superscript_map = {
            '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5',
            '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9', '⁰': '0'
        }
        
        # Get the captured group (first group in parentheses)
        if match.groups():
            matched_text = match.group(1)
        else:
            matched_text = match.group(0)
        
        # Handle different types of citation patterns
        if any(c in superscript_map for c in matched_text):
            # Convert superscript characters to regular numbers
            converted_numbers = []
            prev_was_digit = False
            
            for char in matched_text:
                if char in superscript_map:
                    if prev_was_digit:
                        converted_numbers.append(',')
                    converted_numbers.append(superscript_map[char])
                    prev_was_digit = True
                elif char == ',' or char == ' ':
                    if prev_was_digit:
                        converted_numbers.append(',')
                        prev_was_digit = False
                elif char.isdigit():
                    if prev_was_digit:
                        converted_numbers.append(',')
                    converted_numbers.append(char)
                    prev_was_digit = True
            
            number_string = ''.join(converted_numbers)
        else:
            # For already normal numbers/commas, keep as is
            number_string = matched_text
        
        # Clean up multiple commas and ensure proper formatting
        import re as regex_module
        number_string = regex_module.sub(r',+', ',', number_string)
        number_string = number_string.strip(',')
        
        # Process template
        if '{number}' in template:
            # Single number (remove commas)
            clean_number = number_string.replace(',', '')
            return template.replace('{number}', clean_number)
        
        if '{numbers}' in template:
            # Multiple numbers (preserve commas)
            return template.replace('{numbers}', number_string)
        
        # If already in bracket format, return as is
        if matched_text.startswith('[') and matched_text.endswith(']'):
            return matched_text
        
        # Fallback: wrap in brackets
        return f"[{number_string}]"
    
    def _detect_unsupported_patterns(self, original_content: str, publisher: str, 
                                   normalized_content: str) -> None:
        """Detect unsupported citation patterns and log warnings.
        
        Args:
            original_content: Original markdown content
            publisher: Publisher identifier
            normalized_content: Content after normalization
        """
        # Common citation pattern indicators that might not be handled
        potential_patterns = [
            r'\[[a-zA-Z]+\d+\]',  # [Smith2020] style
            r'\([a-zA-Z]+\s+\d+\)',  # (Smith 2020) style
            r'\([a-zA-Z]+\s+et\s+al\.?\s*,?\s*\d+\)',  # (Smith et al., 2020) style
            r'ref\s*\(\s*\d+\s*\)',  # ref(1) style
            r'reference\s*\[\s*\d+\s*\]',  # reference [1] style
            r'\[\d+\-\d+\]',  # [1-3] range style
            r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+',  # Remaining superscripts
            r'<sup>\d+</sup>',  # HTML superscript
        ]
        
        unsupported_found = []
        
        for pattern in potential_patterns:
            matches = list(re.finditer(pattern, normalized_content))
            if matches:
                for match in matches:
                    unsupported_found.append({
                        'pattern': match.group(0),
                        'position': match.start(),
                        'regex_used': pattern,
                        'context': self._extract_context(normalized_content, match.start(), match.end())
                    })
        
        # Log unsupported patterns
        if unsupported_found:
            self.logger.warning(f"Found {len(unsupported_found)} potentially unsupported citation patterns for publisher '{publisher}':")
            for item in unsupported_found[:5]:  # Log up to 5 examples
                self.logger.warning(f"  Pattern: '{item['pattern']}' at position {item['position']}")
                self.logger.warning(f"  Context: ...{item['context']}...")
            
            if len(unsupported_found) > 5:
                self.logger.warning(f"  ... and {len(unsupported_found) - 5} more patterns")
            
            # Suggest new parser if enabled
            if self.new_parser_suggestion:
                self._suggest_new_parser_patterns(publisher, unsupported_found)
    
    def _extract_context(self, content: str, start: int, end: int, context_length: int = 30) -> str:
        """Extract context around a matched pattern.
        
        Args:
            content: Full content
            start: Start position of match
            end: End position of match
            context_length: Length of context to extract on each side
            
        Returns:
            Context string
        """
        context_start = max(0, start - context_length)
        context_end = min(len(content), end + context_length)
        return content[context_start:context_end]
    
    def _suggest_new_parser_patterns(self, publisher: str, unsupported_patterns: List[Dict[str, Any]]) -> None:
        """Suggest new parser patterns for unsupported citations.
        
        Args:
            publisher: Publisher identifier
            unsupported_patterns: List of unsupported pattern information
        """
        pattern_groups = {}
        
        # Group similar patterns
        for item in unsupported_patterns:
            pattern_type = item['regex_used']
            if pattern_type not in pattern_groups:
                pattern_groups[pattern_type] = []
            pattern_groups[pattern_type].append(item['pattern'])
        
        # Generate suggestions
        suggestions = []
        for pattern_type, examples in pattern_groups.items():
            if len(examples) >= 2:  # Only suggest if pattern appears multiple times
                suggestions.append({
                    'regex_pattern': pattern_type,
                    'examples': examples[:3],  # Up to 3 examples
                    'occurrences': len(examples)
                })
        
        if suggestions:
            self.logger.info(f"Suggested new parser patterns for publisher '{publisher}':")
            for suggestion in suggestions:
                self.logger.info(f"  Pattern: {suggestion['regex_pattern']}")
                self.logger.info(f"  Examples: {', '.join(suggestion['examples'])}")
                self.logger.info(f"  Occurrences: {suggestion['occurrences']}")
        
        # Log to YAML if new parser suggestion is enabled
        if suggestions:
            self._log_unsupported_patterns_to_yaml(publisher, suggestions)
    
    def _log_unsupported_patterns_to_yaml(self, publisher: str, suggestions: List[Dict[str, Any]]) -> None:
        """Log unsupported patterns to YAML file for future parser development.
        
        Args:
            publisher: Publisher identifier
            suggestions: List of pattern suggestions
        """
        try:
            # Create unsupported patterns log file path
            unsupported_log_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'config', 'unsupported_citation_patterns.yaml'
            )
            
            # Load existing data or create new
            unsupported_data = {}
            if os.path.exists(unsupported_log_path):
                with open(unsupported_log_path, 'r', encoding='utf-8') as f:
                    unsupported_data = yaml.safe_load(f) or {}
            
            # Add new suggestions
            if 'unsupported_citation_patterns' not in unsupported_data:
                unsupported_data['unsupported_citation_patterns'] = []
            
            for suggestion in suggestions:
                pattern_entry = {
                    'publisher': publisher,
                    'pattern': suggestion['regex_pattern'],
                    'examples': suggestion['examples'],
                    'occurrences': suggestion['occurrences'],
                    'discovered_at': datetime.now().isoformat(),
                    'suggested_regex': f"\\{suggestion['regex_pattern'].replace('\\', '\\\\')}"
                }
                unsupported_data['unsupported_citation_patterns'].append(pattern_entry)
            
            # Save updated data
            with open(unsupported_log_path, 'w', encoding='utf-8') as f:
                yaml.dump(unsupported_data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Logged {len(suggestions)} unsupported patterns to {unsupported_log_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to log unsupported patterns: {e}")
    
    def _update_yaml_header(self, yaml_header: Dict[str, Any], publisher: str, 
                           normalization_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update YAML header with normalization results.
        
        Args:
            yaml_header: Original YAML header
            publisher: Detected publisher
            normalization_results: Normalization results
            
        Returns:
            Updated YAML header
        """
        # Create citation_normalization section
        citation_normalization = {
            'generated_at': datetime.now().isoformat(),
            'publisher_detected': publisher,
            'parser_used': f"{publisher}_parser",
            'patterns_normalized': normalization_results,
            'total_citations_normalized': len(normalization_results)
        }
        
        # Update YAML header
        updated_header = yaml_header.copy()
        updated_header['citation_normalization'] = citation_normalization
        
        # Update processing status
        processing_status = updated_header.get('processing_status', {})
        processing_status['citation_pattern_normalizer'] = 'completed'
        updated_header['processing_status'] = processing_status
        
        return updated_header
    
    def _remove_citation_links(self, content: str) -> str:
        """Remove hyperlinks from citation patterns.
        
        Args:
            content: Markdown content that may contain linked citations
            
        Returns:
            Content with citation links removed
        """
        # Remove markdown links from citation patterns
        # Pattern: [citation](url) or [citation][ref]
        link_patterns = [
            # Handle escaped patterns like \[4–8](url) with ranges and em-dashes, including ^ patterns
            r'\\?\[([¹²³⁴⁵⁶⁷⁸⁹⁰\d,\s–\-\^]+)\]\\?\([^)]+\\?\)',  # \[citation](url) or [citation](url) - includes ^
            r'\\?\[([¹²³⁴⁵⁶⁷⁸⁹⁰\d,\s–\-\^]+)\]\\?\[[^\]]+\\?\]',  # \[citation][ref] or [citation][ref] - includes ^
            r'<a[^>]*>([¹²³⁴⁵⁶⁷⁸⁹⁰\d,\s–\-\^]+)</a>',             # HTML links - includes ^
            # Simple citation patterns  
            r'\\?\[([¹²³⁴⁵⁶⁷⁸⁹⁰\d,\s\^]+)\]\\?\([^)]+\\?\)',      # \[citation](url) or [citation](url) - includes ^
            r'\\?\[([¹²³⁴⁵⁶⁷⁸⁹⁰\d,\s\^]+)\]\\?\[[^\]]+\\?\]',      # \[citation][ref] or [citation][ref] - includes ^
            r'<a[^>]*>([¹²³⁴⁵⁶⁷⁸⁹⁰\d,\s\^]+)</a>',                 # HTML links - includes ^
        ]
        
        for pattern in link_patterns:
            content = re.sub(pattern, r'[\1]', content)
        
        # Remove escaped backslashes from citation patterns (more comprehensive)
        # First handle simple patterns
        content = re.sub(r'\\(\[[\d,\s–\-\^]+\])\\?', r'\1', content)
        content = re.sub(r'\\(\[[\d,\s–\-\^]+\])', r'\1', content)
        # Handle complex nested patterns like \[[^1],[^2],[^3]\]
        content = re.sub(r'\\(\[[\[\]\d,\s–\-\^]+\])', r'\1', content)
        # Handle remaining backslashes at end
        content = re.sub(r'(\[[\[\]\d,\s–\-\^]+\])\\', r'\1', content)
        
        # Remove ^ symbols and normalize citation format from patterns like [[^1]], [^2],[^3] to [1], [2,3]
        def normalize_citation_numbers(match):
            citation_text = match.group(0)
            # Extract all numbers from patterns like [^1],[^2],[^3] or [[^1],[^2]]
            numbers = re.findall(r'\^?(\d+)', citation_text)
            if numbers:
                return '[' + ','.join(numbers) + ']'
            return citation_text
        
        # Handle complex patterns with ^ symbols first
        content = re.sub(r'\[\[?\^(\d+)(?:,\s*\[?\^(\d+)\]?)*\]?\]?', normalize_citation_numbers, content)
        # Handle simple patterns like [^1] or [[^1]]
        content = re.sub(r'\[+\^(\d+)\]+', r'[\1]', content)
        # Handle remaining patterns with ^ symbols
        content = re.sub(r'\[+[^\]]*\^[^\]]*\]+', normalize_citation_numbers, content)
        
        # Fix various double bracket patterns left after link removal
        # [[1]] -> [1]
        content = re.sub(r'\[\[(\d+(?:[–-]\d+)?(?:,\s*\d+(?:[–-]\d+)?)*)\]\]', r'[\1]', content)
        # [[1], [2]] -> [1,2]
        content = re.sub(r'\[\[(\d+)\],\s*\[(\d+)\]\]', r'[\1,\2]', content)
        # [[26–28], [34]] -> [26–28,34]
        content = re.sub(r'\[\[(\d+(?:[–-]\d+)?)\],\s*\[(\d+(?:[–-]\d+)?)\]\]', r'[\1,\2]', content)
        # More complex: [[1], [2], [3]] -> [1,2,3]
        content = re.sub(r'\[\[(\d+)\],\s*\[(\d+)\],\s*\[(\d+)\]\]', r'[\1,\2,\3]', content)
        
        return content
    
    def register_new_parser(self, publisher: str, pattern_config: Dict[str, Any]) -> bool:
        """Register a new parser pattern.
        
        Args:
            publisher: Publisher identifier
            pattern_config: Pattern configuration with detection and patterns
            
        Returns:
            True if registration succeeded, False otherwise
        """
        try:
            # Validate pattern configuration
            if not self._validate_parser_config(pattern_config):
                self.logger.error(f"Invalid parser configuration for {publisher}")
                return False
            
            # Add to in-memory parsers
            self.publisher_parsers[publisher] = pattern_config
            
            # Optionally save to configuration file for persistence
            if self._save_parser_to_config(publisher, pattern_config):
                self.logger.info(f"Successfully registered and saved new parser for publisher: {publisher}")
            else:
                self.logger.info(f"Registered new parser for publisher: {publisher} (in-memory only)")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to register parser for {publisher}: {e}")
            return False
    
    def _validate_parser_config(self, config: Dict[str, Any]) -> bool:
        """Validate parser configuration structure.
        
        Args:
            config: Parser configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ['detection', 'patterns']
        
        # Check required top-level keys
        for key in required_keys:
            if key not in config:
                self.logger.error(f"Missing required key '{key}' in parser config")
                return False
        
        # Validate detection config
        detection = config['detection']
        if not isinstance(detection, dict):
            self.logger.error("Detection config must be a dictionary")
            return False
        
        # Validate patterns config
        patterns = config['patterns']
        if not isinstance(patterns, list) or len(patterns) == 0:
            self.logger.error("Patterns must be a non-empty list")
            return False
        
        # Validate each pattern
        for i, pattern in enumerate(patterns):
            if not isinstance(pattern, dict):
                self.logger.error(f"Pattern {i} must be a dictionary")
                return False
            
            pattern_required = ['regex', 'replacement', 'description']
            for key in pattern_required:
                if key not in pattern:
                    self.logger.error(f"Pattern {i} missing required key '{key}'")
                    return False
            
            # Test regex validity
            try:
                re.compile(pattern['regex'])
            except re.error as e:
                self.logger.error(f"Invalid regex in pattern {i}: {e}")
                return False
        
        return True
    
    def _save_parser_to_config(self, publisher: str, pattern_config: Dict[str, Any]) -> bool:
        """Save new parser configuration to file.
        
        Args:
            publisher: Publisher identifier
            pattern_config: Pattern configuration
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            patterns_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'config', 'publisher_patterns.yaml'
            )
            
            # Load existing patterns
            existing_patterns = {}
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    existing_patterns = data.get('parsers', {})
            
            # Add new parser
            existing_patterns[publisher] = pattern_config
            
            # Save updated patterns
            updated_data = {'parsers': existing_patterns}
            with open(patterns_file, 'w', encoding='utf-8') as f:
                yaml.dump(updated_data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Saved parser configuration for {publisher} to {patterns_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save parser configuration: {e}")
            return False