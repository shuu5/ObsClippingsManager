# Enhanced Citation Parser 機能仕様書 v3.0

## 概要
ObsClippingsManager v3.0における引用文献パース機能の大幅強化版仕様です。現存するあらゆる引用形式を完全に統一されたフォーマットに変換し、特にエスケープされた引用形式への完全対応を実現します。

## 課題と改善目標

### 現在の課題
TestManuscriptsディレクトリに存在する以下のような不統一な引用形式：
- `\[[1]\]` (エスケープされた基本形式)
- `\[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\]` (エスケープされたURL付き形式)
- `\[[12], [13]\]` (エスケープされた個別形式)
- `\[[^10]\]` (エスケープされた脚注形式)
- `\[[^1],[^2],[^3]\]` (エスケープされた脚注複数形式)

### 改善目標
エスケープパターンと標準パターンを区別した以下の形式への変換：

#### エスケープパターン（外側の `\[\]` を保持）
- 単一引用: `\[[1]\]`
- 複数引用: `\[[2], [3], [4]\]` (常にカンマ+スペース区切り)

#### 標準パターン（従来通り）
- 単一引用: `[1]`
- 複数引用: `[2], [3], [4]` (常にカンマ+スペース区切り)

## 対応パターン詳細仕様

### 1. エスケープされた基本引用

#### パターン定義
```python
ESCAPED_BASIC_PATTERNS = {
    'escaped_single': r'\\?\[\[(\d+)\]\]',
    'escaped_multiple_grouped': r'\\?\[\[(\d+(?:[,\s]*\d+)*)\]\]',
    'escaped_individual_multiple': r'\\?\[\[(\d+)\]\](?:\s*,\s*\\?\[\[(\d+)\]\])*'
}
```

#### 変換例
```
入力: \[[1]\]
出力: \[[1]\]

入力: \[[12], [13]\]  
出力: \[[12], [13]\]

入力: \[[1,2,3]\]
出力: \[[1], [2], [3]\]
```

### 2. エスケープされたURL付き引用

#### パターン定義
```python
ESCAPED_LINKED_PATTERNS = {
    'escaped_single_link': r'\\?\[\[(\d+)\]\(([^)]+)\)\]',
    'escaped_multiple_link': r'\\?\[\[(\d+(?:[,\s]*\d+)*)\]\(([^)]+)\)\]',
    'escaped_range_link': r'\\?\[\[(\d+)[-–](\d+)\]\(([^)]+)\)\]'
}
```

#### 変換例
```
入力: \[[1](https://example.com)\]
処理: 
  1. URLを抽出: https://example.com
  2. 引用番号を統一化、外側エスケープ保持: \[[1]\]
出力: \[[1]\]

入力: \[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\]
処理:
  1. URLを抽出: https://academic.oup.com/jrr/article/64/2/284/
  2. 引用番号を分離・統一化、外側エスケープ保持: \[[4], [5], [6], [7], [8]\]
出力: \[[4], [5], [6], [7], [8]\]
```

### 3. エスケープされた脚注引用

#### パターン定義
```python
ESCAPED_FOOTNOTE_PATTERNS = {
    'escaped_footnote_single': r'\\?\[\[\^(\d+)\]\]',
    'escaped_footnote_multiple_grouped': r'\\?\[\[\^(\d+(?:[,\s]*\d+)*)\]\]',
    'escaped_footnote_multiple_individual': r'\\?\[\[\^(\d+)\]\](?:\s*,\s*\\?\[\[\^(\d+)\]\])*'
}
```

#### 変換例
```
入力: \[[^1]\]
処理:
  1. エスケープ処理
  2. ^記号除去: 1
  3. 統一化、外側エスケープ保持: \[[1]\]
出力: \[[1]\]

入力: \[[^10]\]
処理:
  1. エスケープ処理
  2. ^記号除去: 10
  3. 統一化、外側エスケープ保持: \[[10]\]
出力: \[[10]\]

入力: \[[^1],[^2],[^3]\]
処理:
  1. エスケープ処理
  2. ^記号除去: 1,2,3
  3. 個別化・統一化、外側エスケープ保持: \[[1], [2], [3]\]
出力: \[[1], [2], [3]\]
```

### 4. 既存の標準形式

#### パターン定義
```python
STANDARD_PATTERNS = {
    'single': r'\[(\d+)\]',
    'multiple': r'\[(\d+(?:[,\s]+\d+)*)\]',
    'range': r'\[(\d+)[-–](\d+)\]',
    'footnote': r'\[\^(\d+)\]'
}
```

#### 変換例
```
入力: [1]
出力: [1] (変更なし)

入力: [2,3] または [2, 3] または [2 , 3]
出力: [2], [3] (スペース統一)

入力: [1-5]
出力: [1], [2], [3], [4], [5] (範囲展開)
```

