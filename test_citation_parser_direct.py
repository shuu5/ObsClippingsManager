#!/usr/bin/env python3
"""
直接CitationParserでファイルを処理してテスト
"""

import sys
sys.path.append('code/py')

from modules.citation_parser.citation_parser import CitationParser

def test_direct_processing():
    # ファイルを読み込み
    file_path = "TestManuscripts/Clippings/takenakaW2023J.Radiat.Res.Tokyo/takenakaW2023J.Radiat.Res.Tokyo.md"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f'=== ORIGINAL FILE INFO ===')
    print(f'Length: {len(content)} chars')
    print(f'Lines: {len(content.splitlines())}')
    
    # chemotherapy を含む段落を抽出して確認
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'chemotherapy' in line:
            print(f'Line {i+1}: {line[:100]}...')
            break
    
    print()
    
    # CitationParserで処理
    parser = CitationParser()
    result = parser.parse_document(content)
    
    print(f'=== PROCESSING RESULT ===')
    print(f'Original: {len(content)} chars')
    print(f'Converted: {len(result.converted_text)} chars')
    print(f'Total citations: {result.statistics.total_citations}')
    print(f'Converted citations: {result.statistics.converted_citations}')
    print(f'Errors: {result.statistics.errors}')
    print(f'Processing time: {result.statistics.processing_time:.3f}s')
    print()
    
    # 変換後の chemotherapy 部分を確認
    converted_lines = result.converted_text.split('\n')
    for i, line in enumerate(converted_lines):
        if 'chemotherapy' in line:
            print(f'Converted Line {i+1}: {line[:150]}...')
            break
    
    # ファイルに書き込み
    output_path = "TestManuscripts/Clippings/takenakaW2023J.Radiat.Res.Tokyo/takenakaW2023J.Radiat.Res.Tokyo.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result.converted_text)
    
    print(f'\nFile written to: {output_path}')

if __name__ == "__main__":
    test_direct_processing() 