"""
引用リンク抽出エンジン

リンク付き引用からURLを抽出し、対応表を生成する
"""

import re
import logging
from typing import List, Tuple, Dict, Optional
from urllib.parse import urlparse, urljoin

from .data_structures import CitationMatch, LinkEntry, ProcessingError
from .exceptions import LinkExtractionError


class LinkExtractor:
    """引用リンク抽出エンジン"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger("ObsClippingsManager.CitationParser.LinkExtractor")
        self.link_cache = {}  # URLキャッシュ
    
    def extract_links(self, text: str, matches: List[CitationMatch]) -> Tuple[str, List[LinkEntry]]:
        """
        リンク付き引用を処理し、テキストとリンク表を返す
        
        Args:
            text: 元のテキスト
            matches: 検出された引用マッチ
            
        Returns:
            (クリーンなテキスト, リンクエントリリスト)
        """
        link_entries = []
        clean_text = text
        errors = []
        
        # リンク付き引用のみをフィルタ
        linked_matches = [match for match in matches if match.has_link and match.link_url]
        
        if not linked_matches:
            return text, []
        
        # 位置を逆順でソート（後ろから処理して位置ずれを防ぐ）
        sorted_matches = sorted(linked_matches, key=lambda x: x.start_pos, reverse=True)
        
        for match in sorted_matches:
            try:
                # 複数の引用番号がある場合は、それぞれに対してリンクエントリを作成
                for citation_number in match.citation_numbers:
                    link_entry = self._create_link_entry_for_number(match, citation_number)
                    link_entries.append(link_entry)
                
                # テキストからリンクを除去
                clean_citation = self._remove_link_from_citation(match.original_text)
                clean_text = (
                    clean_text[:match.start_pos] +
                    clean_citation +
                    clean_text[match.end_pos:]
                )
                
            except Exception as e:
                self.logger.warning(f"Failed to extract link: {match.original_text} - {e}")
                errors.append(ProcessingError(
                    error_type="LINK_EXTRACTION_ERROR",
                    message=str(e),
                    position=match.start_pos,
                    original_text=match.original_text
                ))
        
        # 引用番号順にソート
        link_entries.sort(key=lambda x: x.citation_number)
        
        self.logger.info(f"Extracted {len(link_entries)} links")
        return clean_text, link_entries
    
    def _create_link_entry(self, match: CitationMatch) -> LinkEntry:
        """
        CitationMatchからLinkEntryを作成（後方互換性のため）
        
        Args:
            match: 引用マッチ
            
        Returns:
            LinkEntry
        """
        if not match.citation_numbers:
            raise LinkExtractionError("Citation match has no citation numbers")
        
        # 複数の引用番号がある場合は最初のものを使用
        citation_number = match.citation_numbers[0]
        return self._create_link_entry_for_number(match, citation_number)
    
    def _create_link_entry_for_number(self, match: CitationMatch, citation_number: int) -> LinkEntry:
        """
        特定の引用番号に対してLinkEntryを作成
        
        Args:
            match: 引用マッチ
            citation_number: 対象の引用番号
            
        Returns:
            LinkEntry
        """
        if not match.has_link or not match.link_url:
            raise LinkExtractionError("Citation match does not have a link")
        
        # URLを正規化
        normalized_url = self._normalize_url(match.link_url)
        
        # URLの妥当性チェック
        if not self._validate_url(normalized_url):
            raise LinkExtractionError(f"Invalid URL: {normalized_url}")
        
        # 表示テキストを生成
        display_text = self._generate_display_text(normalized_url)
        
        return LinkEntry(
            citation_number=citation_number,
            url=normalized_url,
            display_text=display_text
        )
    
    def _remove_link_from_citation(self, citation_text: str) -> str:
        """
        引用テキストからリンク部分を除去
        
        Args:
            citation_text: 元の引用テキスト
            
        Returns:
            リンクが除去された引用テキスト
        """
        # エスケープされたパターンを優先的に処理
        # \[[4–8](URL)\] -> \[[4–8]\]
        escaped_link_pattern = r'\\\[\[([^\]]+)\]\([^)]+\)\\\]'
        
        def replace_escaped(match):
            content = match.group(1)  # 4–8 or ^1,^2,^3
            return f"\\[[{content}]\\]"
        
        result = re.sub(escaped_link_pattern, replace_escaped, citation_text)
        
        # 通常のパターンも処理
        # [1](URL) -> [1]
        normal_link_pattern = r'\[(\^?\d+)\]\([^)]+\)'
        result = re.sub(normal_link_pattern, r'[\1]', result)
        
        return result
    
    def _normalize_url(self, url: str) -> str:
        """
        URLを正規化
        
        Args:
            url: 元のURL
            
        Returns:
            正規化されたURL
        """
        url = url.strip()
        
        # プロトコルが無い場合はhttpsを追加
        if not url.startswith(('http://', 'https://', 'ftp://')):
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('www.'):
                url = 'https://' + url
            else:
                # DOI等の特殊な場合を考慮
                if url.startswith('10.'):  # DOI pattern
                    url = 'https://doi.org/' + url
                else:
                    url = 'https://' + url
        
        # フラグメント識別子を保持
        return url
    
    def _validate_url(self, url: str) -> bool:
        """
        URLの妥当性を検証
        
        Args:
            url: 検証対象URL
            
        Returns:
            妥当性
        """
        try:
            parsed = urlparse(url)
            
            # 基本的な要件チェック
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # 許可されたスキーム
            allowed_schemes = {'http', 'https', 'ftp'}
            if parsed.scheme.lower() not in allowed_schemes:
                return False
            
            # 明らかに無効なドメイン
            if parsed.netloc.lower() in {'localhost', '127.0.0.1', '0.0.0.0'}:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _generate_display_text(self, url: str) -> str:
        """
        URLから表示テキストを生成
        
        Args:
            url: URL
            
        Returns:
            表示テキスト
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # よく知られたドメインの場合は短縮名を使用
            domain_shortcuts = {
                'www.ncbi.nlm.nih.gov': 'PubMed',
                'pubmed.ncbi.nlm.nih.gov': 'PubMed',
                'academic.oup.com': 'Oxford Academic',
                'www.nature.com': 'Nature',
                'www.sciencedirect.com': 'ScienceDirect',
                'onlinelibrary.wiley.com': 'Wiley Online Library',
                'link.springer.com': 'Springer',
                'journals.plos.org': 'PLOS',
                'doi.org': 'DOI',
                'dx.doi.org': 'DOI'
            }
            
            if domain in domain_shortcuts:
                return domain_shortcuts[domain]
            
            # ドメインを簡略化
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain.title()
            
        except Exception:
            return "Link"
    
    def generate_link_table_markdown(self, link_entries: List[LinkEntry]) -> str:
        """
        リンク対応表のMarkdownを生成
        
        Args:
            link_entries: リンクエントリリスト
            
        Returns:
            Markdown形式のリンク対応表
        """
        if not link_entries:
            return ""
        
        lines = [
            "## 引用文献リンク対応表",
            "",
            "| 引用番号 | URL | 説明 |",
            "|---------|-----|------|"
        ]
        
        for entry in sorted(link_entries, key=lambda x: x.citation_number):
            citation_display = f"[{entry.citation_number}]"
            url_display = f"[{entry.display_text or 'Link'}]({entry.url})"
            description = self._generate_url_description(entry.url)
            
            lines.append(f"| {citation_display} | {url_display} | {description} |")
        
        return "\n".join(lines)
    
    def _generate_url_description(self, url: str) -> str:
        """
        URLから説明テキストを生成
        
        Args:
            url: URL
            
        Returns:
            説明テキスト
        """
        try:
            parsed = urlparse(url)
            
            # DOIの場合
            if 'doi.org' in parsed.netloc:
                return "DOI (デジタルオブジェクト識別子)"
            
            # PubMedの場合
            if 'pubmed' in parsed.netloc or 'ncbi.nlm.nih.gov' in parsed.netloc:
                return "PubMed (医学文献データベース)"
            
            # 一般的な学術サイト
            academic_sites = {
                'nature.com': 'Nature Publishing Group',
                'sciencedirect.com': 'ScienceDirect (Elsevier)',
                'springer.com': 'Springer',
                'wiley.com': 'Wiley Online Library',
                'oup.com': 'Oxford University Press',
                'plos.org': 'PLOS (Public Library of Science)'
            }
            
            for site, description in academic_sites.items():
                if site in parsed.netloc:
                    return description
            
            return "外部リンク"
            
        except Exception:
            return "外部リンク"
    
    def deduplicate_links(self, link_entries: List[LinkEntry]) -> List[LinkEntry]:
        """
        重複するリンクを除去
        
        Args:
            link_entries: リンクエントリリスト
            
        Returns:
            重複除去されたリンクエントリリスト
        """
        seen_urls = set()
        deduplicated = []
        
        for entry in link_entries:
            normalized_url = self._normalize_url(entry.url)
            
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                # 正規化されたURLで更新
                entry.url = normalized_url
                deduplicated.append(entry)
            else:
                self.logger.debug(f"Duplicate URL removed: {normalized_url}")
        
        return deduplicated
    
    def validate_link_entries(self, link_entries: List[LinkEntry]) -> List[ProcessingError]:
        """
        リンクエントリの妥当性を検証
        
        Args:
            link_entries: リンクエントリリスト
            
        Returns:
            検証エラーのリスト
        """
        errors = []
        
        for entry in link_entries:
            # 引用番号の妥当性
            if entry.citation_number <= 0:
                errors.append(ProcessingError(
                    error_type="INVALID_CITATION_NUMBER",
                    message=f"Invalid citation number: {entry.citation_number}"
                ))
            
            # URLの妥当性
            if not self._validate_url(entry.url):
                errors.append(ProcessingError(
                    error_type="INVALID_URL",
                    message=f"Invalid URL: {entry.url}"
                ))
        
        return errors 