## 処理アルゴリズム

### Phase 1: エスケープ解除とパターン検出

```python
def detect_escaped_patterns(text: str) -> List[CitationMatch]:
    """エスケープされたパターンを優先検出"""
    matches = []
    
    # 1. エスケープされたURL付き引用 (最優先)
    for pattern_name, regex in ESCAPED_LINKED_PATTERNS.items():
        for match in re.finditer(regex, text):
            citation_match = create_escaped_linked_match(match, pattern_name)
            matches.append(citation_match)
    
    # 2. エスケープされた脚注引用
    for pattern_name, regex in ESCAPED_FOOTNOTE_PATTERNS.items():
        for match in re.finditer(regex, text):
            citation_match = create_escaped_footnote_match(match, pattern_name)
            matches.append(citation_match)
    
    # 3. エスケープされた基本引用
    for pattern_name, regex in ESCAPED_BASIC_PATTERNS.items():
        for match in re.finditer(regex, text):
            citation_match = create_escaped_basic_match(match, pattern_name)
            matches.append(citation_match)
    
    return remove_overlapping_matches(matches)
```

### Phase 2: URL抽出とリンク表生成

```python
def extract_links_from_escaped_citations(matches: List[CitationMatch]) -> Tuple[List[LinkEntry], List[CitationMatch]]:
    """エスケープされた引用からリンクを抽出"""
    link_entries = []
    cleaned_matches = []
    
    for match in matches:
        if match.has_link and match.link_url:
            # 各引用番号に対してリンクエントリを作成
            for citation_num in match.citation_numbers:
                link_entry = LinkEntry(
                    citation_number=citation_num,
                    url=match.link_url,
                    original_text=match.original_text
                )
                link_entries.append(link_entry)
            
            # リンクなしの引用マッチを作成
            cleaned_match = CitationMatch(
                original_text=match.original_text,
                citation_numbers=match.citation_numbers,
                has_link=False,
                link_url=None,
                pattern_type='cleaned_escaped',
                start_pos=match.start_pos,
                end_pos=match.end_pos
            )
            cleaned_matches.append(cleaned_match)
        else:
            cleaned_matches.append(match)
    
    return link_entries, cleaned_matches
```

### Phase 3: 統一フォーマット変換

```python
def convert_to_unified_format(matches: List[CitationMatch]) -> str:
    """統一フォーマットに変換"""
    
    # 統一変換ルール
    UNIFIED_FORMAT_RULES = {
        'single_template': '[{number}]',
        'multiple_separator': '], [',
        'multiple_template': '[{numbers}]',
        'sort_numbers': True,
        'expand_ranges': True,
        'individual_citations': True  # 常に個別の引用として出力
    }
    
    for match in sorted(matches, key=lambda x: x.start_pos, reverse=True):
        # 引用番号の正規化
        normalized_numbers = normalize_citation_numbers(match.citation_numbers)
        
        # エスケープパターンかどうかの判定
        is_escaped_pattern = match.pattern_type.startswith('escaped_')
        
        # 個別の引用として出力
        if len(normalized_numbers) == 1:
            unified_citation = f"[{normalized_numbers[0]}]"
        else:
            # 複数の場合は個別の引用として分離
            individual_citations = [f"[{num}]" for num in normalized_numbers]
            unified_citation = ', '.join(individual_citations)
        
        # エスケープパターンの場合は外側に \[\] を追加
        if is_escaped_pattern:
            unified_citation = f"\\[{unified_citation}\\]"
        
        # テキスト置換
        text = replace_citation_in_text(text, match, unified_citation)
    
    return text
```

## 設定とカスタマイズ

### デフォルト設定

```yaml
# config/citation_parser_enhanced.yaml
citation_parser:
  # パターン検出設定
  pattern_detection:
    enable_escaped_patterns: true
    priority_order:
      - escaped_linked
      - escaped_footnote  
      - escaped_basic
      - standard_linked
      - standard_range
      - standard_multiple
      - standard_single
  
  # 変換設定
  conversion:
    output_format: "individual" # individual | grouped
    separator: ", "
    expand_ranges: true
    sort_numbers: true
    remove_duplicates: true
  
  # エスケープ処理設定
  escape_handling:
    auto_detect: true
    preserve_original: false
    log_conversions: true
```

### 出力フォーマット設定

```python
class UnifiedOutputFormat:
    """統一出力フォーマット設定"""
    
    INDIVIDUAL_FORMAT = {
        'single': '[{number}]',
        'multiple': '[{num1}], [{num2}], [{num3}]...',
        'separator': '], ['
    }
    
    GROUPED_FORMAT = {
        'single': '[{number}]', 
        'multiple': '[{numbers}]',
        'separator': ', '
    }
```

