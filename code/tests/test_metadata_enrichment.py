#!/usr/bin/env python3
"""
引用文献メタデータ補完のテストスクリプト
lennartzM2023APMISの不完全なエントリをPubMed APIで補完してみる
"""

import sys
import os
import time
from typing import Dict, Optional

# metapubライブラリのインポート
try:
    from metapub import PubMedFetcher
    from metapub.convert import doi2pmid
    print("metapubライブラリのインポートに成功しました")
except ImportError as e:
    print(f"metapubライブラリのインポートに失敗しました: {e}")
    sys.exit(1)

def test_pubmed_enrichment():
    """PubMed APIを使ったメタデータ補完のテスト"""
    
    # lennartzM2023APMISの不完全なエントリのサンプル
    incomplete_refs = [
        {
            'id': 'ref_0',
            'doi': '10.1007/s12038-019-9864-8',
            'note': 'Retrieved from CrossRef'
        },
        {
            'id': 'ref_1', 
            'doi': '10.1016/j.ceb.2014.12.008',
            'note': 'Retrieved from CrossRef'
        },
        {
            'id': 'ref_2',
            'doi': '10.1111/j.1469-7580.2009.01066.x',
            'note': 'Retrieved from CrossRef'
        }
    ]
    
    print("=== PubMed APIによるメタデータ補完テスト ===\n")
    
    # PubMedFetcherの初期化
    try:
        fetch = PubMedFetcher()
        print("PubMedFetcher初期化成功\n")
    except Exception as e:
        print(f"PubMedFetcher初期化失敗: {e}")
        return
    
    enriched_refs = []
    
    for i, ref in enumerate(incomplete_refs):
        print(f"--- エントリ {i+1}: {ref['id']} ---")
        print(f"元のDOI: {ref['doi']}")
        
        try:
            # DOIからPubMedメタデータを取得
            article = fetch.article_by_doi(ref['doi'])
            
            if article:
                # 成功した場合の情報表示
                print("✅ PubMedからメタデータ取得成功:")
                print(f"  PMID: {article.pmid}")
                print(f"  Title: {article.title}")
                print(f"  Authors: {', '.join(article.authors) if article.authors else 'N/A'}")
                print(f"  Journal: {article.journal}")
                print(f"  Year: {article.year}")
                print(f"  Volume: {article.volume if article.volume else 'N/A'}")
                print(f"  Issue: {article.issue if article.issue else 'N/A'}")
                print(f"  Pages: {article.pages if article.pages else 'N/A'}")
                
                # BibTeX形式に変換
                enriched_entry = {
                    'id': ref['id'],
                    'type': 'article',
                    'title': article.title,
                    'author': ', '.join(article.authors) if article.authors else None,
                    'journal': article.journal,
                    'year': str(article.year) if article.year else None,
                    'volume': article.volume,
                    'number': article.issue,
                    'pages': article.pages,
                    'doi': ref['doi'],
                    'pmid': article.pmid,
                    'note': 'Retrieved from PubMed via metapub'
                }
                enriched_refs.append(enriched_entry)
                
            else:
                print("❌ PubMedでメタデータが見つかりませんでした")
                enriched_refs.append(ref)  # 元のエントリをそのまま保持
                
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            enriched_refs.append(ref)  # 元のエントリをそのまま保持
        
        print()
        
        # API制限を考慮して少し待機
        time.sleep(1)
    
    print("=== 補完結果サマリー ===")
    complete_count = sum(1 for ref in enriched_refs if ref.get('type') == 'article')
    print(f"補完前の完全エントリ: 0/3")
    print(f"補完後の完全エントリ: {complete_count}/3")
    print(f"改善率: {(complete_count / len(incomplete_refs)) * 100:.1f}%")
    
    return enriched_refs

def generate_bibtex_output(enriched_refs):
    """補完された引用文献をBibTeX形式で出力"""
    
    print("\n=== BibTeX形式での出力例 ===")
    
    for ref in enriched_refs:
        if ref.get('type') == 'article':
            # 完全な@articleエントリ
            print(f"@article{{{ref['id']},")
            if ref.get('title'):
                print(f"  title = {{{ref['title']}}},")
            if ref.get('author'):
                print(f"  author = {{{ref['author']}}},")
            if ref.get('journal'):
                print(f"  journal = {{{ref['journal']}}},")
            if ref.get('year'):
                print(f"  year = {{{ref['year']}}},")
            if ref.get('volume'):
                print(f"  volume = {{{ref['volume']}}},")
            if ref.get('number'):
                print(f"  number = {{{ref['number']}}},")
            if ref.get('pages'):
                print(f"  pages = {{{ref['pages']}}},")
            if ref.get('doi'):
                print(f"  doi = {{{ref['doi']}}},")
            if ref.get('pmid'):
                print(f"  pmid = {{{ref['pmid']}}},")
            if ref.get('note'):
                print(f"  note = {{{ref['note']}}}")
            print("}")
        else:
            # 元の@miscエントリ
            print(f"@misc{{{ref['id']},")
            if ref.get('doi'):
                print(f"  doi = {{{ref['doi']}}},")
            if ref.get('note'):
                print(f"  note = {{{ref['note']}}}")
            print("}")
        print()

def test_doi_to_pmid_conversion():
    """DOI→PMID変換のテスト"""
    
    print("=== DOI→PMID変換テスト ===")
    
    test_dois = [
        '10.1007/s12038-019-9864-8',
        '10.1016/j.ceb.2014.12.008',
        '10.1111/j.1469-7580.2009.01066.x'
    ]
    
    for doi in test_dois:
        try:
            pmid = doi2pmid(doi)
            if pmid:
                print(f"DOI: {doi} → PMID: {pmid}")
            else:
                print(f"DOI: {doi} → PMID変換失敗")
        except Exception as e:
            print(f"DOI: {doi} → エラー: {e}")
        
        time.sleep(0.5)  # API制限対策

if __name__ == "__main__":
    print("引用文献メタデータ補完テストを開始します...\n")
    
    # DOI→PMID変換テスト
    test_doi_to_pmid_conversion()
    print()
    
    # PubMedメタデータ補完テスト
    enriched_refs = test_pubmed_enrichment()
    
    # BibTeX出力例
    if enriched_refs:
        generate_bibtex_output(enriched_refs)
    
    print("\nテスト完了") 