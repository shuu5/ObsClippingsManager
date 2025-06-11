#!/usr/bin/env python3
"""
実際のファイル内容でCitationParserをテスト
"""

import sys
import os
sys.path.append('code/py')

from modules.citation_parser.citation_parser import CitationParser

def test_real_file():
    # バックアップファイルから実際のテキストを読み込み
    with open('TestManuscripts/backups/KRT13 is upregulated in pancreatic cancer stem-like cells and associated with radioresistance_20250611_015528.backup.md', 'r') as f:
        content = f.read()

    # chemotherapy を含む段落を抽出
    lines = content.split('\n')
    target_paragraph = ''
    for line in lines:
        if 'chemotherapy' in line and 'radiotherapy' in line:
            target_paragraph = line.strip()
            break

    print('=== ACTUAL FILE CONTENT ===')
    print(f'Length: {len(target_paragraph)}')
    print(target_paragraph)
    print()

    # CitationParser で処理
    parser = CitationParser()
    result = parser.parse_document(target_paragraph)

    print('=== PARSED RESULT ===')
    print(f'Length: {len(result.converted_text)}')
    print(result.converted_text)
    print()

    print('=== COMPARISON ===')
    print(f'Original: {len(target_paragraph)} chars')
    print(f'Converted: {len(result.converted_text)} chars')
    print(f'Difference: {len(target_paragraph) - len(result.converted_text)} chars')
    
    # 問題がある部分を特定
    print()
    print('=== ISSUE DETECTION ===')
    if 'metasta' in result.converted_text and 'metastasis' not in result.converted_text:
        print('ISSUE: metastasis is truncated to metasta')
    
    if '[4], [5], [6], [7], [8]' in result.converted_text:
        # 前後の文字を確認
        pos = result.converted_text.find('[4], [5], [6], [7], [8]')
        before = result.converted_text[max(0, pos-10):pos]
        after = result.converted_text[pos+len('[4], [5], [6], [7], [8]'):pos+len('[4], [5], [6], [7], [8]')+10]
        print(f'Citations inserted at: "{before}[4], [5], [6], [7], [8]{after}"')

if __name__ == "__main__":
    test_real_file() 