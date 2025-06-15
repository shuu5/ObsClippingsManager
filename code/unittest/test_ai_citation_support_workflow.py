"""
AI Citation Support Workflow Test Suite

AI理解支援引用文献パーサー機能のテスト
- AICitationSupportWorkflowクラスの基本機能テスト
- references.bib読み込み・解析テスト
- YAMLヘッダー更新テスト
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import yaml
from datetime import datetime

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import ProcessingError


class TestAICitationSupportWorkflow(unittest.TestCase):
    """AICitationSupportWorkflowクラステスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = MagicMock()
        self.logger = MagicMock()
        
        # 設定モック
        self.config_manager.get.return_value = {
            'ai_citation_support': {
                'enabled': True,
                'mapping_version': '2.0',
                'preserve_existing_citations': True,
                'update_existing_mapping': True,
                'batch_size': 10
            }
        }
        
    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # === 基本機能テスト ===
    def test_ai_citation_support_workflow_initialization(self):
        """AICitationSupportワークフロー初期化テスト"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            workflow = AICitationSupportWorkflow(self.config_manager, self.logger)
            
            # 基本属性の確認
            self.assertIsNotNone(workflow.config_manager)
            self.assertIsNotNone(workflow.integrated_logger)
            self.assertIsNotNone(workflow.logger)
            self.assertIsNotNone(workflow.bibtex_parser)
            self.assertIsNotNone(workflow.yaml_processor)
            
        except ImportError:
            # まだ実装されていない場合はスキップ
            self.skipTest("AICitationSupportWorkflow not implemented yet")
    
    def test_find_references_bib_exists(self):
        """references.bibファイル検索テスト（存在する場合）"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            workflow = AICitationSupportWorkflow(self.config_manager, self.logger)
            
            # テスト用論文ディレクトリと references.bib 作成
            paper_dir = Path(self.temp_dir) / "smith2023test"
            paper_dir.mkdir()
            paper_path = paper_dir / "smith2023test.md"
            paper_path.write_text("# Test Paper", encoding='utf-8')
            
            references_bib = paper_dir / "references.bib"
            references_bib.write_text("@article{test, title={Test}}", encoding='utf-8')
            
            # references.bib検索テスト
            found_path = workflow._find_references_bib(str(paper_path))
            
            self.assertIsNotNone(found_path)
            self.assertTrue(found_path.endswith('references.bib'))
            self.assertTrue(os.path.exists(found_path))
            
        except ImportError:
            self.skipTest("AICitationSupportWorkflow not implemented yet")
    
    def test_find_references_bib_not_exists(self):
        """references.bibファイル検索テスト（存在しない場合）"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            workflow = AICitationSupportWorkflow(self.config_manager, self.logger)
            
            # テスト用論文ディレクトリ作成（references.bibなし）
            paper_dir = Path(self.temp_dir) / "smith2023test"
            paper_dir.mkdir()
            paper_path = paper_dir / "smith2023test.md"
            paper_path.write_text("# Test Paper", encoding='utf-8')
            
            # references.bib検索テスト（Noneが返される）
            found_path = workflow._find_references_bib(str(paper_path))
            
            self.assertIsNone(found_path)
            
        except ImportError:
            self.skipTest("AICitationSupportWorkflow not implemented yet")
    
    def test_create_citation_mapping_basic(self):
        """基本的な引用マッピング作成テスト"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            workflow = AICitationSupportWorkflow(self.config_manager, self.logger)
            
            # サンプルBibTeXエントリー
            bibtex_entries = {
                'smith2023test': {
                    'ID': 'smith2023test',
                    'title': 'Novel Method for Cancer Cell Analysis',
                    'author': 'Smith, John',
                    'year': '2023',
                    'journal': 'Cancer Research',
                    'doi': '10.1158/0008-5472.CAN-23-0123'
                },
                'jones2022biomarkers': {
                    'ID': 'jones2022biomarkers',
                    'title': 'Advanced Biomarker Techniques',
                    'author': 'Jones, Alice',
                    'year': '2022',
                    'journal': 'Nature Medicine',
                    'doi': '10.1038/s41591-022-0456-7'
                }
            }
            
            references_bib_path = "/test/path/references.bib"
            
            # 引用マッピング作成
            mapping = workflow.create_citation_mapping(bibtex_entries, references_bib_path)
            
            # 検証
            self.assertIn('citation_metadata', mapping)
            self.assertIn('citations', mapping)
            
            # citation_metadata検証
            metadata = mapping['citation_metadata']
            self.assertEqual(metadata['mapping_version'], '2.0')
            self.assertEqual(metadata['source_bibtex'], 'references.bib')
            self.assertEqual(metadata['total_citations'], 2)
            self.assertIn('last_updated', metadata)
            
            # citations検証
            citations = mapping['citations']
            self.assertEqual(len(citations), 2)
            
            # 第1の引用文献
            self.assertIn(1, citations)
            citation1 = citations[1]
            self.assertEqual(citation1['citation_key'], 'smith2023test')
            self.assertEqual(citation1['title'], 'Novel Method for Cancer Cell Analysis')
            self.assertEqual(citation1['authors'], 'Smith, John')
            self.assertEqual(citation1['year'], '2023')
            self.assertEqual(citation1['journal'], 'Cancer Research')
            self.assertEqual(citation1['doi'], '10.1158/0008-5472.CAN-23-0123')
            
        except ImportError:
            self.skipTest("AICitationSupportWorkflow not implemented yet")
    
    def test_update_yaml_with_citations(self):
        """YAMLヘッダーへの引用情報統合テスト"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            workflow = AICitationSupportWorkflow(self.config_manager, self.logger)
            
            # テスト用Markdownファイル作成
            paper_path = Path(self.temp_dir) / "test_paper.md"
            test_content = """---
