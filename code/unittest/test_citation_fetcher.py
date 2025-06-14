"""
CitationFetcher統合テストスイート

引用文献取得システムの包括的テスト。
CrossRef API、OpenCitations API連携、レート制限、エラーハンドリングを検証。
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import time
import json
from pathlib import Path

# モックによるインポート対応（テスト実行環境で確実に動作させる）
try:
    from code.py.modules.citation_fetcher.citation_fetcher import CitationFetcher
    from code.py.modules.shared.exceptions import APIError, BibTeXError
    CITATION_FETCHER_AVAILABLE = True
except ImportError:
    CITATION_FETCHER_AVAILABLE = False
    CitationFetcher = None


class TestCitationFetcherImport(unittest.TestCase):
    """CitationFetcherクラスのインポートテスト"""
    
    def test_citation_fetcher_import(self):
        """CitationFetcherクラスのインポートテスト"""
        if not CITATION_FETCHER_AVAILABLE:
            try:
                from code.py.modules.citation_fetcher.citation_fetcher import CitationFetcher
                self.assertIsNotNone(CitationFetcher)
            except ImportError:
                self.fail("CitationFetcher should be importable")
        else:
            # インポート成功時のテスト
            self.assertIsNotNone(CitationFetcher)


class TestCitationFetcherBasic(unittest.TestCase):
    """CitationFetcherクラスの基本機能テスト"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcher not implemented yet")
        
        # モックオブジェクト作成
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
        
        # 設定デフォルト値
        self.mock_config_manager.get_api_settings.return_value = {
            'crossref': {
                'base_url': 'https://api.crossref.org',
                'rate_limit': 10,  # requests per second
                'timeout': 30
            },
            'opencitations': {
                'base_url': 'https://opencitations.net/index/api/v1',
                'rate_limit': 5,  # requests per second
                'timeout': 30
            }
        }
        
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    def test_citation_fetcher_initialization(self):
        """CitationFetcherクラスの初期化テスト"""
        fetcher = CitationFetcher(self.mock_config_manager, self.mock_logger)
        
        # 基本属性の確認
        self.assertIsNotNone(fetcher.config_manager)
        self.assertIsNotNone(fetcher.logger)
        
        # 設定読み込み確認
        self.mock_config_manager.get_api_settings.assert_called_once()
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    def test_rate_limiting_initialization(self):
        """レート制限機能の初期化テスト"""
        fetcher = CitationFetcher(self.mock_config_manager, self.mock_logger)
        
        # レート制限機能の確認
        self.assertTrue(hasattr(fetcher, 'rate_limiters'))
        self.assertIn('crossref', fetcher.rate_limiters)
        self.assertIn('opencitations', fetcher.rate_limiters)


class TestCitationFetcherCrossRef(unittest.TestCase):
    """CrossRef API連携テスト"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcher not implemented yet")
        
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
        
        self.mock_config_manager.get_api_settings.return_value = {
            'crossref': {
                'base_url': 'https://api.crossref.org',
                'rate_limit': 10,
                'timeout': 30
            },
            'opencitations': {
                'base_url': 'https://opencitations.net/index/api/v1',
                'rate_limit': 5,
                'timeout': 30
            }
        }
        
        self.fetcher = CitationFetcher(self.mock_config_manager, self.mock_logger)
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_fetch_from_crossref_success(self, mock_get):
        """CrossRef APIからの成功的な引用文献取得テスト"""
        # モックレスポンス作成
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'message': {
                'items': [{
                    'DOI': '10.1000/123456',
                    'title': ['Test Paper Title'],
                    'author': [{'given': 'John', 'family': 'Doe'}],
                    'published-print': {'date-parts': [[2023]]},
                    'container-title': ['Test Journal']
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # DOIによる検索テスト
        result = self.fetcher.fetch_from_crossref('10.1000/123456')
        
        # 結果検証
        self.assertIsNotNone(result)
        self.assertEqual(result['doi'], '10.1000/123456')
        self.assertEqual(result['title'], 'Test Paper Title')
        self.assertEqual(result['year'], '2023')
        
        # API呼び出し確認
        mock_get.assert_called_once()
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_fetch_from_crossref_api_error(self, mock_get):
        """CrossRef API エラーハンドリングテスト"""
        # エラーレスポンス作成
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'status': 'error', 'message': 'Not found'}
        mock_get.return_value = mock_response
        
        # APIエラーでの例外発生確認
        with self.assertRaises(APIError):
            self.fetcher.fetch_from_crossref('10.1000/nonexistent')
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_crossref_rate_limiting(self, mock_get):
        """CrossRef APIレート制限テスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'message': {'items': []}
        }
        mock_get.return_value = mock_response
        
        start_time = time.time()
        
        # 複数リクエストでレート制限動作確認
        for i in range(3):
            self.fetcher.fetch_from_crossref(f'10.1000/test{i}')
        
        end_time = time.time()
        
        # レート制限により適切な時間間隔が空いているか確認
        # (10 requests/second = 0.1 second minimum interval)
        self.assertGreaterEqual(end_time - start_time, 0.2)  # 3回で最低0.2秒


