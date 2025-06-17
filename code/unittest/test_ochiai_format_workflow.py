"""
テスト: OchiaiFormatWorkflow
落合フォーマット6項目要約生成機能のテスト
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import os
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from code.py.modules.ai_tagging_translation.ochiai_format_workflow import OchiaiFormatWorkflow
from code.py.modules.shared_modules.exceptions import ProcessingError


class TestOchiaiFormatWorkflow(unittest.TestCase):
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_integrated_logger = MagicMock()
        self.mock_logger.get_logger.return_value = self.mock_integrated_logger
        
        # バッチサイズ設定
        self.mock_config.config = {
            'ochiai_format': {
                'batch_size': 3,
                'enabled': True,
                'request_delay': 0.1,
                'max_content_length': 5000
            },
            'ai_generation': {
                'api_key_env': 'ANTHROPIC_API_KEY'
            }
        }
        
        # ClaudeAPIClientをモック化
        with patch('code.py.modules.ai_tagging_translation.ochiai_format_workflow.ClaudeAPIClient') as mock_claude_client:
            self.mock_claude_client = mock_claude_client.return_value
            self.workflow = OchiaiFormatWorkflow(self.mock_config, self.mock_logger)
    
    def test_init(self):
        """初期化テスト"""
        self.assertIsNotNone(self.workflow.config_manager)
        self.assertIsNotNone(self.workflow.logger)
        self.assertIsNotNone(self.workflow.claude_client)
    
    def test_extract_paper_content_with_paper_structure(self):
        """paper_structure存在時の論文内容抽出テスト"""
        mock_yaml_header = {
            'citation_key': 'test2023paper',
            'paper_structure': {
                'sections': [
                    {
                        'title': 'Abstract',
                        'section_type': 'abstract',
                        'start_line': 5,
                        'end_line': 10,
                        'word_count': 150
                    },
                    {
                        'title': 'Introduction',
                        'section_type': 'introduction',
                        'start_line': 12,
                        'end_line': 25,
                        'word_count': 800
                    }
                ]
            }
        }
        
        mock_content = ["# Test Paper"] + ["line " + str(i) for i in range(1, 30)]
        
        with patch.object(self.workflow, '_load_paper_with_yaml', return_value=(mock_yaml_header, mock_content)):
            with patch.object(self.workflow, '_extract_important_sections', return_value="extracted content"):
                result = self.workflow.extract_paper_content("/fake/path/test.md")
                self.assertEqual(result, "extracted content")
    
    def test_extract_paper_content_without_paper_structure(self):
        """paper_structure非存在時の論文内容抽出テスト"""
        mock_yaml_header = {'citation_key': 'test2023paper'}
        mock_content = ["# Test Paper", "This is content"]
        
        with patch.object(self.workflow, '_load_paper_with_yaml', return_value=(mock_yaml_header, mock_content)):
            result = self.workflow.extract_paper_content("/fake/path/test.md")
            self.assertEqual(result, mock_content)
    
    def test_build_ochiai_prompt(self):
        """落合フォーマットプロンプト構築テスト"""
        paper_content = [
            "# Advanced Machine Learning in Oncology",
            "## Abstract",
            "This study presents a novel approach...",
            "## Methods", 
            "We used deep learning techniques..."
        ]
        
        prompt = self.workflow._build_ochiai_prompt(paper_content)
        
        # プロンプトに6つの項目が含まれているか確認
        self.assertIn("どんなもの？", prompt)
        self.assertIn("先行研究と比べてどこがすごい？", prompt)
        self.assertIn("技術や手法のキモはどこ？", prompt)
        self.assertIn("どうやって有効だと検証した？", prompt)
        self.assertIn("議論はある？", prompt)
        self.assertIn("次に読むべき論文は？", prompt)
        
        # 論文内容が含まれているか確認
        self.assertIn("Advanced Machine Learning in Oncology", prompt)
    
    def test_parse_ochiai_response_valid_json(self):
        """正常なJSON応答の解析テスト"""
        mock_response = """{
            "what_is_this": "機械学習を用いたがん診断システム",
            "what_is_superior": "従来手法より精度が10%向上",
            "technical_key": "深層学習とデータ拡張の組み合わせ",
            "validation_method": "1000例での後ろ向き研究",
            "discussion_points": "サンプルサイズの制限あり",
            "next_papers": "関連研究3件を推奨"
        }"""
        
        result = self.workflow._parse_ochiai_response(mock_response)
        
        self.assertEqual(result['what_is_this'], "機械学習を用いたがん診断システム")
        self.assertEqual(result['what_is_superior'], "従来手法より精度が10%向上")
        self.assertIn('generated_at', result)
    
    def test_parse_ochiai_response_invalid_json(self):
        """不正なJSON応答の解析テスト（フォールバック処理）"""
        mock_response = "This is not JSON format"
        
        result = self.workflow._parse_ochiai_response(mock_response)
        
        # フォールバック処理により、デフォルト値が設定されるか確認
        self.assertIn('what_is_this', result)
        self.assertIn('generated_at', result)
        self.assertTrue(result['what_is_this'].startswith("解析エラー"))
    
    @patch('code.py.modules.ai_tagging_translation.ochiai_format_workflow.StatusManager')
    def test_process_items_basic(self, mock_status_manager_class):
        """基本的な一括処理テスト"""
        mock_status_manager = MagicMock()
        mock_status_manager_class.return_value = mock_status_manager
        mock_status_manager.get_papers_needing_processing.return_value = [
            "/test/paper1.md",
            "/test/paper2.md"
        ]
        
        with patch.object(self.workflow, 'generate_ochiai_summary_single', return_value={'what_is_this': 'test'}):
            with patch.object(self.workflow, 'update_yaml_with_ochiai'):
                result = self.workflow.process_items("/test/input")
                
                self.assertEqual(result['processed'], 2)
                self.assertEqual(result['skipped'], 0)
                self.assertEqual(result['failed'], 0)
    
    def test_update_yaml_with_ochiai(self):
        """YAML更新機能テスト"""
        ochiai_data = {
            'what_is_this': 'テスト要約',
            'what_is_superior': 'テスト優位性',
            'technical_key': 'テスト技術',
            'validation_method': 'テスト検証',
            'discussion_points': 'テスト議論',
            'next_papers': 'テスト次論文',
            'generated_at': '2025-01-15T12:00:00'
        }
        
        with patch('code.py.modules.ai_tagging_translation.ochiai_format_workflow.YAMLHeaderProcessor') as mock_yaml_processor:
            mock_processor = MagicMock()
            mock_yaml_processor.return_value = mock_processor
            
            self.workflow.update_yaml_with_ochiai("/test/paper.md", ochiai_data)
            
            # YAML処理呼び出し確認
            mock_yaml_processor.assert_called_once()
            mock_processor.update_yaml_header_section.assert_called()


class TestOchiaiFormatWorkflowIntegration(unittest.TestCase):
    """統合テスト"""
    
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_integrated_logger = MagicMock()
        self.mock_logger.get_logger.return_value = self.mock_integrated_logger
        
        self.mock_config.config = {
            'ochiai_format': {
                'batch_size': 3,
                'enabled': True
            },
            'ai_generation': {
                'api_key_env': 'ANTHROPIC_API_KEY'
            }
        }
        
        # ClaudeAPIClientをモック化
        with patch('code.py.modules.ai_tagging_translation.ochiai_format_workflow.ClaudeAPIClient') as mock_claude_client:
            self.mock_claude_client = mock_claude_client.return_value
            self.workflow = OchiaiFormatWorkflow(self.mock_config, self.mock_logger)
    
    def test_full_workflow_simulation(self):
        """完全ワークフローのシミュレーションテスト"""
        paper_path = "/test/sample_paper.md"
        
        # モック設定
        with patch.object(self.workflow, 'extract_paper_content', return_value=["# Test Paper", "Content..."]):
            with patch.object(self.workflow, '_build_ochiai_prompt', return_value="test prompt"):
                with patch.object(self.workflow.claude_client, 'send_request', return_value='{"what_is_this": "test"}'):
                    with patch.object(self.workflow, '_parse_ochiai_response', return_value={'what_is_this': 'parsed'}):
                        result = self.workflow.generate_ochiai_summary_single(paper_path)
                        
                        self.assertEqual(result['what_is_this'], 'parsed')


if __name__ == '__main__':
    unittest.main()