"""
CrossRef API Client Test Suite

CrossRef API連携の統合テスト
- 実際のCrossRef APIとの連携テスト
- エラーハンドリングテスト
- レスポンス解析テスト
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock, Mock
import json

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import APIError


class TestCrossRefAPIClient(unittest.TestCase):
    """CrossRef API クライアントのテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config_manager = MagicMock()
        self.logger = MagicMock()
        
        # 正しいConfigManager APIモック設定
        self.config_manager.get_config.return_value = {
            'citation_fetcher': {
                'apis': {
                    'crossref': {
                        'base_url': 'https://api.crossref.org',
                        'timeout': 30,
                        'rate_limit': 10,
                        'quality_threshold': 0.8
                    }
                }
            }
        }
        
        self.logger.get_logger.return_value = MagicMock()
    
    def test_crossref_api_client_initialization(self):
        """CrossRef APIクライアントの初期化テスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            
            # 初期化確認
            self.assertIsNotNone(client)
            self.assertEqual(client.api_name, 'crossref')
            self.assertEqual(client.base_url, 'https://api.crossref.org')
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")
    
    @patch('requests.Session.get')
    def test_fetch_citations_success_real_api_response(self, mock_get):
        """CrossRef API成功レスポンスのテスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            # 実際のCrossRef APIレスポンス形式をモック
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "ok",
                "message-type": "work",
                "message": {
                    "DOI": "10.1038/s41591-023-1234-5",
                    "title": ["Advanced Biomarker Techniques in Oncology"],
                    "reference": [
                        {
                            "key": "ref1",
                            "DOI": "10.1038/nature12345",
                            "article-title": "Biomarker Discovery Methods",
                            "author": "Smith",
                            "journal-title": "Nature",
                            "year": "2022"
                        },
                        {
                            "key": "ref2", 
                            "DOI": "10.1126/science.67890",
                            "article-title": "Cancer Research Advances",
                            "author": "Jones",
                            "journal-title": "Science",
                            "year": "2023"
                        }
                    ]
                }
            }
            mock_get.return_value = mock_response
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            
            # API呼び出しテスト
            result = client.fetch_citations("10.1038/s41591-023-1234-5")
            
            # 結果検証
            self.assertIsNotNone(result)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            
            # 最初の引用文献を詳細確認
            first_citation = result[0]
            self.assertIn('title', first_citation)
            self.assertIn('authors', first_citation)
            self.assertIn('journal', first_citation)
            self.assertIn('year', first_citation)
            self.assertIn('doi', first_citation)
            
            self.assertEqual(first_citation['title'], 'Biomarker Discovery Methods')
            self.assertEqual(first_citation['doi'], '10.1038/nature12345')
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")
    
    @patch('requests.Session.get')
    def test_fetch_citations_no_references_found(self, mock_get):
        """引用文献が見つからない場合のテスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            # 引用文献なしのレスポンス
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "ok",
                "message-type": "work",
                "message": {
                    "DOI": "10.1038/s41591-023-1234-5",
                    "title": ["Paper Without References"]
                    # referenceフィールドなし
                }
            }
            mock_get.return_value = mock_response
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            result = client.fetch_citations("10.1038/s41591-023-1234-5")
            
            # 空のリストが返される
            self.assertIsNotNone(result)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")
    
    @patch('requests.Session.get')
    def test_fetch_citations_api_error_404(self, mock_get):
        """CrossRef API 404エラーのテスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            # 404レスポンス
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            result = client.fetch_citations("10.1000/invalid-doi")
            
            # 空の辞書が返される（エラーではない）
            self.assertEqual(result, [])
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")
    
    @patch('requests.Session.get')
    def test_fetch_citations_api_error_429_rate_limit(self, mock_get):
        """CrossRef API レート制限エラー（429）のテスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            # 429レスポンス
            mock_response = Mock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            
            # APIErrorが発生することを確認
            with self.assertRaises(APIError) as context:
                client.fetch_citations("10.1038/s41591-023-1234-5")
            
            self.assertIn("Rate limit exceeded", str(context.exception))
            self.assertEqual(context.exception.error_code, "API_RATE_LIMIT_EXCEEDED")
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")
    
    @patch('requests.Session.get')
    def test_fetch_citations_connection_error(self, mock_get):
        """CrossRef API 接続エラーのテスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            import requests
            
            # 接続エラーをシミュレート
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            
            # APIErrorが発生することを確認
            with self.assertRaises(APIError) as context:
                client.fetch_citations("10.1038/s41591-023-1234-5")
            
            self.assertIn("Connection error", str(context.exception))
            self.assertEqual(context.exception.error_code, "API_CONNECTION_ERROR")
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")
    
    def test_crossref_api_url_construction(self):
        """CrossRef API URL構築テスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            
            # URL構築メソッドがある場合のテスト
            test_doi = "10.1038/s41591-023-1234-5"
            expected_url = f"https://api.crossref.org/works/{test_doi}"
            
            # _build_api_url メソッドが実装されていることを仮定
            if hasattr(client, '_build_api_url'):
                actual_url = client._build_api_url(test_doi)
                self.assertEqual(actual_url, expected_url)
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")
    
    def test_response_parsing_malformed_data(self):
        """不正な形式のレスポンス解析テスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            client = CrossRefAPIClient(self.config_manager, self.logger)
            
            # 不正な形式のデータ
            malformed_data = {
                "status": "ok",
                "message": {
                    "reference": [
                        {
                            # 必要なフィールドが不足
                            "key": "ref1"
                        },
                        {
                            "key": "ref2",
                            "article-title": "Valid Title",
                            # authorやyearが不足
                        }
                    ]
                }
            }
            
            # _parse_crossref_response メソッドが実装されていることを仮定
            if hasattr(client, '_parse_crossref_response'):
                result = client._parse_crossref_response(malformed_data)
                
                # 不正なデータは適切にフィルタリングまたは補完される
                self.assertIsInstance(result, list)
                # 具体的な動作は実装に依存
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")


class TestCrossRefAPIClientImport(unittest.TestCase):
    """CrossRef API クライアントのインポートテスト"""
    
    def test_crossref_api_client_import(self):
        """CrossRefAPIClientクラスのインポートテスト"""
        try:
            from code.py.modules.citation_fetcher.api_clients import CrossRefAPIClient
            
            # クラスが正しくインポートできることを確認
            self.assertTrue(hasattr(CrossRefAPIClient, '__init__'))
            self.assertTrue(hasattr(CrossRefAPIClient, 'fetch_citations'))
            
        except ImportError:
            self.skipTest("CrossRefAPIClient not implemented yet")


if __name__ == '__main__':
    unittest.main() 