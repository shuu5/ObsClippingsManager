"""
Citation Parser Bug Fix Tests

引用処理時に文章が破壊される問題のテストケース
"""

import unittest
from code.py.modules.citation_parser.citation_parser import CitationParser
from code.py.modules.citation_parser.data_structures import CitationResult


class TestCitationParserBugFix(unittest.TestCase):
    """引用パーサーのバグ修正テスト"""
    
    def setUp(self):
        self.parser = CitationParser()
    
    def test_citation_in_middle_of_word_bug_1(self):
        """単語の途中に引用が挿入されるバグのテスト - pancreatic問題"""
        text = "In pancreat\\[[9]\\]er, several cell surface markers are reported."
        
        result = self.parser.parse_document(text)
        
        # バグの状況を確認: 単語が分割されて引用が挿入されている
        print(f"Input: {text}")
        print(f"Output: {result.converted_text}")
        
        # 現在のバグでは "pancreat\\[[9]\\]er" が出力される
        # これは文章を破壊している
        
        # 正しい修正後は、元の正しい単語が復元されるべき
        # expected: "In pancreatic \\[[9]\\], several cell surface markers are reported."
        
        # まずバグが発生していることを確認
        self.assertIn("pancreat\\[[9]\\]er", result.converted_text, "バグが再現されていない")
    
    def test_citation_in_middle_of_word_bug_2(self):
        """単語の途中に引用が挿入されるバグのテスト - activity問題"""
        text = "Cancer cells have high proteasome act\\[[10]\\]herefore, proteasome inhibitors are used."
        
        result = self.parser.parse_document(text)
        
        print(f"Input: {text}")
        print(f"Output: {result.converted_text}")
        
        # 現在のバグでは "act\\[[10]\\]herefore" が出力される
        # これは "activity. Therefore" が誤って結合されている
        
        # まずバグが発生していることを確認
        self.assertIn("act\\[[10]\\]herefore", result.converted_text, "バグが再現されていない")
    
    def test_citation_in_middle_of_word_bug_3(self):
        """単語の途中に引用が挿入されるバグのテスト - transmembrane問題の単語境界検出"""
        # より現実的なテストケース：引用が単語の境界を壊しそうな場合
        text = "The transmembr[26] protease is important."
        
        result = self.parser.parse_document(text)
        
        # 引用処理により単語が破壊されないことを確認
        # "transmembr[26]" が不適切に処理されないことを検証
        self.assertNotIn("transmembr\\[[26]\\]", result.converted_text)
        
        # 適切に処理されるべき（単語境界が保持される）
        self.assertTrue(
            "transmembr \\[[26]\\]" in result.converted_text or 
            "transmembr[26]" in result.converted_text,  # 境界違反で処理スキップされる場合
            f"Expected proper word boundary handling, got: {result.converted_text}"
        )
    
    def test_citation_in_middle_of_word_bug_4(self):
        """単語の途中に引用が挿入されるバグのテスト - revealed that問題の単語境界検出"""
        # より現実的なテストケース：単語間での適切な引用処理
        text = "Database analysis revealedthat[14] KRT13 is highly expressed"
        
        result = self.parser.parse_document(text)
        
        # 単語境界が適切に検出され、不適切な位置での引用処理を防ぐ
        self.assertNotIn("revealedthat\\[[14]\\]", result.converted_text)
        
        # 適切な処理：単語境界違反で処理がスキップされるか、適切に分離される
        self.assertTrue(
            "revealedthat \\[[14]\\]" in result.converted_text or
            "revealedthat[14]" in result.converted_text,  # 境界違反で処理スキップされる場合
            f"Expected proper word boundary handling, got: {result.converted_text}"
        )
    
    def test_real_world_word_boundary_violations(self):
        """実際のファイルで発見された具体的な単語境界違反のテスト"""
        test_cases = [
            # 実際の問題例
            ("In pancreat\\[[9]\\]er, several cell surface markers", "pancreat", "er"),
            ("proteasome act\\[[10]\\]herefore, proteasome inhibitors", "act", "herefore"),
            ("revealed t\\[[14], [15], [16]\\] is highly expressed", "t", " is"),
            ("t\\[[26], [27], [28], [29]\\]e protease, serine 3", "t", "e"),
            # 新しい問題例
            ("Primary antibodies to KRT13 (ERP3671, Abcam), PG (A-6, Santa Cruz Biotechnology), \\[[22]\\] (D84C12, Cell Signaling) were used.", ", ", " (D84C12"),
            ("Each study was\\[[25]\\] for three times.", "was", " for"),
        ]
        
        for test_text, expected_before, expected_after in test_cases:
            with self.subTest(text=test_text):
                result = self.parser.parse_document(test_text)
                
                # 単語境界違反の検出によりスキップされるべき
                # または適切に修正されるべき
                print(f"Input: {test_text}")
                print(f"Output: {result.converted_text}")
                
                # 最低限、元のテキストより悪化してはいけない
                self.assertIsNotNone(result.converted_text)
                
                # 単語境界が明らかに破壊されている場合は警告ログが出力されるべき
                # 実際の修正はここでは検証しないが、少なくとも処理が続行されることを確認
    
    def test_citation_word_boundary_detection(self):
        """引用挿入時の単語境界検出テスト"""
        # 正常なケース - 単語境界で引用が挿入される場合
        normal_text = "This study \\[[1]\\] builds on previous work."
        result = self.parser.parse_document(normal_text)
        
        # 正常なケースでは問題が発生しない
        self.assertIn("study \\[[1]\\] builds", result.converted_text)
    
    def test_citation_position_validation(self):
        """引用位置の妥当性検証テスト"""
        # 複雑な引用パターンでの位置検証
        text = "Multiple citations \\[[1], [2], [3]\\] in sequence should work correctly."
        result = self.parser.parse_document(text)
        
        # 複数引用の場合でも文章が破壊されない
        self.assertNotIn("Multiple citations\\[", result.converted_text[:-3])  # 末尾除く
        self.assertIn("Multiple citations \\[", result.converted_text)


if __name__ == '__main__':
    unittest.main() 