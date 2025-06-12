"""
Abstract Translation機能のテスト
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# テスト環境のパス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.abstract_translation.translate_abstract_workflow import TranslateAbstractWorkflow
from modules.ai_tagging.claude_api_client import ClaudeAPIClient  # 共通APIクライアント使用
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError


class TestTranslateAbstractWorkflow(unittest.TestCase):
    """Abstract Translation ワークフローのテスト"""
    
    def setUp(self):
        """テスト前処理"""
        self.temp_dir = tempfile.mkdtemp()
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        os.makedirs(self.clippings_dir)
        
        # テスト用論文ディレクトリとファイル作成
        self.paper_dir = os.path.join(self.clippings_dir, "smith2023test")
        os.makedirs(self.paper_dir)
        
        # テスト用論文ファイル（英語のabstract付き）
        self.paper_file = os.path.join(self.paper_dir, "smith2023test.md")
        paper_content = """---
title: "Cancer Research with Machine Learning"
authors: "Smith et al."
year: 2023
doi: "10.1234/test"
tags:
  - oncology
  - cancer_research
  - KRT13
---

# Cancer Research with Machine Learning

## Abstract

This study investigates KRT13 and EGFR gene expression patterns using machine learning algorithms for improved cancer diagnosis. We developed a novel approach that combines genomic data analysis with artificial intelligence to identify biomarkers associated with cancer progression. Our results demonstrate significant improvements in diagnostic accuracy compared to traditional methods.

## Introduction

Recent advances in oncology have highlighted the importance of molecular biomarkers...

## Methods

