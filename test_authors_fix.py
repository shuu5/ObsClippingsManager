#!/usr/bin/env python3
"""
著者情報修正のテスト用スクリプト
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code', 'py'))

from modules.citation_fetcher.reference_formatter import ReferenceFormatter

def test_authors_formatting():
    """著者情報のフォーマット処理をテスト"""
    
    formatter = ReferenceFormatter()
    
    # Semantic Scholar形式のテストデータ
    test_reference_semantic = {
        'title': 'A Proteomics Analysis of Cell Signaling Alterations in Colorectal Cancer*S',
        'authors': ['J. Madoz-Gúrpide', 'M. Cañamero', 'L. Sánchez', 'J. Solano', 'P. Alfonso', 'J. Casal'],
        'journal': 'Molecular & Cellular Proteomics',
        'year': '2007',
        'doi': '10.1074/mcp.M700006-MCP200',
        'source': 'semantic_scholar'
    }
    
    # OpenAlex形式のテストデータ
    test_reference_openalex = {
        'title': 'A Proteomics Analysis of Cell Signaling Alterations in Colorectal Cancer',
        'authors': ['Juan Madoz‐Gúrpide', 'Marta Cañamero', 'Lydia Sánchez', 'José D. Solano', 'Patricia Alfonso', 'J. Ignacio Casal'],
        'year': '2007',
        'doi': '10.1074/mcp.M700006-MCP200',
        'source': 'openalex'
    }
    
    print("=== Authors Formatting Test ===")
    
    print("\n--- Semantic Scholar データ ---")
    authors_ss = formatter._format_authors_for_bibtex(test_reference_semantic)
    print(f"Authors field: {test_reference_semantic.get('authors')}")
    print(f"Formatted: {authors_ss}")
    
    print("\n--- OpenAlex データ ---") 
    authors_oa = formatter._format_authors_for_bibtex(test_reference_openalex)
    print(f"Authors field: {test_reference_openalex.get('authors')}")
    print(f"Formatted: {authors_oa}")
    
    print("\n--- BibTeX生成テスト ---")
    bibtex_ss = formatter._convert_reference_to_bibtex(test_reference_semantic)
    print("Semantic Scholar BibTeX:")
    print(bibtex_ss)
    
    print("\n" + "="*60)
    bibtex_oa = formatter._convert_reference_to_bibtex(test_reference_openalex)
    print("OpenAlex BibTeX:")
    print(bibtex_oa)

if __name__ == "__main__":
    test_authors_formatting() 