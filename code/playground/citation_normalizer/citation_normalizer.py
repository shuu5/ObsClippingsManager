import re
from typing import List, Tuple


class CitationNormalizer:
    """引用文献の表示形式を統一するクラス"""
    
    def __init__(self):
        # 範囲表記のパターン（ハイフン、エンダッシュ、エムダッシュに対応）
        self.range_pattern = re.compile(r'\[(\d+)[\-–—](\d+)\]')
        # 個別引用のパターン
        self.individual_pattern = re.compile(r'\[(\d+)\]')
        
    def normalize_citations(self, text: str) -> str:
        """
        引用文献の形式を統一する
        
        Args:
            text: 処理対象のテキスト
            
        Returns:
            str: 統一後のテキスト
        """
        # 範囲表記を展開
        text = self._expand_range_citations(text)
        
        # 連続する引用を統合（例：[17], [18] → [17,18]）
        text = self._merge_consecutive_citations(text)
        
        return text
    
    def _expand_range_citations(self, text: str) -> str:
        """
        範囲表記を個別表記に展開する
        例：[2-4] → [2,3,4]
        """
        def replace_range(match):
            start = int(match.group(1))
            end = int(match.group(2))
            
            if start > end:
                # 範囲が逆の場合は元のまま返す
                return match.group(0)
            
            # 範囲を展開
            numbers = list(range(start, end + 1))
            return f"[{','.join(map(str, numbers))}]"
        
        return self.range_pattern.sub(replace_range, text)
    
    def _merge_consecutive_citations(self, text: str) -> str:
        """
        連続する個別引用を統合する
        例：[17], [18] → [17,18]
        """
        # 連続する引用パターンを検索
        consecutive_pattern = re.compile(r'(\[\d+\](?:\s*,\s*\[\d+\])+)')
        
        def merge_citations(match):
            citation_text = match.group(1)
            # 各引用から数字を抽出
            numbers = []
            for num_match in self.individual_pattern.finditer(citation_text):
                numbers.append(int(num_match.group(1)))
            
            # 重複を除去してソート
            unique_numbers = sorted(set(numbers))
            return f"[{','.join(map(str, unique_numbers))}]"
        
        return consecutive_pattern.sub(merge_citations, text)
    
    def extract_citations(self, text: str) -> List[Tuple[str, int, int]]:
        """
        テキストから引用文献を抽出する
        
        Args:
            text: 処理対象のテキスト
            
        Returns:
            List[Tuple[str, int, int]]: (引用文字列, 開始位置, 終了位置)のリスト
        """
        citations = []
        
        # 範囲表記の引用を検索
        for match in self.range_pattern.finditer(text):
            citations.append((match.group(0), match.start(), match.end()))
        
        # 個別引用を検索
        for match in self.individual_pattern.finditer(text):
            # 範囲表記と重複しないかチェック
            is_overlap = False
            for _, start, end in citations:
                if match.start() >= start and match.end() <= end:
                    is_overlap = True
                    break
            
            if not is_overlap:
                citations.append((match.group(0), match.start(), match.end()))
        
        return sorted(citations, key=lambda x: x[1])
    
    def process_file(self, file_path: str) -> str:
        """
        ファイルの引用文献を統一する
        
        Args:
            file_path: 処理対象ファイルのパス
            
        Returns:
            str: 統一後のテキスト
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            normalized_content = self.normalize_citations(content)
            return normalized_content
            
        except Exception as e:
            raise Exception(f"ファイル処理中にエラーが発生しました: {e}")
    
    def process_directory(self, directory_path: str, file_extension: str = '.md') -> dict:
        """
        ディレクトリ内のファイルを一括処理する
        
        Args:
            directory_path: 処理対象ディレクトリのパス
            file_extension: 処理対象の拡張子
            
        Returns:
            dict: {ファイルパス: 統一後テキスト}の辞書
        """
        import os
        
        results = {}
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.endswith(file_extension):
                    file_path = os.path.join(root, file)
                    try:
                        normalized_content = self.process_file(file_path)
                        results[file_path] = normalized_content
                    except Exception as e:
                        print(f"エラー: {file_path} - {e}")
        
        return results 