We collected samples from 500 patients and analyzed gene expression profiles...
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
                "api_key": "test-api-key",
                "timeout": 30,
                "max_retries": 3
            },
            "ai_generation": {
                "translate_abstract": {
                    "batch_size": 3,
                    "parallel_processing": True,
                    "retry_attempts": 3,
                    "request_delay": 1.5
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        self.config_manager = ConfigManager(self.config_file)
        self.logger = IntegratedLogger(self.config_manager)
    
    def tearDown(self):
        """テスト後処理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('modules.abstract_translation.translate_abstract_workflow.ClaudeAPIClient')
    def test_workflow_initialization(self, mock_claude_client):
        """Abstract Translation ワークフロー初期化のテスト"""
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        
        self.assertIsNotNone(workflow.config_manager)
        self.assertIsNotNone(workflow.logger)
        mock_claude_client.assert_called_once()
    
    def test_extract_abstract(self):
        """Abstract部分の抽出テスト"""
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        
        with open(self.paper_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        abstract = workflow.extract_abstract(content)
        
        expected_start = "This study investigates KRT13 and EGFR"
        self.assertTrue(abstract.startswith(expected_start))
        self.assertIn("diagnostic accuracy", abstract)
        self.assertNotIn("## Introduction", abstract)  # Introduction部分は含まれない
    
    @patch('modules.abstract_translation.translate_abstract_workflow.ClaudeAPIClient')
    def test_translate_abstract_single(self, mock_claude_client):
        """単一論文のabstract翻訳テスト"""
        # モック設定
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        
        japanese_translation = """本研究では、がん診断の改善を目的として、機械学習アルゴリズムを用いてKRT13およびEGFR遺伝子の発現パターンを調査した。ゲノムデータ解析と人工知能を組み合わせて、がんの進行に関連するバイオマーカーを特定する新たなアプローチを開発した。我々の結果は、従来の方法と比較して診断精度の大幅な改善を示している。"""
        
        mock_client_instance.translate_abstract_single.return_value = japanese_translation
        
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        result = workflow.translate_abstract_single(self.paper_file)
        
        self.assertEqual(result, japanese_translation)
    
    @patch('modules.abstract_translation.translate_abstract_workflow.ClaudeAPIClient')
    def test_update_yaml_header_with_translation(self, mock_claude_client):
        """YAMLヘッダーへの翻訳追加テスト"""
        # モック設定
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        
        japanese_translation = """本研究では、がん診断の改善を目的として、機械学習アルゴリズムを用いてKRT13およびEGFR遺伝子の発現パターンを調査した。"""
        
        mock_client_instance.translate_abstract_single.return_value = japanese_translation
        
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        result = workflow.process_single_paper(self.paper_file)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['japanese_abstract'], japanese_translation)
        
        # ファイル内容確認
        with open(self.paper_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('abstract_japanese:', content)
        self.assertIn('本研究では', content)
        self.assertIn('KRT13およびEGFR', content)
    
    @patch('modules.abstract_translation.translate_abstract_workflow.ClaudeAPIClient')
    def test_process_papers_batch(self, mock_claude_client):
        """複数論文のバッチ翻訳処理テスト"""
        # 追加の論文ファイル作成
        paper_dir2 = os.path.join(self.clippings_dir, "doe2024test")
        os.makedirs(paper_dir2)
        
        paper_file2 = os.path.join(paper_dir2, "doe2024test.md")
        paper_content2 = """---
title: "Advanced Treatment Approaches"
authors: "Doe et al."
year: 2024
tags:
  - immunotherapy
  - cancer_treatment
---

# Advanced Treatment Approaches

## Abstract

Novel immunotherapy approaches for cancer treatment have shown promising results in clinical trials. This comprehensive review examines recent developments in checkpoint inhibitor therapy and combination treatments.

## Introduction

Immunotherapy has revolutionized cancer treatment...
"""
        
        with open(paper_file2, 'w', encoding='utf-8') as f:
            f.write(paper_content2)
        
        # モック設定
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        mock_client_instance.translate_abstract_single.side_effect = [
            "本研究では、がん診断の改善を目的として機械学習を活用した。",
            "がん治療のための新しい免疫療法アプローチが臨床試験で有望な結果を示している。"
        ]
        
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        results = workflow.process_papers(
            self.clippings_dir,
            target_papers=["smith2023test", "doe2024test"]
        )
        
        self.assertTrue(results['success'])
        self.assertEqual(results['processed_papers'], 2)
        self.assertEqual(len(results['paper_results']), 2)
    
    @patch('modules.abstract_translation.translate_abstract_workflow.ClaudeAPIClient')
    def test_skip_already_translated(self, mock_claude_client):
        """既に翻訳済みの論文をスキップするテスト"""
        # 既に翻訳済みの論文ファイル作成
        translated_content = """---
title: "Cancer Research with Machine Learning"
authors: "Smith et al."
year: 2023
abstract_japanese: |
  既存の日本語翻訳です。
  この論文は既に翻訳済みです。
---

# Cancer Research with Machine Learning

## Abstract

This is the original English abstract...
"""
        
        with open(self.paper_file, 'w', encoding='utf-8') as f:
            f.write(translated_content)
        
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        result = workflow.process_single_paper(self.paper_file)
        
        self.assertTrue(result['success'])
        self.assertTrue(result['skipped'])
        self.assertEqual(result['reason'], 'Already translated')
    
    def test_extract_abstract_missing(self):
        """Abstract部分が存在しない場合のテスト"""
        # Abstract部分のない論文ファイル作成
        no_abstract_file = os.path.join(self.paper_dir, "no_abstract.md")
        no_abstract_content = """---
title: "Paper Without Abstract"
authors: "Test Author"
---

# Paper Without Abstract

## Introduction

This paper has no abstract section...

## Methods

Some methods here...
"""
        
        with open(no_abstract_file, 'w', encoding='utf-8') as f:
            f.write(no_abstract_content)
        
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        
        with open(no_abstract_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        abstract = workflow.extract_abstract(content)
        self.assertEqual(abstract, "")
    
    @patch('modules.abstract_translation.translate_abstract_workflow.ClaudeAPIClient')
    def test_error_handling(self, mock_claude_client):
        """エラーハンドリングのテスト"""
        # APIエラーをシミュレート
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        mock_client_instance.translate_abstract_single.side_effect = Exception("Translation API Error")
        
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        result = workflow.process_single_paper(self.paper_file)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    @patch('modules.abstract_translation.translate_abstract_workflow.ClaudeAPIClient')
    def test_quality_validation(self, mock_claude_client):
        """翻訳品質検証のテスト"""
        # 極端に短い翻訳をシミュレート
        mock_client_instance = Mock()
        mock_claude_client.return_value = mock_client_instance
        mock_client_instance.translate_abstract_single.return_value = "短い"  # 極端に短い翻訳
        
        workflow = TranslateAbstractWorkflow(self.config_manager, self.logger)
        
        # 品質検証メソッドのテスト
        is_valid = workflow.validate_translation_quality("短い", "This is a very long English abstract that should produce a much longer Japanese translation than just two characters.")
        
        self.assertFalse(is_valid)  # 元の英語文に比べて極端に短いため無効


if __name__ == '__main__':
    unittest.main() 