## テスト仕様

### テストケース

#### 1. エスケープ基本形式テスト
```python
def test_escaped_basic_citations():
    test_cases = [
        ('\[[1]\]', '\[[1]\]'),
        ('\[[12], [13]\]', '\[[12], [13]\]'),
        ('\[[1,2,3]\]', '\[[1], [2], [3]\]'),
        ('\[[10]\]', '\[[10]\]'),
    ]
    
    for input_text, expected in test_cases:
        result = parser.parse_document(input_text)
        assert result.converted_text == expected
```

#### 2. エスケープURL付き形式テスト
```python
def test_escaped_linked_citations():
    test_cases = [
        (
            '\[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\]',
            '\[[4], [5], [6], [7], [8]\]'
        ),
        (
            '\[[1](https://example.com)\]',
            '\[[1]\]'
        ),
    ]
    
    for input_text, expected in test_cases:
        result = parser.parse_document(input_text)
        assert result.converted_text == expected
        # リンク表も検証
        assert len(result.link_table) > 0
```

#### 3. エスケープ脚注形式テスト
```python
def test_escaped_footnote_citations():
    """
    エスケープ脚注パターンのテスト
    
    重要: 脚注パターン（^記号）は通常の引用パターンに変換される
    すべての引用は統一フォーマット \[[number]\] になる
    """
    test_cases = [
        ('\[[^1]\]', '\[[1]\]'),              # 脚注 → 通常引用
        ('\[[^10]\]', '\[[10]\]'),            # 脚注 → 通常引用
        ('\[[^27]\]', '\[[27]\]'),            # 脚注 → 通常引用
        ('\[[^1],[^2],[^3]\]', '\[[1], [2], [3]\]'),  # 複数脚注 → 個別通常引用
        ('\[[^22], [^23]\]', '\[[22], [23]\]'),       # 複数脚注 → 個別通常引用
    ]
    
    for input_text, expected in test_cases:
        result = parser.parse_document(input_text)
        assert result.converted_text == expected
        
    # 重要な注意: 
    # - 脚注の^記号は除去される
    # - すべての引用は \[[number]\] 形式に統一される
    # - 複数脚注は個別の引用に分離される
```

#### 4. 混在形式テスト
```python
def test_mixed_citation_formats():
    input_text = """
    This study \[[1]\] builds on previous work \[[2], [3]\].
    Additional references \[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\]
    and footnotes \[[^10],[^11],[^12]\] support the findings.
    """
    
    expected = """
    This study \[[1]\] builds on previous work \[[2], [3]\].
    Additional references \[[4], [5], [6], [7], [8]\]
    and footnotes \[[10], [11], [12]\] support the findings.
    """
    
    result = parser.parse_document(input_text)
    assert normalize_whitespace(result.converted_text) == normalize_whitespace(expected)
```

## 実装ロードマップ

### Phase 1: パターン検出強化
1. EscapedPatternDetector クラス実装
2. 既存PatternDetectorへの統合
3. 優先度ベースの検出ロジック

### Phase 2: 変換エンジン改善  
1. UnifiedFormatConverter クラス実装
2. 個別引用出力対応
3. リンク抽出とクリーンアップ強化

### Phase 3: テスト・検証
1. 包括的テストスイート作成
2. TestManuscriptsでの実地テスト
3. パフォーマンス最適化

### Phase 4: 統合・リリース
1. 既存ワークフローへの統合
2. 設定システム更新
3. ドキュメント更新

## 期待される効果

### 統一性の向上
- エスケープパターンは `\[[1]\]`, `\[[2], [3], [4]\]` 形式に統一
- 標準パターンは `[1]`, `[2], [3], [4]` 形式に統一  
- エスケープと標準の適切な区別維持
- URL付き引用の適切な分離とリンク表生成

### 可読性の改善
- パターン別の一貫した引用フォーマット
- エスケープパターンの外側括弧保持による明確な区別
- 明確な個別引用表現

### データ品質向上
- 引用番号の正規化
- 重複の自動除去
- 範囲の展開による明示化 

#### 統一フォーマット原則

**すべての引用は以下の統一フォーマットになる：**

1. **単一引用**: `\[[24]\]`
2. **複数引用**: `\[[20], [21], [22]\]` （個別形式）
3. **脚注も同様**: `\[[^27]\]` → `\[[27]\]`（^記号除去）
4. **URL付きも同様**: `\[[4,5,6](URL)\]` → `\[[4], [5], [6]\]`

**許可されない形式：**
- `\[[^27]\]` （脚注記号は変換される）
- `\[[20,21,22]\]` （グループ化は個別化される）
- `[27]` （エスケープなしは対象外） 