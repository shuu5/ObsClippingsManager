#!/usr/bin/env python3
"""
CitationParserが実際に使用しているパターンを確認
"""

import sys
sys.path.append('code/py')

from modules.citation_parser.citation_parser import CitationParser

def check_citation_parser_patterns():
    # CitationParserを初期化
    parser = CitationParser()
    
    print('=== CITATION PARSER PATTERNS ===')
    print(f'Total patterns: {len(parser.pattern_detector.patterns)}')
    
    # パターンを優先度順にソート
    sorted_patterns = sorted(
        parser.pattern_detector.patterns.items(),
        key=lambda x: x[1].priority
    )
    
    for name, pattern_config in sorted_patterns:
        print(f'Priority {pattern_config.priority}: {name}')
        print(f'  Regex: {pattern_config.regex}')
        print(f'  Type: {pattern_config.pattern_type}')
        print(f'  Enabled: {pattern_config.enabled}')
        print()
    
    print('=== FORMAT CONVERTER SETTINGS ===')
    output_format = parser.format_converter.output_format
    print(f'Individual citations: {output_format.individual_citations}')
    print(f'Separator: "{output_format.separator}"')
    print(f'Expand ranges: {output_format.expand_ranges}')
    print(f'Sort numbers: {output_format.sort_numbers}')

if __name__ == "__main__":
    check_citation_parser_patterns() 