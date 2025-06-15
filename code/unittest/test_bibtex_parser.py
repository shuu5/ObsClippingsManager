"""
BibTeXParserクラスのユニットテスト

このテストファイルは、BibTeXファイルの解析機能を包括的にテストします。
TDDアプローチに従って、実装前にテストを作成します。
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# テスト対象クラスのインポート（実装後に有効化）
try:
    from code.py.modules.shared_modules.bibtex_parser import BibTeXParser
    BIBTEX_PARSER_AVAILABLE = True
except ImportError:
    BIBTEX_PARSER_AVAILABLE = False

from code.py.modules.shared_modules.exceptions import BibTeXError


class TestBibTeXParserImport(unittest.TestCase):
    """BibTeXParserクラスのインポートテスト"""
    
    def test_bibtex_parser_import(self):
        """BibTeXParserクラスのインポートテスト"""
        if not BIBTEX_PARSER_AVAILABLE:
            self.skipTest("BibTeXParser not yet implemented")
        
        from code.py.modules.shared_modules.bibtex_parser import BibTeXParser
        self.assertTrue(hasattr(BibTeXParser, '__init__'))
        self.assertTrue(hasattr(BibTeXParser, 'parse_file'))
        self.assertTrue(hasattr(BibTeXParser, 'parse_string'))
        self.assertTrue(hasattr(BibTeXParser, 'extract_citation_keys'))
        self.assertTrue(hasattr(BibTeXParser, 'validate_bibtex'))


@unittest.skipUnless(BIBTEX_PARSER_AVAILABLE, "BibTeXParser not yet implemented")
class TestBibTeXParserBasic(unittest.TestCase):
    """BibTeXParserクラスの基本機能テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_logger = Mock()
        self.parser = BibTeXParser(self.mock_logger)
        
        # サンプルBibTeXデータ
        self.sample_bibtex = """
@article{smith2023,
    title={Sample Article},
    author={Smith, John and Doe, Jane},
    journal={Journal of Examples},
    year={2023},
    volume={1},
    pages={1-10},
    doi={10.1000/example.2023.001}
}

@book{johnson2022,
    title={Example Book},
    author={Johnson, Bob},
    publisher={Example Press},
    year={2022},
    isbn={978-0-123456-78-9}
}

@inproceedings{brown2021,
    title={Conference Paper Example},
    author={Brown, Alice},
    booktitle={Proceedings of Example Conference},
    year={2021},
    pages={100-105}
}
"""
        
        # 不正なBibTeXデータ（構文エラー）
        self.invalid_bibtex = """
@article{invalid_entry,
    title="Missing comma after entry type",
    author={Invalid Author}
    year={2023}
@book{incomplete_entry
    title={This entry is completely malformed
"""
    
    def test_bibtex_parser_initialization(self):
        """BibTeXParserクラスの初期化テスト"""
        self.assertIsNotNone(self.parser)
        self.assertEqual(self.parser.logger, self.mock_logger)
    
    def test_parse_string_valid_bibtex(self):
        """有効なBibTeX文字列の解析テスト"""
        result = self.parser.parse_string(self.sample_bibtex)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)
        
        # 各エントリーの存在確認
        self.assertIn('smith2023', result)
        self.assertIn('johnson2022', result)
        self.assertIn('brown2021', result)
        
        # エントリーの詳細確認
        smith_entry = result['smith2023']
        self.assertEqual(smith_entry['title'], 'Sample Article')
        self.assertEqual(smith_entry['author'], 'Smith, John and Doe, Jane')
        self.assertEqual(smith_entry['year'], '2023')
    
    def test_parse_string_invalid_bibtex(self):
        """無効なBibTeX文字列の解析テスト"""
        with self.assertRaises(BibTeXError):
            self.parser.parse_string(self.invalid_bibtex)
    
    def test_parse_string_empty_input(self):
        """空の入力文字列の解析テスト"""
        result = self.parser.parse_string("")
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)
    
    def test_extract_citation_keys_valid_bibtex(self):
        """有効なBibTeXからcitation_key抽出テスト"""
        keys = self.parser.extract_citation_keys(self.sample_bibtex)
        
        self.assertIsInstance(keys, list)
        self.assertEqual(len(keys), 3)
        self.assertIn('smith2023', keys)
        self.assertIn('johnson2022', keys)
        self.assertIn('brown2021', keys)
    
    def test_extract_citation_keys_empty_input(self):
        """空の入力からのcitation_key抽出テスト"""
        keys = self.parser.extract_citation_keys("")
        self.assertIsInstance(keys, list)
        self.assertEqual(len(keys), 0)
    
    def test_validate_bibtex_valid_content(self):
        """有効なBibTeXコンテンツの検証テスト"""
        is_valid, errors = self.parser.validate_bibtex(self.sample_bibtex)
        
        self.assertTrue(is_valid)
        self.assertIsInstance(errors, list)
        self.assertEqual(len(errors), 0)
    
    def test_validate_bibtex_invalid_content(self):
        """無効なBibTeXコンテンツの検証テスト"""
        is_valid, errors = self.parser.validate_bibtex(self.invalid_bibtex)
        
        self.assertFalse(is_valid)
        self.assertIsInstance(errors, list)
        self.assertGreater(len(errors), 0)


