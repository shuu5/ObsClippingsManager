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
        
        # BibTeXパーサーの設定（毎回新しいインスタンスを作成するため、ここでは設定のみ保存）
        self.parser_config = {
            'customization': convert_to_unicode,
            'ignore_nonstandard_types': False,
            'homogenize_fields': True
        }
        
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
                self.logger.error("Invalid BibTeX syntax: malformed entries detected")
                raise BibTeXError(
                    "Invalid BibTeX syntax: malformed entries detected",
                    error_code="BIBTEX_SYNTAX_ERROR",
                    context={"content_preview": bibtex_content[:200]}
                )
            
            # BibTeX解析実行（毎回新しいパーサーを作成して混在を防ぐ）
            try:
                parser = BibtexparserParser()
                parser.customization = self.parser_config['customization']
                parser.ignore_nonstandard_types = self.parser_config['ignore_nonstandard_types']
                parser.homogenize_fields = self.parser_config['homogenize_fields']
                
                bib_database = bibtexparser.loads(bibtex_content, parser=parser)
            except Exception as e:
                self.logger.error(f"Failed to parse BibTeX content: {str(e)}")
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
                parser = BibtexparserParser()
                parser.customization = self.parser_config['customization']
                parser.ignore_nonstandard_types = self.parser_config['ignore_nonstandard_types']
                parser.homogenize_fields = self.parser_config['homogenize_fields']
                
                bib_database = bibtexparser.loads(bibtex_content, parser=parser)
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
        BibTeXコンテンツの基本的な構文チェック
        
        Args:
            bibtex_content (str): 検証対象のBibTeX文字列
            
        Returns:
            bool: 基本的な構文が正しい場合True
        """
        try:
            if not bibtex_content.strip():
                return True  # 空の場合は有効
                
            # @記号があるかチェック
            if '@' not in bibtex_content:
                return True  # @記号がない場合は空文字列と同様に扱う
            
            # 無効なパターンをチェック
            # 1. 未閉じの波括弧
            open_braces = bibtex_content.count('{')
            close_braces = bibtex_content.count('}')
            if abs(open_braces - close_braces) > 2:  # 多少の許容範囲
                return False
            
            # 2. 基本的なエントリーパターンチェック
            # @type{key, または @type{key} の形式があるかチェック
            entry_pattern = r'@\w+\s*\{\s*[^,\s}]+\s*[,}]'
            
            # エントリーが見つかるかチェック
            if not re.search(entry_pattern, bibtex_content, re.IGNORECASE | re.MULTILINE):
                return False
            
            # 3. 明らかな構文エラーパターンをチェック
            # カンマの後に直接@が来る（エントリが完全に終了していない）
            if re.search(r',\s*@', bibtex_content):
                return False
            
            # 4. 未閉じのエントリー（@の後に対応する}がない）
            entry_starts = [m.start() for m in re.finditer(r'@\w+\s*\{', bibtex_content)]
            for i, start in enumerate(entry_starts):
                # 次のエントリーまでの範囲で波括弧がバランスしているかチェック
                if i + 1 < len(entry_starts):
                    entry_content = bibtex_content[start:entry_starts[i + 1]]
                else:
                    entry_content = bibtex_content[start:]
                
                entry_open = entry_content.count('{')
                entry_close = entry_content.count('}')
                if entry_open > entry_close + 1:  # 1つ以上の未閉じ波括弧は問題
                    return False
            
            return True
            
        except Exception:
            return False
    
    # === Citation Fetcher機能拡張 ===
    def extract_doi_from_entries(self, entries: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        BibTeXエントリ辞書からDOIを抽出
        
        Args:
            entries (Dict[str, Dict[str, Any]]): parse_string/parse_fileの結果エントリ辞書
            
        Returns:
            List[str]: 有効なDOIのリスト（重複除去、ソート済み）
        """
        try:
            self.logger.debug(f"Extracting DOIs from {len(entries)} entries")
            
            dois = []
            
            for citation_key, entry in entries.items():
                if 'doi' in entry and entry['doi']:
                    doi = entry['doi'].strip()
                    
                    # DOI形式の基本検証（10.から始まる）
                    if self._is_valid_doi_format(doi):
                        # 正規化（URLプレフィックス除去）
                        normalized_doi = self._normalize_doi(doi)
                        dois.append(normalized_doi)
                    else:
                        self.logger.warning(f"Invalid DOI format in entry '{citation_key}': {doi}")
            
            # 重複除去とソート
            unique_dois = sorted(list(set(dois)))
            
            self.logger.debug(f"Extracted {len(unique_dois)} unique valid DOIs")
            return unique_dois
            
        except Exception as e:
            self.logger.error(f"Error extracting DOIs from entries: {e}")
            raise BibTeXError(
                f"Failed to extract DOIs from entries: {str(e)}",
                error_code="BIBTEX_DOI_EXTRACTION_ERROR",
                context={"original_error": str(e)}
            )
    
    def get_citation_key_to_doi_mapping(self, entries: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """
        Citation Key → DOI マッピング辞書を生成
        
        Args:
            entries (Dict[str, Dict[str, Any]]): parse_string/parse_fileの結果エントリ辞書
            
        Returns:
            Dict[str, str]: citation_key → doi のマッピング辞書
        """
        try:
            self.logger.debug(f"Creating citation_key → DOI mapping from {len(entries)} entries")
            
            mapping = {}
            
            for citation_key, entry in entries.items():
                if 'doi' in entry and entry['doi']:
                    doi = entry['doi'].strip()
                    
                    # DOI形式の基本検証
                    if self._is_valid_doi_format(doi):
                        # 正規化（URLプレフィックス除去）
                        normalized_doi = self._normalize_doi(doi)
                        mapping[citation_key] = normalized_doi
                    else:
                        self.logger.warning(f"Invalid DOI format in entry '{citation_key}': {doi}")
            
            self.logger.debug(f"Created mapping with {len(mapping)} citation_key → DOI pairs")
            return mapping
            
        except Exception as e:
            self.logger.error(f"Error creating citation_key → DOI mapping: {e}")
            raise BibTeXError(
                f"Failed to create citation_key → DOI mapping: {str(e)}",
                error_code="BIBTEX_MAPPING_ERROR",
                context={"original_error": str(e)}
            )
    
    def _is_valid_doi_format(self, doi: str) -> bool:
        """
        DOI形式の基本検証
        
        Args:
            doi (str): 検証対象のDOI文字列
            
        Returns:
            bool: 有効なDOI形式かどうか
        """
        if not doi or not isinstance(doi, str):
            return False
        
        # DOIの基本パターン（10.で始まり、/を含む）
        doi_pattern = r'(?:https?://(?:dx\.)?doi\.org/|doi:)?10\.\d+/.+'
        
        return bool(re.match(doi_pattern, doi.strip(), re.IGNORECASE))
    
    # === AI Citation Support機能拡張: 順序・重複保持 ===
    def parse_file_ordered(self, bibtex_file: str) -> List[Dict[str, Any]]:
        """
        BibTeXファイルの順序・重複保持解析
        
        Args:
            bibtex_file (str): BibTeXファイルのパス
            
        Returns:
            List[Dict[str, Any]]: 順序保持・重複包含のエントリリスト
                                 各エントリにnumberプロパティを追加
            
        Raises:
            BibTeXError: ファイル読み込みエラー、解析エラー時
        """
        try:
            self.logger.debug(f"Starting ordered parse of BibTeX file: {bibtex_file}")
            
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
            except Exception as e:
                raise BibTeXError(
                    f"Failed to read BibTeX file {bibtex_file}: {str(e)}",
                    error_code="BIBTEX_READ_ERROR",
                    context={"file_path": bibtex_file, "original_error": str(e)}
                )
            
            # 順序・重複保持BibTeX解析
            result = self.parse_string_ordered(content)
            
            self.logger.info(f"Successfully parsed BibTeX file (ordered): {bibtex_file} ({len(result)} entries)")
            return result
            
        except BibTeXError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing BibTeX file (ordered) {bibtex_file}: {e}")
            raise BibTeXError(
                f"Unexpected error parsing BibTeX file (ordered) {bibtex_file}: {str(e)}",
                error_code="BIBTEX_UNEXPECTED_ERROR",
                context={"file_path": bibtex_file, "original_error": str(e)}
            )
    
    def parse_string_ordered(self, bibtex_content: str) -> List[Dict[str, Any]]:
        """
        BibTeX文字列の順序・重複保持解析
        
        Args:
            bibtex_content (str): BibTeX形式の文字列
            
        Returns:
            List[Dict[str, Any]]: 順序保持・重複包含のエントリリスト
                                 各エントリにnumberプロパティを追加
            
        Raises:
            BibTeXError: 解析エラー時
        """
        try:
            self.logger.debug("Starting ordered parse of BibTeX string content")
            
            # 空文字列チェック
            if not bibtex_content.strip():
                self.logger.debug("Empty BibTeX content provided")
                return []
            
            # 基本的な構文チェック（解析前）
            if not self._basic_syntax_check(bibtex_content):
                self.logger.error("Invalid BibTeX syntax: malformed entries detected")
                raise BibTeXError(
                    "Invalid BibTeX syntax: malformed entries detected",
                    error_code="BIBTEX_SYNTAX_ERROR",
                    context={"content_preview": bibtex_content[:200]}
                )
            
            # BibTeX解析実行（毎回新しいパーサーを作成して混在を防ぐ）
            try:
                parser = BibtexparserParser()
                parser.customization = self.parser_config['customization']
                parser.ignore_nonstandard_types = self.parser_config['ignore_nonstandard_types']
                parser.homogenize_fields = self.parser_config['homogenize_fields']
                
                bib_database = bibtexparser.loads(bibtex_content, parser=parser)
            except Exception as e:
                self.logger.error(f"Failed to parse BibTeX content: {str(e)}")
                raise BibTeXError(
                    f"Failed to parse BibTeX content: {str(e)}",
                    error_code="BIBTEX_PARSE_ERROR",
                    context={"parse_error": str(e)}
                )
            
            # 順序付きエントリリストの構築（重複保持）
            ordered_entries = []
            for number, entry in enumerate(bib_database.entries, 1):
                if 'ID' not in entry:
                    self.logger.warning(f"BibTeX entry #{number} missing ID field, skipping")
                    continue
                
                citation_key = entry['ID']
                normalized_entry = self._normalize_entry(entry)
                
                # 順序・重複保持エントリの構築
                ordered_entry = {
                    'number': number,
                    'citation_key': citation_key,
                    **normalized_entry
                }
                
                ordered_entries.append(ordered_entry)
            
            self.logger.debug(f"Successfully parsed {len(ordered_entries)} BibTeX entries (ordered)")
            return ordered_entries
            
        except BibTeXError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing BibTeX string (ordered): {e}")
            raise BibTeXError(
                f"Unexpected error parsing BibTeX string (ordered): {str(e)}",
                error_code="BIBTEX_STRING_PARSE_ERROR",
                context={"original_error": str(e)}
            ) 