citation_key: smith2023test
workflow_version: '3.2'
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  ai_citation_support: pending
citation_metadata:
  last_updated: null
  mapping_version: null
  source_bibtex: null
  total_citations: 0
citations: {}
---

# Test Paper Content
"""
            paper_path.write_text(test_content, encoding='utf-8')
            
            # サンプル引用マッピング
            citation_mapping = {
                'citation_metadata': {
                    'last_updated': '2025-01-15T10:30:00.123456',
                    'mapping_version': '2.0',
                    'source_bibtex': 'references.bib',
                    'total_citations': 1
                },
                'citations': {
                    1: {
                        'citation_key': 'smith2023test',
                        'title': 'Test Paper',
                        'authors': 'Smith, John',
                        'year': '2023',
                        'journal': 'Nature',
                        'doi': '10.1038/test'
                    }
                }
            }
            
            # YAMLヘッダー更新
            workflow.update_yaml_with_citations(str(paper_path), citation_mapping)
            
            # 更新結果確認
            with open(paper_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAML部分を抽出して検証
            yaml_start = content.find('---\n') + 4
            yaml_end = content.find('\n---\n', yaml_start)
            yaml_content = content[yaml_start:yaml_end]
            yaml_data = yaml.safe_load(yaml_content)
            
            # 処理状態の更新確認
            self.assertEqual(yaml_data['processing_status']['ai_citation_support'], 'completed')
            
            # citation_metadata更新確認
            metadata = yaml_data['citation_metadata']
            self.assertEqual(metadata['mapping_version'], '2.0')
            self.assertEqual(metadata['source_bibtex'], 'references.bib')
            self.assertEqual(metadata['total_citations'], 1)
            
            # citations更新確認
            citations = yaml_data['citations']
            self.assertEqual(len(citations), 1)
            self.assertIn(1, citations)
            self.assertEqual(citations[1]['citation_key'], 'smith2023test')
            
        except ImportError:
            self.skipTest("AICitationSupportWorkflow not implemented yet")
    
    def test_process_items_with_valid_references(self):
        """有効なreferences.bibファイルがある場合の処理テスト"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            workflow = AICitationSupportWorkflow(self.config_manager, self.logger)
            
            # テスト用ディレクトリ構造作成
            clippings_dir = Path(self.temp_dir) / "Clippings"
            clippings_dir.mkdir()
            
            paper_dir = clippings_dir / "smith2023test"
            paper_dir.mkdir()
            
            # Markdownファイル作成
            paper_path = paper_dir / "smith2023test.md"
            test_content = """---
citation_key: smith2023test
processing_status:
  fetch: completed
  ai_citation_support: pending
citation_metadata:
  total_citations: 0
citations: {}
---

# Test Paper
"""
            paper_path.write_text(test_content, encoding='utf-8')
            
            # references.bibファイル作成
            references_bib = paper_dir / "references.bib"
            bib_content = """@article{test2023,
    title={Test Reference},
    author={Test, Author},
    year={2023},
    journal={Test Journal},
    doi={10.1000/test}
}
"""
            references_bib.write_text(bib_content, encoding='utf-8')
            
            # process_items実行
            with patch.object(workflow, 'bibtex_parser') as mock_parser, \
                 patch('code.py.modules.ai_citation_support.ai_citation_support_workflow.StatusManager') as mock_status_manager_class:
                
                # BibTeXParserのモック設定
                mock_parser.parse_file.return_value = {
                    'test2023': {
                        'ID': 'test2023',
                        'title': 'Test Reference',
                        'author': 'Test, Author',
                        'year': '2023',
                        'journal': 'Test Journal',
                        'doi': '10.1000/test'
                    }
                }
                
                # StatusManagerのモック設定
                mock_status_manager = mock_status_manager_class.return_value
                mock_status_manager.get_papers_needing_processing.return_value = [str(paper_path)]
                
                workflow.process_items(str(clippings_dir))
            
            # 処理結果確認
            with open(paper_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 処理状態が完了に更新されているか確認
            self.assertIn('ai_citation_support: completed', content)
            
        except ImportError:
            self.skipTest("AICitationSupportWorkflow not implemented yet")


class TestAICitationSupportWorkflowImport(unittest.TestCase):
    """AICitationSupportWorkflowインポートテスト"""
    
    def test_ai_citation_support_workflow_import(self):
        """AICitationSupportWorkflowクラスのインポートテスト"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            # クラスの存在確認
            self.assertTrue(callable(AICitationSupportWorkflow))
            
        except ImportError:
            self.skipTest("AICitationSupportWorkflow not implemented yet")
    
    def test_required_methods_exist(self):
        """必要なメソッドの存在確認"""
        try:
            from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
            
            # モックの設定
            mock_config = MagicMock()
            mock_logger = MagicMock()
            
            workflow = AICitationSupportWorkflow(mock_config, mock_logger)
            
            # 必要なメソッドの存在確認
            required_methods = [
                'process_items',
                '_find_references_bib',
                'create_citation_mapping',
                'update_yaml_with_citations'
            ]
            
            for method_name in required_methods:
                self.assertTrue(hasattr(workflow, method_name))
                self.assertTrue(callable(getattr(workflow, method_name)))
                
        except ImportError:
            self.skipTest("AICitationSupportWorkflow not implemented yet")


if __name__ == '__main__':
    unittest.main() 