@unittest.skipUnless(BIBTEX_PARSER_AVAILABLE, "BibTeXParser not yet implemented")
class TestBibTeXParserFileOperations(unittest.TestCase):
    """BibTeXParserクラスのファイル操作テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_logger = Mock()
        self.parser = BibTeXParser(self.mock_logger)
        
        self.sample_bibtex = """
@article{test2023,
    title={Test Article},
    author={Test Author},
    journal={Test Journal},
    year={2023}
}
"""
    
    def test_parse_file_valid_file(self):
        """有効なBibTeXファイルの解析テスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            f.write(self.sample_bibtex)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            
            self.assertIsInstance(result, dict)
            self.assertEqual(len(result), 1)
            self.assertIn('test2023', result)
            
            entry = result['test2023']
            self.assertEqual(entry['title'], 'Test Article')
            self.assertEqual(entry['author'], 'Test Author')
        finally:
            os.unlink(temp_file)
    
    def test_parse_file_nonexistent_file(self):
        """存在しないファイルの解析エラーテスト"""
        with self.assertRaises(BibTeXError):
            self.parser.parse_file('/nonexistent/file.bib')
    
    def test_parse_file_empty_file(self):
        """空のファイルの解析テスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            self.assertIsInstance(result, dict)
            self.assertEqual(len(result), 0)
        finally:
            os.unlink(temp_file)
    
    def test_parse_file_permission_error(self):
        """ファイル読み込み権限エラーテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            f.write(self.sample_bibtex)
            temp_file = f.name
        
        try:
            # ファイル権限を削除
            os.chmod(temp_file, 0o000)
            
            with self.assertRaises(BibTeXError):
                self.parser.parse_file(temp_file)
        finally:
            # 権限を復元してファイルを削除
            os.chmod(temp_file, 0o644)
            os.unlink(temp_file)


@unittest.skipUnless(BIBTEX_PARSER_AVAILABLE, "BibTeXParser not yet implemented")
class TestBibTeXParserAdvanced(unittest.TestCase):
    """BibTeXParserクラスの高度な機能テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_logger = Mock()
        self.parser = BibTeXParser(self.mock_logger)
        
        # Unicode文字を含むBibTeXデータ
        self.unicode_bibtex = """
@article{unicode2023,
    title={Tëst Artícle with Spëcial Charactërs},
    author={Müller, Hans and Žáček, Pavel},
    journal={Internationál Jöurnal},
    year={2023}
}
"""
        
        # 複雑なBibTeXデータ
        self.complex_bibtex = """
