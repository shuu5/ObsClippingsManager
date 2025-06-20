"""
TaggerWorkflow のユニットテスト

TaggerWorkflowクラスの機能をテストします。
"""

import unittest
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.status_management_yaml.status_manager import StatusManager


class TestTaggerWorkflowImport(unittest.TestCase):
    """TaggerWorkflowクラスのインポートテスト"""
    
    def test_tagger_workflow_import(self):
        """TaggerWorkflowクラスのインポートテスト"""
        try:
            from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
            self.assertTrue(True, "TaggerWorkflowクラスのインポートが成功しました")
        except ImportError as e:
            self.fail(f"TaggerWorkflowクラスのインポートが失敗しました: {e}")


class TestTaggerWorkflowBasic(unittest.TestCase):
    """TaggerWorkflowクラスの基本機能テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('tagger', 'enabled'): True,
            ('tagger', 'batch_size'): 8,
            ('tagger', 'tag_count_range'): [10, 20],
        }.get(keys, default)
        
    def test_tagger_workflow_initialization(self):
        """TaggerWorkflow初期化テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow.config_manager, self.config_manager)
        # loggerは get_logger() の戻り値と比較
        self.assertEqual(workflow.logger, self.logger.get_logger.return_value)
        self.logger.get_logger.assert_called_with('TaggerWorkflow')


class TestTaggerWorkflowContentExtraction(unittest.TestCase):
    """TaggerWorkflowの論文コンテンツ抽出機能テスト（title機能含む）"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # テスト用一時ディレクトリ
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('tagger', 'enabled'): True,
            ('tagger', 'batch_size'): 8,
            ('tagger', 'tag_count_range'): [10, 20],
        }.get(keys, default)
    
    def test_extract_paper_content_with_title(self):
        """論文コンテンツ抽出テスト（title付き）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # テスト用Markdownファイル作成（title付き）
        test_content = """---
citation_key: test2023paper
title: "Novel Biomarker Discovery in Cancer Research using Machine Learning"
paper_structure:
  sections:
    - title: "Introduction"
      section_type: "introduction"
      start_line: 1
      end_line: 3
    - title: "Results"
      section_type: "results"
      start_line: 4
      end_line: 6
    - title: "Discussion"
      section_type: "discussion"
      start_line: 7
      end_line: 9
---

## Introduction
This paper introduces a new biomarker detection method.

## Results
We found significant correlation between EGFR and treatment response.

## Discussion
These findings suggest novel therapeutic targets in cancer treatment.
"""
        
        test_file = Path(self.temp_dir) / "test_paper.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        content = workflow.extract_paper_content(str(test_file))
        
        # titleが先頭に追加されているかチェック
        self.assertIn("Novel Biomarker Discovery in Cancer Research using Machine Learning", content)
        # title section として追加されているかチェック
        self.assertTrue(content.startswith("# Novel Biomarker Discovery in Cancer Research using Machine Learning"))
        # 通常のセクションも含まれているかチェック
        self.assertIn("biomarker detection method", content)
        self.assertIn("EGFR and treatment response", content)
        self.assertIn("therapeutic targets", content)
        # YAMLヘッダーは除外されているかチェック
        self.assertNotIn("citation_key:", content)
    
    def test_extract_paper_content_without_title(self):
        """論文コンテンツ抽出テスト（title無し）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # テスト用Markdownファイル作成（title無し）
        test_content = """---
citation_key: test2023paper
paper_structure:
  sections:
    - title: "Introduction"
      section_type: "introduction"
      start_line: 1
      end_line: 3
    - title: "Results"
      section_type: "results"
      start_line: 4
      end_line: 6
---

## Introduction
This paper introduces a new biomarker detection method.

