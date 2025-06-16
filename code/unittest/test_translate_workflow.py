"""
TranslateWorkflow テストスイート

論文要約翻訳ワークフローのユニットテスト
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

import sys
import os

from code.py.modules.ai_tagging_translation.translate_workflow import TranslateWorkflow
from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import ProcessingError


class TestTranslateWorkflow(unittest.TestCase):
    """TranslateWorkflow基本機能テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # モック設定
        self.config_manager = Mock(spec=ConfigManager)
        self.config_manager.get_ai_setting.side_effect = self._mock_get_ai_setting
        
        self.logger = Mock(spec=IntegratedLogger)
        self.mock_logger = Mock()
        self.logger.get_logger.return_value = self.mock_logger
        
        # TranslateWorkflowインスタンス作成
        self.workflow = TranslateWorkflow(self.config_manager, self.logger)
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _mock_get_ai_setting(self, section, key, default=None):
        """AI設定のモック"""
        settings = {
            ('translate_abstract', 'enabled'): True,
            ('translate_abstract', 'batch_size'): 5,
        }
        return settings.get((section, key), default)
    
    def test_init_basic(self):
        """TranslateWorkflow初期化テスト"""
        self.assertIsNotNone(self.workflow)
        self.assertEqual(self.workflow.enabled, True)
        self.assertEqual(self.workflow.batch_size, 5)
        self.assertEqual(self.workflow.config_manager, self.config_manager)
        self.assertEqual(self.workflow.integrated_logger, self.logger)
    
    def test_claude_client_lazy_initialization(self):
        """Claude APIクライアント遅延初期化テスト"""
        # 初期状態では None
        self.assertIsNone(self.workflow._claude_client)
        
        # プロパティアクセス時に初期化
        with patch('code.py.modules.ai_tagging_translation.translate_workflow.ClaudeAPIClient') as MockClaudeClient:
            mock_client = Mock()
            MockClaudeClient.return_value = mock_client
            
            client = self.workflow.claude_client
            self.assertEqual(client, mock_client)
            MockClaudeClient.assert_called_once_with(self.config_manager, self.logger)
    
    def test_process_items_disabled(self):
        """翻訳機能無効時のprocess_itemsテスト"""
        # 機能無効に設定
        self.workflow.enabled = False
        
        result = self.workflow.process_items("/test/dir")
        
        expected = {'status': 'disabled', 'processed': 0, 'skipped': 0, 'failed': 0}
        self.assertEqual(result, expected)
    
    @patch('code.py.modules.ai_tagging_translation.translate_workflow.StatusManager')
    def test_process_items_no_papers(self, MockStatusManager):
        """処理対象論文なしのprocess_itemsテスト"""
        # StatusManagerモック設定
        mock_status_manager = Mock()
        mock_status_manager.get_papers_needing_processing.return_value = []
        MockStatusManager.return_value = mock_status_manager
        
        result = self.workflow.process_items("/test/dir")
        
        expected = {
            'status': 'completed',
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'total_papers': 0
        }
        self.assertEqual(result, expected)
    
    def test_extract_abstract_content_basic(self):
        """基本的なabstract抽出テスト"""
        # テストファイル作成
        test_file = self.test_dir / "test.md"
        yaml_content = """---
paper_structure:
  sections:
    - section_type: "abstract"
      title: "Abstract"
      start_line: 2
      end_line: 4
---
This is test content.
## Abstract
This is the abstract content for testing.
It contains multiple lines of abstract text.
## Introduction
This is introduction content."""
        
        test_file.write_text(yaml_content, encoding='utf-8')
        
        with patch('code.py.modules.ai_tagging_translation.translate_workflow.YAMLHeaderProcessor') as MockProcessor:
            mock_processor = Mock()
            MockProcessor.return_value = mock_processor
            
            # paper_structure の sections データ（subsections含む）
            yaml_data = {
                'paper_structure': {
                    'sections': [
                        {
                            'section_type': 'abstract',
                            'title': 'Abstract',
                            'start_line': 2,
                            'end_line': 4,
                            'subsections': [
                                {
                                    'title': 'Background',
                                    'start_line': 3,
                                    'end_line': 4,
                                    'word_count': 20
                                },
                                {
                                    'title': 'Methods',
                                    'start_line': 5,
                                    'end_line': 6,
                                    'word_count': 25
                                }
                            ]
                        }
                    ]
                }
            }
            markdown_content = """This is test content.
## Abstract
### Background
This is the background section of abstract for testing.
### Methods
This is the methods section of abstract for testing.
## Introduction
This is introduction content."""
            
            mock_processor.parse_yaml_header.return_value = (yaml_data, markdown_content)
            
            result = self.workflow.extract_abstract_content(str(test_file))
            
            # ヘッダー記号が除去され、subsectionsも含む適切な内容が抽出されることを確認
            self.assertIn("This is the background section", result)
            self.assertIn("This is the methods section", result)
            # ヘッダー記号が除去されていることを確認
            self.assertNotIn("## Abstract", result)
            self.assertNotIn("### Background", result)
            self.assertNotIn("### Methods", result)
            # subsection内容が正しく抽出されていることを確認
            self.assertIn("abstract for testing", result)  # 両方のsubsectionに含まれる共通文字列
    
    def test_build_translation_prompt(self):
        """翻訳プロンプト構築テスト"""
        abstract = "This is a test abstract for translation."
        
        prompt = self.workflow._build_translation_prompt(abstract)
        
        self.assertIn("自然で正確な日本語に翻訳", prompt)
        self.assertIn("学術論文として適切な日本語表現", prompt)
        self.assertIn(abstract, prompt)
        self.assertIn("Original Abstract:", prompt)
    
    def test_parse_translation_response_valid(self):
        """有効な翻訳レスポンス解析テスト"""
        # より長い翻訳文でテスト（50文字以上）
        valid_response = "これは翻訳されたアブストラクトの内容です。学術論文として適切な日本語表現を使用しており、研究の背景と目的、方法論、結果、考察が含まれています。"
        
        result = self.workflow._parse_translation_response(valid_response)
        
        # 有効な日本語翻訳が正しく解析されることを確認
        self.assertGreater(len(result), 50, f"Translation should be longer than 50 characters")
        self.assertEqual(result, valid_response)
    
    def test_parse_translation_response_too_short(self):
        """短すぎる翻訳レスポンス解析テスト"""
        short_response = "短い"
        
        result = self.workflow._parse_translation_response(short_response)
        
        self.assertEqual(result, "")
    
    def test_parse_translation_response_with_label(self):
        """ラベル付き翻訳レスポンス解析テスト"""
        # ラベル付きで長い翻訳文でテスト（50文字以上）
        labeled_response = "Translation: これは翻訳されたアブストラクトの内容です。学術論文として適切な日本語表現を使用しており、研究の背景と目的、方法論、結果、考察が含まれています。"
        expected = "これは翻訳されたアブストラクトの内容です。学術論文として適切な日本語表現を使用しており、研究の背景と目的、方法論、結果、考察が含まれています。"
        
        result = self.workflow._parse_translation_response(labeled_response)
        
        self.assertEqual(result, expected)
    
    def test_parse_translation_response_no_japanese(self):
        """日本語が含まれない翻訳レスポンス解析テスト"""
        english_response = "This is an English response that should be rejected as translation."
        
        result = self.workflow._parse_translation_response(english_response)
        
        self.assertEqual(result, "")
    
    def test_evaluate_translation_quality_basic(self):
        """基本的な翻訳品質評価テスト"""
        translation = "これは翻訳されたアブストラクトです。KRT13遺伝子の発現について研究した結果、95%の精度を達成しました。"
        original = "This is the translated abstract. We studied KRT13 gene expression and achieved 95% accuracy."
        
        quality_score = self.workflow.evaluate_translation_quality(translation, original)
        
        # 品質スコアが0.0-1.0の範囲内であることを確認
        self.assertGreaterEqual(quality_score, 0.0)
        self.assertLessEqual(quality_score, 1.0)
        # 適切な翻訳なので、ある程度高いスコアが期待される
        self.assertGreater(quality_score, 0.5)
    
    def test_generate_feedback_report(self):
        """フィードバックレポート生成テスト"""
        translation = "これは翻訳されたアブストラクトです。"
        original = "This is the translated abstract."
        quality_score = 0.85
        
        feedback = self.workflow.generate_feedback_report(translation, original, quality_score)
        
        # 必要なキーが含まれていることを確認
        expected_keys = [
            'quality_score', 'original_length', 'translation_length', 'length_ratio',
            'completeness_score', 'fluency_score', 'consistency_score', 'accuracy_score',
            'suggestions', 'evaluation_timestamp'
        ]
        for key in expected_keys:
            self.assertIn(key, feedback)
        
        self.assertEqual(feedback['quality_score'], quality_score)
    
    def test_suggest_translation_improvements(self):
        """翻訳改善提案生成テスト"""
        # 遺伝子名が欠落している翻訳例
        translation = "この研究では遺伝子発現を調査しました。"
        original = "This study investigated KRT13 gene expression and EGFR pathway."
        
        suggestions = self.workflow.suggest_translation_improvements(translation, original)
        
        self.assertIsInstance(suggestions, list)
        # 遺伝子名の保持に関する提案があることを期待
        gene_suggestion = any("gene symbols" in s for s in suggestions)
        self.assertTrue(gene_suggestion)


