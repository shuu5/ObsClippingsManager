#!/usr/bin/env python3
"""
実際のテキストでパターンマッチングをテスト
"""

import sys
import re
sys.path.append('code/py')

from modules.citation_parser.pattern_detector import PatternDetector

def test_pattern_matching():
    # 実際の問題のあるテキスト
    text_samples = [
        r"chemotherapy \[[4–8](https://academic.oup.com/jrr/article/64/2/284/)\]",
        r"available \[[9](https://academic.oup.com/jrr/article/64/2/284/)\]",
        r"markers \[[10](https://academic.oup.com/jrr/article/64/2/284/)\]",
        r"drugs \[[11](https://academic.oup.com/jrr/article/64/2/284/)\]",
        r"radioresistance \[[12](https://academic.oup.com/jrr/article/64/2/284/), [13](https://academic.oup.com/jrr/article/64/2/284/)\]"
    ]
    
    # PatternDetectorで検出
    detector = PatternDetector()
    
    print('=== PATTERN MATCHING TEST ===')
    for i, sample in enumerate(text_samples, 1):
        print(f'Sample {i}: {sample}')
        matches = detector.detect_patterns(sample)
        print(f'Detected {len(matches)} matches:')
        for match in matches:
            print(f'  Type: {match.pattern_type}')
            print(f'  Text: "{match.original_text}"')
            print(f'  Numbers: {match.citation_numbers}')
            print(f'  Has Link: {match.has_link}')
            print(f'  Position: {match.start_pos}-{match.end_pos}')
            if match.has_link and match.link_url:
                print(f'  URL: {match.link_url}')
        print()
    
    # 個別パターンテスト
    print('=== INDIVIDUAL PATTERN TEST ===')
    escaped_patterns = {
        'escaped_linked_citation': r'\\\[\[(\d+(?:[,\s]*\d+)*)\]\(([^)]+)\)\\\]',
        'escaped_linked_range': r'\\\[\[(\d+)[-–](\d+)\]\(([^)]+)\)\\\]'
    }
    
    test_text = r"chemotherapy \[[4–8](https://academic.oup.com/jrr/article/64/2/284/)\]"
    print(f'Test text: {test_text}')
    
    for name, pattern in escaped_patterns.items():
        matches = re.finditer(pattern, test_text)
        found_matches = list(matches)
        print(f'{name}: {len(found_matches)} matches')
        for match in found_matches:
            print(f'  Match: {match.group()}, Groups: {match.groups()}')

if __name__ == "__main__":
    test_pattern_matching() 