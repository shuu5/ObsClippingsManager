#!/usr/bin/env python3
"""
引用文献パース処理のデバッグスクリプト
"""

import sys
import os
sys.path.append('code/py')

from modules.citation_parser.citation_parser import CitationParser

def debug_citation_process():
    """引用文献パース処理をステップバイステップでデバッグ"""
    
    test_text = """Many studies have shown that CSCs constitute a small population existing in the tumor and have the capacity for self-renewal, high tumorigenicity and resistance to conventional cancer therapies such as radiotherapy and chemotherapy \\[[4–8](https://academic.oup.com/jrr/article/64/2/284/)\\]. The CSC population is therefore considered to be the source of recurrence and metastasis. Although a number of studies have been conducted to elucidate the properties of CSCs and establish a new treatment strategy for targeting them, as yet no therapeutic targeting CSC is available \\[[9](https://academic.oup.com/jrr/article/64/2/284/)\\]."""
    
    print("=== ORIGINAL TEXT ===")
    print(test_text)
    print(f"Length: {len(test_text)}")
    print()
    
    # 統合処理をテスト
    print("=== INTEGRATED CITATION PARSING ===")
    parser = CitationParser()
    result = parser.parse_document(test_text)
    
    print(f"Converted text: '{result.converted_text}'")
    print(f"Length: {len(result.converted_text)}")
    print(f"Link entries: {len(result.link_table)}")
    print(f"Statistics:")
    print(f"  Total citations: {result.statistics.total_citations}")
    print(f"  Converted citations: {result.statistics.converted_citations}")
    print(f"  Processing time: {result.statistics.processing_time:.3f}s")
    print()
    
    # 問題分析
    print("=== ISSUE ANALYSIS ===")
    corrupted_words = []
    words = result.converted_text.split()
    
    for word in words:
        # 文字が合体しているかチェック
        if any(char.isdigit() for char in word) and any(char.isalpha() for char in word):
            if ']' in word and word.index(']') < len(word) - 1:
                after_bracket = word[word.index(']') + 1:]
                if after_bracket.isalpha() and len(after_bracket) > 2:
                    corrupted_words.append(word)
    
    for word in corrupted_words:
        print(f"ISSUE: Corrupted word found: '{word}'")
    
    # 引用番号の重複チェック
    import re
    citation_matches = re.findall(r'\\[\\d+\\]', result.converted_text)
    citation_counts = {}
    for citation in citation_matches:
        citation_counts[citation] = citation_counts.get(citation, 0) + 1
    
    for citation, count in citation_counts.items():
        if count > 1:
            print(f"ISSUE: Citation {citation} appears {count} times")
    
    # 部分文字列のチェック
    fragments = ['metasta', 'elucidate', 'herefore', 'available']
    for fragment in fragments:
        if fragment in result.converted_text:
            print(f"ISSUE: Fragment found: '{fragment}'")
    
    # デバッグ: 各段階での長さ変化
    print()
    print("=== LENGTH ANALYSIS ===")
    print(f"Original length: {len(test_text)}")
    print(f"Final length: {len(result.converted_text)}")
    print(f"Difference: {len(test_text) - len(result.converted_text)}")

if __name__ == "__main__":
    debug_citation_process() 