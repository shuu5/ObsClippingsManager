#!/usr/bin/env python3
"""
筆頭著者のみを抽出する実装のテスト用スクリプト
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code', 'py'))

from modules.citation_fetcher.metadata_enricher import MetadataEnricher
from modules.citation_fetcher.semantic_scholar_client import SemanticScholarMetadata
from modules.citation_fetcher.openalex_client import OpenAlexMetadata
from modules.citation_fetcher.reference_formatter import ReferenceFormatter

def test_first_author_extraction():
    """筆頭著者のみを抽出する処理をテスト"""
    
    enricher = MetadataEnricher()
    formatter = ReferenceFormatter()
    
    # Semantic Scholar形式のテストデータ
    ss_metadata = SemanticScholarMetadata()
    ss_metadata.title = 'A Proteomics Analysis of Cell Signaling Alterations in Colorectal Cancer*S'
    ss_metadata.authors = ['J. Madoz-Gúrpide', 'M. Cañamero', 'L. Sánchez', 'J. Solano', 'P. Alfonso', 'J. Casal']
    ss_metadata.journal = 'Molecular & Cellular Proteomics'
    ss_metadata.year = '2007'
    ss_metadata.doi = '10.1074/mcp.M700006-MCP200'
    
    # OpenAlex形式のテストデータ
    oa_metadata = OpenAlexMetadata()
    oa_metadata.title = 'A Proteomics Analysis of Cell Signaling Alterations in Colorectal Cancer'
    oa_metadata.authors = ['Juan Madoz‐Gúrpide', 'Marta Cañamero', 'Lydia Sánchez', 'José D. Solano', 'Patricia Alfonso', 'J. Ignacio Casal']
    oa_metadata.journal = None  # OpenAlexではjournal情報が欠損
    oa_metadata.year = '2007'
    oa_metadata.doi = '10.1074/mcp.M700006-MCP200'
    
    print("=== 筆頭著者抽出テスト ===")
    
    print("\n--- Semantic Scholar データ正規化 ---")
    ss_normalized = enricher._normalize_metadata(ss_metadata, 'semantic_scholar')
    print(f"元の authors: {ss_metadata.authors}")
    print(f"正規化後の author: {ss_normalized.get('author')}")
    print(f"完全性チェック: {enricher._is_complete_metadata(ss_normalized)}")
    
    print("\n--- OpenAlex データ正規化 ---")
    oa_normalized = enricher._normalize_metadata(oa_metadata, 'openalex')
    print(f"元の authors: {oa_metadata.authors}")
    print(f"正規化後の author: {oa_normalized.get('author')}")
    print(f"完全性チェック: {enricher._is_complete_metadata(oa_normalized)}")
    
    print("\n--- BibTeX生成テスト ---")
    print("Semantic Scholar BibTeX:")
    bibtex_ss = formatter._convert_reference_to_bibtex(ss_normalized)
    print(bibtex_ss)
    
    print("\n" + "="*60)
    print("OpenAlex BibTeX:")
    bibtex_oa = formatter._convert_reference_to_bibtex(oa_normalized)
    print(bibtex_oa)
    
    print("\n--- API統一性確認 ---")
    
    # CrossRef形式（従来通り）
    crossref_data = {
        'title': 'Test Article',
        'author': 'Smith, John',  # 単一著者
        'journal': 'Test Journal',
        'year': '2020',
        'doi': '10.1000/test'
    }
    
    print("CrossRef形式（従来通り）:")
    print(f"author フィールド: {crossref_data.get('author')}")
    
    crossref_normalized = enricher._normalize_metadata(crossref_data, 'crossref')
    print(f"正規化後: {crossref_normalized.get('author')}")
    print(f"完全性チェック: {enricher._is_complete_metadata(crossref_normalized)}")

if __name__ == "__main__":
    test_first_author_extraction() 