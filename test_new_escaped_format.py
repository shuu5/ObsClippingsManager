#!/usr/bin/env python3
"""
新しいエスケープフォーマット仕様をテスト
"""

import sys
sys.path.append('code/py')

from modules.citation_parser.citation_parser import CitationParser

def test_new_escaped_format():
    # テストケース
    test_cases = [
        r"chemotherapy \[[4–8](https://academic.oup.com/jrr/article/64/2/284/)\]",
        r"available \[[9](https://academic.oup.com/jrr/article/64/2/284/)\]",
        r"markers \[[10]\]",
        r"drugs \[[12], [13]\]",
        r"normal citation [1]",
        r"normal linked [2](https://example.com)",
        r"footnote citation [^3]"
    ]
    
    parser = CitationParser()
    
    print('=== NEW ESCAPED FORMAT TEST ===')
    for i, test_case in enumerate(test_cases, 1):
        print(f'Test {i}: {test_case}')
        result = parser.parse_document(test_case)
        print(f'Result: {result.converted_text}')
        print(f'Citations: {result.statistics.total_citations}')
        print()

if __name__ == "__main__":
    test_new_escaped_format() 