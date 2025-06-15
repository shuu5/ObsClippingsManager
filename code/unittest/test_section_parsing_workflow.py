"""
test_section_parsing_workflow.py - SectionParsingWorkflow テストケース

論文セクション分割機能のユニットテスト
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch
from datetime import datetime

# プロジェクトのパスを設定
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'py'))

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import ProcessingError
from code.py.modules.section_parsing.section_parsing_workflow import SectionParsingWorkflow
from code.py.modules.section_parsing.section_structure import Section, PaperStructure


class TestSectionParsingWorkflowBasic(unittest.TestCase):
    """SectionParsingWorkflowの基本機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger(self.config_manager)
        self.workflow = SectionParsingWorkflow(self.config_manager, self.logger)
        
        # テンポラリディレクトリ作成
        self.temp_dir = tempfile.mkdtemp()
        self.test_paper_path = os.path.join(self.temp_dir, "test_paper.md")
        
    def tearDown(self):
        """テストクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_section_parsing_workflow_initialization(self):
        """SectionParsingWorkflowクラスの初期化テスト"""
        # 正常な初期化
        workflow = SectionParsingWorkflow(self.config_manager, self.logger)
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow.config_manager, self.config_manager)
        self.assertIsNotNone(workflow.logger)
        
    def test_is_heading_basic(self):
        """基本的な見出し判定テスト"""
        # 有効な見出し
        self.assertTrue(self.workflow._is_heading("## Abstract"))
        self.assertTrue(self.workflow._is_heading("### Introduction"))
        self.assertTrue(self.workflow._is_heading("#### Methods"))
        
        # 無効な見出し
        self.assertFalse(self.workflow._is_heading("# Title"))  # H1は対象外
        self.assertFalse(self.workflow._is_heading("普通のテキスト"))
        self.assertFalse(self.workflow._is_heading(""))
        
    def test_get_heading_level(self):
        """見出しレベル取得テスト"""
        self.assertEqual(self.workflow._get_heading_level("## Abstract"), 2)
        self.assertEqual(self.workflow._get_heading_level("### Introduction"), 3)
        self.assertEqual(self.workflow._get_heading_level("#### Methods"), 4)
        
    def test_extract_title(self):
        """タイトル抽出テスト"""
        self.assertEqual(self.workflow._extract_title("## Abstract"), "Abstract")
        self.assertEqual(self.workflow._extract_title("### Introduction"), "Introduction")
        self.assertEqual(self.workflow._extract_title("#### Methods and Data"), "Methods and Data")
        

class TestSectionTypeIdentification(unittest.TestCase):
    """セクション種別識別テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger(self.config_manager)
        self.workflow = SectionParsingWorkflow(self.config_manager, self.logger)
        
    def test_identify_section_type_standard_patterns(self):
        """標準的なセクション種別識別テスト"""
        # Abstract
        self.assertEqual(self.workflow._identify_section_type("## Abstract"), "abstract")
        self.assertEqual(self.workflow._identify_section_type("### Summary"), "abstract")
        
        # Introduction
        self.assertEqual(self.workflow._identify_section_type("## Introduction"), "introduction")
        self.assertEqual(self.workflow._identify_section_type("### Background"), "introduction")
        
        # Methods
        self.assertEqual(self.workflow._identify_section_type("## Methods"), "methods")
        self.assertEqual(self.workflow._identify_section_type("### Methodology"), "methods")
        self.assertEqual(self.workflow._identify_section_type("## Materials and Methods"), "methods")
        
        # Results
        self.assertEqual(self.workflow._identify_section_type("## Results"), "results")
        self.assertEqual(self.workflow._identify_section_type("### Findings"), "results")
        
        # Discussion
        self.assertEqual(self.workflow._identify_section_type("## Discussion"), "discussion")
        self.assertEqual(self.workflow._identify_section_type("### Discussion and Conclusions"), "discussion")
        
        # Unknown
        self.assertEqual(self.workflow._identify_section_type("## Unknown Section"), "unknown")


