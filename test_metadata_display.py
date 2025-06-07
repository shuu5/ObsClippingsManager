#!/usr/bin/env python3
"""
メタデータ補完結果の表示テストスクリプト
"""

import sys
sys.path.append('/home/user/proj/ObsClippingsManager/code/py')

from modules.shared.config_manager import ConfigManager
from modules.citation_fetcher.metadata_enricher import MetadataEnricher

def test_single_doi(doi: str):
    """単一DOIのメタデータ補完をテスト"""
    print(f"\n=== Testing DOI: {doi} ===")
    
    config = ConfigManager()
    enricher = MetadataEnricher(config)
    
    result = enricher.enrich_metadata(doi, field_type='life_sciences')
    
    if result.is_successful():
        print(f"✅ Success! Quality score: {result.quality_score:.2f}")
        print(f"Primary source: {result.primary_source}")
        print(f"Sources used: {list(result.source_data.keys())}")
        
        print("\nMerged metadata:")
        for key, value in result.merged_metadata.items():
            if not key.endswith('_source'):
                print(f"  {key}: {value}")
                
        print("\nManual BibTeX conversion:")
        metadata = result.merged_metadata
        
        # 手動でBibTeXエントリを作成
        authors_str = " and ".join(metadata.get('authors', [])) if metadata.get('authors') else "Unknown"
        
        bibtex = f"""@article{{enriched_{doi.replace('/', '_').replace('.', '_')},
  title = {{{metadata.get('title', 'Unknown Title')}}},
  author = {{{authors_str}}},
  journal = {{{metadata.get('journal', 'Unknown Journal')}}},
  year = {{{metadata.get('year', 'Unknown Year')}}},
  doi = {{{doi}}}"""
        
        if metadata.get('volume'):
            bibtex += f",\n  volume = {{{metadata['volume']}}}"
        if metadata.get('issue'):
            bibtex += f",\n  issue = {{{metadata['issue']}}}"
        if metadata.get('pages'):
            bibtex += f",\n  pages = {{{metadata['pages']}}}"
            
        bibtex += "\n}"
        
        print(f"\n{bibtex}")
        
        return bibtex
    else:
        print(f"❌ Failed to enrich metadata")
        print(f"Errors: {result.errors}")
        return None

if __name__ == "__main__":
    # Test the first few problematic DOIs
    test_dois = [
        "10.1007/s12038-019-9864-8",  # First @misc entry
        "10.1016/j.ceb.2014.12.008",  # Second @misc entry  
        "10.1111/j.1469-7580.2009.01066.x"  # Third @misc entry
    ]
    
    print("=== Manual BibTeX Enrichment Test ===")
    
    enriched_entries = []
    for doi in test_dois:
        bibtex = test_single_doi(doi)
        if bibtex:
            enriched_entries.append(bibtex)
    
    # Save manually created entries
    output_file = "/home/user/ManuscriptsManager/Clippings/lennartzM2023APMIS/references_manual_enriched.bib"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("% Manually enriched BibTeX entries\n")
        f.write("% Generated from ObsClippingsManager metadata enrichment system\n\n")
        
        for entry in enriched_entries:
            f.write(entry)
            f.write("\n\n")
    
    print(f"\n=== Results saved to: {output_file} ===")
    print(f"Successfully converted {len(enriched_entries)} @misc entries to complete @article entries!") 