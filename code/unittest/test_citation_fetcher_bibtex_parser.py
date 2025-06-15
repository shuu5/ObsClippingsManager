"""
Citation Fetcher BibTeX Parser Test Suite

Citation Fetcher機能向けのBibTeXParser拡張テスト
- DOI抽出機能のテスト
- 引用文献取得のための前処理テスト
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock

from code.py.modules.shared_modules.bibtex_parser import BibTeXParser
from code.py.modules.shared_modules.exceptions import BibTeXError
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger


class TestBibTeXParserCitationFetcher(unittest.TestCase):
    """Citation Fetcher機能向けBibTeXParser拡張テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.mock_logger = MagicMock()
        self.parser = BibTeXParser(self.mock_logger)
    
    def tearDown(self):
        """テストクリーンアップ"""
        pass
    
    # === DOI抽出機能テスト ===
    def test_extract_doi_from_entries_basic(self):
        """基本的なDOI抽出テスト"""
        entries = {
            'smith2023test': {
                'ID': 'smith2023test',
                'doi': '10.1038/s41591-023-1234-5',
                'title': 'Test Paper',
                'author': 'Smith, John'
            },
            'jones2022': {
                'ID': 'jones2022',
                'doi': '10.1126/science.abcd1234',
                'title': 'Another Paper',
                'author': 'Jones, Alice'
            }
        }
        
        dois = self.parser.extract_doi_from_entries(entries)
        
        self.assertEqual(len(dois), 2)
        self.assertIn('10.1038/s41591-023-1234-5', dois)
        self.assertIn('10.1126/science.abcd1234', dois)
        
    def test_extract_doi_from_entries_missing_doi(self):
        """DOI情報がないエントリを含む場合のテスト"""
        entries = {
            'smith2023test': {
                'ID': 'smith2023test',
                'doi': '10.1038/s41591-023-1234-5',
                'title': 'Test Paper'
            },
            'jones2022': {
                'ID': 'jones2022',
                'title': 'Paper Without DOI'
            }
        }
        
        dois = self.parser.extract_doi_from_entries(entries)
        
        self.assertEqual(len(dois), 1)
        self.assertIn('10.1038/s41591-023-1234-5', dois)
        
    def test_extract_doi_from_entries_empty_entries(self):
        """空のエントリ辞書の場合のテスト"""
        entries = {}
        
        dois = self.parser.extract_doi_from_entries(entries)
        
        self.assertEqual(len(dois), 0)
        self.assertEqual(dois, [])
        
    def test_extract_doi_from_entries_malformed_doi(self):
        """不正なDOI形式が含まれる場合のテスト"""
        entries = {
            'valid_paper': {
                'ID': 'valid_paper',
                'doi': '10.1038/s41591-023-1234-5',
                'title': 'Valid Paper'
            },
            'malformed_paper': {
                'ID': 'malformed_paper', 
                'doi': 'not-a-valid-doi',
                'title': 'Paper with malformed DOI'
            }
        }
        
        dois = self.parser.extract_doi_from_entries(entries)
        
        # 有効なDOIのみが含まれることを確認
        self.assertEqual(len(dois), 1)
        self.assertIn('10.1038/s41591-023-1234-5', dois)
        self.assertNotIn('not-a-valid-doi', dois)
        
    def test_extract_doi_from_entries_with_url_prefix(self):
        """DOI URLプレフィックス付きの場合のテスト"""
        entries = {
            'paper1': {
                'ID': 'paper1',
                'doi': 'https://doi.org/10.1038/s41591-023-1234-5',
                'title': 'Paper with URL DOI'
            },
            'paper2': {
                'ID': 'paper2',
                'doi': 'doi:10.1126/science.abcd1234',
                'title': 'Paper with doi: prefix'
            }
        }
        
        dois = self.parser.extract_doi_from_entries(entries)
        
        # 正規化されたDOI（プレフィックス除去）が返されることを確認
        self.assertEqual(len(dois), 2)
        self.assertIn('10.1038/s41591-023-1234-5', dois)
        self.assertIn('10.1126/science.abcd1234', dois)
        
    def test_extract_doi_from_entries_duplicate_dois(self):
        """重複DOIが含まれる場合のテスト"""
        entries = {
            'paper1': {
                'ID': 'paper1',
                'doi': '10.1038/s41591-023-1234-5',
                'title': 'First Paper'
            },
            'paper2': {
                'ID': 'paper2',
                'doi': '10.1038/s41591-023-1234-5',
                'title': 'Duplicate DOI Paper'
            }
        }
        
        dois = self.parser.extract_doi_from_entries(entries)
        
        # 重複が除去されることを確認
        self.assertEqual(len(dois), 1)
        self.assertIn('10.1038/s41591-023-1234-5', dois)
        
    # === Citation Key → DOI マッピング機能テスト ===
    def test_get_citation_key_to_doi_mapping_basic(self):
        """基本的なCitation Key → DOIマッピング取得テスト"""
        entries = {
            'smith2023test': {
                'ID': 'smith2023test',
                'doi': '10.1038/s41591-023-1234-5',
                'title': 'Test Paper'
            },
            'jones2022': {
                'ID': 'jones2022',
                'doi': '10.1126/science.abcd1234',
                'title': 'Another Paper'
            }
        }
        
        mapping = self.parser.get_citation_key_to_doi_mapping(entries)
        
        expected_mapping = {
            'smith2023test': '10.1038/s41591-023-1234-5',
            'jones2022': '10.1126/science.abcd1234'
        }
        
        self.assertEqual(mapping, expected_mapping)
        
    def test_get_citation_key_to_doi_mapping_missing_doi(self):
        """DOIが欠けているエントリを含む場合のテスト"""
        entries = {
            'smith2023test': {
                'ID': 'smith2023test',
                'doi': '10.1038/s41591-023-1234-5',
                'title': 'Test Paper'
            },
            'jones2022': {
                'ID': 'jones2022',
                'title': 'Paper Without DOI'
            }
        }
        
        mapping = self.parser.get_citation_key_to_doi_mapping(entries)
        
        expected_mapping = {
            'smith2023test': '10.1038/s41591-023-1234-5'
        }
        
        self.assertEqual(mapping, expected_mapping)
        
    # === 統合テスト ===
    def test_citation_fetcher_workflow_integration(self):
        """Citation Fetcher統合ワークフローテスト"""
        # サンプルBibTeX文字列
        bibtex_content = """
        @article{smith2023test,
            title={Advanced Biomarker Techniques in Oncology},
            author={Smith, John and Doe, Jane},
            journal={Nature Medicine},
            year={2023},
            doi={10.1038/s41591-023-1234-5}
        }
        
        @article{jones2022biomarkers,
            title={Biomarker Discovery in Cancer Research},
            author={Jones, Alice and Brown, Bob},
            journal={Science},
            year={2022},
            doi={10.1126/science.abcd1234}
        }
        
        @book{wilson2021handbook,
            title={Cancer Research Handbook},
            author={Wilson, Carol},
            publisher={Academic Press},
            year={2021}
        }
        """
        
        # BibTeX解析
        entries = self.parser.parse_string(bibtex_content)
        
        # DOI抽出
        dois = self.parser.extract_doi_from_entries(entries)
        
        # Citation Key → DOI マッピング
        mapping = self.parser.get_citation_key_to_doi_mapping(entries)
        
        # 検証
        self.assertEqual(len(entries), 3)
        self.assertEqual(len(dois), 2)  # DOIを持つ論文は2つ
        self.assertEqual(len(mapping), 2)  # マッピングも2つ
        
        self.assertIn('10.1038/s41591-023-1234-5', dois)
        self.assertIn('10.1126/science.abcd1234', dois)
        
        self.assertEqual(mapping['smith2023test'], '10.1038/s41591-023-1234-5')
        self.assertEqual(mapping['jones2022biomarkers'], '10.1126/science.abcd1234')


class TestCitationFetcherBibTeXParserImport(unittest.TestCase):
    """Citation Fetcher BibTeX Parser拡張機能インポートテスト"""
    
    def test_extended_methods_available(self):
        """拡張メソッドの利用可能性テスト"""
        mock_logger = MagicMock()
        parser = BibTeXParser(mock_logger)
        
        # 新機能メソッドの存在確認
        self.assertTrue(hasattr(parser, 'extract_doi_from_entries'))
        self.assertTrue(callable(getattr(parser, 'extract_doi_from_entries')))
        
        self.assertTrue(hasattr(parser, 'get_citation_key_to_doi_mapping'))
        self.assertTrue(callable(getattr(parser, 'get_citation_key_to_doi_mapping')))


if __name__ == '__main__':
    unittest.main() 