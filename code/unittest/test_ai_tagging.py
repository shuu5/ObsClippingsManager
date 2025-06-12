"""
AI Tagging機能のテスト
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys

# テスト環境のパス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.ai_tagging.tagger_workflow import TaggerWorkflow
from modules.ai_tagging.claude_api_client import ClaudeAPIClient
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError


class TestClaudeAPIClient(unittest.TestCase):
    """Claude API クライアントのテスト"""
    
    def setUp(self):
        """テスト前処理"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        
        # テスト用設定
        config_data = {
            "common": {
                "workspace_path": self.temp_dir,
                "bibtex_file": os.path.join(self.temp_dir, "references.bib"),
                "clippings_dir": os.path.join(self.temp_dir, "Clippings")
            },
            "claude_api": {
                "model": "claude-3-5-sonnet-20241022",
                "api_key": "test-api-key",
                "timeout": 30,
                "max_retries": 3
            },
            "ai_generation": {
                "tagger": {
                    "batch_size": 5,
                    "parallel_processing": True,
                    "tag_count_range": [10, 20],
                    "retry_attempts": 3,
                    "request_delay": 1.0
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        self.config_manager = ConfigManager(self.config_file)
        self.logger = IntegratedLogger(log_level="INFO")
        
    def tearDown(self):
        """テスト後処理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_claude_client_initialization(self):
        """Claude APIクライアント初期化のテスト"""
        client = ClaudeAPIClient(self.config_manager, self.logger)
        
        self.assertEqual(client.model, "claude-3-5-sonnet-20241022")
        self.assertEqual(client.api_key, "test-api-key")
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.max_retries, 3)
    
    @patch('modules.ai_tagging.claude_api_client.anthropic.Anthropic')
    def test_generate_tags_single(self, mock_anthropic):
        """単一論文のタグ生成テスト"""
        # モック設定
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '["oncology", "cancer_research", "KRT13", "EGFR", "machine_learning"]'
        mock_client.messages.create.return_value = mock_response
        
        client = ClaudeAPIClient(self.config_manager, self.logger)
        
        paper_content = """
        Title: Cancer Research with Machine Learning
        Abstract: This study investigates KRT13 and EGFR gene expression patterns
        using machine learning algorithms for improved cancer diagnosis.
        """
        
        tags = client.generate_tags_single(paper_content)
        
        expected_tags = ["oncology", "cancer_research", "KRT13", "EGFR", "machine_learning"]
        self.assertEqual(tags, expected_tags)
    
    @patch('modules.ai_tagging.claude_api_client.anthropic.Anthropic')
    def test_api_error_handling(self, mock_anthropic):
        """APIエラーハンドリングのテスト"""
        # APIエラーをシミュレート
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")
        
        client = ClaudeAPIClient(self.config_manager, self.logger)
        
        with self.assertRaises(ObsClippingsError):
            client.generate_tags_single("test content")
    
    def test_validate_tags(self):
        """タグ検証のテスト"""
        client = ClaudeAPIClient(self.config_manager, self.logger)
        
        # 正常なタグ
        valid_tags = ["oncology", "KRT13", "machine_learning"]
        validated = client.validate_tags(valid_tags)
        self.assertEqual(validated, valid_tags)
        
        # 不正なタグ（キャメルケース）
        invalid_tags = ["oncology", "machineLearning", "KRT13"]
        validated = client.validate_tags(invalid_tags)
        expected = ["oncology", "machine_learning", "KRT13"]  # 正規化
        self.assertEqual(validated, expected)


class TestTaggerWorkflow(unittest.TestCase):
    """Tagger ワークフローのテスト"""
    
    def setUp(self):
        """テスト前処理"""
        self.temp_dir = tempfile.mkdtemp()
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        os.makedirs(self.clippings_dir)
        
        # テスト用論文ディレクトリとファイル作成
        self.paper_dir = os.path.join(self.clippings_dir, "smith2023test")
        os.makedirs(self.paper_dir)
        
        # テスト用論文ファイル
        self.paper_file = os.path.join(self.paper_dir, "smith2023test.md")
        paper_content = """---
title: "Cancer Research with Machine Learning"
authors: "Smith et al."
year: 2023
doi: "10.1234/test"
---

# Cancer Research with Machine Learning

## Abstract
This study investigates KRT13 and EGFR gene expression patterns
using machine learning algorithms for improved cancer diagnosis.

## Introduction
Recent advances in oncology...
"""
        
        with open(self.paper_file, 'w', encoding='utf-8') as f:
            f.write(paper_content)
        
        # 設定ファイル作成
        self.config_file = os.path.join(self.temp_dir, "config.json")
        config_data = {
            "common": {
                "workspace_path": self.temp_dir,
                "clippings_dir": self.clippings_dir
            },
            "claude_api": {
                "model": "claude-3-5-sonnet-20241022",
                "api_key": "test-api-key"
            },
            "ai_generation": {
                "tagger": {
                    "batch_size": 5,
                    "tag_count_range": [10, 20]
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        self.config_manager = ConfigManager(self.config_file)
        self.logger = IntegratedLogger(log_level="INFO")
    
    def tearDown(self):
        """テスト後処理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('modules.ai_tagging.tagger_workflow.ClaudeAPIClient')
    def test_tagger_workflow_initialization(self, mock_claude_client):
        """Tagger ワークフロー初期化のテスト"""
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        self.assertIsNotNone(workflow.config_manager)
        self.assertIsNotNone(workflow.logger)
        mock_claude_client.assert_called_once()
    
    @patch('modules.ai_tagging.tagger_workflow.ClaudeAPIClient')
    def test_generate_tags_single_paper(self, mock_claude_client):
        """単一論文のタグ生成テスト"""
        # モック設定
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        mock_client_instance.generate_tags_single.return_value = [
            "oncology", "cancer_research", "KRT13", "EGFR", "machine_learning"
        ]
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        tags = workflow.generate_tags_single(self.paper_file)
        
        expected_tags = ["oncology", "cancer_research", "KRT13", "EGFR", "machine_learning"]
        self.assertEqual(tags, expected_tags)
    
    @patch('modules.ai_tagging.tagger_workflow.ClaudeAPIClient')
    def test_update_yaml_header_with_tags(self, mock_claude_client):
        """YAMLヘッダーへのタグ追加テスト"""
        # モック設定
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        mock_client_instance.generate_tags_single.return_value = [
            "oncology", "cancer_research", "KRT13"
        ]
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        result = workflow.process_single_paper(self.paper_file)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['tags']), 3)
        
        # ファイル内容確認
        with open(self.paper_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('tags:', content)
        self.assertIn('- oncology', content)
        self.assertIn('- cancer_research', content)
        self.assertIn('- KRT13', content)
    
    @patch('modules.ai_tagging.tagger_workflow.ClaudeAPIClient')
    def test_process_papers_batch(self, mock_claude_client):
        """複数論文のバッチ処理テスト"""
        # 追加の論文ファイル作成
        paper_dir2 = os.path.join(self.clippings_dir, "doe2024test")
        os.makedirs(paper_dir2)
        
        paper_file2 = os.path.join(paper_dir2, "doe2024test.md")
        paper_content2 = """---
title: "Advanced Treatment Approaches"
authors: "Doe et al."
year: 2024
---

# Advanced Treatment Approaches

## Abstract
Novel immunotherapy approaches for cancer treatment...
"""
        
        with open(paper_file2, 'w', encoding='utf-8') as f:
            f.write(paper_content2)
        
        # モック設定
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        mock_client_instance.generate_tags_single.side_effect = [
            ["oncology", "cancer_research", "KRT13"],
            ["immunotherapy", "cancer_treatment", "clinical_trials"]
        ]
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        results = workflow.process_papers(
            self.clippings_dir,
            target_papers=["smith2023test", "doe2024test"]
        )
        
        self.assertTrue(results['success'])
        self.assertEqual(results['processed_papers'], 2)
        self.assertEqual(len(results['paper_results']), 2)
    
    @patch('modules.ai_tagging.tagger_workflow.ClaudeAPIClient')
    def test_error_handling(self, mock_claude_client):
        """エラーハンドリングのテスト"""
        # APIエラーをシミュレート
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        mock_client_instance.generate_tags_single.side_effect = Exception("API Error")
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        result = workflow.process_single_paper(self.paper_file)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main() 