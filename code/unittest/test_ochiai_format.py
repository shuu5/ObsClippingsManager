#!/usr/bin/env python3
"""
落合フォーマット要約機能のテスト

落合フォーマット要約機能のすべての機能をテストします。
"""

import unittest
import tempfile
import os
import json
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any
from unittest.mock import Mock, patch

# テスト環境のパス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.ochiai_format.ochiai_format_workflow import OchiaiFormatWorkflow
from modules.ochiai_format.data_structures import OchiaiFormat
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError


class TestOchiaiFormat(unittest.TestCase):
    """OchiaiFormatデータクラスのテスト"""
    
    def test_ochiai_format_creation(self):
        """OchiaiFormatオブジェクト作成のテスト"""
        ochiai = OchiaiFormat(
            what_is_this="新しい機械学習手法による論文分類システム",
            what_is_superior="従来手法と比較して精度が20%向上",
            technical_key="深層学習とトランスファーラーニングの組み合わせ",
            validation_method="1000論文のデータセットで検証",
            discussion_points="計算コストが高い点が課題",
            next_papers="1. Smith et al. (2023) - 関連手法, 2. Jones et al. (2024) - 改善案",
            generated_at="2025-01-15T11:00:00.123456"
        )
        
        self.assertIsInstance(ochiai.what_is_this, str)
        self.assertIsInstance(ochiai.what_is_superior, str)
        self.assertIsInstance(ochiai.technical_key, str)
        self.assertIsInstance(ochiai.validation_method, str)
        self.assertIsInstance(ochiai.discussion_points, str)
        self.assertIsInstance(ochiai.next_papers, str)
        self.assertIsInstance(ochiai.generated_at, str)


class TestOchiaiFormatWorkflow(unittest.TestCase):
    """OchiaiFormatWorkflowのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger()
        
        # Claude APIクライアントをモック化
        with patch('modules.ochiai_format.ochiai_format_workflow.ClaudeAPIClient'):
            self.workflow = OchiaiFormatWorkflow(self.config_manager, self.logger)
        
        # テスト用Markdownファイルの作成
        self.test_md_content = """---
citation_key: test2023paper
processing_status:
  ochiai_format: pending
workflow_version: '3.2'
---

# Machine Learning Approach for Cancer Diagnosis

## Abstract

This paper presents a novel machine learning approach for cancer diagnosis using deep learning techniques. The proposed method achieves 95% accuracy in cancer detection, significantly outperforming traditional methods.

## Introduction

Cancer diagnosis is a critical medical challenge. Traditional methods rely on subjective interpretation by pathologists, leading to variability in diagnosis.

## Methods

We developed a convolutional neural network (CNN) architecture trained on a dataset of 10,000 histopathological images. The model uses transfer learning from ImageNet.

## Results

Our model achieved 95% accuracy, 92% sensitivity, and 98% specificity on the test dataset. This represents a 20% improvement over conventional methods.

## Discussion

The proposed method shows promise for clinical application. However, challenges remain in terms of computational cost and interpretability.

## References

