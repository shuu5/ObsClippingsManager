"""
Enhanced Citation Parser テストスイート

エスケープされた引用形式への完全対応とTDD開発のためのテストケース
"""

import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../py')))

from modules.citation_parser.citation_parser import CitationParser
from modules.citation_parser.data_structures import CitationResult, LinkEntry


class TestEscapedBasicCitations(unittest.TestCase):
    """エスケープされた基本引用形式のテスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_escaped_single_citation(self):
        """エスケープされた単一引用のテスト"""
        test_cases = [
            (r'\[[1]\]', '[1]'),
            (r'\[[5]\]', '[5]'),
            (r'\[[10]\]', '[10]'),
            (r'\[[123]\]', '[123]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)
                self.assertGreater(result.statistics.converted_citations, 0)
    
    def test_escaped_multiple_individual_citations(self):
        """エスケープされた個別複数引用のテスト"""
        test_cases = [
            (r'\[[2], [3]\]', '[2], [3]'),
            (r'\[[1], [4], [7]\]', '[1], [4], [7]'),
            (r'\[[10], [20]\]', '[10], [20]'),
            (r'\[[12], [13]\]', '[12], [13]'),  # ユーザー指定のテストケース
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)
                self.assertGreater(result.statistics.converted_citations, 0)
    
    def test_escaped_multiple_grouped_citations(self):
        """エスケープされたグループ化複数引用のテスト"""
        test_cases = [
            (r'\[[1,2,3]\]', '[1], [2], [3]'),
            (r'\[[4, 5, 6]\]', '[4], [5], [6]'),
            (r'\[[1,2,3,4,5]\]', '[1], [2], [3], [4], [5]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)


class TestEscapedLinkedCitations(unittest.TestCase):
    """エスケープされたリンク付き引用形式のテスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_escaped_single_linked_citation(self):
        """エスケープされた単一リンク付き引用のテスト"""
        test_cases = [
            (r'\[[1](https://example.com)\]', '[1]'),
            (r'\[[5](https://test.org)\]', '[5]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)
                self.assertGreater(len(result.link_table), 0)
    
    def test_escaped_multiple_linked_citation(self):
        """エスケープされた複数リンク付き引用のテスト"""
        # ユーザー指定のテストケース
        input_text = r'\[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\]'
        expected = '[4], [5], [6], [7], [8]'
        
        result = self.parser.parse_document(input_text)
        self.assertEqual(result.converted_text, expected)
        self.assertGreater(len(result.link_table), 0)
        
        # リンク表には複数のエントリが含まれている必要がある
        self.assertEqual(len(result.link_table), 5)


class TestEscapedFootnoteCitations(unittest.TestCase):
    """エスケープされた脚注引用形式のテスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_escaped_single_footnote_citation(self):
        """エスケープされた単一脚注引用のテスト"""
        test_cases = [
            (r'\[[^1]\]', '[1]'),
            (r'\[[^5]\]', '[5]'),
            (r'\[[^10]\]', '[10]'),  # ユーザー指定のテストケース
            (r'\[[^123]\]', '[123]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)
                self.assertGreater(result.statistics.converted_citations, 0)
    
    def test_escaped_multiple_footnote_citation(self):
        """エスケープされた複数脚注引用のテスト"""
        # ユーザー指定のテストケース
        input_text = r'\[[^1],[^2],[^3]\]'
        expected = '[1], [2], [3]'
        
        result = self.parser.parse_document(input_text)
        self.assertEqual(result.converted_text, expected)
        self.assertEqual(result.statistics.converted_citations, 3)


class TestMixedEscapedCitations(unittest.TestCase):
    """混在するエスケープされた引用形式のテスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_mixed_escaped_citation_formats(self):
        """混在するエスケープ引用形式のテスト"""
        input_text = """
        This study \\[[1]\\] builds on previous work \\[[2], [3]\\].
        Additional references \\[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\\]
        and footnotes \\[[^10]\\], \\[[^1],[^2],[^3]\\] support the findings.
        """
        
        expected = """
        This study [1] builds on previous work [2], [3].
        Additional references [4], [5], [6], [7], [8]
        and footnotes [10], [1], [2], [3] support the findings.
        """
        
        result = self.parser.parse_document(input_text)
        
        # 空白の正規化を行って比較
        def normalize_whitespace(text):
            import re
            return re.sub(r'\s+', ' ', text.strip())
        
        self.assertEqual(
            normalize_whitespace(result.converted_text),
            normalize_whitespace(expected)
        )
        
        # リンクが適切に抽出されているかチェック
        self.assertGreater(len(result.link_table), 0)


class TestStandardFormatImprovement(unittest.TestCase):
    """既存の標準形式の改善テスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_standard_citation_no_change(self):
        """標準形式は変更されないことをテスト"""
        test_cases = [
            ('[1]', '[1]'),
            ('[5]', '[5]'),
            ('[10]', '[10]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)
    
    def test_multiple_citation_spacing_normalization(self):
        """複数引用のスペース正規化テスト"""
        test_cases = [
            ('[2,3]', '[2], [3]'),
            ('[2, 3]', '[2], [3]'),
            ('[2 , 3]', '[2], [3]'),
            ('[1,5,10]', '[1], [5], [10]'),
            ('[1, 5, 10]', '[1], [5], [10]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)
    
    def test_range_expansion(self):
        """範囲引用の展開テスト"""
        test_cases = [
            ('[1-3]', '[1], [2], [3]'),
            ('[5-7]', '[5], [6], [7]'),
            ('[1-5]', '[1], [2], [3], [4], [5]'),
            ('[10-12]', '[10], [11], [12]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)


class TestMixedCitationFormats(unittest.TestCase):
    """混在した引用形式のテスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_mixed_escaped_and_standard_citations(self):
        """エスケープと標準形式の混在テスト"""
        input_text = """
        This study \[[1]\] builds on previous work [2, 3].
        Additional references \[[4,5,6]\] and [7] support the findings.
        """
        
        expected_text = """
        This study [1] builds on previous work [2], [3].
        Additional references [4], [5], [6] and [7] support the findings.
        """
        
        result = self.parser.parse_document(input_text)
        self.assertEqual(self._normalize_whitespace(result.converted_text), 
                        self._normalize_whitespace(expected_text))
    
    def test_complex_mixed_citations_with_links(self):
        """複雑な混在形式（リンク付き）のテスト"""
        input_text = """
        Previous studies \[[1]\] and \[[2,3,4](https://example.com)\] 
        showed that \[[^5],[^6]\] and [7-9] are important.
        """
        
        expected_text = """
        Previous studies [1] and [2], [3], [4] 
        showed that [5], [6] and [7], [8], [9] are important.
        """
        
        result = self.parser.parse_document(input_text)
        self.assertEqual(self._normalize_whitespace(result.converted_text), 
                        self._normalize_whitespace(expected_text))
        
        # リンク表の確認
        self.assertGreater(len(result.link_table), 0)
        link_urls = [entry.url for entry in result.link_table]
        self.assertIn('https://example.com', link_urls)
    
    def test_real_manuscript_pattern(self):
        """実際のマニュスクリプトパターンのテスト"""
        input_text = """
        Pancreatic cancer is extremely poor worldwide \[[1]\]. 
        Radiotherapy is an option \[[2], [3]\]. 
        Several studies have been conducted \[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\].
        CSCs can be purified \[[12], [13]\].
        """
        
        expected_text = """
        Pancreatic cancer is extremely poor worldwide [1]. 
        Radiotherapy is an option [2], [3]. 
        Several studies have been conducted [4], [5], [6], [7], [8].
        CSCs can be purified [12], [13].
        """
        
        result = self.parser.parse_document(input_text)
        self.assertEqual(self._normalize_whitespace(result.converted_text), 
                        self._normalize_whitespace(expected_text))
    
    def _normalize_whitespace(self, text: str) -> str:
        """テスト用のホワイトスペース正規化"""
        import re
        # 複数の改行を単一の改行に
        text = re.sub(r'\n\s*\n', '\n', text)
        # 行頭・行末の空白を除去
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(line for line in lines if line)


class TestEdgeCases(unittest.TestCase):
    """エッジケースのテスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_empty_text(self):
        """空文字列のテスト"""
        result = self.parser.parse_document("")
        self.assertEqual(result.converted_text, "")
        self.assertEqual(len(result.link_table), 0)
        self.assertEqual(result.statistics.total_citations, 0)
    
    def test_no_citations(self):
        """引用がないテキストのテスト"""
        input_text = "This is a text without any citations."
        result = self.parser.parse_document(input_text)
        self.assertEqual(result.converted_text, input_text)
        self.assertEqual(len(result.link_table), 0)
        self.assertEqual(result.statistics.total_citations, 0)
    
    def test_malformed_escaped_citations(self):
        """不正なエスケープ引用のテスト"""
        test_cases = [
            r'\[[]\]',     # 空の引用番号
            r'\[[abc]\]',  # 数字でない引用番号
            r'\[[1]',      # 閉じ括弧なし
            r'[[1]\]',     # エスケープなし
        ]
        
        for input_text in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                # エラーが発生するか、元のテキストがそのまま残るかのどちらか
                self.assertIsInstance(result, CitationResult)
    
    def test_large_citation_numbers(self):
        """大きな引用番号のテスト"""
        test_cases = [
            (r'\[[999]\]', '[999]'),
            (r'\[[1000]\]', '[1000]'),
            (r'\[[123,456,789]\]', '[123], [456], [789]'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.parser.parse_document(input_text)
                self.assertEqual(result.converted_text, expected)
    
    def test_overlapping_patterns(self):
        """重複するパターンのテスト"""
        # この場合は最初に検出されたパターンが優先される
        input_text = r'\[[1]\] and \[[1]\] again'
        expected = '[1] and [1] again'
        
        result = self.parser.parse_document(input_text)
        self.assertEqual(result.converted_text, expected)


class TestPerformance(unittest.TestCase):
    """パフォーマンステスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_large_document_performance(self):
        """大きなドキュメントのパフォーマンステスト"""
        # 多数の引用を含む大きなテキストを生成
        citations = [r'\[[{}]\]'.format(i) for i in range(1, 101)]
        large_text = ' '.join(f"Reference {citation} is important." for citation in citations)
        
        result = self.parser.parse_document(large_text)
        
        # 結果の検証
        self.assertEqual(result.statistics.total_citations, 100)
        self.assertEqual(result.statistics.converted_citations, 100)
        self.assertLess(result.statistics.processing_time, 5.0)  # 5秒以内


if __name__ == '__main__':
    # テストスイートの実行
    unittest.main(verbosity=2) 