## Results
We found significant correlation between markers.
"""
        
        test_file = Path(self.temp_dir) / "test_paper.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        content = workflow.extract_paper_content(str(test_file))
        
        # title section が追加されていないかチェック（通常のセクション##で始まる）
        self.assertTrue(content.startswith("##"))  # 通常のセクションで始まる
        self.assertFalse(content.startswith("# "))  # titleセクション（single #）は含まれない
        # 通常のセクションは含まれているかチェック
        self.assertIn("biomarker detection method", content)
        self.assertIn("correlation between markers", content)
    
    def test_extract_paper_content_with_empty_title(self):
        """論文コンテンツ抽出テスト（空のtitle）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # テスト用Markdownファイル作成（空のtitle）
        test_content = """---
citation_key: test2023paper
title: ""
paper_structure:
  sections:
    - title: "Introduction"
      section_type: "introduction"
      start_line: 1
      end_line: 3
---

## Introduction
This paper introduces a new biomarker detection method.
"""
        
        test_file = Path(self.temp_dir) / "test_paper.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        content = workflow.extract_paper_content(str(test_file))
        
        # 空titleは追加されないかチェック（通常のセクション##で始まる）
        self.assertTrue(content.startswith("##"))  # 通常のセクションで始まる
        self.assertFalse(content.startswith("# "))  # titleセクション（single #）は含まれない
        # 通常のセクションは含まれているかチェック
        self.assertIn("biomarker detection method", content)
    
    def test_extract_paper_content_with_list_title(self):
        """論文コンテンツ抽出テスト（リスト形式のtitle）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # テスト用Markdownファイル作成（リスト形式のtitle）
        test_content = """---
citation_key: test2023paper
title: 
  - "Cancer Research"
  - "Biomarker Discovery"
paper_structure:
  sections:
    - title: "Introduction"
      section_type: "introduction"  
      start_line: 1
      end_line: 3
---

## Introduction
This paper introduces a new biomarker detection method.
"""
        
        test_file = Path(self.temp_dir) / "test_paper.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        content = workflow.extract_paper_content(str(test_file))
        
        # リスト形式titleは適切に処理されるかチェック
        self.assertTrue(content.startswith("# Cancer Research - Biomarker Discovery"))
        # 通常のセクションも含まれているかチェック
        self.assertIn("biomarker detection method", content)


class TestTaggerWorkflowTagGeneration(unittest.TestCase):
    """TaggerWorkflowのタグ生成機能テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # テスト用一時ディレクトリ
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('tagger', 'enabled'): True,
            ('tagger', 'batch_size'): 8,
            ('tagger', 'tag_count_range'): [10, 20],
        }.get(keys, default)
        
    def test_extract_paper_content(self):
        """論文コンテンツ抽出テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # テスト用Markdownファイル作成
        test_content = """---
citation_key: test2023paper
paper_structure:
  sections:
    - title: "Abstract"
      section_type: "abstract"
      start_line: 1
      end_line: 3
    - title: "Introduction"
      section_type: "introduction"
      start_line: 4
      end_line: 6
---

## Abstract
This is a test abstract for cancer research.

## Introduction
This paper introduces a new biomarker detection method.
"""
        
        test_file = Path(self.temp_dir) / "test_paper.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        content = workflow.extract_paper_content(str(test_file))
        
        self.assertIn("biomarker detection", content)
        self.assertNotIn("citation_key:", content)  # YAMLヘッダーは除外
    
    def test_build_tagging_prompt(self):
        """タグ生成プロンプト構築テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        paper_content = "This is a cancer research paper about EGFR mutations."
        
        prompt = workflow._build_tagging_prompt(paper_content)
        
        self.assertIn("10-20個のタグを生成", prompt)
        self.assertIn("スネークケース", prompt)
        self.assertIn("cancer research paper about EGFR", prompt)
        self.assertIn("JSON配列形式", prompt)
    
    @patch('code.py.modules.ai_tagging_translation.tagger_workflow.ClaudeAPIClient')
    def test_generate_tags_single(self, mock_claude_client_class):
        """単一論文のタグ生成テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # ClaudeAPIClientのモック
        mock_claude_client = Mock()
        mock_claude_client.send_request.return_value = '["cancer_research", "egfr_mutations", "biomarkers"]'
        mock_claude_client_class.return_value = mock_claude_client
        
        # テスト用Markdownファイル作成
        test_content = """---
