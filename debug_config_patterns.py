#!/usr/bin/env python3
"""
ConfigManagerのパターン設定を確認
"""

import sys
sys.path.append('code/py')

from modules.citation_parser.config_manager import ConfigManager

def check_config_patterns():
    config = ConfigManager()
    patterns = config.get_pattern_configs()
    
    print('=== LOADED PATTERNS ===')
    for pattern in patterns:
        if 'escaped' in pattern.name:
            print(f'{pattern.name}:')
            print(f'  Regex: {pattern.regex}')
            print(f'  Priority: {pattern.priority}')
            print(f'  Type: {pattern.pattern_type}')
            print(f'  Enabled: {pattern.enabled}')
            print()
    
    print('=== PRIORITY ORDER ===')
    sorted_patterns = sorted(patterns, key=lambda x: x.priority)
    for pattern in sorted_patterns:
        print(f'Priority {pattern.priority}: {pattern.name} (enabled: {pattern.enabled})')

if __name__ == "__main__":
    check_config_patterns() 