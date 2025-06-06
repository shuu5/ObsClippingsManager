"""
ファイル照合エンジン

MarkdownファイルのYAML frontmatter内のdoiとBibTeX項目のdoiフィールドの照合を行います。
"""

import logging
import os
import re
import yaml
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from fuzzywuzzy import fuzz, process

from ..shared.utils import normalize_text_for_comparison
from .exceptions import FileMatchingError


class FileMatcher:
    """MarkdownファイルとBibTeXエントリのファイル照合エンジン"""
    
    def __init__(self, similarity_threshold: float = 0.8, case_sensitive: bool = False, 
                 doi_matching_enabled: bool = True, title_fallback_enabled: bool = True,
                 title_sync_enabled: bool = True):
        """
        Args:
            similarity_threshold: 照合閾値（0.0-1.0）
            case_sensitive: 大文字小文字を区別するか
            doi_matching_enabled: DOI照合の有効/無効
            title_fallback_enabled: DOI未検出時のタイトル照合フォールバック
            title_sync_enabled: BibTeXタイトルとの自動同期
        """
        self.similarity_threshold = similarity_threshold
        self.case_sensitive = case_sensitive
        self.doi_matching_enabled = doi_matching_enabled
        self.title_fallback_enabled = title_fallback_enabled
        self.title_sync_enabled = title_sync_enabled
        self.logger = logging.getLogger("ObsClippingsManager.RenameMkDir.FileMatcher")
    
    def match_files_to_citations(self, 
                                md_files: List[str], 
                                bib_entries: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """
        Markdownファイルと最適なBibTeX項目をDOI照合で実行
        タイトル同期処理も含む
        
        Args:
            md_files: Markdownファイルパスのリスト
            bib_entries: BibTeX項目の辞書
            
        Returns:
            Dict[ファイルパス, citation_key] の照合結果
        """
        matches = {}
        
        for md_file in md_files:
            file_path = Path(md_file)
            
            # DOI照合を試行
            if self.doi_matching_enabled:
                citation_key = self._match_by_doi(md_file, bib_entries)
                if citation_key:
                    matches[md_file] = citation_key
                    self.logger.info(f"DOI match successful: {file_path.name} -> {citation_key}")
                    continue
            
            # DOI照合に失敗した場合、タイトル照合にフォールバック
            if self.title_fallback_enabled:
                filename = file_path.stem
                best_citation_key, best_score = self.find_best_match(filename, bib_entries)
                
                if best_citation_key:
                    matches[md_file] = best_citation_key
                    title = bib_entries[best_citation_key].get('title', '')
                    self.logger.info(
                        f"Title match successful: {file_path.name} -> {best_citation_key} "
                        f"(similarity: {best_score:.3f})"
                    )
                else:
                    self.logger.info(
                        f"No match found: {file_path.name} "
                        f"(best similarity: {best_score:.3f} < threshold: {self.similarity_threshold})"
                    )
            else:
                self.logger.info(f"No DOI found and title fallback disabled: {file_path.name}")
        
        return matches
    
    def find_best_match(self, filename: str, bib_entries: Dict[str, Dict[str, str]]) -> Tuple[Optional[str], float]:
        """
        最適なマッチを検索
        
        Args:
            filename: 検索対象のファイル名（拡張子なし）
            bib_entries: BibTeX項目の辞書
            
        Returns:
            (最適citation_key, 類似度スコア)
        """
        best_match = None
        best_score = 0.0
        
        for citation_key, entry in bib_entries.items():
            title = entry.get('title', '')
            if not title:
                continue
            
            similarity = self.calculate_similarity(filename, title)
            
            if similarity > best_score:
                best_score = similarity
                best_match = citation_key
        
        # 閾値を満たさない場合はNoneを返す
        if best_score < self.similarity_threshold:
            return None, best_score
        
        return best_match, best_score
    
    def calculate_similarity(self, filename: str, title: str) -> float:
        """
        ファイル名とタイトルの類似度を計算
        
        Args:
            filename: Markdownファイル名（拡張子なし）
            title: BibTeX titleフィールド
            
        Returns:
            類似度スコア (0.0-1.0)
        """
        # 正規化処理
        if not self.case_sensitive:
            normalized_filename = normalize_for_matching(filename)
            normalized_title = normalize_for_matching(title)
        else:
            normalized_filename = filename
            normalized_title = title
        
        # 複数の類似度計算手法を組み合わせ
        ratio = fuzz.ratio(normalized_filename, normalized_title) / 100.0
        partial_ratio = fuzz.partial_ratio(normalized_filename, normalized_title) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(normalized_filename, normalized_title) / 100.0
        token_set_ratio = fuzz.token_set_ratio(normalized_filename, normalized_title) / 100.0
        
        # 重み付き平均で最終スコアを計算（Token Sort Ratio重視）
        similarity = (
            ratio * 0.2 + 
            partial_ratio * 0.2 + 
            token_sort_ratio * 0.35 +  # 順序無関係の単語マッチング重視
            token_set_ratio * 0.25
        )
        
        return similarity
    
    def get_potential_matches(self, 
                            filename: str, 
                            bib_entries: Dict[str, Dict[str, str]], 
                            top_n: int = 5) -> List[Tuple[str, float, str]]:
        """
        ファイル名に対する潜在的なマッチ候補を取得
        
        Args:
            filename: 検索対象のファイル名
            bib_entries: BibTeX項目の辞書
            top_n: 取得する候補数
            
        Returns:
            [(citation_key, 類似度スコア, title), ...] のリスト
        """
        candidates = []
        filename_stem = Path(filename).stem
        
        for citation_key, entry in bib_entries.items():
            title = entry.get('title', '')
            if not title:
                continue
            
            similarity = self.calculate_similarity(filename_stem, title)
            candidates.append((citation_key, similarity, title))
        
        # 類似度でソートして上位N件を返す
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]
    
    def validate_matches(self, 
                        matches: Dict[str, str],
                        bib_entries: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, str], List[str]]:
        """
        マッチ結果を検証し、問題のあるマッチを特定
        
        Args:
            matches: 照合結果
            bib_entries: BibTeX項目の辞書
            
        Returns:
            (検証済みマッチ, 警告メッセージリスト)
        """
        valid_matches = {}
        warnings = []
        
        # citation_keyの重複をチェック
        citation_keys_used = {}
        
        for file_path, citation_key in matches.items():
            filename = Path(file_path).name
            
            # citation_keyの存在確認
            if citation_key not in bib_entries:
                warnings.append(f"Invalid citation key: {citation_key} for file {filename}")
                continue
            
            # 重複チェック
            if citation_key in citation_keys_used:
                other_file = citation_keys_used[citation_key]
                warnings.append(
                    f"Citation key '{citation_key}' is matched to multiple files: "
                    f"{filename} and {other_file}"
                )
                continue
            
            valid_matches[file_path] = citation_key
            citation_keys_used[citation_key] = filename
        
        return valid_matches, warnings
    
    def _match_by_doi(self, file_path: str, bib_entries: Dict[str, Dict[str, str]]) -> Optional[str]:
        """
        DOI照合でBibTeX項目を検索
        
        Args:
            file_path: Markdownファイルパス
            bib_entries: BibTeX項目の辞書
            
        Returns:
            マッチしたcitation_key（見つからない場合はNone）
        """
        # MarkdownファイルからDOIを抽出
        md_doi = self.extract_doi_from_markdown(file_path)
        if not md_doi:
            return None
        
        # DOI形式の妥当性チェック
        if not self.validate_doi_format(md_doi):
            self.logger.warning(f"Invalid DOI format in {file_path}: {md_doi}")
            return None
        
        # 正規化
        normalized_md_doi = self.normalize_doi(md_doi)
        
        # BibTeX項目とのDOI照合
        for citation_key, entry in bib_entries.items():
            bib_doi = entry.get('doi', '')
            if not bib_doi:
                continue
            
            normalized_bib_doi = self.normalize_doi(bib_doi)
            
            if normalized_md_doi == normalized_bib_doi:
                return citation_key
        
        return None
    
    def extract_doi_from_markdown(self, file_path: str) -> Optional[str]:
        """
        MarkdownファイルのYAML frontmatterからDOIを抽出
        
        Args:
            file_path: Markdownファイルパス
            
        Returns:
            抽出されたDOI文字列（見つからない場合はNone）
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAML frontmatterを抽出
            if not content.startswith('---'):
                return None
            
            # 2番目の---までの部分を取得
            parts = content.split('---', 2)
            if len(parts) < 3:
                return None
            
            yaml_content = parts[1].strip()
            
            # YAMLを解析
            try:
                frontmatter = yaml.safe_load(yaml_content)
                if isinstance(frontmatter, dict):
                    return frontmatter.get('doi')
            except yaml.YAMLError:
                self.logger.warning(f"Failed to parse YAML frontmatter in {file_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None
        
        return None
    
    def normalize_doi(self, doi: str) -> str:
        """
        DOI文字列を正規化
        
        Args:
            doi: 元のDOI文字列
            
        Returns:
            正規化されたDOI文字列（小文字変換、プレフィックス除去等）
        """
        if not doi:
            return ""
        
        # 小文字変換
        normalized = doi.lower().strip()
        
        # プレフィックス除去
        if normalized.startswith('doi:'):
            normalized = normalized[4:].strip()
        elif normalized.startswith('https://doi.org/'):
            normalized = normalized[16:].strip()
        elif normalized.startswith('http://doi.org/'):
            normalized = normalized[15:].strip()
        
        return normalized
    
    def validate_doi_format(self, doi: str) -> bool:
        """
        DOI形式の妥当性を検証
        
        Args:
            doi: 検証対象のDOI文字列
            
        Returns:
            True: 有効なDOI形式, False: 無効
        """
        if not doi:
            return False
        
        # 基本的なDOIパターンをチェック
        # 例: 10.1000/123456
        doi_pattern = r'^10\.\d{4,}/[-._;()/:\w\[\]]+$'
        
        normalized_doi = self.normalize_doi(doi)
        return bool(re.match(doi_pattern, normalized_doi))
    
    def process_matched_file(self, file_path: str, citation_key: str, bib_entry: Dict) -> bool:
        """
        マッチしたファイルの後処理（タイトル同期等）
        
        Args:
            file_path: Markdownファイルパス
            citation_key: マッチしたcitation_key
            bib_entry: 対応するBibTeX項目
            
        Returns:
            True: 処理成功, False: 処理失敗
        """
        try:
            # タイトル同期が有効な場合
            if self.title_sync_enabled:
                bib_title = bib_entry.get('title', '')
                if bib_title:
                    return self._sync_title_with_bibtex(file_path, bib_title)
            return True
        except Exception as e:
            self.logger.error(f"Error processing matched file {file_path}: {e}")
            return False
    
    def _sync_title_with_bibtex(self, file_path: str, bib_title: str) -> bool:
        """
        MarkdownファイルのtitleをBibTeXのtitleと同期
        
        Args:
            file_path: 対象のMarkdownファイルパス
            bib_title: BibTeXのtitleフィールド値
            
        Returns:
            True: 同期成功, False: 同期失敗またはスキップ
        """
        try:
            # 現在のタイトルを取得
            current_frontmatter = self._parse_yaml_frontmatter(file_path)
            if not current_frontmatter:
                return False
            
            current_title = current_frontmatter.get('title', '')
            
            # タイトル比較
            if self._compare_titles(current_title, bib_title):
                self.logger.debug(f"Title already synchronized: {file_path}")
                return True
            
            # タイトルを更新
            current_frontmatter['title'] = bib_title
            return self._update_yaml_frontmatter(file_path, current_frontmatter)
            
        except Exception as e:
            self.logger.error(f"Error synchronizing title for {file_path}: {e}")
            return False
    
    def _parse_yaml_frontmatter(self, file_path: str) -> Optional[Dict]:
        """
        MarkdownファイルのYAML frontmatterを解析
        
        Args:
            file_path: 解析対象のMarkdownファイルパス
            
        Returns:
            解析されたYAMLデータの辞書
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.startswith('---'):
                return {}
            
            parts = content.split('---', 2)
            if len(parts) < 3:
                return {}
            
            yaml_content = parts[1].strip()
            return yaml.safe_load(yaml_content) or {}
            
        except Exception as e:
            self.logger.error(f"Error parsing YAML frontmatter in {file_path}: {e}")
            return None
    
    def _update_yaml_frontmatter(self, file_path: str, updates: Dict) -> bool:
        """
        MarkdownファイルのYAML frontmatterを更新
        
        Args:
            file_path: 更新対象のMarkdownファイルパス
            updates: 更新するYAMLデータ
            
        Returns:
            True: 更新成功, False: 更新失敗
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.startswith('---'):
                # YAML frontmatterが存在しない場合は追加
                yaml_content = yaml.dump(updates, default_flow_style=False, allow_unicode=True)
                new_content = f"---\n{yaml_content}---\n\n{content}"
            else:
                parts = content.split('---', 2)
                if len(parts) < 3:
                    return False
                
                # 新しいYAMLを生成
                yaml_content = yaml.dump(updates, default_flow_style=False, allow_unicode=True)
                new_content = f"---\n{yaml_content}---{parts[2]}"
            
            # ファイルを更新
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.logger.info(f"Updated YAML frontmatter: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating YAML frontmatter in {file_path}: {e}")
            return False
    
    def _compare_titles(self, md_title: str, bib_title: str) -> bool:
        """
        MarkdownとBibTeXのタイトルを比較
        
        Args:
            md_title: Markdownのtitleフィールド
            bib_title: BibTeXのtitleフィールド
            
        Returns:
            True: タイトルが一致, False: タイトルが異なる
        """
        if not md_title or not bib_title:
            return False
        
        # 正規化して比較
        normalized_md = self._normalize_title_for_comparison(md_title)
        normalized_bib = self._normalize_title_for_comparison(bib_title)
        
        return normalized_md == normalized_bib
    
    def _normalize_title_for_comparison(self, title: str) -> str:
        """
        タイトル比較用の正規化
        
        Args:
            title: 正規化対象のタイトル
            
        Returns:
            正規化されたタイトル
        """
        if not title:
            return ""
        
        # 前後空白の除去
        normalized = title.strip()
        
        # BibTeX特殊記号の除去
        normalized = re.sub(r'[{}]', '', normalized)
        
        # 改行文字の正規化
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()


# 便利関数
def match_files_to_citations(md_files: List[str], 
                           bib_entries: Dict[str, Dict[str, str]],
                           threshold: float = 0.8) -> Dict[str, str]:
    """
    Markdownファイルと最適なBibTeX項目を照合（簡易版）
    
    Args:
        md_files: Markdownファイルパスのリスト
        bib_entries: BibTeX項目の辞書
        threshold: 類似度閾値
        
    Returns:
        Dict[ファイルパス, citation_key] の照合結果
    """
    matcher = FileMatcher(similarity_threshold=threshold)
    return matcher.match_files_to_citations(md_files, bib_entries)


def calculate_similarity(filename: str, title: str, case_sensitive: bool = False) -> float:
    """
    ファイル名とタイトルの類似度を計算（簡易版）
    
    Args:
        filename: Markdownファイル名（拡張子なし）
        title: BibTeX titleフィールド
        case_sensitive: 大文字小文字を区別するか
        
    Returns:
        類似度スコア (0.0-1.0)
    """
    matcher = FileMatcher(case_sensitive=case_sensitive)
    return matcher.calculate_similarity(filename, title)


def normalize_for_matching(text: str) -> str:
    """
    照合用にテキストを正規化
    - 特殊文字除去
    - 小文字変換
    - 空白正規化
    
    Args:
        text: 正規化対象テキスト
        
    Returns:
        正規化されたテキスト
    """
    # 共通の正規化関数を使用
    normalized = normalize_text_for_comparison(text)
    
    # LaTeX記法やBibTeX特有の文字を追加で除去
    normalized = normalized.replace('{', '').replace('}', '')
    normalized = normalized.replace('\\', '')
    normalized = normalized.replace('--', '-')
    
    return normalized 