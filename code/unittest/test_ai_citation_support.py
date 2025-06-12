"""
AI理解支援引用文献統合機能 v4.0 テスト

新機能の包括的なテストを提供します。
"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# テスト対象モジュールのインポート
from modules.ai_citation_support.data_structures import (
    CitationMapping, CitationInfo, MappingStatistics, AIGenerationResult
)
from modules.ai_citation_support.citation_mapping_engine import CitationMappingEngine
from modules.ai_citation_support.citation_resolver import CitationResolver
from modules.ai_citation_support.ai_mapping_workflow import AIMappingWorkflow


class TestDataStructures(unittest.TestCase):
    """データ構造のテスト"""
    
    def test_citation_mapping_creation(self):
        """CitationMapping作成のテスト"""
        mapping = CitationMapping(
            references_file="/test/references.bib",
            index_map={1: "smith2023", 2: "doe2024"},
            last_updated=datetime.now(),
            mapping_version="1.0",
            total_citations=2
        )
        
        self.assertEqual(mapping.total_citations, 2)
        self.assertEqual(mapping.index_map[1], "smith2023")
        self.assertEqual(mapping.mapping_version, "1.0")
    
    def test_citation_mapping_yaml_conversion(self):
        """CitationMappingのYAML変換テスト"""
        citation1 = CitationInfo(citation_key="smith2023", title="Test 1", year=2023)
        citation2 = CitationInfo(citation_key="doe2024", title="Test 2", year=2024)
        
        mapping = CitationMapping(
            references_file="/test/references.bib",
            index_map={1: citation1, 2: citation2},
            last_updated=datetime(2024, 1, 1, 12, 0, 0),
            mapping_version="1.0",
            total_citations=2
        )
        
        # to_yaml_dictメソッドは削除されたため、直接属性をテスト
        self.assertEqual(mapping.references_file, "/test/references.bib")
        self.assertEqual(mapping.total_citations, 2)
        self.assertIn(1, mapping.index_map)
        self.assertIn(2, mapping.index_map)
        
        # CitationInfoオブジェクトの確認
        self.assertEqual(mapping.index_map[1].citation_key, "smith2023")
        self.assertEqual(mapping.index_map[2].citation_key, "doe2024")
    
    def test_citation_info_reference_line(self):
        """CitationInfoのReference Line生成テスト"""
        citation = CitationInfo(
            citation_key="smith2023",
            title="Test Paper",
            authors="Smith, J. & Doe, A.",
            year=2023,
            journal="Test Journal",
            volume="10",
            pages="1-10",
            doi="10.1000/test"
        )
        
        reference_line = citation.to_reference_line()
        self.assertIn("Smith, J. & Doe, A.", reference_line)
        self.assertIn("(2023)", reference_line)
        self.assertIn("Test Paper", reference_line)
        self.assertIn("DOI: 10.1000/test", reference_line)
    
    # test_ai_readable_document_markdown は削除されました
    # 仕様書に従い、AIReadableDocumentクラスは削除されました


class TestCitationMappingEngine(unittest.TestCase):
    """CitationMappingEngineのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.markdown_file = os.path.join(self.temp_dir, "test.md")
        self.bib_file = os.path.join(self.temp_dir, "references.bib")
        
        # テスト用Markdownファイル作成
        with open(self.markdown_file, 'w', encoding='utf-8') as f:
            f.write("""# Test Paper

This research [1] demonstrates that cancer cells [2],[3] are important.
Recent studies \\[[4]\\] also show similar results.
""")
        
        # テスト用BibTeXファイル作成
        with open(self.bib_file, 'w', encoding='utf-8') as f:
            f.write("""@article{smith2023,
  title={First Paper},
  author={Smith, John},
  year={2023}
}

@article{doe2024,
  title={Second Paper},
  author={Doe, Jane},
  year={2024}
}

@article{brown2022,
  title={Third Paper},
  author={Brown, Bob},
  year={2022}
}

@article{wilson2021,
  title={Fourth Paper},
  author={Wilson, Will},
  year={2021}
}
""")
    
    def tearDown(self):
        """テスト後の清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_citation_mapping_creation(self):
        """引用マッピング作成のテスト"""
        engine = CitationMappingEngine()
        mapping = engine.create_citation_mapping(self.markdown_file, self.bib_file)
        
        self.assertEqual(mapping.total_citations, 4)
        self.assertIn(1, mapping.index_map)
        self.assertIn(2, mapping.index_map)
        self.assertIn(3, mapping.index_map)
        self.assertIn(4, mapping.index_map)
        
        # citation_keyの順序確認
        self.assertEqual(mapping.index_map[1].citation_key, "smith2023")
        self.assertEqual(mapping.index_map[2].citation_key, "doe2024")
        self.assertEqual(mapping.index_map[3].citation_key, "brown2022")
        self.assertEqual(mapping.index_map[4].citation_key, "wilson2021")
    
    def test_yaml_header_update(self):
        """YAMLヘッダー更新のテスト"""
        engine = CitationMappingEngine()
        mapping = engine.create_citation_mapping(self.markdown_file, self.bib_file)
        success = engine.update_yaml_header(self.markdown_file, mapping)
        
        self.assertTrue(success)
        
        # 更新されたファイルの内容を確認
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn("citations:", content)
        self.assertIn("1:", content)
        self.assertIn("citation_metadata:", content)


class TestCitationResolver(unittest.TestCase):
    """CitationResolverのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.markdown_file = os.path.join(self.temp_dir, "test.md")
        self.bib_file = os.path.join(self.temp_dir, "references.bib")
        
        # YAMLヘッダー付きMarkdownファイル作成
        with open(self.markdown_file, 'w', encoding='utf-8') as f:
            f.write("""---
citations:
  1:
    citation_key: smith2023
    title: Novel Method for Cancer Analysis
    authors: Smith, John and Brown, Alice
    year: 2023
    journal: Nature Medicine
    volume: 29
    pages: 123-130
    doi: 10.1038/test.2023
  2:
    citation_key: doe2024
    title: Advanced Treatment Approaches
    authors: Doe, Jane
    year: 2024
    journal: Cell
    volume: 187
    pages: 45-60
    doi: 10.1016/test.2024
citation_metadata:
  last_updated: '2024-01-01T12:00:00'
  mapping_version: '2.0'
  source_bibtex: {}
  total_citations: 2
---

# Test Paper

This research [1] demonstrates that cancer cells [2] are important.
""".format(os.path.basename(self.bib_file)))
        
        # BibTeXファイル作成
        with open(self.bib_file, 'w', encoding='utf-8') as f:
            f.write("""@article{smith2023,
  title={Novel Method for Cancer Analysis},
  author={Smith, John and Brown, Alice},
  year={2023},
  journal={Nature Medicine},
  volume={29},
  pages={123-130},
  doi={10.1038/test.2023}
}

@article{doe2024,
  title={Advanced Treatment Approaches},
  author={Doe, Jane},
  year={2024},
  journal={Cell},
  volume={187},
  pages={45-60},
  doi={10.1016/test.2024}
}
""")
    
    def tearDown(self):
        """テスト後の清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_citation_resolution(self):
        """引用解決のテスト"""
        resolver = CitationResolver()
        citation_info = resolver.resolve_citation(1, self.markdown_file)
        
        self.assertIsNotNone(citation_info)
        self.assertEqual(citation_info.citation_key, "smith2023")
        self.assertEqual(citation_info.title, "Novel Method for Cancer Analysis")
        self.assertEqual(citation_info.year, 2023)
        self.assertIn("Smith", citation_info.authors)
        self.assertEqual(citation_info.doi, "10.1038/test.2023")
    
    def test_batch_citation_resolution(self):
        """バッチ引用解決のテスト"""
        resolver = CitationResolver()
        results = resolver.batch_resolve_citations([1, 2], self.markdown_file)
        
        self.assertEqual(len(results), 2)
        self.assertIn(1, results)
        self.assertIn(2, results)
        
        # 1番目の引用
        citation1 = results[1]
        self.assertEqual(citation1.citation_key, "smith2023")
        self.assertEqual(citation1.year, 2023)
        
        # 2番目の引用
        citation2 = results[2]
        self.assertEqual(citation2.citation_key, "doe2024")
        self.assertEqual(citation2.year, 2024)
    
    def test_context_extraction(self):
        """文脈抽出のテスト"""
        resolver = CitationResolver()
        context = resolver.extract_citation_context(self.markdown_file, 1)
        
        self.assertIn("research", context.lower())
        self.assertIn("[1]", context)


# AI用ファイル生成機能のテストは削除されました
# 仕様書に従い、YAMLヘッダー統合機能のみを実装します


class TestAIMappingWorkflow(unittest.TestCase):
    """AIMappingWorkflowのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.markdown_file = os.path.join(self.temp_dir, "test.md")
        self.bib_file = os.path.join(self.temp_dir, "references.bib")
        
        # Markdownファイル作成
        with open(self.markdown_file, 'w', encoding='utf-8') as f:
            f.write("""# Test Paper

This research [1] demonstrates that cancer cells [2] are important.
""")
        
        # BibTeXファイル作成
        with open(self.bib_file, 'w', encoding='utf-8') as f:
            f.write("""@article{smith2023,
  title={Novel Method for Cancer Analysis},
  author={Smith, John},
  year={2023}
}

@article{doe2024,
  title={Advanced Treatment Approaches},
  author={Doe, Jane},
  year={2024}
}
""")
    
    def tearDown(self):
        """テスト後の清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_ai_mapping_workflow_execution(self):
        """AI理解支援ワークフロー実行のテスト（YAMLヘッダー統合のみ）"""
        workflow = AIMappingWorkflow()
        # 仕様書に従い、AI用ファイル生成は行わない
        result = workflow.execute_ai_mapping(
            self.markdown_file, 
            self.bib_file,
            generate_ai_file=False
        )
        
        self.assertTrue(result.success)
        # AI用ファイルは生成されない
        self.assertEqual(result.output_file, "")
        self.assertIsNotNone(result.statistics)
        self.assertEqual(result.statistics.total_citations_mapped, 2)
        
        # YAMLヘッダーが正しく更新されたかを確認
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # YAMLヘッダーに引用マッピングが追加されていることを確認
        self.assertIn("citations:", content)
    
    def test_mapping_only_workflow(self):
        """マッピングのみワークフローのテスト"""
        workflow = AIMappingWorkflow()
        result = workflow.execute_ai_mapping(
            self.markdown_file, 
            self.bib_file,
            generate_ai_file=False
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.output_file, "")  # AI用ファイルは生成されない
        self.assertIsNotNone(result.statistics)
    
    def test_dry_run_execution(self):
        """ドライラン実行のテスト"""
        workflow = AIMappingWorkflow()
        dry_run_report = workflow.dry_run_ai_mapping(self.markdown_file, self.bib_file)
        
        self.assertIn("Dry Run Analysis", dry_run_report)
        self.assertIn("Citations Found: 2", dry_run_report)
        self.assertIn("smith2023", dry_run_report)
        self.assertIn("doe2024", dry_run_report)
    
    def test_batch_execution(self):
        """バッチ実行のテスト"""
        # 2つ目のファイルペア作成
        markdown_file2 = os.path.join(self.temp_dir, "test2.md")
        with open(markdown_file2, 'w', encoding='utf-8') as f:
            f.write("# Test Paper 2\n\nThis shows [1] results.")
        
        workflow = AIMappingWorkflow()
        file_pairs = [
            (self.markdown_file, self.bib_file),
            (markdown_file2, self.bib_file)
        ]
        
        # 仕様書に従い、AI用ファイル生成は行わない
        results = workflow.batch_execute_ai_mapping(file_pairs, generate_ai_files=False)
        
        self.assertEqual(len(results), 2)
        self.assertIn(self.markdown_file, results)
        self.assertIn(markdown_file2, results)
        
        # 両方とも成功していることを確認
        self.assertTrue(results[self.markdown_file].success)
        self.assertTrue(results[markdown_file2].success)
        
        # AI用ファイルは生成されない
        self.assertEqual(results[self.markdown_file].output_file, "")
        self.assertEqual(results[markdown_file2].output_file, "")
    
    def test_workflow_statistics(self):
        """ワークフロー統計のテスト"""
        workflow = AIMappingWorkflow()
        
        # 初期統計確認
        initial_stats = workflow.get_workflow_statistics()
        self.assertEqual(initial_stats['total_files_processed'], 0)
        
        # ワークフロー実行（仕様書に従いAI用ファイル生成は行わない）
        result = workflow.execute_ai_mapping(
            self.markdown_file, 
            self.bib_file,
            generate_ai_file=False
        )
        self.assertTrue(result.success)
        
        # 更新された統計確認
        updated_stats = workflow.get_workflow_statistics()
        self.assertEqual(updated_stats['total_files_processed'], 1)
        self.assertEqual(updated_stats['successful_mappings'], 1)
        # AI用ファイル生成は行わないため、successful_generationsは0
        self.assertEqual(updated_stats['successful_generations'], 0)
        self.assertEqual(updated_stats['mapping_success_rate'], 1.0)


if __name__ == '__main__':
    unittest.main() 