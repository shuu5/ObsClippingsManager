#!/usr/bin/env python3
"""
CrossRef vs OpenCitations API 比較分析スクリプト

両APIから取得した引用文献の比較を行い、
使い分けの必要性を評価する
"""

import bibtexparser
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_dois_from_bib(bib_file_path):
    """
    .bibファイルからDOIを抽出する
    """
    dois = set()
    try:
        with open(bib_file_path, 'r', encoding='utf-8') as bib_file:
            bib_database = bibtexparser.load(bib_file)
            for entry in bib_database.entries:
                doi = entry.get('doi', '').strip()
                if doi and doi.startswith('10.'):
                    dois.add(doi)
        logger.info(f"Extracted {len(dois)} DOIs from {bib_file_path}")
        return dois
    except Exception as e:
        logger.error(f"Error reading {bib_file_path}: {e}")
        return set()

def analyze_performance_efficiency():
    """
    パフォーマンスと効率性の分析
    """
    logger.info("\n=== パフォーマンス・効率性分析 ===")
    
    print("1. データ取得効率:")
    print("   CrossRef: 1回のAPIコールで完全なメタデータ取得")
    print("   OpenCitations: DOI取得 + 各DOIのメタデータ取得（N+1回のAPIコール）")
    
    print("\n2. 処理時間:")
    print("   CrossRef: 高速（~1秒）")
    print("   OpenCitations: 低速（~1分、51件のDOI × 0.5秒 + α）")
    
    print("\n3. APIリクエスト数:")
    print("   CrossRef: 1回")
    print("   OpenCitations: 52回（引用リスト取得 + 51件のメタデータ取得）")

def compare_citation_coverage():
    """
    引用文献のカバレッジ比較
    """
    output_dir = Path("code/playground/output")
    
    # 同じDOIに対する両方のAPIの結果を比較
    test_doi = "10.18632_oncotarget.13175"
    crossref_file = output_dir / f"crossref_references_{test_doi}.bib"
    opencitations_file = output_dir / f"opencitations_references_{test_doi}.bib"
    
    if not (crossref_file.exists() and opencitations_file.exists()):
        logger.error("比較ファイルが見つかりません")
        return
    
    logger.info(f"\n=== 引用文献カバレッジ比較 (DOI: {test_doi.replace('_', '/')}) ===")
    
    crossref_dois = extract_dois_from_bib(crossref_file)
    opencitations_dois = extract_dois_from_bib(opencitations_file)
    
    logger.info(f"CrossRef取得DOI数: {len(crossref_dois)}")
    logger.info(f"OpenCitations取得DOI数: {len(opencitations_dois)}")
    
    # 重複分析
    common_dois = crossref_dois & opencitations_dois
    crossref_only = crossref_dois - opencitations_dois
    opencitations_only = opencitations_dois - crossref_dois
    
    logger.info(f"共通DOI数: {len(common_dois)}")
    logger.info(f"CrossRefのみ: {len(crossref_only)}")
    logger.info(f"OpenCitationsのみ: {len(opencitations_only)}")
    
    # 重複率
    if len(crossref_dois) > 0:
        overlap_rate = len(common_dois) / len(crossref_dois) * 100
        logger.info(f"重複率: {overlap_rate:.1f}%")
    
    # サンプル表示
    if crossref_only:
        logger.info(f"\nCrossRefのみの例（最初の3件）: {list(crossref_only)[:3]}")
    if opencitations_only:
        logger.info(f"OpenCitationsのみの例（最初の3件）: {list(opencitations_only)[:3]}")
    
    return {
        'crossref_count': len(crossref_dois),
        'opencitations_count': len(opencitations_dois),
        'common_count': len(common_dois),
        'crossref_only_count': len(crossref_only),
        'opencitations_only_count': len(opencitations_only),
        'overlap_rate': len(common_dois) / len(crossref_dois) * 100 if len(crossref_dois) > 0 else 0
    }

def analyze_data_quality():
    """
    データ品質の分析
    """
    logger.info("\n=== データ品質分析 ===")
    
    print("1. メタデータの完全性:")
    print("   CrossRef: 論文のreferenceフィールドから直接取得、メタデータ豊富")
    print("   OpenCitations: DOI関係のみ、メタデータは別途CrossRefから取得")
    
    print("\n2. データの信頼性:")
    print("   CrossRef: 出版社が直接提供、公式データ")
    print("   OpenCitations: オープンサイエンス、透明性が高いが網羅性に課題の可能性")
    
    print("\n3. データの鮮度:")
    print("   CrossRef: 出版社の更新に依存、通常は最新")
    print("   OpenCitations: 独立したクロール・インデックス、更新頻度は限定的")

def provide_recommendations():
    """
    使い分けの推奨案を提示
    """
    logger.info("\n=== 使い分け推奨案 ===")
    
    print("【推奨アプローチ】")
    print("1. メイン: CrossRef API")
    print("   - 高速、効率的")
    print("   - 完全なメタデータ")
    print("   - 1回のAPIコールで完了")
    
    print("\n2. フォールバック: OpenCitations API")
    print("   - CrossRefで引用文献が取得できない場合のみ")
    print("   - または、オープンデータを重視する場合")
    
    print("\n【具体的な実装戦略】")
    print("```python")
    print("def get_references(doi):")
    print("    # まずCrossRefを試行")
    print("    crossref_refs = get_crossref_references(doi)")
    print("    if crossref_refs:")
    print("        return crossref_refs, 'crossref'")
    print("    ")
    print("    # CrossRefで失敗した場合のみOpenCitations")
    print("    logger.info('CrossRef failed, trying OpenCitations')")
    print("    opencitations_refs = get_opencitations_references(doi)")
    print("    return opencitations_refs, 'opencitations'")
    print("```")
    
    print("\n【両方を使う場合】")
    print("- 研究目的でデータソース間の差異を調査したい場合")
    print("- オープンサイエンスの観点でOpenCitationsを優先したい場合")
    print("- 最大限の網羅性を求める場合（両方の結果をマージ）")

def main():
    """
    メイン分析関数
    """
    logger.info("CrossRef vs OpenCitations API 比較分析開始")
    
    # 1. 引用文献カバレッジの比較
    coverage_results = compare_citation_coverage()
    
    # 2. パフォーマンス分析
    analyze_performance_efficiency()
    
    # 3. データ品質分析
    analyze_data_quality()
    
    # 4. 推奨案の提示
    provide_recommendations()
    
    # 5. 結論
    logger.info("\n=== 結論 ===")
    if coverage_results:
        if coverage_results['overlap_rate'] > 80:
            print(f"重複率が{coverage_results['overlap_rate']:.1f}%と高いため、")
            print("CrossRefをメインとし、失敗時のみOpenCitationsを使用することを推奨")
        else:
            print(f"重複率が{coverage_results['overlap_rate']:.1f}%と低いため、")
            print("両APIを併用して最大限の網羅性を確保することも考慮可能")
    
    print("\n効率性を重視する場合: CrossRef API のみ")
    print("網羅性を重視する場合: CrossRef → OpenCitations のフォールバック")
    print("研究・分析目的: 両API併用でデータソース比較")

if __name__ == "__main__":
    main() 