@article{complex2023,
    title={A Very Long Title That Spans Multiple Lines and Contains Various {Special} Characters},
    author={First Author and Second Author and Third Author and Fourth Author},
    journal={Journal with a Very Long Name That Also Spans Multiple Lines},
    year={2023},
    volume={42},
    number={7},
    pages={123--456},
    doi={10.1000/very.long.doi.string.2023.001},
    url={https://example.com/very/long/url/path/to/article},
    keywords={keyword1, keyword2, keyword3, keyword4},
    abstract={This is a very long abstract that contains multiple sentences and various punctuation marks. It also includes some special characters and symbols.}
}
"""
    
    def test_parse_unicode_content(self):
        """Unicode文字を含むBibTeXの解析テスト"""
        result = self.parser.parse_string(self.unicode_bibtex)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 1)
        self.assertIn('unicode2023', result)
        
        entry = result['unicode2023']
        self.assertIn('Tëst Artícle', entry['title'])
        self.assertIn('Müller', entry['author'])
    
    def test_parse_complex_entry(self):
        """複雑なBibTeXエントリーの解析テスト"""
        result = self.parser.parse_string(self.complex_bibtex)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 1)
        self.assertIn('complex2023', result)
        
        entry = result['complex2023']
        self.assertIn('Special', entry['title'])
        self.assertEqual(entry['volume'], '42')
        self.assertEqual(entry['number'], 7)  # numberフィールドは整数として期待
        self.assertIn('10.1000', entry['doi'])
    
    def test_extract_citation_keys_mixed_case(self):
        """大文字小文字混合のcitation_key抽出テスト"""
        mixed_case_bibtex = """
@Article{MixedCase2023,
    title={Mixed Case Test},
    author={Test Author}
}

@BOOK{UPPERCASE2023,
    title={Uppercase Test},
    author={Test Author}
}

@inproceedings{lowercase2023,
    title={Lowercase Test},
    author={Test Author}
}
"""
        
        keys = self.parser.extract_citation_keys(mixed_case_bibtex)
        
        self.assertIn('MixedCase2023', keys)
        self.assertIn('UPPERCASE2023', keys)
        self.assertIn('lowercase2023', keys)
    
    def test_validate_bibtex_missing_required_fields(self):
        """必須フィールド不足のBibTeX検証テスト"""
        incomplete_bibtex = """
@article{incomplete2023,
    title={Incomplete Article}
}
"""
        
        is_valid, errors = self.parser.validate_bibtex(incomplete_bibtex)
        
        # 厳密な検証では必須フィールド不足はエラーとする
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_logging_integration(self):
        """ログ統合機能テスト"""
        # 正常な解析時のログ
        self.parser.parse_string(self.unicode_bibtex)
        
        # ログメソッドが呼ばれたことを確認
        self.mock_logger.debug.assert_called()
        
        # エラー時のログ - より確実にエラーを起こす文字列を使用
        invalid_bibtex = "@article{test, title={unclosed brace"
        try:
            self.parser.parse_string(invalid_bibtex)
        except BibTeXError:
            pass
        
        # errorまたはwarningログが呼ばれたことを確認（どちらか）
        self.assertTrue(
            self.mock_logger.error.called or self.mock_logger.warning.called,
            "Expected error or warning log to be called for invalid BibTeX"
        )


@unittest.skipUnless(BIBTEX_PARSER_AVAILABLE, "BibTeXParser not yet implemented")
class TestBibTeXParserIntegration(unittest.TestCase):
    """BibTeXParserクラスの統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_logger = Mock()
        self.parser = BibTeXParser(self.mock_logger)
        
        # 実際の論文データベースを模擬した大規模データ
        self.large_bibtex = self._generate_large_bibtex_data()
    
    def _generate_large_bibtex_data(self):
        """大規模BibTeXデータの生成"""
        entries = []
        entry_types = ['article', 'book', 'inproceedings', 'incollection', 'phdthesis']
        
        for i in range(100):
            entry_type = entry_types[i % len(entry_types)]
            
            # エントリータイプに応じて必須フィールドを設定
            if entry_type == 'article':
                specific_fields = "journal={Test Journal},"
            elif entry_type == 'book':
                specific_fields = "publisher={Test Publisher},"
            elif entry_type == 'inproceedings':
                specific_fields = "booktitle={Test Conference},"
            elif entry_type == 'incollection':
                specific_fields = "booktitle={Test Collection},"
            elif entry_type == 'phdthesis':
                specific_fields = "school={Test University},"
            else:
                specific_fields = ""
            
            entry = f"""
@{entry_type}{{test{i:03d},
    title={{Test Entry {i}}},
    author={{Author {i} and Co-Author {i}}},
    year={2020 + (i % 4)},
    {specific_fields}
}}"""
            entries.append(entry)
        
        return '\n'.join(entries)
    
    def test_parse_large_bibtex_file(self):
        """大規模BibTeXファイルの解析パフォーマンステスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            f.write(self.large_bibtex)
            temp_file = f.name
        
        try:
            import time
            start_time = time.time()
            
            result = self.parser.parse_file(temp_file)
            
            end_time = time.time()
            parse_time = end_time - start_time
            
            # パフォーマンス検証
            self.assertLess(parse_time, 5.0)  # 5秒以内
            self.assertEqual(len(result), 100)
            
            # いくつかのエントリーをサンプル確認
            self.assertIn('test000', result)
            self.assertIn('test050', result)
            self.assertIn('test099', result)
            
        finally:
            os.unlink(temp_file)
    
    def test_extract_all_citation_keys_large_data(self):
        """大規模データからの全citation_key抽出テスト"""
        keys = self.parser.extract_citation_keys(self.large_bibtex)
        
        self.assertEqual(len(keys), 100)
        self.assertIn('test000', keys)
        self.assertIn('test099', keys)
        
        # ソート確認
        sorted_keys = sorted(keys)
        self.assertEqual(keys, sorted_keys)
    
    def test_workflow_integration_simulation(self):
        """ワークフロー統合シミュレーションテスト"""
        # 1. ファイル解析
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            f.write(self.large_bibtex)
            temp_file = f.name
        
        try:
            # 2. 解析実行
            entries = self.parser.parse_file(temp_file)
            
            # 3. citation_key抽出
            keys = list(entries.keys())
            
            # 4. 検証
            is_valid, errors = self.parser.validate_bibtex(self.large_bibtex)
            
            # 5. 結果確認
            self.assertEqual(len(entries), 100)
            self.assertEqual(len(keys), 100)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)
            
        finally:
            os.unlink(temp_file)


@unittest.skipUnless(BIBTEX_PARSER_AVAILABLE, "BibTeXParser not yet implemented")
class TestBibTeXParserOrdered(unittest.TestCase):
    """BibTeXParserクラスの順序・重複保持機能テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_logger = Mock()
        self.parser = BibTeXParser(self.mock_logger)
        
        # 重複を含むBibTeXデータ
        self.duplicate_bibtex = """
@article{adikrisna2012,
    title={Identification of pancreatic cancer stem cells and selective toxicity of chemotherapeutic agents},
    author={Adikrisna},
    journal={Gastroenterology},
    year={2012},
    doi={10.1053/j.gastro.2012.03.054}
}

@article{smith2023,
    title={Novel Method for Cancer Cell Analysis},
    author={Smith, John},
    journal={Cancer Research},
    year={2023},
    doi={10.1158/0008-5472.CAN-23-0123}
}

@article{adikrisna2012,
    title={Identification of pancreatic cancer stem cells and selective toxicity of chemotherapeutic agents},
    author={Adikrisna},
    journal={Gastroenterology},
    year={2012},
    doi={10.1053/j.gastro.2012.03.054}
}
"""
    
    def test_parse_string_ordered_with_duplicates(self):
        """重複を含むBibTeX文字列の順序保持解析テスト"""
        result = self.parser.parse_string_ordered(self.duplicate_bibtex)
        
        # 重複を含めて3つのエントリがあることを確認
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        
        # 順序の確認
        self.assertEqual(result[0]['number'], 1)
        self.assertEqual(result[0]['citation_key'], 'adikrisna2012')
        
        self.assertEqual(result[1]['number'], 2)
        self.assertEqual(result[1]['citation_key'], 'smith2023')
        
        self.assertEqual(result[2]['number'], 3)
        self.assertEqual(result[2]['citation_key'], 'adikrisna2012')
        
        # numberプロパティの確認
        for i, entry in enumerate(result, 1):
            self.assertEqual(entry['number'], i)
            self.assertIn('citation_key', entry)
            self.assertIn('title', entry)
            self.assertIn('author', entry)
    
    def test_parse_file_ordered_with_duplicates(self):
        """重複を含むBibTeXファイルの順序保持解析テスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            f.write(self.duplicate_bibtex)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file_ordered(temp_file)
            
            # 重複を含めて3つのエントリがあることを確認
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)
            
            # 重複した引用文献のタイトルが同じことを確認
            self.assertEqual(result[0]['title'], result[2]['title'])
            self.assertEqual(result[0]['citation_key'], result[2]['citation_key'])
            
            # しかし番号は異なることを確認
            self.assertEqual(result[0]['number'], 1)
            self.assertEqual(result[2]['number'], 3)
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_string_ordered_empty_input(self):
        """空の入力文字列の順序保持解析テスト"""
        result = self.parser.parse_string_ordered("")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    def test_compare_ordered_vs_regular_parsing(self):
        """順序保持解析と通常解析の比較テスト"""
        # 通常解析（重複除去される）
        regular_result = self.parser.parse_string(self.duplicate_bibtex)
        
        # 順序保持解析（重複保持される）
        ordered_result = self.parser.parse_string_ordered(self.duplicate_bibtex)
        
        # 通常解析では重複が除去されて2つのエントリ
        self.assertEqual(len(regular_result), 2)
        
        # 順序保持解析では重複が保持されて3つのエントリ
        self.assertEqual(len(ordered_result), 3)
        
        # 通常解析の結果確認
        self.assertIn('adikrisna2012', regular_result)
        self.assertIn('smith2023', regular_result)
        
        # 順序保持解析の結果確認
        citation_keys = [entry['citation_key'] for entry in ordered_result]
        self.assertEqual(citation_keys, ['adikrisna2012', 'smith2023', 'adikrisna2012'])
    
    def test_ordered_parsing_number_property(self):
        """順序保持解析のnumberプロパティテスト"""
        result = self.parser.parse_string_ordered(self.duplicate_bibtex)
        
        # 各エントリにnumberプロパティがあることを確認
        for i, entry in enumerate(result, 1):
            self.assertIn('number', entry)
            self.assertEqual(entry['number'], i)
            self.assertIsInstance(entry['number'], int)
        
        # numberプロパティが連続していることを確認
        numbers = [entry['number'] for entry in result]
        self.assertEqual(numbers, [1, 2, 3])


if __name__ == '__main__':
    unittest.main() 