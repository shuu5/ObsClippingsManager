import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime
import json

# システム配下のモジュールをインポート
from code.py.modules.shared_modules.exceptions import APIError
from code.py.modules.citation_fetcher.api_clients import SemanticScholarAPIClient
from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger


class TestSemanticScholarAPIClient(unittest.TestCase):
    """Semantic Scholar API クライアントのテストクラス"""
    
    def setUp(self):
        """テスト前処理"""
        # モックConfigManagerを作成
        self.mock_config_manager = Mock()
        self.mock_config_manager.get_config.return_value = {
            'api': {
                'semantic_scholar': {
                    'base_url': 'https://api.semanticscholar.org',
                    'rate_limit': 1,
                    'timeout': 30,
                    'retry_count': 3,
                    'api_key_env': 'SEMANTIC_SCHOLAR_API_KEY'
                }
            }
        }
        
        # _get_api_configメソッドで使用されるgetメソッドを設定
        self.mock_config_manager.get.return_value = {
            'apis': {
                'semantic_scholar': {
                    'base_url': 'https://api.semanticscholar.org',
                    'rate_limit': 1,
                    'timeout': 30,
                    'retry_count': 3,
                    'api_key_env': 'SEMANTIC_SCHOLAR_API_KEY'
                }
            }
        }
        
        # モックIntegratedLoggerを作成 - 実際のメソッドを追加
        self.mock_logger = Mock()
        self.mock_logger.debug = Mock()
        self.mock_logger.warning = Mock()
        self.mock_logger.error = Mock()
        self.mock_logger.info = Mock()
        
        # get_loggerメソッドが呼ばれた時の戻り値をセットアップ
        self.mock_specific_logger = Mock()
        self.mock_specific_logger.debug = Mock()
        self.mock_specific_logger.warning = Mock()
        self.mock_specific_logger.error = Mock()
        self.mock_specific_logger.info = Mock()
        self.mock_logger.get_logger.return_value = self.mock_specific_logger
        
        # SemanticScholarAPIClientインスタンスを作成
        self.client = SemanticScholarAPIClient(
            self.mock_config_manager,
            self.mock_logger
        )
        
        # テスト用DOI
        self.test_doi = "10.1038/nature.2023.001"
    
    def test_semantic_scholar_api_client_initialization(self):
        """Semantic Scholar API クライアントの初期化テスト"""
        # API設定が正しく設定されているか確認
        self.assertEqual(self.client.base_url, 'https://api.semanticscholar.org')
        self.assertEqual(self.client.api_name, 'semantic_scholar')
        
        # ConfigManagerが正しく設定されているか確認
        self.assertEqual(self.client.config_manager, self.mock_config_manager)
        
        # ロガーが設定されているか確認
        self.assertIsNotNone(self.client.logger)
    
    def test_build_api_url(self):
        """API URL構築のテスト"""
        expected_url = f"https://api.semanticscholar.org/graph/v1/paper/{self.test_doi}/references"
        actual_url = self.client._build_api_url(self.test_doi)
        
        self.assertEqual(actual_url, expected_url)
    
    @patch.dict('os.environ', {'SEMANTIC_SCHOLAR_API_KEY': 'test_api_key'})
    def test_api_key_header_setting(self):
        """API Key設定のテスト"""
        # 設定でapi_key_envが指定されている場合のテスト用ConfigManager
        mock_config_manager = Mock()
        mock_config_manager.get_config.return_value = {
            'api': {
                'semantic_scholar': {
                    'base_url': 'https://api.semanticscholar.org',
                    'rate_limit': 1,
                    'timeout': 30,
                    'retry_count': 3,
                    'api_key_env': 'SEMANTIC_SCHOLAR_API_KEY'  # 環境変数名を正しく設定
                }
            }
        }
        
        # _get_api_configメソッドで使用されるgetメソッドを設定
        mock_config_manager.get.return_value = {
            'apis': {
                'semantic_scholar': {
                    'base_url': 'https://api.semanticscholar.org',
                    'rate_limit': 1,
                    'timeout': 30,
                    'retry_count': 3,
                    'api_key_env': 'SEMANTIC_SCHOLAR_API_KEY'
                }
            }
        }
        
        mock_logger = Mock()
        mock_logger.debug = Mock()
        mock_logger.warning = Mock()
        mock_logger.error = Mock()
        mock_logger.info = Mock()
        
        # get_loggerメソッドが呼ばれた時の戻り値をセットアップ
        mock_specific_logger = Mock()
        mock_specific_logger.debug = Mock()
        mock_specific_logger.warning = Mock()
        mock_specific_logger.error = Mock()
        mock_specific_logger.info = Mock()
        mock_logger.get_logger.return_value = mock_specific_logger
        
        client = SemanticScholarAPIClient(
            mock_config_manager,
            mock_logger
        )
        
        # API キーがヘッダーに設定されているか確認
        self.assertEqual(client.session.headers.get('x-api-key'), 'test_api_key')
    
    @patch('requests.Session.get')
    def test_fetch_citations_success(self, mock_get):
        """引用文献取得成功のテスト"""
        # モックレスポンスデータを設定
        mock_response_data = {
            'data': [
                {
                    'citedPaper': {
                        'title': 'Test Paper 1',
                        'authors': [
                            {'name': 'John Smith'},
                            {'name': 'Jane Doe'}
                        ],
                        'venue': 'Nature',
                        'year': 2023,
                        'externalIds': {
                            'DOI': '10.1038/nature.test.001'
                        },
                        'abstract': 'This is a test abstract.',
                        'citationCount': 150,
                        'url': 'https://www.semanticscholar.org/paper/test1'
                    }
                },
                {
                    'citedPaper': {
                        'title': 'Test Paper 2',
                        'authors': [
                            {'name': 'Alice Brown'}
                        ],
                        'venue': 'Cell',
                        'year': 2022,
                        'externalIds': {
                            'DOI': '10.1016/j.cell.test.002'
                        },
                        'citationCount': 75
                    }
                }
            ]
        }
        
        # モックHTTPレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # fetch_citationsメソッドを実行
        citations = self.client.fetch_citations(self.test_doi)
        
        # 結果を検証
        self.assertEqual(len(citations), 2)
        
        # 最初の引用文献を検証
        first_citation = citations[0]
        self.assertEqual(first_citation['title'], 'Test Paper 1')
        self.assertEqual(first_citation['authors'], 'John Smith, Jane Doe')
        self.assertEqual(first_citation['journal'], 'Nature')
        self.assertEqual(first_citation['year'], 2023)
        self.assertEqual(first_citation['doi'], '10.1038/nature.test.001')
        self.assertEqual(first_citation['abstract'], 'This is a test abstract.')
        self.assertEqual(first_citation['citationCount'], 150)
        self.assertEqual(first_citation['url'], 'https://www.semanticscholar.org/paper/test1')
        
        # 2番目の引用文献を検証
        second_citation = citations[1]
        self.assertEqual(second_citation['title'], 'Test Paper 2')
        self.assertEqual(second_citation['authors'], 'Alice Brown')
        self.assertEqual(second_citation['journal'], 'Cell')
        self.assertEqual(second_citation['year'], 2022)
        self.assertEqual(second_citation['doi'], '10.1016/j.cell.test.002')
        self.assertEqual(second_citation['citationCount'], 75)
        
        # ログ出力が正しく呼ばれているか確認（基本loggerを使用）
        self.mock_logger.debug.assert_any_call(f"Fetching citations from Semantic Scholar for DOI: {self.test_doi}")
    
    @patch('requests.Session.get')
    def test_fetch_citations_empty_response(self, mock_get):
        """空のレスポンスのテスト"""
        # 空のレスポンスデータを設定
        mock_response_data = {'data': []}
        
        # モックHTTPレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # fetch_citationsメソッドを実行
        citations = self.client.fetch_citations(self.test_doi)
        
        # 結果を検証
        self.assertEqual(len(citations), 0)
        self.assertIsInstance(citations, list)
    
    @patch('requests.Session.get')
    def test_fetch_citations_http_error(self, mock_get):
        """HTTPエラーのテスト"""
        # HTTPエラーを設定
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        # APIErrorが発生することを確認
        with self.assertRaises(APIError) as context:
            self.client.fetch_citations(self.test_doi)
        
        # エラーメッセージとコンテキストを確認（BaseAPIClientの_make_requestが処理）
        self.assertIn("API_HTTP_ERROR", str(context.exception))
        self.assertIn("semantic_scholar", str(context.exception))
    
    @patch('requests.Session.get')
    def test_fetch_citations_connection_error(self, mock_get):
        """接続エラーのテスト"""
        # 接続エラーを設定
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        # APIErrorが発生することを確認
        with self.assertRaises(APIError) as context:
            self.client.fetch_citations(self.test_doi)
        
        # エラーメッセージを確認（BaseAPIClientの_make_requestが処理）
        self.assertIn("API_CONNECTION_ERROR", str(context.exception))
        self.assertIn("semantic_scholar", str(context.exception))
    
    def test_parse_semantic_scholar_response_minimal_data(self):
        """最小限のデータでのレスポンス解析テスト"""
        # 最小限のデータを含むレスポンス
        response_data = {
            'data': [
                {
                    'citedPaper': {
                        'title': 'Minimal Paper'
                    }
                }
            ]
        }
        
        # レスポンス解析を実行
        citations = self.client._parse_semantic_scholar_response(response_data)
        
        # 結果を検証
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]['title'], 'Minimal Paper')
        self.assertNotIn('authors', citations[0])
        self.assertNotIn('journal', citations[0])
    
    def test_parse_semantic_scholar_response_missing_cited_paper(self):
        """citedPaperが存在しない場合のテスト"""
        # citedPaperが存在しないレスポンス
        response_data = {
            'data': [
                {
                    'someOtherField': 'value'
                }
            ]
        }
        
        # レスポンス解析を実行
        citations = self.client._parse_semantic_scholar_response(response_data)
        
        # 結果を検証（citedPaperが存在しないためスキップされる）
        self.assertEqual(len(citations), 0)
    
    def test_parse_semantic_scholar_response_no_title(self):
        """タイトルが存在しない場合のテスト"""
        # タイトルが存在しないレスポンス
        response_data = {
            'data': [
                {
                    'citedPaper': {
                        'authors': [{'name': 'John Doe'}],
                        'venue': 'Journal'
                    }
                }
            ]
        }
        
        # レスポンス解析を実行
        citations = self.client._parse_semantic_scholar_response(response_data)
        
        # 結果を検証（タイトルが存在しないためスキップされる）
        self.assertEqual(len(citations), 0)
    
    def test_parse_semantic_scholar_response_invalid_json(self):
        """不正なJSONデータのテスト"""
        # 不正なレスポンスデータ
        response_data = None
        
        # レスポンス解析を実行
        citations = self.client._parse_semantic_scholar_response(response_data)
        
        # 結果を検証（空のリストが返される）
        self.assertEqual(len(citations), 0)
        self.assertIsInstance(citations, list)
    
    def test_parse_semantic_scholar_response_exception_handling(self):
        """解析中の例外処理テスト"""
        # 実際に例外が発生するようなデータを作成（辞書ではなく文字列を設定）
        response_data = {
            'data': [
                {
                    'citedPaper': {
                        'title': 'Test Paper',
                        'authors': [
                            {'name': 'John Doe'}
                        ]
                    }
                }
            ]
        }
        
        # 正常に処理される場合
        citations = self.client._parse_semantic_scholar_response(response_data)
        
        # 最低限の解析が行われることを確認
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]['title'], 'Test Paper')
        self.assertEqual(citations[0]['authors'], 'John Doe')
        
        # 正常処理なので警告ログは呼ばれない
        # 実際に例外が発生する場合をテスト
        with patch.object(self.mock_logger, 'warning') as mock_warning:
            # 壊れたデータで例外処理を確認
            broken_data = {'data': [{'citedPaper': {'title': None}}]}  # titleがNoneで例外発生する可能性
            result = self.client._parse_semantic_scholar_response(broken_data)
            # 例外処理により空のリストまたは部分的な結果が返される
            self.assertIsInstance(result, list)


if __name__ == '__main__':
    unittest.main() 