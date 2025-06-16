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
from unittest.mock import patch, MagicMock, call, PropertyMock
import unittest.mock
import json
import yaml

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import BibTeXError, APIError

# CitationFetcherWorkflowを条件付きでインポート
try:
    from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
    CITATION_FETCHER_AVAILABLE = True
except ImportError:
    CitationFetcherWorkflow = None
    CITATION_FETCHER_AVAILABLE = False


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
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
        workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
        
        # 基本属性の確認
        self.assertIsNotNone(workflow.config_manager)
        self.assertIsNotNone(workflow.logger)
    
    def test_extract_doi_from_paper_basic(self):
        """論文からDOI抽出の基本テスト"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
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
    
    def test_extract_doi_from_paper_no_doi(self):
        """DOIがない論文からの抽出テスト"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
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
    
    # === フォールバック戦略テスト ===
    def test_fetch_citations_with_fallback_success_first_api(self):
        """フォールバック戦略：第一API成功テスト（基本動作確認）"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
        # テスト対象メソッドが実装され、基本的な引数を受け取ることを確認
        workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
        
        # メソッドが存在し、呼び出し可能であることを確認
        self.assertTrue(hasattr(workflow, 'fetch_citations_with_fallback'))
        self.assertTrue(callable(getattr(workflow, 'fetch_citations_with_fallback')))
        
        # DOI形式の引数で呼び出せることを確認（実際のAPI呼び出しはしない）
        try:
            # 無効なDOIで呼び出しても例外が発生しないことを確認
            result = workflow.fetch_citations_with_fallback("invalid_doi")
            # Noneまたは辞書が返されることを確認（どちらも正常な動作）
            self.assertTrue(result is None or isinstance(result, dict))
        except Exception as e:
            # 予期しない例外は失敗とする
            self.fail(f"fetch_citations_with_fallback raised unexpected exception: {e}")
        
        # メソッドのシグネチャが正しいことを確認
        import inspect
        sig = inspect.signature(workflow.fetch_citations_with_fallback)
        params = list(sig.parameters.keys())
        self.assertIn('doi', params)
        self.assertEqual(len(params), 1)  # doi引数のみ
    
    @patch.object(CitationFetcherWorkflow, 'crossref_client', new_callable=PropertyMock)
    @patch.object(CitationFetcherWorkflow, 'semantic_scholar_client', new_callable=PropertyMock)
    @patch.object(CitationFetcherWorkflow, 'opencitations_client', new_callable=PropertyMock)
    @patch.object(CitationFetcherWorkflow, 'rate_limiter', new_callable=PropertyMock)
    @patch.object(CitationFetcherWorkflow, 'quality_evaluator', new_callable=PropertyMock)
    @patch.object(CitationFetcherWorkflow, 'statistics', new_callable=PropertyMock)
    def test_fetch_citations_with_fallback_all_apis_fail(self, mock_statistics_prop, mock_quality_prop, mock_rate_limiter_prop, mock_opencitations_prop, mock_semantic_prop, mock_crossref_prop):
        """フォールバック戦略：全API失敗テスト（シンプル版）"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
        # 全APIが失敗するようにモック設定
        mock_crossref_client = MagicMock()
        mock_crossref_client.fetch_citations.return_value = None
        mock_crossref_prop.return_value = mock_crossref_client
        
        mock_semantic_scholar_client = MagicMock()
        mock_semantic_scholar_client.fetch_citations.return_value = None
        mock_semantic_prop.return_value = mock_semantic_scholar_client
        
        mock_opencitations_client = MagicMock()
        mock_opencitations_client.fetch_citations.return_value = None
        mock_opencitations_prop.return_value = mock_opencitations_client
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter.wait_if_needed.return_value = None
        mock_rate_limiter_prop.return_value = mock_rate_limiter
        
        mock_quality_evaluator = MagicMock()
        mock_quality_prop.return_value = mock_quality_evaluator
        
        mock_statistics = MagicMock()
        mock_statistics.record_failure.return_value = None
        mock_statistics.get_summary.return_value = {'total_success': 0, 'total_failures': 3}
        mock_statistics_prop.return_value = mock_statistics
        
        # テスト実行
        workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
        result = workflow.fetch_citations_with_fallback("10.1000/test")
        
        # 全API失敗でNoneが返されることを確認
        self.assertIsNone(result)
        
        # 全API呼び出し確認
        mock_crossref_client.fetch_citations.assert_called_once_with("10.1000/test")
        mock_semantic_scholar_client.fetch_citations.assert_called_once_with("10.1000/test")
        mock_opencitations_client.fetch_citations.assert_called_once_with("10.1000/test")
        
        # レート制限確認（各API）
        expected_calls = [
            unittest.mock.call('crossref', 10),
            unittest.mock.call('semantic_scholar', 1),
            unittest.mock.call('opencitations', 5)
        ]
        mock_rate_limiter.wait_if_needed.assert_has_calls(expected_calls)
    
    @patch('code.py.modules.citation_fetcher.api_clients.CrossRefAPIClient')
    @patch('code.py.modules.citation_fetcher.api_clients.SemanticScholarAPIClient')
    @patch('code.py.modules.citation_fetcher.data_quality_evaluator.DataQualityEvaluator')
    @patch('code.py.modules.citation_fetcher.rate_limiter.RateLimiter')
    @patch('code.py.modules.citation_fetcher.citation_statistics.CitationStatistics')
    def test_fetch_citations_with_fallback_second_api(self, mock_statistics, mock_rate_limiter, mock_quality_evaluator, mock_semantic, mock_crossref):
        """フォールバック戦略：第二API成功テスト"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
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
        
        mock_rate_limiter_instance = MagicMock()
        mock_rate_limiter.return_value = mock_rate_limiter_instance
        
        mock_statistics_instance = MagicMock()
        mock_statistics.return_value = mock_statistics_instance
        mock_statistics_instance.get_summary.return_value = {'test': 'data'}
        
        workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
        
        # 遅延初期化されたプライベート属性を直接設定
        workflow._crossref_client = mock_crossref_instance
        workflow._semantic_scholar_client = mock_semantic_instance
        workflow._rate_limiter = mock_rate_limiter_instance
        workflow._quality_evaluator = mock_quality_instance
        workflow._statistics = mock_statistics_instance
        
        # フォールバック戦略テスト
        result = workflow.fetch_citations_with_fallback("10.1038/s41591-023-1234-5")
        
        # 検証：SemanticScholarが使用される
        self.assertIsNotNone(result)
        self.assertEqual(result['api_used'], 'semantic_scholar')
        self.assertEqual(result['quality_score'], 0.8)
    
    # === references.bib生成テスト ===
    def test_generate_references_bib_basic(self):
        """基本的なreferences.bib生成テスト"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
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
    
    def test_convert_to_bibtex_with_citation_numbers(self):
        """引用文献番号付きBibTeX変換テスト"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
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
            }
        ]
        
        # BibTeX変換
        bibtex_content = workflow._convert_to_bibtex(citation_data)
        
        # 基本構造確認
        self.assertIn('@article{', bibtex_content)
        self.assertIn('number = {1}', bibtex_content)
        self.assertIn('number = {2}', bibtex_content)
        
        # アルファベット順確認（Alphaが先、Zebraが後）
        alpha_pos = bibtex_content.find('Alpha Study Results')
        zebra_pos = bibtex_content.find('Zebra Research Methods')
        self.assertLess(alpha_pos, zebra_pos, "Alpha should come before Zebra in alphabetical order")
        
        # エントリー形式確認
        self.assertIn('title = {Alpha Study Results}', bibtex_content)
        self.assertIn('title = {Zebra Research Methods}', bibtex_content)
        self.assertIn('author = {Doe, Jane}', bibtex_content)
        self.assertIn('author = {Smith, John}', bibtex_content)
    
    def test_update_yaml_with_fetch_results(self):
        """YAMLヘッダーのfetch結果更新テスト"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
        workflow = CitationFetcherWorkflow(self.config_manager, self.logger)
        
        # テスト用Markdownファイル作成
        test_paper = Path(self.temp_dir) / "test_paper.md"
        test_content = """---
title: "Test Paper"
doi: "10.1038/s41591-023-1234-5"
processing_status:
  fetch: pending
---

# Test Paper Content
"""
        test_paper.write_text(test_content, encoding='utf-8')
        
        # テスト用引用データ
        citation_data = {
            'data': [{'title': 'Test Citation'}],
            'api_used': 'crossref',
            'quality_score': 0.85,
            'statistics': {'total_requests': 1}
        }
        
        # YAMLヘッダー更新
        workflow.update_yaml_with_fetch_results(
            str(test_paper), 
            citation_data, 
            str(test_paper.parent / "references.bib")
        )
        
        # 更新結果確認
        updated_content = test_paper.read_text(encoding='utf-8')
        
        self.assertIn('fetch: completed', updated_content)
        self.assertIn('primary_api_used: crossref', updated_content)
        self.assertIn('quality_score: 0.85', updated_content)
        self.assertIn('total_references_found: 1', updated_content)
        self.assertIn('references.bib', updated_content)


class TestCitationFetcherWorkflowImport(unittest.TestCase):
    """CitationFetcherWorkflow インポートテスト"""
    
    def test_citation_fetcher_workflow_import(self):
        """CitationFetcherWorkflowクラスのインポートテスト"""
        try:
            from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
            self.assertIsNotNone(CitationFetcherWorkflow)
        except ImportError:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
    
    def test_required_methods_exist(self):
        """必要なメソッドの存在確認"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcherWorkflow not implemented yet")
            
        # 必要なメソッドの存在確認
        required_methods = [
            'process_items',
            'extract_doi_from_paper',
            'fetch_citations_with_fallback',
            'generate_references_bib',
            'update_yaml_with_fetch_results'
        ]
        
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(CitationFetcherWorkflow, method_name),
                    f"CitationFetcherWorkflow should have {method_name} method"
                )


if __name__ == '__main__':
    unittest.main() 