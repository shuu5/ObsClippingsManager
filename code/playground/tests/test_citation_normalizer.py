import unittest
import tempfile
import os
from pathlib import Path
import sys

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from citation_normalizer.citation_normalizer import CitationNormalizer


class TestCitationNormalizer(unittest.TestCase):
    
    def setUp(self):
        self.normalizer = CitationNormalizer()
    
    def test_expand_range_citations_hyphen(self):
        """ハイフンでの範囲表記の展開テスト"""
        text = "これは引用です [2-4] その他のテキスト"
        expected = "これは引用です [2,3,4] その他のテキスト"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_expand_range_citations_endash(self):
        """エンダッシュでの範囲表記の展開テスト"""
        text = "これは引用です [4–8] その他のテキスト"
        expected = "これは引用です [4,5,6,7,8] その他のテキスト"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_expand_range_citations_emdash(self):
        """エムダッシュでの範囲表記の展開テスト"""
        text = "これは引用です [10—13] その他のテキスト"
        expected = "これは引用です [10,11,12,13] その他のテキスト"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_expand_multiple_ranges(self):
        """複数の範囲表記の展開テスト"""
        text = "引用 [2-4] と [14–21] と [26–29] があります"
        expected = "引用 [2,3,4] と [14,15,16,17,18,19,20,21] と [26,27,28,29] があります"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_invalid_range(self):
        """無効な範囲（逆順）のテスト"""
        text = "無効な範囲 [8-4] はそのまま残る"
        expected = "無効な範囲 [8-4] はそのまま残る"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_merge_consecutive_citations(self):
        """連続する引用の統合テスト"""
        text = "引用 [17], [18] を統合"
        expected = "引用 [17,18] を統合"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_merge_multiple_consecutive_citations(self):
        """複数の連続引用の統合テスト"""
        text = "引用 [1], [2], [3] を統合"
        expected = "引用 [1,2,3] を統合"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_merge_with_spaces(self):
        """スペースありの連続引用統合テスト"""
        text = "引用 [17] , [18] , [19] を統合"
        expected = "引用 [17,18,19] を統合"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_no_change_individual_citations(self):
        """個別引用はそのまま残るテスト"""
        text = "個別引用 [1] と [5] と [10] はそのまま"
        expected = "個別引用 [1] と [5] と [10] はそのまま"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_complex_citation_pattern(self):
        """複雑な引用パターンのテスト"""
        text = "複雑な例: [1] と [4–8] と [10], [11] と [15-17]"
        expected = "複雑な例: [1] と [4,5,6,7,8] と [10,11] と [15,16,17]"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_extract_citations(self):
        """引用文献抽出のテスト"""
        text = "テキスト [1] と [4–8] と [10], [11]"
        citations = self.normalizer.extract_citations(text)
        
        # 引用の数をチェック
        self.assertEqual(len(citations), 4)
        
        # 各引用の内容をチェック
        citation_texts = [citation[0] for citation in citations]
        expected_citations = ['[1]', '[4–8]', '[10]', '[11]']
        self.assertEqual(citation_texts, expected_citations)
    
    def test_duplicate_removal_in_merge(self):
        """統合時の重複除去テスト"""
        text = "重複引用 [5], [5], [6] を統合"
        expected = "重複引用 [5,6] を統合"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_sorting_in_merge(self):
        """統合時のソートテスト"""
        text = "順序が逆の引用 [8], [7], [6] を統合"
        expected = "順序が逆の引用 [6,7,8] を統合"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)
    
    def test_process_file(self):
        """ファイル処理のテスト"""
        # 一時ファイルを作成
        test_content = "これは引用です [2-4] と [10], [11] があります"
        expected_content = "これは引用です [2,3,4] と [10,11] があります"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name
        
        try:
            result = self.normalizer.process_file(temp_file_path)
            self.assertEqual(result, expected_content)
        finally:
            os.unlink(temp_file_path)
    
    def test_process_directory(self):
        """ディレクトリ処理のテスト"""
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            # テストファイルを作成
            test_file_path = os.path.join(temp_dir, 'test.md')
            test_content = "引用 [4–8] があります"
            expected_content = "引用 [4,5,6,7,8] があります"
            
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # ディレクトリ処理を実行
            results = self.normalizer.process_directory(temp_dir, '.md')
            
            # 結果を確認
            self.assertEqual(len(results), 1)
            self.assertEqual(results[test_file_path], expected_content)
    
    def test_empty_text(self):
        """空のテキストのテスト"""
        text = ""
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, "")
    
    def test_no_citations(self):
        """引用がないテキストのテスト"""
        text = "引用文献がないテキストです。"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, text)
    
    def test_real_world_example(self):
        """実世界の例に基づくテスト"""
        text = """
        Pancreatic cancer is one of the most aggressive cancers [1]. 
        Radiotherapy is an option for adjuvant therapy [2], [3]. 
        Several studies have been conducted [4–8]. 
        The proteasome activity is a common biologic property [14–21].
        """
        
        expected = """
        Pancreatic cancer is one of the most aggressive cancers [1]. 
        Radiotherapy is an option for adjuvant therapy [2,3]. 
        Several studies have been conducted [4,5,6,7,8]. 
        The proteasome activity is a common biologic property [14,15,16,17,18,19,20,21].
        """
        
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)

    def test_merge_consecutive_citations_with_spaces(self):
        """スペースありの連続引用統合のテスト"""
        text = "[5] , [6] , [7]"
        expected = "[5,6,7]"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)

    def test_footnote_consecutive_citations(self):
        """脚注形式の連続引用統合のテスト"""
        text = "[^1], [^2], [^3]"
        expected = "[^1,^2,^3]"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)

    def test_footnote_range_citations(self):
        """脚注形式の範囲表記展開のテスト"""
        text = "[^2-^4]"
        expected = "[^2,^3,^4]"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)

    def test_footnote_mixed_pattern(self):
        """脚注形式の混合パターンのテスト"""
        text = "[^4], [^5], [^7-^9]"
        expected = "[^4,^5], [^7,^8,^9]"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)

    def test_footnote_with_spaces(self):
        """脚注形式でスペースありの連続引用統合のテスト"""
        text = "[^1] , [^2] , [^3]"
        expected = "[^1,^2,^3]"
        result = self.normalizer.normalize_citations(text)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main() 