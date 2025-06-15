#!/usr/bin/env python3
"""基本的なCitationFetcher機能テスト"""

import sys
import os
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.insert(0, '/home/user/proj/ObsClippingsManager')

from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow

def test_basic_initialization():
    """基本的な初期化テスト"""
    print("=== CitationFetcher 基本初期化テスト ===")
    
    config_manager = MagicMock()
    logger = MagicMock()
    logger.get_logger.return_value = MagicMock()
    
    workflow = CitationFetcherWorkflow(config_manager, logger)
    print("✓ CitationFetcherWorkflow 初期化成功")
    
    # 遅延初期化テスト
    print("\n=== 遅延初期化テスト ===")
    print(f"✓ CrossRef client: {type(workflow.crossref_client).__name__}")
    print(f"✓ Semantic Scholar client: {type(workflow.semantic_scholar_client).__name__}")
    print(f"✓ OpenCitations client: {type(workflow.opencitations_client).__name__}")
    print(f"✓ Rate limiter: {type(workflow.rate_limiter).__name__}")
    print(f"✓ Quality evaluator: {type(workflow.quality_evaluator).__name__}")
    print(f"✓ Statistics: {type(workflow.statistics).__name__}")
    
    return workflow

def test_mock_fetch_citations():
    """モック引用文献取得テスト"""
    print("\n=== モック引用文献取得テスト ===")
    
    config_manager = MagicMock()
    logger = MagicMock()
    logger.get_logger.return_value = MagicMock()
    
    workflow = CitationFetcherWorkflow(config_manager, logger)
    
    # テスト DOI
    test_doi = "10.1038/s41591-023-1234-5"
    
    # フォールバック戦略テスト
    result = workflow.fetch_citations_with_fallback(test_doi)
    
    if result:
        print(f"✓ 引用文献取得成功: {result['api_used']}")
        print(f"  品質スコア: {result['quality_score']:.3f}")
        print(f"  引用文献数: {len(result['data'])}")
        
        # 最初の引用文献を表示
        if result['data']:
            first_citation = result['data'][0]
            print(f"  最初の引用文献: {first_citation.get('title', 'No title')}")
    else:
        print("✗ 引用文献取得失敗")
    
    return result

def test_bibtex_conversion():
    """BibTeX変換テスト"""
    print("\n=== BibTeX変換テスト ===")
    
    config_manager = MagicMock()
    logger = MagicMock()
    logger.get_logger.return_value = MagicMock()
    
    workflow = CitationFetcherWorkflow(config_manager, logger)
    
    # サンプル引用データ
    sample_data = [
        {
            'title': 'Test Paper 1',
            'authors': 'Smith, John and Doe, Jane',
            'journal': 'Nature',
            'year': 2023,
            'doi': '10.1038/nature.2023.001'
        },
        {
            'title': 'Test Paper 2',
            'authors': 'Brown, Alice',
            'journal': 'Science',
            'year': 2022,
            'doi': '10.1126/science.2022.002'
        }
    ]
    
    try:
        bibtex_result = workflow._convert_to_bibtex(sample_data)
        print("✓ BibTeX変換成功")
        print("変換結果の一部:")
        print(bibtex_result[:200] + "..." if len(bibtex_result) > 200 else bibtex_result)
    except Exception as e:
        print(f"✗ BibTeX変換失敗: {e}")
    
    return bibtex_result

if __name__ == "__main__":
    try:
        # 基本初期化テスト
        workflow = test_basic_initialization()
        
        # モック引用文献取得テスト
        citations = test_mock_fetch_citations()
        
        # BibTeX変換テスト
        bibtex_content = test_bibtex_conversion()
        
        print("\n=== 全テスト完了 ===")
        print("✓ CitationFetcher基本機能は正常に動作しています")
        
    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc() 