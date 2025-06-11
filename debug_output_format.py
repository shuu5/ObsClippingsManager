#!/usr/bin/env python3
"""
出力フォーマット設定の詳細をデバッグ
"""

import sys
sys.path.append('code/py')

from modules.citation_parser.config_manager import ConfigManager
from modules.citation_parser.citation_parser import CitationParser

def debug_output_format():
    # ConfigManagerの設定を直接確認
    config_manager = ConfigManager()
    format_config = config_manager.get_output_format_config('standard')
    
    print('=== CONFIG MANAGER SETTINGS ===')
    for key, value in format_config.items():
        print(f'{key}: {repr(value)}')
    print()
    
    # CitationParserで実際に適用される設定を確認
    parser = CitationParser()
    
    print('=== CITATION PARSER FORMAT SETTINGS ===')
    output_format = parser.format_converter.output_format
    print(f'single_template: {repr(output_format.single_template)}')
    print(f'multiple_template: {repr(output_format.multiple_template)}')
    print(f'separator: {repr(output_format.separator)}')
    print(f'sort_numbers: {output_format.sort_numbers}')
    print(f'expand_ranges: {output_format.expand_ranges}')
    print(f'remove_spaces: {output_format.remove_spaces}')
    print(f'individual_citations: {output_format.individual_citations}')
    print()
    
    # FormatConverterの個別引用モードを確認
    print('=== FORMAT CONVERTER INTERNAL STATE ===')
    print(f'Individual citation mode: {getattr(parser.format_converter, "_individual_mode", "Not set")}')

if __name__ == "__main__":
    debug_output_format() 