class TestCitationFetcherOpenCitations(unittest.TestCase):
    """OpenCitations API連携テスト"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcher not implemented yet")
        
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
        
        self.mock_config_manager.get_api_settings.return_value = {
            'crossref': {
                'base_url': 'https://api.crossref.org',
                'rate_limit': 10,
                'timeout': 30
            },
            'opencitations': {
                'base_url': 'https://opencitations.net/index/api/v1',
                'rate_limit': 5,
                'timeout': 30
            }
        }
        
        self.fetcher = CitationFetcher(self.mock_config_manager, self.mock_logger)
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_fetch_from_opencitations_success(self, mock_get):
        """OpenCitations APIからの成功的な引用文献取得テスト"""
        # モックレスポンス作成
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'cited': 'doi:10.1000/123456',
            'citing': 'doi:10.1000/789012',
            'creation': '2023-01-01',
            'timespan': 'P1Y'
        }]
        mock_get.return_value = mock_response
        
        # DOIによる引用関係取得テスト
        result = self.fetcher.fetch_citations_from_opencitations('10.1000/123456')
        
        # 結果検証
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # API呼び出し確認
        mock_get.assert_called_once()
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_opencitations_rate_limiting(self, mock_get):
        """OpenCitations APIレート制限テスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        start_time = time.time()
        
        # 複数リクエストでレート制限動作確認
        for i in range(3):
            self.fetcher.fetch_citations_from_opencitations(f'10.1000/test{i}')
        
        end_time = time.time()
        
        # レート制限により適切な時間間隔が空いているか確認
        # (5 requests/second = 0.2 second minimum interval)
        self.assertGreaterEqual(end_time - start_time, 0.4)  # 3回で最低0.4秒


