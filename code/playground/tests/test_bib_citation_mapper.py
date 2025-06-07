"""
BibCitationMapperクラスのテストケース
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# テスト対象のモジュールをインポート
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from citation_normalizer.bib_citation_mapper import BibCitationMapper


class TestBibCitationMapper(unittest.TestCase):
    """BibCitationMapperクラスのテストケース"""
    
    def setUp(self):
        """テストの前準備"""
        self.mapper = BibCitationMapper()
    
    def test_extract_citations_from_text_simple(self):
        """単純な引用番号抽出のテスト"""
        text = "これは論文 [1] と [2] の引用です。"
        expected = [1, 2]
        result = self.mapper.extract_citations_from_text(text)
        self.assertEqual(result, expected)
    
    def test_extract_citations_from_text_footnote(self):
        """脚注形式の引用番号抽出のテスト"""
        text = "これは論文 [^1] と [^3] の引用です。"
        expected = [1, 3]
        result = self.mapper.extract_citations_from_text(text)
        self.assertEqual(result, expected)
    
    def test_extract_citations_from_text_mixed(self):
        """混合形式の引用番号抽出のテスト"""
        text = "これは論文 [1], [^2], [5] と [^3] の引用です。"
        expected = [1, 2, 3, 5]
        result = self.mapper.extract_citations_from_text(text)
        self.assertEqual(result, expected)
    
    def test_extract_citations_from_text_duplicates(self):
        """重複する引用番号の処理テスト"""
        text = "これは論文 [1], [2], [1] と [3] の引用です。"
        expected = [1, 2, 3]
        result = self.mapper.extract_citations_from_text(text)
        self.assertEqual(result, expected)
    
    def test_extract_citations_from_text_no_citations(self):
        """引用番号がないテキストのテスト"""
        text = "これは引用番号がない論文です。"
        expected = []
        result = self.mapper.extract_citations_from_text(text)
        self.assertEqual(result, expected)
    
    def test_parse_bib_file_simple(self):
        """単純なBibTeXファイル解析のテスト"""
        bib_content = """
% This is a comment
@article{Sung2021CCJ,
  title = {Global cancer statistics},
  author = {Sung},
  year = {2021},
  journal = {CA Cancer J Clin},
  volume = {71},
  pages = {209}
}

@article{Hall2019RO,
  title = {Radiation therapy},
  author = {Hall},
  year = {2019},
  journal = {Radiat Oncol}
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            f.write(bib_content)
            bib_file_path = f.name
        
        try:
            result = self.mapper.parse_bib_file(bib_file_path)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['entry_type'], 'article')
            self.assertEqual(result[0]['entry_key'], 'Sung2021CCJ')
            self.assertEqual(result[1]['entry_key'], 'Hall2019RO')
        finally:
            os.unlink(bib_file_path)
    
    def test_add_citation_numbers_to_bib(self):
        """citation_numberプロパティ追加のテスト"""
        bib_entries = [
            {
                'raw_content': '@article{Test1,\n  title = {Test Title 1},\n  year = {2021}\n}',
                'entry_type': 'article',
                'entry_key': 'Test1'
            },
            {
                'raw_content': '@article{Test2,\n  title = {Test Title 2},\n  year = {2022}\n}',
                'entry_type': 'article',
                'entry_key': 'Test2'
            }
        ]
        
        citations = [1, 2]
        result = self.mapper.add_citation_numbers_to_bib(bib_entries, citations)
        
        self.assertEqual(len(result), 2)
        self.assertIn('citation_number', result[0])
        self.assertEqual(result[0]['citation_number'], 1)
        self.assertIn('citation_number = {1}', result[0]['raw_content'])
        self.assertEqual(result[1]['citation_number'], 2)
        self.assertIn('citation_number = {2}', result[1]['raw_content'])
    
    def test_add_citation_numbers_insufficient_citations(self):
        """引用番号が不足している場合のテスト"""
        bib_entries = [
            {
                'raw_content': '@article{Test1,\n  title = {Test Title 1}\n}',
                'entry_type': 'article',
                'entry_key': 'Test1'
            },
            {
                'raw_content': '@article{Test2,\n  title = {Test Title 2}\n}',
                'entry_type': 'article',
                'entry_key': 'Test2'
            }
        ]
        
        citations = [1]  # 1つしかない
        result = self.mapper.add_citation_numbers_to_bib(bib_entries, citations)
        
        self.assertEqual(len(result), 2)
        self.assertIn('citation_number', result[0])
        self.assertEqual(result[0]['citation_number'], 1)
        self.assertNotIn('citation_number', result[1])  # 2番目にはcitation_numberがない
    
    def test_process_paper_directory_dry_run(self):
        """論文ディレクトリ処理のドライランテスト"""
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            # Markdownファイルを作成
            md_content = "これは論文 [1] と [2] の引用です。"
            md_file = os.path.join(temp_dir, "test_paper.md")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            # BibTeXファイルを作成
            bib_content = """
% Test references
@article{Test1,
  title = {Test Title 1},
  year = {2021}
}

@article{Test2,
  title = {Test Title 2},
  year = {2022}
}
"""
            bib_file = os.path.join(temp_dir, "references.bib")
            with open(bib_file, 'w', encoding='utf-8') as f:
                f.write(bib_content)
            
            # ドライランで処理
            result = self.mapper.process_paper_directory(temp_dir, dry_run=True)
            
            self.assertEqual(result['citations_found'], [1, 2])
            self.assertEqual(result['bib_entries_count'], 2)
            self.assertEqual(result['updated_entries_count'], 2)
            self.assertFalse(result['file_updated'])
    
    def test_real_world_citation_pattern(self):
        """実際の論文でのより複雑な引用パターンのテスト"""
        text = """
        Pancreatic cancer is one of the most aggressive cancers [1]. 
        Several studies have shown [2,3,4] that radiotherapy is effective.
        Cancer stem cells [^1], [^2] are important factors.
        """
        expected = [1, 2, 3, 4]  # [5-8]は除去、脚注形式は1,2として重複除去される
        result = self.mapper.extract_citations_from_text(text)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main() 