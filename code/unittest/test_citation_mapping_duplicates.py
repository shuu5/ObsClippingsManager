"""
Citation Mapping重複エントリーテスト

references.bibとYAML citation mappingの不整合を検証します。
"""

import unittest
import tempfile
import sys
from pathlib import Path

# テスト対象モジュールをインポートするためのパス設定
project_root = Path(__file__).parent.parent.parent
code_py_dir = project_root / "code" / "py"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(code_py_dir))

from modules.ai_citation_support.citation_mapping_engine import CitationMappingEngine
from modules.shared.bibtex_parser import BibTeXParser


class TestCitationMappingDuplicates(unittest.TestCase):
    """Citation Mapping重複エントリーテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = CitationMappingEngine()
        self.bibtex_parser = BibTeXParser()
        
    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_duplicate_citation_keys_handling(self):
        """重複citation_keyの処理テスト"""
        # 重複エントリーを含むBibTeXコンテンツ
        bibtex_content = """
        @article{kim2006,
            title={First Paper},
            author={Kim, S},
            journal={Nature},
            year={2006},
            doi={10.1038/nature04659}
        }
        
        @article{saha2017,
            title={Second Paper},
            author={Saha, SK},
            journal={Oncogene},
            year={2017},
            doi={10.1038/onc.2016.221}
        }
        
        @article{li2016,
            title={Li2016 First Entry},
            author={Li, X},
            journal={Oncotarget},
            year={2016},
            doi={10.18632/oncotarget.7331}
        }
        
        @article{li2016,
            title={Li2016 Duplicate Entry},
            author={Li, Q},
            journal={Oncotarget},
            year={2016},
            doi={10.18632/oncotarget.15650}
        }
        
        @article{zhao2014,
            title={Fifth Paper},
            author={Zhao, X},
            journal={BMC Cancer},
            year={2014},
            doi={10.1186/1471-2407-14-211}
        }
        """
        
        markdown_content = """---
title: Test Paper
---

# Test Paper

This paper references [1], [2], [3], [4], and [5].
"""
        
        # テストファイルを作成
        bib_file = Path(self.temp_dir) / "references.bib"
        md_file = Path(self.temp_dir) / "test.md"
        
        with open(bib_file, 'w', encoding='utf-8') as f:
            f.write(bibtex_content)
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 新しい重複を含むBibTeXパーサーでエントリー数を確認
        bib_entries = self.bibtex_parser.parse_file_with_duplicates(str(bib_file))
        print(f"BibTeX parser found {len(bib_entries)} entries (with duplicates)")
        
        # 重複を含む全エントリーが保持されることを確認
        self.assertEqual(len(bib_entries), 5)  # 重複を含む5エントリー
        
        # Citation mappingを作成
        mapping = self.engine.create_citation_mapping(str(md_file), str(bib_file))
        
        # 重要：total_citationsはBibTeXの実際のエントリー数と一致すべき（重複を含む）
        self.assertEqual(mapping.total_citations, 5)  # 重複を含む5エントリー
        
        # 引用番号1-5のすべてが存在し、プレースホルダーが存在しないことを確認
        self.assertEqual(len(mapping.index_map), 5)
        for i in range(1, 6):
            self.assertIn(i, mapping.index_map)
            citation_info = mapping.index_map[i]
            self.assertNotEqual(citation_info.citation_key, f"placeholder_{i}")
            self.assertNotIn("[Citation", citation_info.title)
        
        # 重複キーが順序通りにマッピングされていることを確認
        # 1: kim2006, 2: saha2017, 3: li2016 (first), 4: li2016 (second), 5: zhao2014
        self.assertEqual(mapping.index_map[1].citation_key, "kim2006")
        self.assertEqual(mapping.index_map[2].citation_key, "saha2017")
        self.assertEqual(mapping.index_map[3].citation_key, "li2016")
        self.assertEqual(mapping.index_map[4].citation_key, "li2016")  # 重複
        self.assertEqual(mapping.index_map[5].citation_key, "zhao2014")
        
        # 重複した li2016 の内容が異なることを確認
        self.assertEqual(mapping.index_map[3].authors, "Li, X")
        self.assertEqual(mapping.index_map[4].authors, "Li, Q")
        self.assertNotEqual(mapping.index_map[3].title, mapping.index_map[4].title)
    
    def test_real_yinL2022_references_processing(self):
        """実際のyinL2022BreastCancerResのreferences.bib処理テスト"""
        real_bib_file = Path(project_root) / "TestManuscripts" / "Clippings" / "yinL2022BreastCancerRes" / "references.bib"
        real_md_file = Path(project_root) / "TestManuscripts" / "Clippings" / "yinL2022BreastCancerRes" / "yinL2022BreastCancerRes.md"
        
        if not real_bib_file.exists():
            self.skipTest(f"Real BibTeX file not found: {real_bib_file}")
        
        # 実際のファイルでBibTeXエントリー数を確認（重複を含む）
        bib_entries_with_duplicates = self.bibtex_parser.parse_file_with_duplicates(str(real_bib_file))
        bib_entries_unique = self.bibtex_parser.parse_file(str(real_bib_file))
        print(f"Real BibTeX file has {len(bib_entries_with_duplicates)} entries (with duplicates)")
        print(f"Real BibTeX file has {len(bib_entries_unique)} unique entries")
        
        # Citation mappingを作成
        mapping = self.engine.create_citation_mapping(str(real_md_file), str(real_bib_file))
        
        # total_citationsは重複を含むBibTeXエントリー数と一致すべき
        self.assertEqual(mapping.total_citations, len(bib_entries_with_duplicates))
        
        # プレースホルダーが存在しないことを確認
        for citation_num, citation_info in mapping.index_map.items():
            self.assertFalse(citation_info.citation_key.startswith("placeholder_"))
            self.assertNotIn("[Citation", citation_info.title)
        
        print(f"Citation mapping created with {mapping.total_citations} citations")
        print(f"Should match BibTeX entries (with duplicates): {len(bib_entries_with_duplicates)}")


if __name__ == '__main__':
    unittest.main() 