citation_key: test2023paper
---

## Abstract
This is a test abstract for cancer research.
"""
        
        test_file = Path(self.temp_dir) / "test_paper.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        tags = workflow.generate_tags_single(str(test_file))
        
        self.assertEqual(tags, ["cancer_research", "egfr_mutations", "biomarkers"])
        mock_claude_client.send_request.assert_called_once()
    
    def test_parse_tags_response_valid_json(self):
        """タグレスポンス解析テスト（有効なJSON）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        response = '["cancer_research", "machine_learning", "biomarkers", "KRT13"]'
        tags = workflow._parse_tags_response(response)
        
        # 新しい仕様: prefixなし遺伝子シンボル（KRT13）は小文字化される
        self.assertEqual(tags, ["cancer_research", "machine_learning", "biomarkers", "krt13"])
    
    def test_parse_tags_response_invalid_json(self):
        """タグレスポンス解析テスト（無効なJSON）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        response = 'invalid json response'
        
        tags = workflow._parse_tags_response(response)
        
        self.assertEqual(tags, [])  # エラー時は空リスト
    
    @patch('code.py.modules.ai_tagging_translation.tagger_workflow.YAMLHeaderProcessor')
    def test_update_yaml_with_tags(self, mock_yaml_processor_class):
        """YAMLヘッダーのタグ更新テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # YAMLHeaderProcessorのモック
        mock_processor = Mock()
        mock_processor.parse_yaml_header.return_value = (
            {"citation_key": "test2023paper"}, 
            "# Test content\nThis is test markdown content"
        )
        mock_yaml_processor_class.return_value = mock_processor
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        tags = ["cancer_research", "biomarkers", "machine_learning"]
        
        workflow.update_yaml_with_tags("test_paper.md", tags)
        
        # YAMLヘッダー更新の呼び出し確認
        mock_processor.parse_yaml_header.assert_called_once()
        mock_processor.write_yaml_header.assert_called_once()
        
        # 呼び出し時の引数確認
        args, kwargs = mock_processor.write_yaml_header.call_args
        updated_yaml = args[1]
        self.assertEqual(updated_yaml['tags'], tags)


class TestTaggerWorkflowProcessItems(unittest.TestCase):
    """TaggerWorkflowの論文一括処理テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # テスト用一時ディレクトリ
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('tagger', 'enabled'): True,
            ('tagger', 'batch_size'): 8,
            ('tagger', 'tag_count_range'): [10, 20],
        }.get(keys, default)
        
    @patch('code.py.modules.ai_tagging_translation.tagger_workflow.StatusManager')
    @patch('code.py.modules.ai_tagging_translation.tagger_workflow.ClaudeAPIClient')
    def test_process_items_success(self, mock_claude_client_class, mock_status_manager_class):
        """論文一括処理成功テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        # StatusManagerのモック
        mock_status_manager = Mock()
        mock_status_manager.get_papers_needing_processing.return_value = ["paper1.md", "paper2.md"]
        mock_status_manager_class.return_value = mock_status_manager
        
        # ClaudeAPIClientのモック
        mock_claude_client = Mock()
        mock_claude_client.send_request.return_value = '["cancer_research", "biomarkers"]'
        mock_claude_client_class.return_value = mock_claude_client
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        with patch.object(workflow, 'extract_paper_content', return_value="test content"):
            with patch.object(workflow, 'update_yaml_with_tags'):
                result = workflow.process_items(self.temp_dir)
        
        # StatusManagerの呼び出し確認
        mock_status_manager.get_papers_needing_processing.assert_called_once_with(
            self.temp_dir, 'tagger', None
        )
        
        # 完了状態の更新確認
        self.assertEqual(mock_status_manager.update_status.call_count, 2)


