"""
Citation Fetcher Workflow Test Suite

引用文献取得ワークフローのテスト
- CitationFetcherWorkflowクラスの基本機能テスト
- API統合とフォールバック戦略のテスト
- references.bib生成のテスト
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import json
import yaml

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import BibTeXError, APIError


class TestCitationFetcherWorkflow(unittest.TestCase):
    """CitationFetcherWorkflowクラステスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = MagicMock()
        self.logger = MagicMock()
        
        # 設定モック
        self.config_manager.get.return_value = {
            'citation_fetcher': {
                'enabled': True,
                'apis': {
                    'crossref': {
                        'enabled': True,
                        'rate_limit': 10,
                        'quality_threshold': 0.8
                    },
                    'semantic_scholar': {
                        'enabled': True,
                        'rate_limit': 1,
                        'quality_threshold': 0.7
                    },
                    'opencitations': {
                        'enabled': True,
                        'rate_limit': 5,
                        'quality_threshold': 0.5
                    }
                }
            }
        }
        
    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # === 基本機能テスト ===
    def test_citation_fetcher_workflow_initialization(self):
        """CitationFetcherワークフロー初期化テスト"""
        # citation_fetcherモジュールを一時的にインポート可能にする
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # 基本属性の確認
            self.assertIsNotNone(workflow.config_manager)
            self.assertIsNotNone(workflow.logger)
            
        except ImportError:
            # まだ実装されていない場合はスキップ
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    def test_extract_doi_from_paper_basic(self):
        """論文からDOI抽出の基本テスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # テスト用Markdownファイル作成
            test_paper = Path(self.temp_dir) / "test_paper.md"
            test_content = """---
title: "Test Paper"
doi: "10.1038/s41591-023-1234-5"
---

