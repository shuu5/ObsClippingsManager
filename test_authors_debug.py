#!/usr/bin/env python3
"""
著者情報取得のデバッグ用スクリプト
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code', 'py'))

from modules.citation_fetcher.crossref_client import CrossRefClient
from modules.citation_fetcher.semantic_scholar_client import SemanticScholarClient
from modules.citation_fetcher.openalex_client import OpenAlexClient
from modules.shared.config_manager import ConfigManager

def test_doi_authors(doi):
    """指定されたDOIで各APIクライアントの著者情報取得をテスト"""
    print(f"\n=== Testing DOI: {doi} ===")
    
    config = ConfigManager()
    
    # CrossRef
    print("\n--- CrossRef ---")
    try:
        crossref_client = CrossRefClient()
        metadata = crossref_client.get_metadata_by_doi(doi)
        if metadata:
            print(f"Title: {metadata.get('title', 'N/A')}")
            print(f"Authors: {metadata.get('authors', 'N/A')}")
            print(f"Journal: {metadata.get('journal', 'N/A')}")
            print(f"Year: {metadata.get('year', 'N/A')}")
        else:
            print("No metadata found")
    except Exception as e:
        print(f"Error: {e}")
    
    # Semantic Scholar
    print("\n--- Semantic Scholar ---")
    try:
        ss_client = SemanticScholarClient(config)
        metadata = ss_client.get_metadata_by_doi(doi)
        if metadata:
            print(f"Title: {metadata.title}")
            print(f"Authors: {metadata.authors}")
            print(f"Journal: {metadata.journal}")
            print(f"Year: {metadata.year}")
        else:
            print("No metadata found")
    except Exception as e:
        print(f"Error: {e}")
    
    # OpenAlex
    print("\n--- OpenAlex ---")
    try:
        openalex_client = OpenAlexClient(config)
        metadata = openalex_client.get_metadata_by_doi(doi)
        if metadata:
            print(f"Title: {metadata.title}")
            print(f"Authors: {metadata.authors}")
            print(f"Journal: {metadata.journal}")
            print(f"Year: {metadata.year}")
        else:
            print("No metadata found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # PubMedで失敗したDOIをテスト
    test_dois = [
        "10.1074/mcp.M700006-MCP200",
        "10.1097/01.MP.0000067683.84284.66"
    ]
    
    for doi in test_dois:
        test_doi_authors(doi)
        print("\n" + "="*80) 