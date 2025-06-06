#!/usr/bin/env python3
"""
CrossRef and OpenCitations API Test Script

このスクリプトは以下の機能をテストします：
1. .bibファイルから論文DOIを読み込み
2. CrossRef APIで引用文献を取得
3. OpenCitations APIで引用文献を取得
4. 取得したデータを.bibファイル形式で出力
"""

import requests
import bibtexparser
import json
import time
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any
import urllib.parse

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CitationFetcher:
    def __init__(self):
        # CrossRef API設定
        self.crossref_base_url = "https://api.crossref.org"
        self.crossref_headers = {
            'User-Agent': 'CitationFetcher/1.0 (mailto:test@example.com)'
        }
        
        # OpenCitations API設定
        self.opencitations_base_url = "https://opencitations.net/index/coci/api/v1"
        
        # APIリクエストの間隔（秒）
        self.request_delay = 1.0
        
    def load_bib_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        .bibファイルを読み込んでパースする
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as bib_file:
                bib_database = bibtexparser.load(bib_file)
                logger.info(f"Loaded {len(bib_database.entries)} entries from {file_path}")
                return bib_database.entries
        except Exception as e:
            logger.error(f"Error loading bib file {file_path}: {e}")
            return []
    
    def extract_dois(self, bib_entries: List[Dict[str, Any]]) -> List[str]:
        """
        .bibエントリからDOIを抽出する
        """
        dois = []
        for entry in bib_entries:
            doi = entry.get('doi', '').strip()
            if doi:
                # DOIの形式を正規化（10.から始まる部分のみ抽出）
                if doi.startswith('http'):
                    doi = doi.split('/')[-2] + '/' + doi.split('/')[-1]
                if doi.startswith('10.'):
                    dois.append(doi)
                    logger.info(f"Found DOI: {doi} from entry: {entry.get('ID', 'unknown')}")
        return dois
    
    def get_crossref_references(self, doi: str) -> List[Dict[str, Any]]:
        """
        CrossRef APIを使用して引用文献を取得する
        """
        try:
            # DOIをURLエンコード
            encoded_doi = urllib.parse.quote(doi, safe='')
            url = f"{self.crossref_base_url}/works/{encoded_doi}"
            
            logger.info(f"Requesting CrossRef data for DOI: {doi}")
            response = requests.get(url, headers=self.crossref_headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                work = data.get('message', {})
                references = work.get('reference', [])
                logger.info(f"Found {len(references)} references via CrossRef for {doi}")
                return references
            else:
                logger.warning(f"CrossRef API returned status {response.status_code} for {doi}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching CrossRef references for {doi}: {e}")
            return []
        finally:
            time.sleep(self.request_delay)
    
    def get_opencitations_references(self, doi: str) -> List[Dict[str, Any]]:
        """
        OpenCitations APIを使用して引用文献を取得する
        複数のエンドポイントを試してより堅牢にする
        """
        endpoints = [
            f"{self.opencitations_base_url}/references/{doi}",
            f"https://opencitations.net/index/api/v1/references/{doi}",
            f"https://w3id.org/oc/index/coci/api/v1/references/{doi}"
        ]
        
        for i, url in enumerate(endpoints):
            try:
                # DOIをURLエンコード
                encoded_doi = urllib.parse.quote(doi, safe='')
                formatted_url = url.replace(doi, encoded_doi)
                
                logger.info(f"Requesting OpenCitations data from endpoint {i+1}: {formatted_url}")
                response = requests.get(formatted_url, timeout=30)
                
                if response.status_code == 200:
                    try:
                        references = response.json()
                        if isinstance(references, list) and len(references) > 0:
                            # デバッグ用：最初の数件のデータ構造を確認
                            logger.info(f"Sample OpenCitations data structure: {references[:2]}")
                            logger.info(f"Found {len(references)} references via OpenCitations (endpoint {i+1}) for {doi}")
                            return references
                        else:
                            logger.info(f"Empty response from OpenCitations endpoint {i+1} for {doi}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error from OpenCitations endpoint {i+1}: {e}")
                elif response.status_code == 404:
                    logger.info(f"OpenCitations endpoint {i+1} returned 404 (not found) for {doi}")
                else:
                    logger.warning(f"OpenCitations endpoint {i+1} returned status {response.status_code} for {doi}")
                    
            except Exception as e:
                logger.error(f"Error fetching from OpenCitations endpoint {i+1} for {doi}: {e}")
            
            time.sleep(self.request_delay)
        
        logger.warning(f"All OpenCitations endpoints failed for {doi}")
        return []
    
    def crossref_to_bibtex(self, reference: Dict[str, Any], entry_id: str) -> str:
        """
        CrossRefの引用データをBibTeX形式に変換する
        """
        bib_entry = f"@article{{{entry_id},\n"
        
        # タイトル
        if 'article-title' in reference:
            title = reference['article-title'].replace('{', '').replace('}', '')
            bib_entry += f"  title = {{{title}}},\n"
        
        # 著者
        if 'author' in reference:
            authors = reference['author']
            if isinstance(authors, str):
                bib_entry += f"  author = {{{authors}}},\n"
        
        # ジャーナル
        if 'journal-title' in reference:
            journal = reference['journal-title']
            bib_entry += f"  journal = {{{journal}}},\n"
        
        # 年
        if 'year' in reference:
            bib_entry += f"  year = {{{reference['year']}}},\n"
        
        # ボリューム
        if 'volume' in reference:
            bib_entry += f"  volume = {{{reference['volume']}}},\n"
        
        # ページ
        if 'first-page' in reference:
            pages = reference['first-page']
            if 'last-page' in reference:
                pages += f"--{reference['last-page']}"
            bib_entry += f"  pages = {{{pages}}},\n"
        
        # DOI
        if 'DOI' in reference:
            bib_entry += f"  doi = {{{reference['DOI']}}},\n"
        
        bib_entry += "}\n\n"
        return bib_entry
    
    def opencitations_to_bibtex(self, reference: Dict[str, Any], entry_id: str) -> str:
        """
        OpenCitationsの引用データをBibTeX形式に変換する
        OpenCitationsは主にDOIのみを提供するため、cited DOIからCrossRefでメタデータを取得
        """
        cited_doi = reference.get('cited', '')
        if not cited_doi:
            return f"@article{{{entry_id},\n  note = {{No DOI available}},\n}}\n\n"
        
        # 簡単なキャッシュ機能（同じDOIのメタデータを重複取得しない）
        if not hasattr(self, '_citation_cache'):
            self._citation_cache = {}
            
        if cited_doi in self._citation_cache:
            crossref_data = self._citation_cache[cited_doi]
        else:
            # CrossRef APIから引用文献のメタデータを取得
            try:
                encoded_doi = urllib.parse.quote(cited_doi, safe='')
                url = f"{self.crossref_base_url}/works/{encoded_doi}"
                response = requests.get(url, headers=self.crossref_headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    crossref_data = data.get('message', {})
                    self._citation_cache[cited_doi] = crossref_data
                else:
                    crossref_data = {}
                    self._citation_cache[cited_doi] = {}
                    
                time.sleep(0.5)  # 短い間隔でリクエスト
                
            except Exception as e:
                logger.debug(f"Failed to get metadata for cited DOI {cited_doi}: {e}")
                crossref_data = {}
                
        # BibTeX エントリを構築
        bib_entry = f"@article{{{entry_id},\n"
        
        # タイトル
        title = crossref_data.get('title', ['Unknown Title'])[0] if crossref_data.get('title') else 'Unknown Title'
        bib_entry += f"  title = {{{title}}},\n"
        
        # 著者
        authors = crossref_data.get('author', [])
        if authors:
            author_names = []
            for author in authors[:3]:  # 最初の3人の著者のみ
                given = author.get('given', '')
                family = author.get('family', '')
                if family:
                    if given:
                        author_names.append(f"{family}, {given}")
                    else:
                        author_names.append(family)
            if len(authors) > 3:
                author_names.append("and others")
            author_str = " and ".join(author_names)
            bib_entry += f"  author = {{{author_str}}},\n"
        
        # ジャーナル
        container_title = crossref_data.get('container-title', [])
        if container_title:
            journal = container_title[0]
            bib_entry += f"  journal = {{{journal}}},\n"
        
        # 年
        published = crossref_data.get('published-print') or crossref_data.get('published-online')
        if published and 'date-parts' in published:
            year = published['date-parts'][0][0]
            bib_entry += f"  year = {{{year}}},\n"
        
        # ボリューム
        volume = crossref_data.get('volume')
        if volume:
            bib_entry += f"  volume = {{{volume}}},\n"
        
        # 号
        issue = crossref_data.get('issue')
        if issue:
            bib_entry += f"  number = {{{issue}}},\n"
        
        # ページ
        page = crossref_data.get('page')
        if page:
            bib_entry += f"  pages = {{{page}}},\n"
        
        # DOI
        bib_entry += f"  doi = {{{cited_doi}}},\n"
        
        # OpenCitations固有の情報
        if 'creation' in reference:
            bib_entry += f"  note = {{OpenCitations creation date: {reference['creation']}}},\n"
        
        bib_entry += "}\n\n"
        return bib_entry
    
    def save_references_as_bib(self, references: List[str], output_file: str, source_api: str):
        """
        引用文献リストを.bibファイルとして保存する
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"% Generated by CitationFetcher using {source_api} API\n")
                f.write(f"% Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for ref in references:
                    f.write(ref)
            logger.info(f"Saved {len(references)} references to {output_file}")
        except Exception as e:
            logger.error(f"Error saving references to {output_file}: {e}")

def main():
    """
    メイン実行関数
    """
    logger.info("Starting Citation Fetcher Test")
    
    # 設定
    input_bib_file = "/home/user/ManuscriptsManager/CurrentManuscript.bib"
    output_dir = Path("code/playground/output")
    output_dir.mkdir(exist_ok=True)
    
    # CitationFetcherインスタンス作成
    fetcher = CitationFetcher()
    
    # 1. .bibファイルを読み込み
    logger.info("Step 1: Loading bib file")
    bib_entries = fetcher.load_bib_file(input_bib_file)
    if not bib_entries:
        logger.error("No entries found in bib file")
        return
    
    # 2. DOIを抽出
    logger.info("Step 2: Extracting DOIs")
    dois = fetcher.extract_dois(bib_entries)
    if not dois:
        logger.error("No DOIs found in bib entries")
        return
    
    logger.info(f"Found {len(dois)} DOIs to process")
    
    # 3. 最初のDOIを使用してテスト（すべて処理する場合は後で変更可能）
    test_doi = dois[1]  # 2番目のDOIに変更
    logger.info(f"Testing with DOI: {test_doi}")
    
    # 4. CrossRef APIで引用文献を取得
    logger.info("Step 3: Fetching references via CrossRef API")
    crossref_refs = fetcher.get_crossref_references(test_doi)
    
    if crossref_refs:
        # CrossRefデータをBibTeX形式に変換
        crossref_bibtex = []
        for i, ref in enumerate(crossref_refs):
            entry_id = f"crossref_ref_{i+1:03d}"
            bibtex_entry = fetcher.crossref_to_bibtex(ref, entry_id)
            crossref_bibtex.append(bibtex_entry)
        
        # 保存
        crossref_output = output_dir / f"crossref_references_{test_doi.replace('/', '_')}.bib"
        fetcher.save_references_as_bib(crossref_bibtex, str(crossref_output), "CrossRef")
    
    # 5. OpenCitations APIで引用文献を取得
    logger.info("Step 4: Fetching references via OpenCitations API")
    opencitations_refs = fetcher.get_opencitations_references(test_doi)
    
    if opencitations_refs:
        # OpenCitationsデータをBibTeX形式に変換
        opencitations_bibtex = []
        for i, ref in enumerate(opencitations_refs):
            entry_id = f"opencitations_ref_{i+1:03d}"
            bibtex_entry = fetcher.opencitations_to_bibtex(ref, entry_id)
            opencitations_bibtex.append(bibtex_entry)
        
        # 保存
        opencitations_output = output_dir / f"opencitations_references_{test_doi.replace('/', '_')}.bib"
        fetcher.save_references_as_bib(opencitations_bibtex, str(opencitations_output), "OpenCitations")
    
    # 6. 結果レポート
    logger.info("\n" + "="*60)
    logger.info("CITATION FETCHER TEST RESULTS")
    logger.info("="*60)
    logger.info(f"Source bib file: {input_bib_file}")
    logger.info(f"Total DOIs found: {len(dois)}")
    logger.info(f"Test DOI: {test_doi}")
    logger.info(f"CrossRef references found: {len(crossref_refs)}")
    logger.info(f"OpenCitations references found: {len(opencitations_refs)}")
    
    if crossref_refs:
        logger.info(f"CrossRef output saved to: {crossref_output}")
    else:
        logger.info("No CrossRef references were obtained")
    
    if opencitations_refs:
        logger.info(f"OpenCitations output saved to: {opencitations_output}")
    else:
        logger.info("No OpenCitations references were obtained")
    
    logger.info("="*60)

if __name__ == "__main__":
    main()