class TestCitationFetcherErrorHandling(unittest.TestCase):
    """CitationFetcherエラーハンドリングテスト"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcher not implemented yet")
        
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
        
        self.mock_config_manager.get_api_settings.return_value = {
            'crossref': {
                'base_url': 'https://api.crossref.org',
                'rate_limit': 10,
                'timeout': 30
            },
            'opencitations': {
                'base_url': 'https://opencitations.net/index/api/v1',
                'rate_limit': 5,
                'timeout': 30
            }
        }
        
        self.fetcher = CitationFetcher(self.mock_config_manager, self.mock_logger)
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_network_timeout_handling(self, mock_get):
        """ネットワークタイムアウトエラーハンドリングテスト"""
        # タイムアウト例外をモック
        import requests
        mock_get.side_effect = requests.Timeout("Request timeout")
        
        # タイムアウト時の例外発生確認
        with self.assertRaises(APIError):
            self.fetcher.fetch_from_crossref('10.1000/timeout')
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_connection_error_handling(self, mock_get):
        """接続エラーハンドリングテスト"""
        # 接続エラー例外をモック
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        
        # 接続エラー時の例外発生確認
        with self.assertRaises(APIError):
            self.fetcher.fetch_from_crossref('10.1000/connection_error')
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    def test_invalid_doi_validation(self):
        """無効なDOI検証テスト"""
        # 無効なDOI形式での例外発生確認
        invalid_dois = ['', 'invalid_doi', '10.1000/', 'not_a_doi']
        
        for invalid_doi in invalid_dois:
            with self.assertRaises(APIError):
                self.fetcher.fetch_from_crossref(invalid_doi)
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_retry_mechanism(self, mock_get):
        """リトライ機構テスト"""
        # 最初の2回は失敗、3回目は成功のパターン
        mock_responses = [
            Mock(status_code=500),
            Mock(status_code=503),
            Mock(status_code=200)
        ]
        mock_responses[2].json.return_value = {
            'status': 'ok',
            'message': {'items': []}
        }
        mock_get.side_effect = mock_responses
        
        # リトライ後の成功を確認
        result = self.fetcher.fetch_from_crossref('10.1000/retry_test')
        self.assertIsNotNone(result)
        
        # 3回呼び出されたことを確認
        self.assertEqual(mock_get.call_count, 3)


class TestCitationFetcherIntegration(unittest.TestCase):
    """CitationFetcher統合テスト"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        if not CITATION_FETCHER_AVAILABLE:
            self.skipTest("CitationFetcher not implemented yet")
        
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
        
        self.mock_config_manager.get_api_settings.return_value = {
            'crossref': {
                'base_url': 'https://api.crossref.org',
                'rate_limit': 10,
                'timeout': 30
            },
            'opencitations': {
                'base_url': 'https://opencitations.net/index/api/v1',
                'rate_limit': 5,
                'timeout': 30
            }
        }
        
        self.fetcher = CitationFetcher(self.mock_config_manager, self.mock_logger)
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    @patch('requests.get')
    def test_batch_citation_fetching(self, mock_get):
        """バッチ引用文献取得テスト"""
        # 複数DOIのモックレスポンス
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'message': {
                'items': [{
                    'DOI': '10.1000/123456',
                    'title': ['Test Paper 1'],
                    'author': [{'given': 'John', 'family': 'Doe'}],
                    'published-print': {'date-parts': [[2023]]},
                    'container-title': ['Test Journal']
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # 複数DOIでのバッチ処理テスト
        dois = ['10.1000/123456', '10.1000/789012', '10.1000/345678']
        results = self.fetcher.batch_fetch(dois)
        
        # 結果検証
        self.assertEqual(len(results), len(dois))
        for result in results:
            self.assertIsNotNone(result)
            self.assertIn('doi', result)
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    def test_citation_data_normalization(self):
        """引用データ正規化テスト"""
        # 様々な形式のデータ正規化をテスト
        raw_data = {
            'title': ['Title with Extra Spaces  '],
            'author': [
                {'given': 'John', 'family': 'Doe'},
                {'given': 'Jane', 'family': 'Smith'}
            ],
            'published-print': {'date-parts': [[2023, 5, 15]]},
            'DOI': '10.1000/123456'
        }
        
        normalized = self.fetcher.normalize_citation_data(raw_data)
        
        # 正規化結果の確認
        self.assertEqual(normalized['title'], 'Title with Extra Spaces')
        self.assertEqual(normalized['authors'], 'John Doe, Jane Smith')
        self.assertEqual(normalized['year'], '2023')
        self.assertEqual(normalized['doi'], '10.1000/123456')
    
    @unittest.skipIf(not CITATION_FETCHER_AVAILABLE, "CitationFetcher not implemented yet")
    def test_duplicate_detection(self):
        """重複検出機能テスト"""
        # 重複DOIのリスト
        dois_with_duplicates = [
            '10.1000/123456',
            '10.1000/789012',
            '10.1000/123456',  # 重複
            '10.1000/345678',
            '10.1000/789012'   # 重複
        ]
        
        unique_dois = self.fetcher.remove_duplicate_dois(dois_with_duplicates)
        
        # 重複が除去されていることを確認
        self.assertEqual(len(unique_dois), 3)
        self.assertIn('10.1000/123456', unique_dois)
        self.assertIn('10.1000/789012', unique_dois)
        self.assertIn('10.1000/345678', unique_dois)


if __name__ == '__main__':
    unittest.main() 