class TestTaggerWorkflowQualityAssessment(unittest.TestCase):
    """TaggerWorkflowの品質評価・フィードバック機能テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('tagger', 'enabled'): True,
            ('tagger', 'batch_size'): 8,
            ('tagger', 'tag_count_range'): [10, 20],
        }.get(keys, default)
        
    def test_evaluate_tag_quality_high_quality(self):
        """タグ品質評価テスト（高品質）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        # 高品質タグ（適切な数、形式、専門性、論文内容と関連性高）
        tags = ["cancer_research", "breast_cancer", "biomarkers", "gene_krt13", "protein_egfr", 
                "oncology", "tumor_analysis", "protein_expression", "clinical_studies", 
                "molecular_biology", "gene_expression", "pathology"]
        
        paper_content = """This paper studies breast cancer biomarkers including gene_KRT13 and protein_EGFR genes. 
        The research focuses on cancer research methodologies and oncology applications. 
        We performed tumor analysis using protein expression and molecular biology techniques.
        Clinical studies were conducted to evaluate gene expression patterns in pathology samples."""
        
        quality_score = workflow.evaluate_tag_quality(tags, paper_content)
        
        self.assertGreaterEqual(quality_score, 0.7)  # 現実的な高品質閾値に調整
    
    def test_evaluate_tag_quality_low_quality(self):
        """タグ品質評価テスト（低品質）"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        # 低品質タグ（少数、形式不正、内容不適切）
        tags = ["test", "data123", "invalid tag", "x"]
        
        paper_content = "This paper studies breast cancer biomarkers including gene_KRT13 and protein_EGFR"
        
        quality_score = workflow.evaluate_tag_quality(tags, paper_content)
        
        self.assertLess(quality_score, 0.5)  # 低品質として評価
    
    def test_generate_feedback_report(self):
        """フィードバックレポート生成テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        tags = ["cancer_research", "biomarkers", "gene_krt13"]
        paper_content = "This paper studies breast cancer biomarkers"
        quality_score = 0.65
        
        feedback = workflow.generate_feedback_report(tags, paper_content, quality_score)
        
        self.assertIsInstance(feedback, dict)
        self.assertIn('quality_score', feedback)
        self.assertIn('tag_count', feedback)
        self.assertIn('format_compliance', feedback)
        self.assertIn('content_relevance', feedback)
        self.assertIn('suggestions', feedback)
        
        self.assertEqual(feedback['quality_score'], 0.65)
        self.assertEqual(feedback['tag_count'], 3)
    
    def test_suggest_improvements(self):
        """改善提案機能テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        # 少ないタグ数の場合
        tags = ["cancer", "research"]
        paper_content = "This paper studies breast cancer biomarkers including gene_KRT13"
        
        suggestions = workflow.suggest_improvements(tags, paper_content)
        
        self.assertIsInstance(suggestions, list)
        self.assertTrue(any("more tags" in suggestion.lower() for suggestion in suggestions))
        self.assertTrue(any("gene_krt13" in suggestion.lower() for suggestion in suggestions))
    
    def test_validate_tag_relevance(self):
        """タグ関連性検証テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        paper_content = "This paper studies breast cancer biomarkers including gene_KRT13 and protein_EGFR"
        
        # 関連性の高いタグ
        relevant_tag = "breast_cancer"
        relevance_score = workflow.validate_tag_relevance(relevant_tag, paper_content)
        self.assertGreater(relevance_score, 0.7)
        
        # 関連性の低いタグ
        irrelevant_tag = "astronomy"
        relevance_score = workflow.validate_tag_relevance(irrelevant_tag, paper_content)
        self.assertLess(relevance_score, 0.3)