# Test Paper Content
"""
            test_paper.write_text(test_content, encoding='utf-8')
            
            # DOI抽出テスト
            doi = workflow.extract_doi_from_paper(str(test_paper))
            
            self.assertEqual(doi, "10.1038/s41591-023-1234-5")
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    def test_extract_doi_from_paper_no_doi(self):
        """DOIがない論文からの抽出テスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # DOIなしのテスト用Markdownファイル作成
            test_paper = Path(self.temp_dir) / "test_paper_no_doi.md"
            test_content = """---
title: "Test Paper Without DOI"
author: "Test Author"
---

# Test Paper Content
"""
            test_paper.write_text(test_content, encoding='utf-8')
            
            # DOI抽出テスト（Noneが返される）
            doi = workflow.extract_doi_from_paper(str(test_paper))
            
            self.assertIsNone(doi)
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    # === フォールバック戦略テスト ===
    @patch('code.py.modules.citation_fetcher.api_clients.CrossRefAPIClient')
    @patch('code.py.modules.citation_fetcher.data_quality_evaluator.DataQualityEvaluator')
    def test_fetch_citations_with_fallback_success_first_api(self, mock_quality_evaluator, mock_crossref):
        """フォールバック戦略：第一API成功テスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            # モック設定
            mock_crossref_instance = MagicMock()
            mock_crossref.return_value = mock_crossref_instance  
            mock_crossref_instance.fetch_citations.return_value = [
                {'title': 'Test Citation', 'doi': '10.1000/test'}
            ]
            
            mock_quality_instance = MagicMock()
            mock_quality_evaluator.return_value = mock_quality_instance
            mock_quality_instance.evaluate.return_value = 0.9  # 高品質
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # フォールバック戦略テスト
            result = workflow.fetch_citations_with_fallback("10.1038/s41591-023-1234-5")
            
            # 検証
            self.assertIsNotNone(result)
            self.assertEqual(result['api_used'], 'crossref')
            self.assertEqual(result['quality_score'], 0.9)
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    @patch('code.py.modules.citation_fetcher.api_clients.CrossRefAPIClient')
    @patch('code.py.modules.citation_fetcher.api_clients.SemanticScholarAPIClient')
    @patch('code.py.modules.citation_fetcher.data_quality_evaluator.DataQualityEvaluator')
    def test_fetch_citations_with_fallback_second_api(self, mock_quality_evaluator, mock_semantic, mock_crossref):
        """フォールバック戦略：第二API成功テスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            # モック設定：CrossRefは低品質
            mock_crossref_instance = MagicMock()
            mock_crossref.return_value = mock_crossref_instance
            mock_crossref_instance.fetch_citations.return_value = [
                {'title': 'Low Quality Citation'}
            ]
            
            # SemanticScholarは高品質
            mock_semantic_instance = MagicMock() 
            mock_semantic.return_value = mock_semantic_instance
            mock_semantic_instance.fetch_citations.return_value = [
                {'title': 'High Quality Citation', 'doi': '10.1000/test'}
            ]
            
            mock_quality_instance = MagicMock()
            mock_quality_evaluator.return_value = mock_quality_instance
            mock_quality_instance.evaluate.side_effect = [0.6, 0.8]  # 低品質、高品質
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # フォールバック戦略テスト
            result = workflow.fetch_citations_with_fallback("10.1038/s41591-023-1234-5")
            
            # 検証：SemanticScholarが使用される
            self.assertIsNotNone(result)
            self.assertEqual(result['api_used'], 'semantic_scholar')
            self.assertEqual(result['quality_score'], 0.8)
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    # === references.bib生成テスト ===
    def test_generate_references_bib_basic(self):
        """基本的なreferences.bib生成テスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # テスト用論文ディレクトリ作成
            paper_dir = Path(self.temp_dir) / "smith2023test"
            paper_dir.mkdir()
            paper_path = paper_dir / "smith2023test.md"
            paper_path.write_text("# Test Paper", encoding='utf-8')
            
            # サンプル引用データ
            citation_data = {
                'data': [
                    {
                        'title': 'Reference Paper 1',
                        'authors': 'Smith, John',
                        'journal': 'Nature',
                        'year': 2023,
                        'doi': '10.1038/nature.2023.001'
                    },
                    {
                        'title': 'Reference Paper 2', 
                        'authors': 'Doe, Jane',
                        'journal': 'Science',
                        'year': 2022,
                        'doi': '10.1126/science.2022.002'
                    }
                ]
            }
            
            # references.bib生成
            bib_path = workflow.generate_references_bib(str(paper_path), citation_data)
            
            # 検証
            self.assertTrue(os.path.exists(bib_path))
            self.assertTrue(bib_path.endswith('references.bib'))
            
            # BibTeX内容確認
            with open(bib_path, 'r', encoding='utf-8') as f:
                bib_content = f.read()
            
            self.assertIn('Reference Paper 1', bib_content)
            self.assertIn('Reference Paper 2', bib_content)
            self.assertIn('Smith, John', bib_content)
            self.assertIn('Doe, Jane', bib_content)
            
            # 引用文献番号（number フィールド）の確認
            self.assertIn('number = {1}', bib_content)
            self.assertIn('number = {2}', bib_content)
            
            # タイトルのアルファベット順になっているか確認
            paper1_pos = bib_content.find('Reference Paper 1')
            paper2_pos = bib_content.find('Reference Paper 2')
            # "Reference Paper 1" が "Reference Paper 2" より先に来るはず
            self.assertLess(paper1_pos, paper2_pos)
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    def test_convert_to_bibtex_with_citation_numbers(self):
        """引用文献番号付きBibTeX変換テスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # サンプル引用データ（タイトル順序をテスト）
            citation_data = [
                {
                    'title': 'Zebra Research Methods',
                    'authors': 'Smith, John',
                    'journal': 'Animal Science',
                    'year': 2023,
                    'doi': '10.1000/zebra'
                },
                {
                    'title': 'Alpha Study Results',
                    'authors': 'Doe, Jane', 
                    'journal': 'Nature',
                    'year': 2022,
                    'doi': '10.1000/alpha'
                },
                {
                    'title': 'Beta Analysis Framework',
                    'authors': 'Brown, Bob',
                    'journal': 'Science',
                    'year': 2021,
                    'doi': '10.1000/beta'
                }
            ]
            
            # BibTeX変換
            bibtex_content = workflow._convert_to_bibtex(citation_data)
            
            # 番号付与の確認
            self.assertIn('number = {1}', bibtex_content)
            self.assertIn('number = {2}', bibtex_content)
            self.assertIn('number = {3}', bibtex_content)
            
            # タイトルアルファベット順の確認
            alpha_pos = bibtex_content.find('Alpha Study Results')
            beta_pos = bibtex_content.find('Beta Analysis Framework')
            zebra_pos = bibtex_content.find('Zebra Research Methods')
            
            # Alpha -> Beta -> Zebra の順序
            self.assertLess(alpha_pos, beta_pos)
            self.assertLess(beta_pos, zebra_pos)
            
            # 対応する番号も順序通りに
            alpha_number_pos = bibtex_content.find('number = {1}')
            beta_number_pos = bibtex_content.find('number = {2}')
            zebra_number_pos = bibtex_content.find('number = {3}')
            
            self.assertLess(alpha_number_pos, beta_number_pos)
            self.assertLess(beta_number_pos, zebra_number_pos)
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    # === YAMLヘッダー更新テスト ===
    def test_update_yaml_with_fetch_results(self):
        """YAMLヘッダーのfetch結果更新テスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
            
            # テスト用論文ファイル作成
            paper_path = Path(self.temp_dir) / "test_paper.md"
            initial_content = """---
