"""
OpenCitations API Client Unit Tests

OpenCitations APIクライアントの機能をテストする
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# パスを追加してモジュールをインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from code.py.modules.citation_fetcher.api_clients import OpenCitationsAPIClient
from code.py.modules.shared_modules.exceptions import APIError
from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger


class TestOpenCitationsAPIClient(unittest.TestCase):
    """OpenCitations APIクライアントのテストクラス"""
    
    def setUp(self):
        """テストの前準備"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.mock_logger_instance = Mock()
        self.logger.get_logger.return_value = self.mock_logger_instance
        
        self.client = OpenCitationsAPIClient(self.config_manager, self.logger)
    
    def test_opencitations_api_client_initialization(self):
        """OpenCitations APIクライアントの初期化テスト"""
        # configの確認
        self.assertIsNotNone(self.client.config_manager)
        self.assertIsNotNone(self.client.logger)
        self.assertEqual(self.client.base_url, 'https://opencitations.net/index/api/v1')
    
    def test_opencitations_api_url_construction(self):
        """OpenCitations API URL構築テスト"""
        doi = "10.1186/1756-8722-6-59"
        expected_url = "https://opencitations.net/index/api/v1/references/10.1186/1756-8722-6-59"
        
        url = self.client._build_api_url(doi)
        self.assertEqual(url, expected_url)
    
    @patch('code.py.modules.citation_fetcher.api_clients.requests.Session.get')
    def test_fetch_citations_success_real_api_response(self, mock_get):
        """OpenCitations API成功レスポンスのテスト"""
        # モックレスポンス（実際のOpenCitations APIレスポンス形式）
        mock_response_data = [
            {
                "oci": "06190834283-06101389277",
                "citing": "10.1186/1756-8722-6-59",
                "cited": "10.1124/dmd.111.040840",
                "creation": "2013-08-19",
                "timespan": "P2Y1M11D",
                "journal_sc": "no",
                "author_sc": "no"
            },
            {
                "oci": "06190834283-06102258727",
                "citing": "10.1186/1756-8722-6-59",
                "cited": "10.1093/hmg/3.10.1743",
                "creation": "2013-08-19",
                "timespan": "P19Y",
                "journal_sc": "no",
                "author_sc": "no"
            }
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response
        
        # テスト実行
        doi = "10.1186/1756-8722-6-59"
        result = self.client.fetch_citations(doi)
        
        # 結果検証
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        # 最初の引用文献の検証
        first_citation = result[0]
        self.assertIn('doi', first_citation)
        self.assertEqual(first_citation['doi'], '10.1124/dmd.111.040840')
        self.assertIn('oci', first_citation)
        self.assertEqual(first_citation['oci'], '06190834283-06101389277')
        self.assertIn('creation', first_citation)
        self.assertEqual(first_citation['creation'], '2013-08-19')
        self.assertIn('timespan', first_citation)
        self.assertEqual(first_citation['timespan'], 'P2Y1M11D')
    
    @patch('code.py.modules.citation_fetcher.api_clients.requests.Session.get')
    def test_fetch_citations_no_references_found(self, mock_get):
        """引用文献が見つからない場合のテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        doi = "10.1000/nonexistent.doi"
        result = self.client.fetch_citations(doi)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    @patch('code.py.modules.citation_fetcher.api_clients.requests.Session.get')
    def test_fetch_citations_api_error_404(self, mock_get):
        """OpenCitations API 404エラーのテスト"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        doi = "10.1000/nonexistent.doi"
        result = self.client.fetch_citations(doi)
        
        # 404の場合は空のレスポンスが返される
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    @patch('code.py.modules.citation_fetcher.api_clients.requests.Session.get')
    def test_fetch_citations_api_error_429_rate_limit(self, mock_get):
        """OpenCitations API レート制限エラー（429）のテスト"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        doi = "10.1186/1756-8722-6-59"
        
        with self.assertRaises(APIError) as context:
            self.client.fetch_citations(doi)
        
        self.assertIn("API_RATE_LIMIT_EXCEEDED", str(context.exception))
        self.assertIn("opencitations", str(context.exception))
    
    @patch('code.py.modules.citation_fetcher.api_clients.requests.Session.get')
    def test_fetch_citations_connection_error(self, mock_get):
        """OpenCitations API 接続エラーのテスト"""
        from requests.exceptions import ConnectionError
        
        mock_get.side_effect = ConnectionError("Connection failed")
        
        doi = "10.1186/1756-8722-6-59"
        
        with self.assertRaises(APIError) as context:
            self.client.fetch_citations(doi)
        
        self.assertIn("API_CONNECTION_ERROR", str(context.exception))
        self.assertIn("opencitations", str(context.exception))
    
    def test_response_parsing_malformed_data(self):
        """不正な形式のレスポンス解析テスト"""
        # 不正なレスポンスデータ
        malformed_data = [
            {
                "invalid_field": "some_value"
                # 必要なフィールドが不足
            },
            {
                "cited": "10.1000/test.doi"
                # 他のフィールドが不足
            }
        ]
        
        result = self.client._parse_opencitations_response(malformed_data)
        
        # 不正なデータでも空のリストまたは部分的なデータが返される
        self.assertIsInstance(result, list)
        # 少なくとも2番目のアイテムはDOIが含まれているので処理される
        self.assertGreaterEqual(len(result), 1)
    
    @patch('code.py.modules.citation_fetcher.api_clients.requests.Session.get')
    def test_fetch_citations_json_parsing_error(self, mock_get):
        """JSON解析エラーのテスト"""
        import json
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid JSON response"
        mock_get.return_value = mock_response
        
        doi = "10.1186/1756-8722-6-59"
        
        with self.assertRaises(APIError) as context:
            self.client.fetch_citations(doi)
        
        self.assertIn("API_INVALID_JSON", str(context.exception))
        self.assertIn("opencitations", str(context.exception))
    
    def test_normalize_doi_for_api(self):
        """DOI正規化（OpenCitations API用）のテスト"""
        # DOI URLプレフィックスの除去
        doi_with_prefix = "https://doi.org/10.1186/1756-8722-6-59"
        normalized = self.client._normalize_doi_for_api(doi_with_prefix)
        self.assertEqual(normalized, "10.1186/1756-8722-6-59")
        
        # 既に正規化済みのDOI
        clean_doi = "10.1186/1756-8722-6-59"
        normalized = self.client._normalize_doi_for_api(clean_doi)
        self.assertEqual(normalized, clean_doi)
    
    def test_rate_limit_compliance(self):
        """レート制限遵守のテスト（5req/sec）"""
        # レート制限の設定確認
        self.assertEqual(self.client.rate_limit, 5)
        
        # 最低限の間隔確認（1秒あたり5リクエスト = 0.2秒間隔）
        min_interval = 1.0 / 5  # 0.2秒
        self.assertAlmostEqual(self.client.min_request_interval, min_interval, places=2)


class TestOpenCitationsAPIClientImport(unittest.TestCase):
    """OpenCitations APIクライアントインポートテスト"""
    
    def test_opencitations_api_client_import(self):
        """OpenCitationsAPIClientクラスのインポートテスト"""
        from code.py.modules.citation_fetcher.api_clients import OpenCitationsAPIClient
        self.assertTrue(hasattr(OpenCitationsAPIClient, 'fetch_citations'))
        self.assertTrue(hasattr(OpenCitationsAPIClient, '_build_api_url'))
        self.assertTrue(hasattr(OpenCitationsAPIClient, '_parse_opencitations_response'))


if __name__ == '__main__':
    unittest.main() 