class TestSectionExtraction(unittest.TestCase):
    """セクション抽出機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger(self.config_manager)
        self.workflow = SectionParsingWorkflow(self.config_manager, self.logger)
        
        # テンポラリディレクトリ作成
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """テストクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_extract_sections_basic_structure(self):
        """基本的なセクション構造抽出テスト"""
        content_lines = [
            "---",
            "title: Test Paper",
            "---",
            "",
            "## Abstract",
            "This is the abstract content.",
            "It contains multiple lines.",
            "",
            "## Introduction", 
            "This is the introduction.",
            "Background information here.",
            "",
            "### Background",
            "Detailed background information.",
            "",
            "## Methods",
            "Description of methods used.",
            "Step by step procedures."
        ]
        
        sections = self.workflow._extract_sections(content_lines)
        
        # セクション数の確認
        self.assertEqual(len(sections), 3)  # Abstract, Introduction, Methods
        
        # Abstract セクション確認
        abstract = sections[0]
        self.assertEqual(abstract.title, "Abstract")
        self.assertEqual(abstract.level, 2)
        self.assertEqual(abstract.section_type, "abstract")
        self.assertEqual(abstract.start_line, 2)  # 5行目-3行目 = 2行目（YAMLヘッダー除外後の相対行数）
        self.assertEqual(abstract.end_line, 5)   # 8行目-3行目 = 5行目
        
        # Introduction セクション確認
        introduction = sections[1]
        self.assertEqual(introduction.title, "Introduction")
        self.assertEqual(introduction.level, 2)
        self.assertEqual(introduction.section_type, "introduction")
        self.assertEqual(introduction.start_line, 6)  # 9行目-3行目 = 6行目
        self.assertEqual(introduction.end_line, 9)   # 12行目-3行目 = 9行目
        
        # Introduction の子セクション確認
        self.assertEqual(len(introduction.subsections), 1)
        background = introduction.subsections[0]
        self.assertEqual(background.title, "Background")
        self.assertEqual(background.level, 3)
        
    def test_extract_sections_no_headings(self):
        """見出しなしのテキスト処理テスト"""
        content_lines = [
            "---",
            "title: Test Paper",
            "---",
            "",
            "This is a paper without headings.",
            "It contains only plain text.",
            "No section structure."
        ]
        
        sections = self.workflow._extract_sections(content_lines)
        
        # セクションなしの場合は空リスト
        self.assertEqual(len(sections), 0)
        
    def test_count_words(self):
        """文字数カウントテスト"""
        content_lines = [
            "---",
            "title: Test",
            "---",
            "## Test Section",
            "",
            "This is a test content.",
            "It has multiple lines.",
            "Each line contains words."
        ]
        
        yaml_header_end_line = 3  # YAMLヘッダーは3行目まで
        word_count = self.workflow._count_words_from_markdown_lines(content_lines, yaml_header_end_line, 1, 5)
        
        # 文字数が計算されていることを確認
        self.assertGreater(word_count, 0)

    def test_extract_sections_with_real_yaml_header(self):
        """実際のYAMLヘッダーがある場合のセクション抽出テスト"""
        content_lines = [
            "---",
            "citation_key: test2023paper",
            "title: Test Paper",
            "paper_structure:",
            "  sections:",
            "  - title: Abstract",
            "    start_line: 41",
            "    end_line: 45",
            "---",
            "",
            "Journal Article",
            "",
            "## Abstract",
            "",
            "This is the actual abstract content.",
            "It contains multiple lines of text.",
            "",
            "## INTRODUCTION",
            "",
            "This is the introduction section.",
            "Background information is provided here.",
            "",
            "## MATERIALS AND METHODS",
            "",
            "This section describes the methodology.",
            "",
            "## RESULTS",
            "",
            "Results are presented here.",
            "",
            "## DISCUSSION",
            "",
            "Discussion of the results."
        ]
        
        sections = self.workflow._extract_sections(content_lines)
        
        # セクション数の確認
        self.assertEqual(len(sections), 5)  # Abstract, Introduction, Methods, Results, Discussion
        
        # Abstract セクション確認（YAMLヘッダー除外後の相対行数）
        abstract = sections[0]
        self.assertEqual(abstract.title, "Abstract")
        self.assertEqual(abstract.level, 2)
        self.assertEqual(abstract.section_type, "abstract")
        self.assertEqual(abstract.start_line, 4)  # 13行目-9行目 = 4行目（YAMLヘッダー除外後の相対行数）
        
        # Introduction セクション確認
        introduction = sections[1]
        self.assertEqual(introduction.title, "INTRODUCTION")
        self.assertEqual(introduction.level, 2)
        self.assertEqual(introduction.section_type, "introduction")
        self.assertEqual(introduction.start_line, 9)  # 18行目-9行目 = 9行目（YAMLヘッダー除外後の相対行数）
        
        # Methods セクション確認
        methods = sections[2]
        self.assertEqual(methods.title, "MATERIALS AND METHODS")
        self.assertEqual(methods.level, 2)
        self.assertEqual(methods.section_type, "methods")
        self.assertEqual(methods.start_line, 14)  # 23行目-9行目 = 14行目（YAMLヘッダー除外後の相対行数）
        
        # Results セクション確認
        results = sections[3]
        self.assertEqual(results.title, "RESULTS")
        self.assertEqual(results.level, 2)
        self.assertEqual(results.section_type, "results")
        self.assertEqual(results.start_line, 18)  # 27行目-9行目 = 18行目（YAMLヘッダー除外後の相対行数）
        
        # Discussion セクション確認
        discussion = sections[4]
        self.assertEqual(discussion.title, "DISCUSSION")
        self.assertEqual(discussion.level, 2)
        self.assertEqual(discussion.section_type, "discussion")
        self.assertEqual(discussion.start_line, 22)  # 31行目-9行目 = 22行目（YAMLヘッダー除外後の相対行数）