citation_key: "smith2023test"
workflow_version: "3.2"
processing_status:
  organize: completed
  sync: completed
  fetch: pending
citation_metadata:
  last_updated: null
---

# Test Paper Content
"""
            paper_path.write_text(initial_content, encoding='utf-8')
            
            # サンプル引用データ
            citation_data = {
                'data': [
                    {'title': 'Test Reference', 'doi': '10.1000/test1'},
                    {'title': 'Another Reference', 'doi': '10.1000/test2'}
                ],
                'api_used': 'crossref',
                'quality_score': 0.9,
                'statistics': {
                    'crossref_requests': 1,
                    'success_rate': 1.0
                }
            }
            
            references_bib_path = str(paper_path.parent / "references.bib")
            
            # YAMLヘッダー更新
            workflow.update_yaml_with_fetch_results(
                str(paper_path), citation_data, references_bib_path
            )
            
            # 更新された内容を確認
            updated_content = paper_path.read_text(encoding='utf-8')
            
            self.assertIn('fetch: completed', updated_content)
            self.assertIn('primary_api_used: crossref', updated_content)
            self.assertIn('quality_score: 0.9', updated_content)
            self.assertIn('references.bib', updated_content)
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")


class TestCitationFetcherWorkflowImport(unittest.TestCase):
    """CitationFetcherWorkflowインポートテスト"""
    
    def test_citation_fetcher_workflow_import(self):
        """CitationFetcherWorkflowクラスのインポートテスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            # クラスの存在確認
            self.assertTrue(callable(CitationFetcherWorkflow))
            
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    def test_required_methods_exist(self):
        """必要なメソッドの存在確認"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            
            # モックの設定
            mock_config = MagicMock()
            mock_logger = MagicMock()
            
            workflow = CitationFetcherWorkflow(mock_config, mock_logger)
            
            # 必要なメソッドの存在確認
            required_methods = [
                'process_items',
                'extract_doi_from_paper',
                'fetch_citations_with_fallback',
                'generate_references_bib',
                'update_yaml_with_fetch_results'
            ]
            
            for method_name in required_methods:
                self.assertTrue(hasattr(workflow, method_name))
                self.assertTrue(callable(getattr(workflow, method_name)))
                
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")


if __name__ == '__main__':
    unittest.main() 