class TestTaggerWorkflowGeneSymbolPreservation(unittest.TestCase):
    """遺伝子・タンパク質prefix付きタグ保護機能のテスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config_manager = Mock(spec=ConfigManager)
        self.logger = Mock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = Mock()
        
        # デフォルト設定をモック
        self.config_manager.get_ai_setting.side_effect = lambda *keys, default=None: {
            ('tagger', 'enabled'): True,
            ('tagger', 'batch_size'): 8,
            ('tagger', 'tag_count_range'): [10, 20],
        }.get(keys, default)
    
    def test_is_prefixed_gene_protein_tag(self):
        """prefix付き遺伝子・タンパク質タグ判定テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        # prefix付き遺伝子・タンパク質タグのテストケース
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_KRT13"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_KRT13"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_EGFR"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_EGFR"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_TP53"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_TP53"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_BRCA1"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_BRCA1"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_PIK3CA"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_PIK3CA"))
        
        # 非対象タグのテストケース
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("KRT13"))  # prefixなし
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("EGFR"))   # prefixなし
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("cancer_research"))
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("breast_cancer"))
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("oncology"))
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("western_blot"))
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("123"))
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("gene_"))  # シンボル部分なし
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("protein_"))  # シンボル部分なし
        self.assertFalse(workflow._is_prefixed_gene_protein_tag("rna_KRT13"))  # 無効なprefix
    
    def test_is_prefixed_gene_protein_tag_lowercase(self):
        """小文字形式からのprefix付きタグ判定テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        # 小文字のprefix付きタグも判定可能か
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_krt13"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_krt13"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_egfr"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_egfr"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("gene_tp53"))
        self.assertTrue(workflow._is_prefixed_gene_protein_tag("protein_tp53"))
    
    def test_preserve_prefixed_gene_protein_case(self):
        """prefix付き遺伝子・タンパク質タグ大文字保護機能テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        # prefix付き遺伝子・タンパク質タグはシンボル部分が大文字に変換される
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("gene_krt13"), "gene_KRT13")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("protein_krt13"), "protein_KRT13")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("gene_egfr"), "gene_EGFR")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("protein_egfr"), "protein_EGFR")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("gene_tp53"), "gene_TP53")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("protein_tp53"), "protein_TP53")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("gene_brca1"), "gene_BRCA1")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("protein_brca1"), "protein_BRCA1")
        
        # 一般的なタグは小文字のまま
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("cancer_research"), "cancer_research")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("breast_cancer"), "breast_cancer")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("oncology"), "oncology")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("western_blot"), "western_blot")
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("KRT13"), "krt13")  # prefixなし遺伝子は小文字
        self.assertEqual(workflow._preserve_prefixed_gene_protein_case("EGFR"), "egfr")   # prefixなし遺伝子は小文字
    
    def test_parse_tags_response_with_prefixed_gene_protein_tags(self):
        """prefix付き遺伝子・タンパク質タグ保護機能付きタグ解析テスト"""
        from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
        
        workflow = TaggerWorkflow(self.config_manager, self.logger)
        
        # LLMからの返答（prefix付きタグが大文字で返されたケース）
        response_uppercase = '["gene_KRT13", "cancer_research", "protein_EGFR", "breast_cancer", "gene_TP53"]'
        tags_uppercase = workflow._parse_tags_response(response_uppercase)
        
        expected_uppercase = ["gene_KRT13", "cancer_research", "protein_EGFR", "breast_cancer", "gene_TP53"]
        self.assertEqual(tags_uppercase, expected_uppercase)
        
        # LLMからの返答（prefix付きタグが小文字で返されたケース）
        response_lowercase = '["gene_krt13", "cancer_research", "protein_egfr", "breast_cancer", "gene_tp53"]'
        tags_lowercase = workflow._parse_tags_response(response_lowercase)
        
        expected_lowercase = ["gene_KRT13", "cancer_research", "protein_EGFR", "breast_cancer", "gene_TP53"]
        self.assertEqual(tags_lowercase, expected_lowercase)
        
        # 混在ケース（prefix付きとprefixなし混在）
        response_mixed = '["gene_KRT13", "cancer_research", "EGFR", "breast_cancer", "protein_tp53", "KRT13"]'
        tags_mixed = workflow._parse_tags_response(response_mixed)
        
        expected_mixed = ["gene_KRT13", "cancer_research", "egfr", "breast_cancer", "protein_TP53", "krt13"]
        self.assertEqual(tags_mixed, expected_mixed)


if __name__ == '__main__':
    unittest.main() 