"""
引用番号が1から始まることを確認するテスト
"""

import unittest
import tempfile
import os
from pathlib import Path

from modules.ai_citation_support.citation_mapping_engine import CitationMappingEngine


class TestCitationMappingOneBased(unittest.TestCase):
    """引用番号が1から始まることを確認するテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.markdown_file = os.path.join(self.temp_dir, "test.md")
        self.bib_file = os.path.join(self.temp_dir, "references.bib")
        
        # テスト用Markdownファイル作成（引用番号1,2,3を含む）
        with open(self.markdown_file, 'w', encoding='utf-8') as f:
            f.write("""# Test Paper

This is a test paper with citations [1], [2], and [3].

More text with citation [1] again.
""")
        
        # テスト用BibTeXファイル作成（3つのエントリ）
        with open(self.bib_file, 'w', encoding='utf-8') as f:
            f.write("""@article{first2023,
  title={First Paper},
  author={First, Author},
  year={2023},
  journal={Test Journal},
  volume={1},
  pages={1-10},
  doi={10.1000/first}
}

@article{second2024,
  title={Second Paper},
  author={Second, Author},
  year={2024},
  journal={Test Journal},
  volume={2},
  pages={11-20},
  doi={10.1000/second}
}

@article{third2022,
  title={Third Paper},
  author={Third, Author},
  year={2022},
  journal={Test Journal},
  volume={3},
  pages={21-30},
  doi={10.1000/third}
}
""")
    
    def tearDown(self):
        """テスト後の清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_citation_mapping_starts_from_one(self):
        """引用番号が1から始まることを確認"""
        engine = CitationMappingEngine()
        mapping = engine.create_citation_mapping(self.markdown_file, self.bib_file)
        
        # 引用番号1, 2, 3が存在することを確認
        self.assertIn(1, mapping.index_map)
        self.assertIn(2, mapping.index_map)
        self.assertIn(3, mapping.index_map)
        
        # 引用番号0が存在しないことを確認
        self.assertNotIn(0, mapping.index_map)
        
        # 総引用数が3であることを確認
        self.assertEqual(mapping.total_citations, 3)
        
        # 各引用番号が正しいBibTeXエントリにマッピングされていることを確認
        citation_1 = mapping.index_map[1]
        citation_2 = mapping.index_map[2]
        citation_3 = mapping.index_map[3]
        
        # 引用番号1はfirst2023にマッピングされるべき
        self.assertEqual(citation_1.citation_key, "first2023")
        self.assertEqual(citation_1.title, "First Paper")
        
        # 引用番号2はsecond2024にマッピングされるべき
        self.assertEqual(citation_2.citation_key, "second2024")
        self.assertEqual(citation_2.title, "Second Paper")
        
        # 引用番号3はthird2022にマッピングされるべき
        self.assertEqual(citation_3.citation_key, "third2022")
        self.assertEqual(citation_3.title, "Third Paper")
    
    def test_yaml_header_citations_start_from_one(self):
        """YAMLヘッダーでの引用セクションが1から始まることを確認"""
        engine = CitationMappingEngine()
        mapping = engine.create_citation_mapping(self.markdown_file, self.bib_file)
        
        # YAMLヘッダーを更新
        success = engine.update_yaml_header(self.markdown_file, mapping)
        self.assertTrue(success)
        
        # ファイル内容を確認
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 引用番号1, 2, 3がYAMLに含まれていることを確認
        self.assertIn("1:", content)
        self.assertIn("2:", content)
        self.assertIn("3:", content)
        
        # 引用番号0がYAMLに含まれていないことを確認
        self.assertNotIn("0:", content)
        
        # citations:セクションの後に1:が最初に来ることを確認
        import re
        citations_match = re.search(r'citations:\s*\n\s*(\d+):', content)
        if citations_match:
            first_citation_num = int(citations_match.group(1))
            self.assertEqual(first_citation_num, 1, "First citation should be numbered 1, not 0")


if __name__ == '__main__':
    unittest.main() 