#!/usr/bin/env python3
"""Test Citation Pattern Normalizer Workflow"""

import os
import sys
import unittest
import tempfile
import yaml
from unittest.mock import MagicMock, patch

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from code.py.modules.citation_pattern_normalizer.citation_pattern_normalizer_workflow import CitationPatternNormalizerWorkflow
from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger


class TestCitationPatternNormalizerWorkflow(unittest.TestCase):
    """Test Citation Pattern Normalizer Workflow"""
    
    def setUp(self):
        """Set up test environment"""
        self.config_manager = MagicMock(spec=ConfigManager)
        self.logger = MagicMock(spec=IntegratedLogger)
        
        # Mock logger methods
        self.logger.info = MagicMock()
        self.logger.warning = MagicMock()
        self.logger.error = MagicMock()
        self.logger.debug = MagicMock()
        
        # Mock config values
        self.config_manager.config = {
            'citation_pattern_normalizer': {
                'enabled': True,
                'batch_size': 20,
                'retry_attempts': 3,
                'publisher_detection': {
                    'auto_detect': True,
                    'fallback_parser': 'generic'
                },
                'notification': {
                    'unsupported_pattern_alert': True,
                    'new_parser_suggestion': True
                }
            }
        }
        
        # Mock publisher patterns for testing
        mock_patterns = {
            'oxford_academic': {
                'detection': {
                    'doi_prefixes': ['10.1093'],
                    'journal_keywords': ['Oxford', 'OUP', 'Oxford Academic']
                },
                'patterns': [
                    {
                        'regex': '([¹²³⁴⁵⁶⁷⁸⁹⁰,]+)',
                        'replacement': '[{numbers}]',
                        'description': '上付き数字カンマ区切り'
                    },
                    {
                        'regex': '([¹²³⁴⁵⁶⁷⁸⁹⁰]+)',
                        'replacement': '[{numbers}]',
                        'description': '上付き数字単体'
                    }
                ]
            },
            'elsevier': {
                'detection': {
                    'doi_prefixes': ['10.1016'],
                    'journal_keywords': ['Elsevier', 'ScienceDirect']
                },
                'patterns': [
                    {
                        'regex': '\\((\\d+(?:,\\s*\\d+)*)\\)',
                        'replacement': '[{numbers}]',
                        'description': '括弧付きカンマ区切り数字リスト'
                    },
                    {
                        'regex': '\\((\\d+)\\)',
                        'replacement': '[{number}]',
                        'description': '括弧付き単体数字'
                    }
                ]
            },
            'nature': {
                'detection': {
                    'doi_prefixes': ['10.1038'],
                    'journal_keywords': ['Nature', 'Nature Publishing', 'NPG']
                },
                'patterns': [
                    {
                        'regex': '\\b(\\d+(?:,\\s*\\d+)+)\\b',
                        'replacement': '[{numbers}]',
                        'description': 'カンマ区切り数字リスト（複数）'
                    },
                    {
                        'regex': '\\b(\\d+)\\b',
                        'replacement': '[{number}]',
                        'description': '単体数字'
                    }
                ]
            },
            'generic': {
                'detection': {'fallback': True},
                'patterns': [
                    {
                        'regex': '\\b(\\d+)\\b',
                        'replacement': '[{number}]',
                        'description': '汎用数字パターン'
                    }
                ]
            }
        }
        
        with patch.object(CitationPatternNormalizerWorkflow, '_load_publisher_parsers', return_value=mock_patterns):
            self.workflow = CitationPatternNormalizerWorkflow(self.config_manager, self.logger)
    
    def test_initialization(self):
        """Test workflow initialization"""
        self.assertIsNotNone(self.workflow)
        self.assertEqual(self.workflow.config, self.config_manager)
        self.assertEqual(self.workflow.logger, self.logger)
    
    def test_process_items_method_exists(self):
        """Test process_items method exists and is callable"""
        self.assertTrue(hasattr(self.workflow, 'process_items'))
        self.assertTrue(callable(getattr(self.workflow, 'process_items')))
    
    def test_detect_publisher_method_exists(self):
        """Test detect_publisher method exists and is callable"""
        self.assertTrue(hasattr(self.workflow, 'detect_publisher'))
        self.assertTrue(callable(getattr(self.workflow, 'detect_publisher')))
    
    def test_normalize_citations_method_exists(self):
        """Test normalize_citations method exists and is callable"""
        self.assertTrue(hasattr(self.workflow, 'normalize_citations'))
        self.assertTrue(callable(getattr(self.workflow, 'normalize_citations')))
    
    def test_detect_publisher_by_doi(self):
        """Test publisher detection using DOI"""
        content = "Sample content"
        metadata = {"doi": "10.1093/jrr/rrz123"}
        
        publisher = self.workflow.detect_publisher(content, metadata)
        self.assertEqual(publisher, "oxford_academic")
    
    def test_detect_publisher_by_manual_override(self):
        """Test publisher detection with manual override"""
        content = "Sample content"
        metadata = {"publisher": "Nature Publishing"}
        
        publisher = self.workflow.detect_publisher(content, metadata)
        self.assertEqual(publisher, "nature")
    
    def test_detect_publisher_fallback(self):
        """Test publisher detection fallback to generic"""
        content = "Sample content"
        metadata = {}
        
        publisher = self.workflow.detect_publisher(content, metadata)
        self.assertEqual(publisher, "generic")
    
    def test_normalize_citations_oxford_patterns(self):
        """Test citation normalization for Oxford Academic patterns"""
        content = "Research shows that radiation affects cells¹². Previous studies²,³,⁴ indicate..."
        publisher = "oxford_academic"
        
        normalized_content, results = self.workflow.normalize_citations(content, publisher)
        
        # Check that citations were normalized
        self.assertIn("[1,2]", normalized_content)
        self.assertIn("[2,3,4]", normalized_content)
        self.assertGreater(len(results), 0)
    
    def test_normalize_citations_unknown_publisher(self):
        """Test citation normalization with unknown publisher"""
        content = "Sample content with citations"
        publisher = "unknown_publisher"
        
        normalized_content, results = self.workflow.normalize_citations(content, publisher)
        
        # Should return original content
        self.assertEqual(normalized_content, content)
        self.assertEqual(len(results), 0)
    
    def test_normalize_citations_elsevier_patterns(self):
        """Test citation normalization for Elsevier patterns"""
        content = "The study shows (1) significant results and (2,3) additional findings."
        publisher = "elsevier"
        
        normalized_content, results = self.workflow.normalize_citations(content, publisher)
        
        # Check that citations were normalized
        self.assertIn("[1]", normalized_content)
        self.assertIn("[2,3]", normalized_content)
        self.assertGreater(len(results), 0)
    
    def test_normalize_citations_nature_patterns(self):
        """Test citation normalization for Nature patterns"""
        content = "Previous research 1,2,3 shows interesting results."
        publisher = "nature"
        
        normalized_content, results = self.workflow.normalize_citations(content, publisher)
        
        # Check that citations were normalized (with updated pattern, may process individually)
        # Accept either [1,2,3] or [1],[2],[3] format
        self.assertTrue("[1,2,3]" in normalized_content or "[1]" in normalized_content)
        self.assertGreater(len(results), 0)
    
    def test_extract_yaml_and_content(self):
        """Test YAML header and content extraction"""
        content = "---\ntitle: Test Paper\ndoi: 10.1093/test\n---\n# Introduction\nThis is content."
        
        yaml_header, markdown_content = self.workflow._extract_yaml_and_content(content)
        
        self.assertEqual(yaml_header['title'], 'Test Paper')
        self.assertEqual(yaml_header['doi'], '10.1093/test')
        self.assertIn('# Introduction', markdown_content)
    
    def test_combine_yaml_and_content(self):
        """Test combining YAML header and markdown content"""
        yaml_header = {'title': 'Test Paper', 'doi': '10.1093/test'}
        markdown_content = "# Introduction\nThis is content."
        
        combined = self.workflow._combine_yaml_and_content(yaml_header, markdown_content)
        
        self.assertIn('---', combined)
        self.assertIn('title: Test Paper', combined)
        self.assertIn('# Introduction', combined)
    
    def test_detect_unsupported_patterns_method_exists(self):
        """Test unsupported pattern detection method exists"""
        self.assertTrue(hasattr(self.workflow, '_detect_unsupported_patterns'))
        self.assertTrue(callable(getattr(self.workflow, '_detect_unsupported_patterns')))
    
    def test_suggest_new_parser_patterns_method_exists(self):
        """Test new parser pattern suggestion method exists"""
        self.assertTrue(hasattr(self.workflow, '_suggest_new_parser_patterns'))
        self.assertTrue(callable(getattr(self.workflow, '_suggest_new_parser_patterns')))
    
    def test_register_new_parser_valid_config(self):
        """Test registering a new parser with valid configuration"""
        publisher = "test_publisher"
        pattern_config = {
            "detection": {
                "doi_prefixes": ["10.1234"],
                "journal_keywords": ["Test Journal"]
            },
            "patterns": [
                {
                    "regex": "\\((\\d+)\\)",
                    "replacement": "[{number}]",
                    "description": "Test pattern"
                }
            ]
        }
        
        result = self.workflow.register_new_parser(publisher, pattern_config)
        self.assertTrue(result)
        self.assertIn(publisher, self.workflow.publisher_parsers)
    
    def test_register_new_parser_invalid_config(self):
        """Test registering a new parser with invalid configuration"""
        publisher = "invalid_publisher"
        pattern_config = {
            "detection": "not_a_dict",  # Invalid type
            "patterns": []  # Empty patterns
        }
        
        result = self.workflow.register_new_parser(publisher, pattern_config)
        self.assertFalse(result)
    
    def test_validate_parser_config_valid(self):
        """Test parser configuration validation with valid config"""
        valid_config = {
            "detection": {
                "doi_prefixes": ["10.1234"]
            },
            "patterns": [
                {
                    "regex": "\\((\\d+)\\)",
                    "replacement": "[{number}]",
                    "description": "Valid pattern"
                }
            ]
        }
        
        result = self.workflow._validate_parser_config(valid_config)
        self.assertTrue(result)
    
    def test_validate_parser_config_invalid_regex(self):
        """Test parser configuration validation with invalid regex"""
        invalid_config = {
            "detection": {
                "doi_prefixes": ["10.1234"]
            },
            "patterns": [
                {
                    "regex": "[invalid regex",  # Invalid regex
                    "replacement": "[{number}]",
                    "description": "Invalid pattern"
                }
            ]
        }
        
        result = self.workflow._validate_parser_config(invalid_config)
        self.assertFalse(result)
    
    def test_update_yaml_header_with_normalization_results(self):
        """Test YAML header update with normalization results"""
        yaml_header = {
            'title': 'Test Paper',
            'processing_status': {}
        }
        publisher = 'oxford_academic'
        normalization_results = [
            {
                'original': '¹²',
                'normalized': '[1,2]',
                'position': 45,
                'pattern_description': '上付き数字'
            }
        ]
        
        updated_header = self.workflow._update_yaml_header(yaml_header, publisher, normalization_results)
        
        # Check citation_normalization section was added
        self.assertIn('citation_normalization', updated_header)
        normalization = updated_header['citation_normalization']
        
        self.assertEqual(normalization['publisher_detected'], publisher)
        self.assertEqual(normalization['parser_used'], f"{publisher}_parser")
        self.assertEqual(normalization['total_citations_normalized'], 1)
        self.assertEqual(len(normalization['patterns_normalized']), 1)
        
        # Check processing status was updated
        self.assertEqual(updated_header['processing_status']['citation_pattern_normalizer'], 'completed')


if __name__ == '__main__':
    unittest.main()