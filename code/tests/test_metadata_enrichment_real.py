#!/usr/bin/env python3
"""
実際のAPIを使ったメタデータ補完機能のテスト
lennartzM2023APMISの不完全なエントリを実際に補完してみる
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'py'))

from modules.citation_fetcher.metadata_enricher import MetadataEnricher
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import get_integrated_logger


def test_single_doi_enrichment():
    """単一DOIのメタデータ補完テスト"""
    logger = get_integrated_logger().get_logger("Test")
    
    # lennartzM2023APMISの不完全なエントリの一つをテスト
    test_doi = "10.1007/s12038-019-9864-8"
    
    logger.info(f"Testing metadata enrichment for: {test_doi}")
    
    # メタデータ補完エンジンを初期化
    enricher = MetadataEnricher()
    
    # 利用可能なクライアントを確認
    available_clients = enricher.get_available_clients()
    logger.info(f"Available clients: {available_clients}")
    
    # メタデータ補完を実行
    result = enricher.enrich_metadata(test_doi, field_type='life_sciences')
    
    # 結果を表示
    logger.info(f"Enrichment result for {test_doi}:")
    logger.info(f"  Primary source: {result.primary_source}")
    logger.info(f"  Quality score: {result.quality_score:.2f}")
    logger.info(f"  Processing time: {result.processing_time:.2f}s")
    logger.info(f"  Sources used: {list(result.source_data.keys())}")
    logger.info(f"  Complete fields: {result.get_complete_fields()}")
    
    if result.merged_metadata:
        logger.info("  Merged metadata:")
        for key, value in result.merged_metadata.items():
            if not key.endswith('_source'):
                logger.info(f"    {key}: {value}")
    
    if result.errors:
        logger.warning("  Errors encountered:")
        for source, error in result.errors.items():
            logger.warning(f"    {source}: {error}")
    
    return result


def test_multiple_dois():
    """複数DOIのメタデータ補完テスト"""
    logger = get_integrated_logger().get_logger("Test")
    
    # lennartzM2023APMISの不完全なエントリから複数選択
    test_dois = [
        "10.1007/s12038-019-9864-8",
        "10.1016/j.ceb.2014.12.008", 
        "10.1111/j.1469-7580.2009.01066.x"
    ]
    
    enricher = MetadataEnricher()
    results = []
    
    logger.info(f"Testing metadata enrichment for {len(test_dois)} DOIs")
    
    for i, doi in enumerate(test_dois, 1):
        logger.info(f"\n--- Testing DOI {i}/{len(test_dois)}: {doi} ---")
        
        result = enricher.enrich_metadata(doi, field_type='life_sciences')
        results.append(result)
        
        # 簡潔な結果表示
        success = "✅" if result.is_successful() else "❌"
        sources_count = len(result.source_data)
        logger.info(f"{success} {doi}: {sources_count} sources, quality={result.quality_score:.2f}")
        
        if result.merged_metadata:
            title = result.merged_metadata.get('title', 'No title')[:80]
            authors = result.merged_metadata.get('authors', [])
            author_count = len(authors) if authors else 0
            journal = result.merged_metadata.get('journal', 'No journal')[:40]
            year = result.merged_metadata.get('year', 'No year')
            
            logger.info(f"    Title: {title}...")
            logger.info(f"    Authors: {author_count} authors")
            logger.info(f"    Journal: {journal}")
            logger.info(f"    Year: {year}")
    
    # 統計情報
    statistics = enricher.get_statistics()
    logger.info(f"\n--- Enrichment Statistics ---")
    logger.info(f"Total processed: {statistics.total_processed}")
    logger.info(f"Successful enrichments: {statistics.enrichment_success}")
    logger.info(f"Improvement rate: {statistics.get_enrichment_improvement_rate():.1f}%")
    
    for source, rates in statistics.api_success_rates.items():
        if rates['attempts'] > 0:
            success_rate = (rates['successes'] / rates['attempts']) * 100
            logger.info(f"{source}: {rates['successes']}/{rates['attempts']} ({success_rate:.1f}%)")
    
    return results


def test_client_availability():
    """各APIクライアントの利用可能性テスト"""
    logger = get_integrated_logger().get_logger("Test")
    
    enricher = MetadataEnricher()
    
    logger.info("Testing client availability...")
    test_results = enricher.test_clients()
    
    for client_name, result in test_results.items():
        status = "✅" if result['test_successful'] else "❌"
        time_str = f"{result['response_time']:.2f}s" if 'response_time' in result else "N/A"
        
        logger.info(f"{status} {client_name}: {time_str}")
        
        if 'error' in result:
            logger.warning(f"    Error: {result['error']}")
        
        if result.get('client_info'):
            info = result['client_info']
            if 'target_fields' in info:
                logger.info(f"    Target fields: {info['target_fields']}")


def main():
    """メイン実行関数"""
    logger = get_integrated_logger().get_logger("Test")
    
    logger.info("=== Metadata Enrichment Real API Test ===")
    
    try:
        # 1. クライアント利用可能性テスト
        logger.info("\n1. Testing client availability...")
        test_client_availability()
        
        # 2. 単一DOIテスト
        logger.info("\n2. Testing single DOI enrichment...")
        single_result = test_single_doi_enrichment()
        
        # 3. 複数DOIテスト
        logger.info("\n3. Testing multiple DOIs enrichment...")
        multiple_results = test_multiple_dois()
        
        # 成功率の計算
        successful_count = sum(1 for r in multiple_results if r.is_successful())
        success_rate = (successful_count / len(multiple_results)) * 100
        
        logger.info(f"\n=== Final Results ===")
        logger.info(f"Overall success rate: {successful_count}/{len(multiple_results)} ({success_rate:.1f}%)")
        
        if success_rate >= 66:
            logger.info("✅ Metadata enrichment is working well!")
        elif success_rate >= 33:
            logger.info("⚠️ Metadata enrichment has moderate success")
        else:
            logger.warning("❌ Metadata enrichment needs improvement")
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise


if __name__ == "__main__":
    main() 