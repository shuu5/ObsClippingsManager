#!/usr/bin/env python3
"""
BibTeXファイルのメタデータ補完テストスクリプト

不完全な@miscエントリを含むBibTeXファイルを読み込み、
メタデータ補完システムを使って完全な@articleエントリに変換します。
"""

import sys
import os
import time
from typing import Dict, List

# パスの追加
sys.path.append('/home/user/proj/ObsClippingsManager/code/py')

from modules.shared.bibtex_parser import BibTeXParser
from modules.shared.config_manager import ConfigManager
from modules.citation_fetcher.metadata_enricher import MetadataEnricher
from modules.citation_fetcher.reference_formatter import ReferenceFormatter
from modules.shared.logger import get_integrated_logger


def extract_dois_from_bibtex(file_path: str) -> List[str]:
    """BibTeXファイルからDOIを抽出"""
    parser = BibTeXParser()
    entries_dict = parser.parse_file(file_path)
    
    dois = []
    for entry_key, entry_data in entries_dict.items():
        if 'doi' in entry_data:
            doi = entry_data['doi']
            # DOIの前後の括弧や引用符を除去
            doi = doi.strip().strip('{}').strip('"')
            dois.append(doi)
    
    return dois


def enrich_bibtex_file(input_file: str, output_file: str = None):
    """BibTeXファイルのメタデータを補完"""
    logger = get_integrated_logger().get_logger("BibtexEnrichment")
    
    if output_file is None:
        output_file = input_file.replace('.bib', '_enriched.bib')
    
    logger.info(f"Starting BibTeX enrichment: {input_file} -> {output_file}")
    
    # 設定とコンポーネントの初期化
    config = ConfigManager()
    enricher = MetadataEnricher(config)
    formatter = ReferenceFormatter(config)
    
    # DOIの抽出
    logger.info("Extracting DOIs from BibTeX file...")
    dois = extract_dois_from_bibtex(input_file)
    logger.info(f"Found {len(dois)} DOIs to process")
    
    if not dois:
        logger.warning("No DOIs found in the file")
        return
    
    # メタデータ補完の実行
    enriched_entries = []
    start_time = time.time()
    
    for i, doi in enumerate(dois[:10], 1):  # 最初の10件をテスト
        logger.info(f"Processing DOI {i}/{min(10, len(dois))}: {doi}")
        
        try:
            # メタデータ補完
            result = enricher.enrich_metadata(doi, field_type='life_sciences')
            
            if result.is_successful():
                # BibTeX形式に変換
                bibtex_entry = formatter.format_to_bibtex(
                    result.merged_metadata, 
                    f"enriched_{i-1}"
                )
                enriched_entries.append(bibtex_entry)
                
                logger.info(f"✅ Successfully enriched {doi} (quality: {result.quality_score:.2f})")
            else:
                logger.warning(f"❌ Failed to enrich {doi}")
                # 元の@miscエントリを保持
                original_entry = f"""@misc{{ref_{i-1},
  doi = {{{doi}}},
  note = {{Failed to enrich from original @misc}}
}}"""
                enriched_entries.append(original_entry)
                
        except Exception as e:
            logger.error(f"Error processing {doi}: {e}")
            continue
    
    # 結果の書き出し
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"% Enriched BibTeX file\n")
        f.write(f"% Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"% Original file: {input_file}\n")
        f.write(f"% Total entries processed: {len(enriched_entries)}\n\n")
        
        for entry in enriched_entries:
            f.write(entry)
            f.write("\n\n")
    
    processing_time = time.time() - start_time
    logger.info(f"Enrichment completed in {processing_time:.2f}s")
    logger.info(f"Results saved to: {output_file}")
    
    # 統計情報の表示
    stats = enricher.get_statistics()
    logger.info("=== Enrichment Statistics ===")
    logger.info(f"Total processed: {stats.total_processed}")
    logger.info(f"Successful enrichments: {stats.enrichment_success}")
    logger.info(f"Success rate: {(stats.enrichment_success/stats.total_processed)*100:.1f}%")
    
    for source, data in stats.api_success_rates.items():
        if data['attempts'] > 0:
            success_rate = (data['successes'] / data['attempts']) * 100
            logger.info(f"{source}: {data['successes']}/{data['attempts']} ({success_rate:.1f}%)")


if __name__ == "__main__":
    input_file = "/home/user/ManuscriptsManager/Clippings/lennartzM2023APMIS/references.bib"
    output_file = "/home/user/ManuscriptsManager/Clippings/lennartzM2023APMIS/references_enriched.bib"
    
    print("=== BibTeX Metadata Enrichment Test ===")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print()
    
    enrich_bibtex_file(input_file, output_file) 