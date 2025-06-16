"""
ClaudeAPIClient のユニットテスト

ClaudeAPIClientクラスの機能をテストします。
"""

import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import APIError


class TestClaudeAPIClientImport(unittest.TestCase):
    """ClaudeAPIClientクラスのインポートテスト"""
    
    def test_claude_api_client_import(self):
        """ClaudeAPIClientクラスのインポートテスト"""
        try:
            from code.py.modules.ai_tagging_translation.claude_api_client import ClaudeAPIClient
            self.assertTrue(True, "ClaudeAPIClientクラスのインポートが成功しました")
        except ImportError as e:
            self.fail(f"ClaudeAPIClientクラスのインポートが失敗しました: {e}")


class TestClaudeAPIClientBasic(unittest.TestCase):
    """ClaudeAPIClientクラスの基本機能テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('default_model',): 'claude-3-5-haiku-20241022',
            ('api_key_env',): 'ANTHROPIC_API_KEY',
        }.get(keys, default)
        
        # 環境変数をモック
        self.api_key_patcher = patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-api-key'})
        self.api_key_patcher.start()
        
    def tearDown(self):
        """テストのクリーンアップ"""
        self.api_key_patcher.stop()
    
    def test_claude_api_client_initialization(self):
        """ClaudeAPIClient初期化テスト"""
        from code.py.modules.ai_tagging_translation.claude_api_client import ClaudeAPIClient
        
        client = ClaudeAPIClient(self.config_manager, self.logger)
        
        self.assertIsNotNone(client)
        self.assertEqual(client.model, 'claude-3-5-haiku-20241022')
        self.assertEqual(client.api_key, 'test-api-key')
        self.logger.get_logger.assert_called_with('ClaudeAPIClient')


class TestClaudeAPIClientRequest(unittest.TestCase):
    """ClaudeAPIClientのリクエスト機能テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('default_model',): 'claude-3-5-haiku-20241022',
            ('api_key_env',): 'ANTHROPIC_API_KEY',
        }.get(keys, default)
        
        self.config_manager.get_api_setting.side_effect = lambda key, default=None: {
            'timeout': 30,
            'max_retries': 3,
            'request_delay': 0.5
        }.get(key, default)
        
        # 環境変数をモック
        self.api_key_patcher = patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-api-key'})
        self.api_key_patcher.start()
        
    def tearDown(self):
        """テストのクリーンアップ"""
        self.api_key_patcher.stop()
    
    @patch('anthropic.Anthropic')
    def test_send_request_success(self, mock_anthropic):
        """正常なAPIリクエストテスト"""
        from code.py.modules.ai_tagging_translation.claude_api_client import ClaudeAPIClient
        
        # レスポンスをモック
        mock_response = Mock()
        mock_response.content = [Mock(text='test response')]
        mock_anthropic.return_value.messages.create.return_value = mock_response
        
        client = ClaudeAPIClient(self.config_manager, self.logger)
        response = client.send_request("test prompt")
        
        self.assertEqual(response, 'test response')
        mock_anthropic.return_value.messages.create.assert_called_once()
    
    @patch('anthropic.Anthropic')
    def test_send_request_api_error(self, mock_anthropic):
        """APIエラー時のテスト"""
        from code.py.modules.ai_tagging_translation.claude_api_client import ClaudeAPIClient
        
        # APIエラーをモック
        mock_anthropic.return_value.messages.create.side_effect = Exception("API Error")
        
        client = ClaudeAPIClient(self.config_manager, self.logger)
        
        with self.assertRaises(APIError):
            client.send_request("test prompt")


if __name__ == '__main__':
    unittest.main() 