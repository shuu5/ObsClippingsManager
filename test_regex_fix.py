#!/usr/bin/env python3
import re

def test_link_removal():
    # 実際のテキストを使用
    test_text = '\\[[4–8](https://academic.oup.com/jrr/article/64/2/284/)\\]'
    
    print(f"Test text: {test_text}")
    print(f"Test text repr: {repr(test_text)}")
    print(f"Length: {len(test_text)}")
    print()
    
    # 様々なパターンをテスト
    patterns = [
        r'\\?\[\[([^\]]+)\]\([^)]+\)\\?\]\]',
        r'\\\[\[([^\]]+)\]\([^)]+\)\\\]',
        r'\\\\?\[\[([^\]]+)\]\([^)]+\)\\\\?\]\]',
        r'\\\\\[\[([^\]]+)\]\([^)]+\)\\\\\]',
        r'\\\[\[([^\\]+)\]\([^)]+\)\\\]',
    ]
    
    for i, pattern in enumerate(patterns):
        print(f"=== Pattern {i+1}: {pattern} ===")
        try:
            matches = list(re.finditer(pattern, test_text))
            print(f"Matches found: {len(matches)}")
            for j, match in enumerate(matches):
                print(f"  Match {j}: {match.groups()}")
            
            if matches:
                result = re.sub(pattern, lambda m: f"\\[[{m.group(1)}]\\]", test_text)
                print(f"After replace: {result}")
                print(f"Changed: {test_text != result}")
            else:
                print("No matches, no replacement")
        except Exception as e:
            print(f"Error: {e}")
        print()

if __name__ == "__main__":
    test_link_removal() 