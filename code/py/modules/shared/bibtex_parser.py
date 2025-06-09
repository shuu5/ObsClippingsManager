"""
BibTeX解析エンジン

ObsClippingsManager統合システムで使用されるBibTeX解析機能を提供します。
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import bibtexparser
from bibtexparser.bparser import BibTexParser as BibtexparserBibTexParser
from bibtexparser.customization import convert_to_unicode

from .exceptions import BibTeXParseError, ValidationError


class BibTeXParser:
    """BibTeX解析エンジン"""
    
    # 対応エントリタイプ
    SUPPORTED_ENTRY_TYPES = {
        'article', 'book', 'inproceedings', 'incollection',
        'techreport', 'phdthesis', 'masterthesis', 'misc'
    }
    
    # 必須フィールド定義
    REQUIRED_FIELDS = {
        'article': ['title', 'author', 'journal', 'year'],
        'book': ['title', 'author', 'publisher', 'year'],
        'inproceedings': ['title', 'author', 'booktitle', 'year'],
        'incollection': ['title', 'author', 'booktitle', 'year'],
        'techreport': ['title', 'author', 'institution', 'year'],
        'phdthesis': ['title', 'author', 'school', 'year'],
        'masterthesis': ['title', 'author', 'school', 'year'],
        'misc': ['title']
    }
    
    def __init__(self, encoding: str = "utf-8"):
        """
        Args:
            encoding: ファイルエンコーディング
        """
        self.encoding = encoding
        self.entries = {}
        
    def parse_file(self, file_path: str) -> Dict[str, Dict[str, str]]:
        """
        BibTeXファイルを解析
        
        Args:
            file_path: BibTeXファイルパス
            
        Returns:
            Dict[citation_key, エントリ情報] の辞書
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise BibTeXParseError(f"BibTeX file not found: {file_path}")
        
        try:
            with open(file_path_obj, 'r', encoding=self.encoding) as bibtex_file:
                parser = BibtexparserBibTexParser(common_strings=True)
                parser.customization = convert_to_unicode
                bib_database = bibtexparser.load(bibtex_file, parser=parser)
            
            # エントリを内部形式に変換
            entries = {}
            for entry in bib_database.entries:
                citation_key = entry.get('ID', '')
                if citation_key:
                    normalized_entry = self.normalize_entry(entry)
                    entries[citation_key] = normalized_entry
            
            self.entries = entries
            logging.info(f"Parsed {len(entries)} BibTeX entries from {file_path}")
            return entries
            
        except Exception as e:
            raise BibTeXParseError(f"Failed to parse BibTeX file: {e}")
    
    def extract_dois(self, entries: Dict[str, Dict[str, str]]) -> List[str]:
        """
        BibTeX項目からDOIを抽出
        
        Args:
            entries: parse_fileで取得したエントリ辞書
            
        Returns:
            DOIのリスト
        """
        dois = []
        
        for citation_key, entry in entries.items():
            doi = self.extract_doi_from_entry(entry)
            if doi:
                dois.append(doi)
                
        logging.info(f"Extracted {len(dois)} DOIs from {len(entries)} entries")
        return dois
    
    def normalize_entry(self, entry: Dict[str, str]) -> Dict[str, str]:
        """
        BibTeXエントリを正規化
        - titleフィールドの特殊文字処理
        - authorフィールドの正規化
        - フィールド名の統一
        """
        normalized = {}
        
        # エントリタイプを正規化
        entry_type = entry.get('ENTRYTYPE', 'misc').lower()
        normalized['entry_type'] = entry_type
        
        # ID/citation_keyの処理
        normalized['citation_key'] = entry.get('ID', '')
        
        # 各フィールドを正規化
        field_mappings = {
            'title': 'title',
            'author': 'author',
            'year': 'year',
            'journal': 'journal',
            'booktitle': 'booktitle',
            'publisher': 'publisher',
            'institution': 'institution',
            'school': 'school',
            'doi': 'doi',
            'url': 'url',
            'pages': 'pages',
            'volume': 'volume',
            'number': 'number',
            'note': 'note',
            'abstract': 'abstract',
            # 状態管理フィールド
            'obsclippings_organize_status': 'obsclippings_organize_status',
            'obsclippings_sync_status': 'obsclippings_sync_status',
            'obsclippings_fetch_status': 'obsclippings_fetch_status',
            'obsclippings_parse_status': 'obsclippings_parse_status'
        }
        
        for bibtex_field, normalized_field in field_mappings.items():
            if bibtex_field in entry:
                value = entry[bibtex_field]
                
                # titleフィールドの特殊処理
                if normalized_field == 'title':
                    normalized[normalized_field] = self.normalize_title(value)
                    normalized['raw_title'] = value  # 元のタイトルも保持
                    
                # authorフィールドの特殊処理
                elif normalized_field == 'author':
                    normalized[normalized_field] = self._normalize_authors(value)
                    normalized['raw_author'] = value  # 元の著者情報も保持
                    
                else:
                    normalized[normalized_field] = value.strip()
        
        # DOIの抽出（複数フィールドから試行）
        if 'doi' not in normalized:
            doi = self.extract_doi_from_entry(entry)
            if doi:
                normalized['doi'] = doi
        
        return normalized
    
    def _normalize_authors(self, authors: str) -> str:
        """著者名を正規化"""
        # "and"で区切られた著者リストを処理
        author_list = re.split(r'\s+and\s+', authors, flags=re.IGNORECASE)
        normalized_authors = []
        
        for author in author_list:
            author = author.strip()
            # 姓名の順序を統一（簡易版）
            if ',' in author:
                # "Last, First" 形式
                parts = author.split(',', 1)
                if len(parts) == 2:
                    author = f"{parts[1].strip()} {parts[0].strip()}"
            normalized_authors.append(author)
        
        return ' and '.join(normalized_authors)
    
    @staticmethod
    def extract_doi_from_entry(entry: Dict[str, str]) -> Optional[str]:
        """
        単一のBibTeXエントリからDOIを抽出
        
        Args:
            entry: BibTeX項目辞書
            
        Returns:
            DOI文字列またはNone
        """
        # DOIフィールドから直接取得
        if 'doi' in entry:
            doi = entry['doi'].strip()
            # URLプレフィックスを除去
            doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi)
            return doi
        
        # URLフィールドからDOI抽出を試行
        if 'url' in entry:
            url = entry['url']
            # DOI URLパターン
            doi_match = re.search(r'doi\.org/(.+?)(?:\s|$)', url)
            if doi_match:
                return doi_match.group(1)
        
        # noteフィールドからDOI抽出を試行
        if 'note' in entry:
            note = entry['note']
            doi_match = re.search(r'(?:DOI|doi):\s*(.+?)(?:\s|$)', note)
            if doi_match:
                return doi_match.group(1)
        
        return None
    
    def validate_bibtex_entry(self, entry: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        BibTeXエントリの妥当性チェック
        
        Args:
            entry: 検証対象のBibTeX項目
            
        Returns:
            (妥当性, エラーメッセージリスト)
        """
        errors = []
        
        # エントリタイプのチェック
        entry_type = entry.get('entry_type', '').lower()
        if not entry_type:
            errors.append("Missing entry type")
            return False, errors
        
        if entry_type not in self.SUPPORTED_ENTRY_TYPES:
            errors.append(f"Unsupported entry type: {entry_type}")
        
        # 必須フィールドのチェック
        if entry_type in self.REQUIRED_FIELDS:
            required = self.REQUIRED_FIELDS[entry_type]
            for field in required:
                if field not in entry or not entry[field].strip():
                    errors.append(f"Missing required field: {field}")
        
        # citation_keyのチェック
        citation_key = entry.get('citation_key', '')
        if not citation_key:
            errors.append("Missing citation key")
        elif not re.match(r'^[\w\-.:]+$', citation_key):
            errors.append(f"Invalid citation key format: {citation_key}")
        
        # 年のフォーマットチェック
        if 'year' in entry:
            year = entry['year']
            if not re.match(r'^\d{4}$', year):
                errors.append(f"Invalid year format: {year}")
        
        # DOIフォーマットチェック（存在する場合）
        if 'doi' in entry:
            doi = entry['doi']
            if not validate_doi(doi):
                errors.append(f"Invalid DOI format: {doi}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """
        Titleフィールドを正規化
        - LaTeX命令の除去
        - 特殊文字の処理
        - 空白の正規化
        
        Args:
            title: 元のタイトル文字列
            
        Returns:
            正規化されたタイトル
        """
        if not title:
            return ""
        
        # LaTeXコマンドを処理
        # \command{content} -> content
        title = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', title)
        
        # 波括弧を除去
        title = re.sub(r'[{}]', '', title)
        
        # LaTeX特殊文字を処理
        latex_replacements = {
            r'\\&': '&',
            r'\\%': '%',
            r'\\_': '_',
            r'\\#': '#',
            r'\\$': '$',
            r'\\textquoteright': "'",
            r'\\textquoteleft': "'",
            r'\\textquotedblright': '"',
            r'\\textquotedblleft': '"',
            r'--': '–',  # en dash
            r'---': '—',  # em dash
        }
        
        for pattern, replacement in latex_replacements.items():
            title = title.replace(pattern, replacement)
        
        # 連続する空白を単一スペースに
        title = re.sub(r'\s+', ' ', title)
        
        # 前後の空白を除去
        title = title.strip()
        
        return title

    # API一貫性のためのメソッド追加
    def parse_content(self, content: str) -> Dict[str, Dict[str, str]]:
        """
        BibTeXコンテンツ文字列を解析
        
        Args:
            content: BibTeXコンテンツ文字列
            
        Returns:
            Dict[citation_key, エントリ情報] の辞書
        """
        import tempfile
        import os
        
        # 一時ファイルを作成してparse_fileを使用
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False, encoding=self.encoding) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            return self.parse_file(temp_file_path)
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def validate_entry(self, entry: Dict[str, str], citation_key: str = None) -> Tuple[bool, List[str]]:
        """
        エントリ検証 (validate_bibtex_entryのエイリアス)
        
        Args:
            entry: 検証対象のエントリ
            citation_key: citation key (entry内にない場合に使用)
            
        Returns:
            (妥当性, エラーメッセージリスト)
        """
        # citation_keyが指定されている場合は追加
        if citation_key and 'citation_key' not in entry:
            entry = entry.copy()
            entry['citation_key'] = citation_key
        
        return self.validate_bibtex_entry(entry)
    
    def is_valid_doi(self, doi: str) -> bool:
        """
        DOI検証 (validate_doiのインスタンスメソッド版)
        
        Args:
            doi: 検証するDOI
            
        Returns:
            DOIの妥当性
        """
        return validate_doi(doi)
    
    def parse_authors(self, author_string: str) -> List[Dict[str, str]]:
        """
        著者文字列を解析して構造化データに変換
        
        Args:
            author_string: 著者文字列
            
        Returns:
            著者情報のリスト
        """
        authors = []
        author_list = re.split(r'\s+and\s+', author_string, flags=re.IGNORECASE)
        
        for author in author_list:
            author = author.strip()
            author_info = {}
            
            if ',' in author:
                # "Last, First" 形式
                parts = author.split(',', 1)
                author_info['family'] = parts[0].strip()
                author_info['given'] = parts[1].strip()
            else:
                # "First Last" 形式
                parts = author.split()
                if len(parts) >= 2:
                    author_info['given'] = ' '.join(parts[:-1])
                    author_info['family'] = parts[-1]
                else:
                    author_info['family'] = author
                    author_info['given'] = ''
            
            authors.append(author_info)
        
        return authors
    
    def generate_statistics(self, entries: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        エントリ統計情報を生成
        
        Args:
            entries: エントリ辞書
            
        Returns:
            統計情報
        """
        stats = {
            'total_entries': len(entries),
            'entries_with_doi': 0,
            'by_entry_type': {},
            'by_year': {}
        }
        
        for citation_key, entry in entries.items():
            # DOI統計
            if 'doi' in entry:
                stats['entries_with_doi'] += 1
            
            # エントリタイプ統計
            entry_type = entry.get('entry_type', 'unknown')
            stats['by_entry_type'][entry_type] = stats['by_entry_type'].get(entry_type, 0) + 1
            
            # 年統計
            year = entry.get('year', 'unknown')
            stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
        
        return stats


# 便利関数
def parse_bibtex_file(file_path: str) -> Dict[str, Dict[str, str]]:
    """
    BibTeXファイルを読み込み、パース
    
    Args:
        file_path: BibTeXファイルパス
        
    Returns:
        Citation keyをキーとする辞書
    """
    parser = BibTeXParser()
    return parser.parse_file(file_path)


def extract_citation_key(entry_text: str) -> str:
    """
    BibTeXエントリからcitation_keyを抽出
    
    Args:
        entry_text: BibTeXエントリのテキスト
        
    Returns:
        Citation key文字列
    """
    pattern = r'@\w+\s*\{\s*([^,\s}]+)'
    match = re.search(pattern, entry_text)
    
    if match:
        return match.group(1).strip()
    return ""


def normalize_title(title: str) -> str:
    """
    Titleフィールドを正規化（静的メソッドのラッパー）
    
    Args:
        title: 元のタイトル文字列
        
    Returns:
        正規化されたタイトル
    """
    return BibTeXParser.normalize_title(title)


def extract_doi_from_entry(entry: Dict[str, str]) -> Optional[str]:
    """
    単一のBibTeXエントリからDOIを抽出（静的メソッドのラッパー）
    
    Args:
        entry: BibTeX項目辞書
        
    Returns:
        DOI文字列またはNone
    """
    return BibTeXParser.extract_doi_from_entry(entry)


def validate_doi(doi: str) -> bool:
    """
    DOI形式の妥当性チェック
    
    Args:
        doi: チェック対象のDOI文字列
        
    Returns:
        妥当性の真偽値
    """
    # 基本的なDOIパターン（10.xxxx/yyyy形式）
    doi_pattern = r'^10\.\d{4,}(?:\.\d+)*/.+$'
    return bool(re.match(doi_pattern, doi)) 