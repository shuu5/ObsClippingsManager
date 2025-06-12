#!/usr/bin/env python3
"""
論文セクション分割機能のテスト

論文セクション分割機能のすべての機能をテストします。
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any

# テスト環境のパス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.section_parsing.section_parser_workflow import SectionParserWorkflow
from modules.section_parsing.data_structures import Section, PaperStructure
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError


class TestSection(unittest.TestCase):
    """Sectionデータクラスのテスト"""
    
    def test_section_creation(self):
        """Sectionオブジェクト作成のテスト"""
        section = Section(
            title="Introduction",
            level=2,
            content="This is the introduction section...",
            start_line=10,
            end_line=50,
            word_count=250,
            subsections=[],
            section_type="introduction"
        )
        
        self.assertEqual(section.title, "Introduction")
        self.assertEqual(section.level, 2)
        self.assertEqual(section.section_type, "introduction")
        self.assertEqual(section.word_count, 250)
        self.assertEqual(len(section.subsections), 0)


class TestPaperStructure(unittest.TestCase):
    """PaperStructureデータクラスのテスト"""
    
    def test_paper_structure_creation(self):
        """PaperStructureオブジェクト作成のテスト"""
        sections = [
            Section("Abstract", 2, "Abstract content...", 1, 10, 100, [], "abstract"),
            Section("Introduction", 2, "Introduction content...", 12, 50, 400, [], "introduction")
        ]
        
        structure = PaperStructure(
            sections=sections,
            total_sections=2,
            section_types_found=["abstract", "introduction"],
            parsed_at="2025-01-15T10:30:00.123456"
        )
        
        self.assertEqual(len(structure.sections), 2)
        self.assertEqual(structure.total_sections, 2)
        self.assertIn("abstract", structure.section_types_found)
        self.assertIn("introduction", structure.section_types_found)


class TestSectionParserWorkflow(unittest.TestCase):
    """SectionParserWorkflowのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger()
        self.workflow = SectionParserWorkflow(self.config_manager, self.logger)
        
        # テスト用Markdownファイルの作成
        self.test_md_content = """---
citation_key: test2023paper
processing_status:
  section_parsing: pending
workflow_version: '3.2'
---

# Test Paper

## Abstract

This is the abstract section of the test paper. It contains a brief summary of the research work.

## Introduction

This is the introduction section. It provides background information about the research topic.

### Background

This is a subsection of the introduction that provides specific background details.

## Methods

This section describes the methodology used in the research.

## Results

This section presents the findings of the research.

## Discussion

This section discusses the implications of the results.

## Conclusion

This section provides concluding remarks.
"""
        
        self.test_paper_path = os.path.join(self.test_dir, "test2023paper", "test2023paper.md")
        os.makedirs(os.path.dirname(self.test_paper_path), exist_ok=True)
        
        with open(self.test_paper_path, 'w', encoding='utf-8') as f:
            f.write(self.test_md_content)
    
    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_extract_sections_by_heading(self):
        """見出しレベルによるセクション分割のテスト"""
        sections = self.workflow.extract_sections_by_heading(self.test_md_content)
        
        # セクション数の確認
        self.assertGreater(len(sections), 0)
        
        # 各セクションの基本属性確認
        for section in sections:
            self.assertIsInstance(section.title, str)
            self.assertIsInstance(section.level, int)
            self.assertIsInstance(section.content, str)
            self.assertIsInstance(section.start_line, int)
            self.assertIsInstance(section.end_line, int)
            self.assertIsInstance(section.word_count, int)
    
    def test_identify_section_types(self):
        """セクションタイプ自動識別のテスト"""
        sections = self.workflow.extract_sections_by_heading(self.test_md_content)
        self.workflow.identify_section_types(sections)
        
        # 特定のセクションタイプが正しく識別されているか確認
        section_types = [section.section_type for section in sections]
        
        self.assertIn("abstract", section_types)
        self.assertIn("introduction", section_types)
        self.assertIn("methods", section_types)
        self.assertIn("results", section_types)
        self.assertIn("discussion", section_types)
    
    def test_parse_paper_structure(self):
        """単一論文の構造解析のテスト"""
        structure = self.workflow.parse_paper_structure(self.test_paper_path)
        
        # 基本構造の確認
        self.assertIsInstance(structure, PaperStructure)
        self.assertGreater(structure.total_sections, 0)
        self.assertGreater(len(structure.sections), 0)
        self.assertGreater(len(structure.section_types_found), 0)
        self.assertIsInstance(structure.parsed_at, str)
        
        # 特定セクションが含まれているか確認
        self.assertIn("abstract", structure.section_types_found)
        self.assertIn("introduction", structure.section_types_found)
    
    def test_update_yaml_with_structure(self):
        """YAMLヘッダーへのセクション情報記録のテスト"""
        structure = self.workflow.parse_paper_structure(self.test_paper_path)
        success = self.workflow.update_yaml_with_structure(self.test_paper_path, structure)
        
        self.assertTrue(success)
        
        # 更新されたファイルの確認
        with open(self.test_paper_path, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        # YAMLヘッダーにpaper_structureが追加されているか確認
        self.assertIn("paper_structure:", updated_content)
        self.assertIn("parsed_at:", updated_content)
        self.assertIn("total_sections:", updated_content)
        self.assertIn("sections:", updated_content)
    
    def test_process_papers_batch(self):
        """論文の一括セクション解析処理のテスト"""
        result = self.workflow.process_papers(self.test_dir, ["test2023paper"])
        
        self.assertIn("status", result)
        self.assertIn("processed_count", result)
        self.assertIn("failed_count", result)
        
        # 正常処理の確認
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["failed_count"], 0)


class TestSectionPatternMatching(unittest.TestCase):
    """セクション識別パターンマッチングのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger()
        self.workflow = SectionParserWorkflow(self.config_manager, self.logger)
    
    def test_abstract_pattern_matching(self):
        """Abstract パターンマッチングのテスト"""
        test_titles = ["Abstract", "ABSTRACT", "Summary", "摘要"]
        
        for title in test_titles[:2]:  # Abstract, ABSTRACT のみテスト
            section = Section(title, 2, "content", 1, 10, 100, [], "unknown")
            self.workflow.identify_section_types([section])
            self.assertEqual(section.section_type, "abstract")
    
    def test_introduction_pattern_matching(self):
        """Introduction パターンマッチングのテスト"""
        test_titles = ["Introduction", "INTRODUCTION", "Intro", "Background"]
        
        for title in test_titles:
            section = Section(title, 2, "content", 1, 10, 100, [], "unknown")
            self.workflow.identify_section_types([section])
            self.assertEqual(section.section_type, "introduction")
    
    def test_methods_pattern_matching(self):
        """Methods パターンマッチングのテスト"""
        test_titles = ["Methods", "Methodology", "Materials and Methods", "Experimental"]
        
        for title in test_titles:
            section = Section(title, 2, "content", 1, 10, 100, [], "unknown")
            self.workflow.identify_section_types([section])
            self.assertEqual(section.section_type, "methods")
    
    def test_unknown_section_handling(self):
        """不明セクションの処理テスト"""
        section = Section("Unknown Section", 2, "content", 1, 10, 100, [], "unknown")
        self.workflow.identify_section_types([section])
        self.assertEqual(section.section_type, "unknown")


if __name__ == '__main__':
    unittest.main() 