1. Smith, J. et al. (2022). Deep Learning in Medical Imaging. Nature Medicine.
2. Jones, A. et al. (2023). CNN Architectures for Pathology. Medical AI Journal.
3. Brown, K. et al. (2024). Transfer Learning in Healthcare. JAMA.
"""
        
        self.test_paper_path = os.path.join(self.test_dir, "test2023paper", "test2023paper.md")
        os.makedirs(os.path.dirname(self.test_paper_path), exist_ok=True)
        
        with open(self.test_paper_path, 'w', encoding='utf-8') as f:
            f.write(self.test_md_content)
    
    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_extract_paper_content(self):
        """論文内容抽出のテスト"""
        content = self.workflow.extract_paper_content(self.test_paper_path)
        
        self.assertIn("title", content)
        self.assertIn("content", content)
        self.assertIsInstance(content["title"], str)
        self.assertIsInstance(content["content"], str)
        
        # タイトルが正しく抽出されているか確認
        self.assertIn("Machine Learning", content["title"])
        
        # 本文に各セクションが含まれているか確認
        self.assertIn("Abstract", content["content"])
        self.assertIn("Introduction", content["content"])
        self.assertIn("Methods", content["content"])
        self.assertIn("Results", content["content"])
    
    @patch('modules.ochiai_format.ochiai_format_workflow.ClaudeAPIClient')
    def test_generate_ochiai_summary_single(self, mock_claude_client):
        """単一論文の落合フォーマット要約生成のテスト"""
        # Claude APIのレスポンスをモック
        mock_response = {
            "what_is_this": "機械学習を用いたがん診断の新手法。深層学習技術により従来法より高精度な診断を実現。",
            "what_is_superior": "従来の主観的診断に対し、客観的で一貫性のある診断を提供。精度20%向上を達成。",
            "technical_key": "畳み込みニューラルネットワーク(CNN)とImageNetからの転移学習を組み合わせた手法。",
            "validation_method": "10,000枚の病理組織画像データセットでの検証。精度95%、感度92%、特異度98%を達成。",
            "discussion_points": "計算コストと解釈可能性に課題。臨床実装には更なる検証が必要。",
            "next_papers": "1. Smith et al. (2022) - 医療画像の深層学習基礎, 2. Jones et al. (2023) - 病理向けCNN, 3. Brown et al. (2024) - 医療転移学習"
        }
        
        mock_claude_client.return_value.generate_ochiai_summary.return_value = mock_response
        
        ochiai = self.workflow.generate_ochiai_summary_single(self.test_paper_path)
        
        self.assertIsInstance(ochiai, OchiaiFormat)
        self.assertIn("機械学習", ochiai.what_is_this)
        self.assertIn("従来", ochiai.what_is_superior)
        self.assertIn("CNN", ochiai.technical_key)
        self.assertIn("10,000", ochiai.validation_method)
        self.assertIn("計算コスト", ochiai.discussion_points)
        self.assertIn("Smith", ochiai.next_papers)
    
    def test_validate_ochiai_format(self):
        """落合フォーマット品質検証のテスト"""
        # 正常なフォーマット
        valid_ochiai = OchiaiFormat(
            what_is_this="十分な長さの説明文。詳細な内容を含む。",
            what_is_superior="比較に関する詳細な説明。優位性を明確に記述。",
            technical_key="技術的な核心部分の詳細。具体的な手法を説明。",
            validation_method="検証方法の詳細。データと結果を含む。",
            discussion_points="議論点の詳細。限界と課題を明記。",
            next_papers="推奨論文リスト。参考文献から選出。",
            generated_at="2025-01-15T11:00:00.123456"
        )
        
        self.assertTrue(self.workflow.validate_ochiai_format(valid_ochiai))
        
        # 不正なフォーマット（短すぎる内容）
        invalid_ochiai = OchiaiFormat(
            what_is_this="短い",
            what_is_superior="短い",
            technical_key="短い",
            validation_method="短い",
            discussion_points="短い",
            next_papers="短い",
            generated_at="2025-01-15T11:00:00.123456"
        )
        
        self.assertFalse(self.workflow.validate_ochiai_format(invalid_ochiai))
    
    def test_update_yaml_with_ochiai(self):
        """YAMLヘッダーへの落合フォーマット記録のテスト"""
        ochiai = OchiaiFormat(
            what_is_this="機械学習を用いたがん診断システム",
            what_is_superior="従来手法より20%精度向上",
            technical_key="CNNと転移学習の組み合わせ",
            validation_method="10,000画像での検証",
            discussion_points="計算コストが課題",
            next_papers="関連論文3本を推奨",
            generated_at="2025-01-15T11:00:00.123456"
        )
        
        success = self.workflow.update_yaml_with_ochiai(self.test_paper_path, ochiai)
        self.assertTrue(success)
        
        # 更新されたファイルの確認
        with open(self.test_paper_path, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        # YAMLヘッダーにochiai_formatが追加されているか確認
        self.assertIn("ochiai_format:", updated_content)
        self.assertIn("generated_at:", updated_content)
        self.assertIn("questions:", updated_content)
        self.assertIn("what_is_this:", updated_content)
        self.assertIn("what_is_superior:", updated_content)
    
    @patch('modules.ochiai_format.ochiai_format_workflow.ClaudeAPIClient')
    def test_process_papers_batch(self, mock_claude_client):
        """論文の一括落合フォーマット要約処理のテスト"""
        # Claude APIのレスポンスをモック
        mock_response = {
            "what_is_this": "機械学習診断システム",
            "what_is_superior": "精度向上20%",
            "technical_key": "CNN技術",
            "validation_method": "大規模データセット検証",
            "discussion_points": "計算コスト課題",
            "next_papers": "関連論文推奨"
        }
        
        mock_claude_client.return_value.generate_ochiai_summary.return_value = mock_response
        
        result = self.workflow.process_papers(self.test_dir, ["test2023paper"], batch_size=1)
        
        self.assertIn("status", result)
        self.assertIn("processed_count", result)
        self.assertIn("failed_count", result)
        
        # 正常処理の確認
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["failed_count"], 0)


class TestOchiaiFormatSectionIntegration(unittest.TestCase):
    """セクション分割機能との連携テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger()
        
        with patch('modules.ochiai_format.ochiai_format_workflow.ClaudeAPIClient'):
            self.workflow = OchiaiFormatWorkflow(self.config_manager, self.logger)
        
        # セクション情報付きのテストファイル
        self.test_md_with_structure = """---
citation_key: test2023paper
paper_structure:
  parsed_at: '2025-01-15T10:30:00.123456'
  total_sections: 3
  sections:
    - title: "Abstract" 
      level: 2
      section_type: "abstract"
      start_line: 8
      end_line: 12
      word_count: 50
    - title: "Introduction"
      level: 2  
      section_type: "introduction"
      start_line: 14
      end_line: 18
      word_count: 80
    - title: "Methods"
      level: 2
      section_type: "methods" 
      start_line: 20
      end_line: 24
      word_count: 70
  section_types_found: ["abstract", "introduction", "methods"]
processing_status:
  section_parsing: completed
  ochiai_format: pending
workflow_version: '3.2'
---

# Test Paper

## Abstract
Brief summary of the research.

## Introduction
Background information.

## Methods
Research methodology.
"""
        
        self.test_paper_path = os.path.join(self.test_dir, "test2023paper", "test2023paper.md")
        os.makedirs(os.path.dirname(self.test_paper_path), exist_ok=True)
        
        with open(self.test_paper_path, 'w', encoding='utf-8') as f:
            f.write(self.test_md_with_structure)
    
    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_extract_paper_content_with_sections(self):
        """セクション情報を活用したコンテンツ抽出のテスト"""
        content = self.workflow.extract_paper_content(self.test_paper_path)
        
        # セクション別情報が含まれているか確認
        if "abstract_content" in content:
            self.assertIn("Brief summary", content["abstract_content"])
        if "introduction_content" in content:
            self.assertIn("Background", content["introduction_content"])
        if "methods_content" in content:
            self.assertIn("methodology", content["methods_content"])


if __name__ == '__main__':
    unittest.main() 