class TestTranslateWorkflowQualityEvaluation(unittest.TestCase):
    """TranslateWorkflow品質評価機能テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.config_manager = Mock(spec=ConfigManager)
        self.config_manager.get_ai_setting.return_value = True
        
        self.logger = Mock(spec=IntegratedLogger)
        self.mock_logger = Mock()
        self.logger.get_logger.return_value = self.mock_logger
        
        self.workflow = TranslateWorkflow(self.config_manager, self.logger)
    
    def test_evaluate_completeness_ideal_ratio(self):
        """完全性評価 - 理想的な長さ比率テスト"""
        # 理想的な比率（0.8-1.5の範囲内）になるように調整
        translation = "これは翻訳されたテキストです。" * 3  # 45文字
        original = "This is translated text." * 2  # 50文字（比率約0.9）
        
        score = self.workflow._evaluate_completeness(translation, original)
        
        self.assertEqual(score, 1.0)
    
    def test_evaluate_completeness_too_short(self):
        """完全性評価 - 短すぎる翻訳テスト"""
        translation = "短い翻訳"
        original = "This is a much longer original text that should result in longer translation."
        
        score = self.workflow._evaluate_completeness(translation, original)
        
        self.assertLess(score, 1.0)
    
    def test_evaluate_fluency_good_japanese(self):
        """自然性評価 - 良い日本語テスト"""
        translation = "これは自然な日本語の翻訳です。適切な句読点を使用しています。"
        
        score = self.workflow._evaluate_fluency(translation)
        
        self.assertGreater(score, 0.8)
    
    def test_evaluate_fluency_no_japanese(self):
        """自然性評価 - 日本語なしテスト"""
        translation = "This is English text."
        
        score = self.workflow._evaluate_fluency(translation)
        
        self.assertLess(score, 0.5)
    
    def test_evaluate_consistency_appropriate_english(self):
        """一貫性評価 - 適切な英語混入テスト"""
        translation = "この研究では、KRT13遺伝子とEGFRタンパク質の相互作用を調査しました。"
        
        score = self.workflow._evaluate_consistency(translation)
        
        # 専門用語の英語混入は許容されるべき
        self.assertGreaterEqual(score, 0.7)
    
    def test_evaluate_accuracy_preserves_numbers_and_genes(self):
        """正確性評価 - 数値・遺伝子名保持テスト"""
        translation = "この研究では、KRT13遺伝子の発現が95%の症例で観察されました。"
        original = "This study found KRT13 gene expression in 95% of cases."
        
        score = self.workflow._evaluate_accuracy(translation, original)
        
        # 遺伝子名と数値が保持されているので高スコア期待
        self.assertGreaterEqual(score, 0.8)
    
    def test_evaluate_accuracy_missing_important_info(self):
        """正確性評価 - 重要情報欠落テスト"""
        translation = "この研究では遺伝子発現を調査しました。"
        original = "This study investigated KRT13 gene expression with 95% accuracy and EGFR pathway."
        
        score = self.workflow._evaluate_accuracy(translation, original)
        
        # 重要な情報が欠落しているので低スコア期待
        self.assertLess(score, 0.5)


class TestTranslateWorkflowYAMLIntegration(unittest.TestCase):
    """TranslateWorkflow YAML統合機能テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.mock_logger = Mock()
        self.logger.get_logger.return_value = self.mock_logger
        
        self.workflow = TranslateWorkflow(self.config_manager, self.logger)
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @patch('code.py.modules.ai_tagging_translation.translate_workflow.YAMLHeaderProcessor')
    def test_update_yaml_with_translation_and_quality(self, MockProcessor):
        """YAML翻訳・品質情報更新テスト"""
        mock_processor = Mock()
        MockProcessor.return_value = mock_processor
        
        # 現在のYAMLデータ
        current_yaml = {
            'title': 'Test Paper',
            'processing_status': {}
        }
        markdown_content = "# Test Content"
        
        mock_processor.parse_yaml_header.return_value = (current_yaml, markdown_content)
        
        # テストデータ
        paper_path = str(self.test_dir / "test.md")
        translation = "これはテスト翻訳です。"
        feedback = {
            'quality_score': 0.85,
            'completeness_score': 0.9,
            'fluency_score': 0.8,
            'consistency_score': 0.85,
            'accuracy_score': 0.9,
            'original_length': 100,
            'translation_length': 80,
            'length_ratio': 0.8,
            'evaluation_timestamp': '2024-01-15T10:30:00',
            'suggestions': ['Test suggestion']
        }
        
        # メソッド実行
        self.workflow.update_yaml_with_translation_and_quality(paper_path, translation, feedback)
        
        # write_yaml_header が適切な引数で呼ばれることを確認
        mock_processor.write_yaml_header.assert_called_once()
        call_args = mock_processor.write_yaml_header.call_args
        updated_yaml = call_args[0][1]  # 第2引数がupdated_yaml
        
        # ai_content セクションが正しく更新されているか確認
        self.assertIn('ai_content', updated_yaml)
        self.assertIn('abstract_japanese', updated_yaml['ai_content'])
        self.assertEqual(updated_yaml['ai_content']['abstract_japanese']['content'], translation)
        
        # translation_quality セクションが正しく更新されているか確認
        self.assertIn('translation_quality', updated_yaml)
        self.assertEqual(updated_yaml['translation_quality']['quality_score'], 0.85)
        self.assertEqual(updated_yaml['translation_quality']['completeness_score'], 0.9)
        
        # processing_status が更新されているか確認
        self.assertEqual(updated_yaml['processing_status']['translate_abstract'], 'completed')
        
        # last_updated が更新されているか確認
        self.assertIn('last_updated', updated_yaml)


if __name__ == '__main__':
    unittest.main()