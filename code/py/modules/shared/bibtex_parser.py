"""
BibTeX解析エンジン

このモジュールは、BibTeXファイルの読み込み、解析、検証機能を提供します。
citation_key抽出とメタデータ正規化を行い、統一的なデータ形式で出力します。
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import bibtexparser
    from bibtexparser.bparser import BibTexParser as BibtexparserParser
    from bibtexparser.customization import convert_to_unicode
    BIBTEXPARSER_AVAILABLE = True
except ImportError:
    BIBTEXPARSER_AVAILABLE = False

from .exceptions import BibTeXError


class BibTeXParser:
    """
    BibTeX解析エンジン
    
    BibTeXファイルの読み込み、解析、検証機能を提供。
    citation_key抽出とメタデータ正規化を統一的に処理。
    """
    
    def __init__(self, logger):
        """
        BibTeXParserの初期化
        
        Args:
            logger: ログシステムインスタンス
        """
        self.logger = logger
        
        if not BIBTEXPARSER_AVAILABLE:
            raise BibTeXError(
                "bibtexparser library is not available. Please install it with: pip install bibtexparser",
                error_code="BIBTEX_DEPENDENCY_ERROR"
            )
        
        # BibTeXパーサーの設定
        self.parser = BibtexparserParser()
        self.parser.customization = convert_to_unicode
        self.parser.ignore_nonstandard_types = False
        self.parser.homogenize_fields = True
        
        self.logger.debug("BibTeXParser initialized successfully")
    
    def parse_file(self, bibtex_file: str) -> Dict[str, Dict[str, Any]]:
        """
        BibTeXファイルの解析
        
        Args:
            bibtex_file (str): BibTeXファイルのパス
            
        Returns:
            Dict[str, Dict[str, Any]]: citation_keyをキーとしたエントリ辞書
            
        Raises:
            BibTeXError: ファイル読み込みエラー、解析エラー時
        """
        try:
            self.logger.debug(f"Starting to parse BibTeX file: {bibtex_file}")
            
            # ファイル存在確認
            if not os.path.exists(bibtex_file):
                raise BibTeXError(
                    f"BibTeX file not found: {bibtex_file}",
                    error_code="BIBTEX_FILE_NOT_FOUND",
                    context={"file_path": bibtex_file}
                )
            
            # ファイル読み込み
            try:
                with open(bibtex_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except PermissionError:
                raise BibTeXError(
                    f"Permission denied reading BibTeX file: {bibtex_file}",
                    error_code="BIBTEX_PERMISSION_ERROR",
                    context={"file_path": bibtex_file}
                )
            except Exception as e:
                raise BibTeXError(
                    f"Failed to read BibTeX file {bibtex_file}: {str(e)}",
                    error_code="BIBTEX_READ_ERROR",
                    context={"file_path": bibtex_file, "original_error": str(e)}
                )
            
            # BibTeX解析
            result = self.parse_string(content)
            
            self.logger.info(f"Successfully parsed BibTeX file: {bibtex_file} ({len(result)} entries)")
            return result
            
        except BibTeXError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing BibTeX file {bibtex_file}: {e}")
            raise BibTeXError(
                f"Unexpected error parsing BibTeX file {bibtex_file}: {str(e)}",
                error_code="BIBTEX_UNEXPECTED_ERROR",
                context={"file_path": bibtex_file, "original_error": str(e)}
            )
    
    def parse_string(self, bibtex_content: str) -> Dict[str, Dict[str, Any]]:
        """
        BibTeX文字列の解析
        
        Args:
            bibtex_content (str): BibTeX形式の文字列
            
        Returns:
            Dict[str, Dict[str, Any]]: citation_keyをキーとしたエントリ辞書
            
        Raises:
            BibTeXError: 解析エラー時
        """
        try:
            self.logger.debug("Starting to parse BibTeX string content")
            
            # 空文字列チェック
            if not bibtex_content.strip():
                self.logger.debug("Empty BibTeX content provided")
                return {}
            
            # 基本的な構文チェック（解析前）
            if not self._basic_syntax_check(bibtex_content):
                raise BibTeXError(
                    "Invalid BibTeX syntax: malformed entries detected",
                    error_code="BIBTEX_SYNTAX_ERROR",
                    context={"content_preview": bibtex_content[:200]}
                )
            
            # BibTeX解析実行
            try:
                bib_database = bibtexparser.loads(bibtex_content, parser=self.parser)
            except Exception as e:
                raise BibTeXError(
                    f"Failed to parse BibTeX content: {str(e)}",
                    error_code="BIBTEX_PARSE_ERROR",
                    context={"parse_error": str(e)}
                )
            
            # エントリ辞書の構築
            entries = {}
            for entry in bib_database.entries:
                if 'ID' not in entry:
                    self.logger.warning("BibTeX entry missing ID field, skipping")
                    continue
                
                citation_key = entry['ID']
                entries[citation_key] = self._normalize_entry(entry)
            
            self.logger.debug(f"Successfully parsed {len(entries)} BibTeX entries")
            return entries
            
        except BibTeXError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing BibTeX string: {e}")
            raise BibTeXError(
                f"Unexpected error parsing BibTeX string: {str(e)}",
                error_code="BIBTEX_STRING_PARSE_ERROR",
                context={"original_error": str(e)}
            )
    
    def extract_citation_keys(self, bibtex_content: str) -> List[str]:
        """
        BibTeXコンテンツからcitation_keyを抽出
        
        Args:
            bibtex_content (str): BibTeX形式の文字列
            
        Returns:
            List[str]: citation_keyのリスト（ソート済み）
        """
        try:
            self.logger.debug("Extracting citation keys from BibTeX content")
            
            # 空文字列チェック
            if not bibtex_content.strip():
                return []
            
            # 正規表現によるcitation_key抽出
            # @article{key, @book{key, @inproceedings{key 等をマッチ
            pattern = r'@\w+\s*\{\s*([^,\s}]+)'
            matches = re.findall(pattern, bibtex_content, re.IGNORECASE)
            
            # 重複削除とソート
            keys = sorted(list(set(matches)))
            
            self.logger.debug(f"Extracted {len(keys)} unique citation keys")
            return keys
            
        except Exception as e:
            self.logger.error(f"Error extracting citation keys: {e}")
            raise BibTeXError(
                f"Failed to extract citation keys: {str(e)}",
                error_code="BIBTEX_KEY_EXTRACTION_ERROR",
                context={"original_error": str(e)}
            )
    
    def validate_bibtex(self, bibtex_content: str) -> Tuple[bool, List[str]]:
        """
        BibTeXコンテンツの検証
        
        Args:
            bibtex_content (str): BibTeX形式の文字列
            
        Returns:
            Tuple[bool, List[str]]: (検証結果, エラーメッセージリスト)
        """
        try:
            self.logger.debug("Validating BibTeX content")
            
            errors = []
            
            # 空文字列チェック
            if not bibtex_content.strip():
                return True, []
            
            # 基本的な構文チェック（事前）
            if not self._basic_syntax_check(bibtex_content):
                errors.append("Basic BibTeX syntax error: malformed entries detected")
                return False, errors
            
            # 基本的な構文チェック
            try:
                bib_database = bibtexparser.loads(bibtex_content, parser=self.parser)
            except Exception as e:
                errors.append(f"BibTeX syntax error: {str(e)}")
                return False, errors
            
            # エントリレベルの検証
            required_fields = {
                'article': ['title', 'author', 'journal', 'year'],
                'book': ['title', 'author', 'publisher', 'year'],
                'inproceedings': ['title', 'author', 'booktitle', 'year'],
                'incollection': ['title', 'author', 'booktitle', 'year'],
                'phdthesis': ['title', 'author', 'school', 'year'],
                'mastersthesis': ['title', 'author', 'school', 'year']
            }
            
            for entry in bib_database.entries:
                entry_type = entry.get('ENTRYTYPE', '').lower()
                citation_key = entry.get('ID', 'unknown')
                
                # IDチェック
                if not entry.get('ID'):
                    errors.append(f"Entry missing citation key (ID)")
                    continue
                
                # 必須フィールドチェック
                if entry_type in required_fields:
                    missing_fields = []
                    for field in required_fields[entry_type]:
                        if field not in entry or not entry[field].strip():
                            missing_fields.append(field)
                    
                    if missing_fields:
                        errors.append(
                            f"Entry '{citation_key}' missing required fields: {', '.join(missing_fields)}"
                        )
            
            is_valid = len(errors) == 0
            
            if is_valid:
                self.logger.debug("BibTeX content validation passed")
            else:
                self.logger.warning(f"BibTeX content validation failed with {len(errors)} errors")
            
            return is_valid, errors
            
        except Exception as e:
            self.logger.error(f"Error validating BibTeX content: {e}")
            raise BibTeXError(
                f"Failed to validate BibTeX content: {str(e)}",
                error_code="BIBTEX_VALIDATION_ERROR",
                context={"original_error": str(e)}
            )
    
    def _normalize_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        BibTeXエントリの正規化
        
        Args:
            entry (Dict[str, Any]): 生のBibTeXエントリ
            
        Returns:
            Dict[str, Any]: 正規化されたエントリ
        """
        normalized = {}
        
        # 基本フィールドをコピー
        for key, value in entry.items():
            if key == 'ID':
                continue  # IDは外部で管理
            
            # 文字列フィールドの正規化
            if isinstance(value, str):
                # 余計な空白を削除
                value = value.strip()
                
                # 波括弧の処理（LaTeXコマンド保護）
                value = self._clean_latex_braces(value)
                
                # 改行と複数空白の正規化
                value = re.sub(r'\s+', ' ', value)
            
            normalized[key.lower()] = value
        
        # DOIの正規化
        if 'doi' in normalized and normalized['doi']:
            normalized['doi'] = self._normalize_doi(normalized['doi'])
        
        return normalized
    
    def _clean_latex_braces(self, text: str) -> str:
        """
        LaTeX波括弧の適切な処理
        
        Args:
            text (str): 処理対象テキスト
            
        Returns:
            str: 処理済みテキスト
        """
        # 保護すべき波括弧を除いて不要な波括弧を削除
        # 簡易実装: 単純な波括弧ペアを削除
        while True:
            new_text = re.sub(r'\{([^{}]*)\}', r'\1', text)
            if new_text == text:
                break
            text = new_text
        
        return text
    
    def _normalize_doi(self, doi: str) -> str:
        """
        DOIの正規化
        
        Args:
            doi (str): 生のDOI文字列
            
        Returns:
            str: 正規化されたDOI
        """
        # URLプレフィックスを削除
        doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi)
        doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
        
        return doi.strip()
    
    def _basic_syntax_check(self, bibtex_content: str) -> bool:
        """
        BibTeX基本構文チェック
        
        Args:
            bibtex_content (str): BibTeX文字列
            
        Returns:
            bool: 構文が正しいかどうか
        """
        try:
            # @記号で始まるエントリーの基本チェック
            entries = re.findall(r'@\w+\s*\{[^}]*\}', bibtex_content, re.DOTALL)
            if not entries and '@' in bibtex_content:
                # @記号があるのにエントリーが見つからない場合は構文エラー
                return False
            
            # 波括弧のバランスチェック
            open_braces = bibtex_content.count('{')
            close_braces = bibtex_content.count('}')
            
            # 完全にバランスが取れていない場合は無効
            if abs(open_braces - close_braces) > 2:  # 多少の誤差は許容
                return False
            
            # 基本的なエントリーパターンの確認
            if '@' in bibtex_content:
                # @記号があるなら、少なくとも1つの有効なエントリー形式があるべき
                valid_entry_pattern = r'@\w+\s*\{\s*\w+\s*,'
                if not re.search(valid_entry_pattern, bibtex_content):
                    return False
            
            return True
            
        except Exception:
            return False 