class TestPaperStructureBuilding(unittest.TestCase):
    """論文構造構築テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger(self.config_manager)
        self.workflow = SectionParsingWorkflow(self.config_manager, self.logger)
        
    def test_build_paper_structure(self):
        """論文構造構築テスト"""
        # テスト用セクション作成
        sections = [
            Section("Abstract", 2, "abstract", 5, 8, 25, ["Abstract content"]),
            Section("Introduction", 2, "introduction", 10, 15, 50, ["Intro content"]),
            Section("Methods", 2, "methods", 17, 22, 75, ["Methods content"])
        ]
        
        paper_structure = self.workflow._build_paper_structure(sections)
        
        # 基本構造確認
        self.assertIsInstance(paper_structure, PaperStructure)
        self.assertEqual(paper_structure.total_sections, 3)
        self.assertEqual(len(paper_structure.sections), 3)
        self.assertIn("abstract", paper_structure.section_types_found)
        self.assertIn("introduction", paper_structure.section_types_found)
        self.assertIn("methods", paper_structure.section_types_found)
        
    def test_yaml_dict_conversion(self):
        """YAML辞書変換テスト"""
        paper_structure = PaperStructure()
        section = Section("Abstract", 2, "abstract", 5, 8, 25)
        paper_structure.add_section(section)
        
        yaml_dict = paper_structure.to_yaml_dict()
        
        # 必要なキーの存在確認
        self.assertIn('parsed_at', yaml_dict)
        self.assertIn('total_sections', yaml_dict)
        self.assertIn('sections', yaml_dict)
        self.assertIn('section_types_found', yaml_dict)
        
        # 値の確認
        self.assertEqual(yaml_dict['total_sections'], 1)
        self.assertEqual(len(yaml_dict['sections']), 1)
        self.assertIn('abstract', yaml_dict['section_types_found'])


class TestSectionParsingWorkflowImport(unittest.TestCase):
    """SectionParsingWorkflowインポートテスト"""
    
    def test_section_parsing_workflow_import(self):
        """SectionParsingWorkflowクラスのインポートテスト"""
        try:
            from code.py.modules.section_parsing.section_parsing_workflow import SectionParsingWorkflow
            self.assertTrue(True)
        except ImportError:
            self.fail("SectionParsingWorkflowクラスのインポートに失敗しました")
    
    def test_section_structure_import(self):
        """Section・PaperStructureクラスのインポートテスト"""
        try:
            from code.py.modules.section_parsing.section_structure import Section, PaperStructure
            self.assertTrue(True)
        except ImportError:
            self.fail("セクション構造クラスのインポートに失敗しました")
    
    def test_section_parsing_module_import(self):
        """section_parsingモジュール全体のインポートテスト"""
        try:
            from code.py.modules.section_parsing import SectionParsingWorkflow, Section, PaperStructure
            self.assertTrue(True)
        except ImportError:
            self.fail("section_parsingモジュールのインポートに失敗しました")


if __name__ == '__main__':
    unittest.main() 