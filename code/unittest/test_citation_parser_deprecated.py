"""
引用文献パーサーのテスト

ObsClippingsManager Citation Parser のテストスイート
"""

import unittest
import sys
import os
from pathlib import Path

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.citation_parser import (
    CitationParser, PatternDetector, FormatConverter, LinkExtractor,
    CitationMatch, CitationResult, LinkEntry, ProcessingStats, PatternConfig
)
from modules.citation_parser.exceptions import (
    CitationParserError, PatternDetectionError, FormatConversionError, LinkExtractionError
)


class TestPatternDetector(unittest.TestCase):
    """パターン検出エンジンのテスト"""
    
    def setUp(self):
        self.detector = PatternDetector()
    
    def test_single_citation_detection(self):
        """単一引用の検出テスト"""
        text = "This is referenced [1] in the paper."
        matches = self.detector.detect_patterns(text)
        
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].citation_numbers, [1])
        self.assertEqual(matches[0].pattern_type, 'single')
        self.assertEqual(matches[0].original_text, '[1]')
        self.assertFalse(matches[0].has_link)
    
    def test_multiple_citation_detection(self):
        """複数引用の検出テスト"""
        text = "Studies [1, 2, 3] show that..."
        matches = self.detector.detect_patterns(text)
        
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].citation_numbers, [1, 2, 3])
        self.assertEqual(matches[0].pattern_type, 'multiple')
    
    def test_range_citation_detection(self):
        """範囲引用の検出テスト"""
        text = "Multiple studies [1-5] demonstrate..."
        matches = self.detector.detect_patterns(text)
        
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].citation_numbers, [1, 2, 3, 4, 5])
        self.assertEqual(matches[0].pattern_type, 'range')


class TestFormatConverter(unittest.TestCase):
    """フォーマット変換エンジンのテスト"""
    
    def setUp(self):
        self.converter = FormatConverter()
    
    def test_single_citation_formatting(self):
        """単一引用のフォーマットテスト"""
        match = CitationMatch(
            original_text="[1]",
            citation_numbers=[1],
            has_link=False,
            pattern_type="single",
            start_pos=0,
            end_pos=3
        )
        
        formatted = self.converter._format_citation(match)
        self.assertEqual(formatted, "[1]")


class TestCitationParser(unittest.TestCase):
    """メインパーサーのテスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_basic_document_parsing(self):
        """基本的な文書解析テスト"""
        text = "This study [1] builds on previous work [2, 3]."
        
        result = self.parser.parse_document(text)
        
        # 基本的な結果検証
        self.assertIsInstance(result, CitationResult)
        self.assertGreater(result.statistics.total_citations, 0)


def run_citation_parser_tests():
    """引用パーサーテストを実行"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestPatternDetector,
        TestFormatConverter,
        TestCitationParser
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=== Citation Parser Tests ===")
    success = run_citation_parser_tests()
    
    if success:
        print("\n✅ All citation parser tests passed!")
    else:
        print("\n❌ Some citation parser tests failed!")
    
    sys.exit(0 if success else 1) 