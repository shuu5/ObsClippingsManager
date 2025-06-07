# 引用文献統一化パーサー仕様書

## 概要
様々な形式で記載された引用文献を統一されたフォーマットに変換し、リンク付き引用からは対応表を生成するパーサーシステムの仕様を定義する。

## 機能要件

### 1. 基本機能
- **引用パターン検出**: 複数の引用形式を自動検出
- **統一フォーマット変換**: 検出した引用を標準形式に変換
- **リンク抽出**: リンク付き引用からURLを抽出し、対応表を生成
- **エラー処理**: 不正な引用形式の検出と報告

### 2. 対応する引用パターン

#### Phase 1: 基本パターン
1. **単一引用**: `[1]`, `[13]`, `[^5]`
2. **複数引用**: `[1, 2]`, `[17, 18]`, `[^1,^2]`
3. **範囲引用**: `[1-5]`, `[4–8]`, `[14–21]`
4. **リンク付き**: `[1](URL)`, `[^2](URL)`

#### Phase 2: 高度なパターン
1. **混合形式**: `[23] – [25]`, `[26,27,28], [34]`
2. **スペース処理**: `[1 , 2]`, `[3,  4]`
3. **特殊文字**: `[1–3]`, `[4-6]` （異なるダッシュ文字）

#### Phase 3: 将来拡張
1. **著者年**: `(Smith et al., 2020)`
2. **複合引用**: `[1a, 1b]`
3. **章節引用**: `[Chapter 1.2]`

### 3. 統一フォーマット仕様

#### 出力形式
```
単一引用: [1]
複数引用: [1,2,3]
範囲引用: [1,2,3,4,5] （個別展開）
```

#### リンク対応表形式
```markdown
## 引用文献リンク対応表

| 引用番号 | URL |
|---------|-----|
| [1] | https://www.example.com/article1 |
| [2] | https://academic.oup.com/article2 |
| [^3] | https://doi.org/10.1000/example |
```

## システム設計

### 1. アーキテクチャ

```
CitationParser
├── PatternDetector      # パターン検出エンジン
├── FormatConverter      # フォーマット変換エンジン
├── LinkExtractor        # リンク抽出エンジン
├── ConfigManager        # 設定管理
├── ErrorHandler         # エラー処理
└── OutputGenerator      # 出力生成
```

### 2. クラス設計

#### CitationParser（メインクラス）
```python
class CitationParser:
    def __init__(self, config_path: str = None)
    def parse_document(self, text: str) -> CitationResult
    def add_pattern(self, pattern: PatternConfig) -> None
    def set_output_format(self, format_type: str) -> None
```

#### PatternDetector
```python
class PatternDetector:
    def detect_patterns(self, text: str) -> List[CitationMatch]
    def register_pattern(self, pattern: RegexPattern) -> None
    def get_pattern_stats(self) -> Dict[str, int]
```

#### FormatConverter
```python
class FormatConverter:
    def convert_to_unified(self, matches: List[CitationMatch]) -> str
    def expand_ranges(self, range_citation: str) -> List[int]
    def standardize_spacing(self, citation: str) -> str
```

### 3. データ構造

#### CitationMatch
```python
@dataclass
class CitationMatch:
    original_text: str
    citation_numbers: List[int]
    has_link: bool
    link_url: Optional[str] = None
    pattern_type: str = ""
    start_pos: int = 0
    end_pos: int = 0
```

#### CitationResult
```python
@dataclass
class CitationResult:
    converted_text: str
    link_table: List[LinkEntry]
    statistics: ProcessingStats
    errors: List[ProcessingError]
```

### 4. 設定ファイル仕様

#### citation_patterns.yaml
```yaml
patterns:
  basic_citation:
    regex: '\[(\d+)\]'
    type: 'single'
    priority: 1
    
  range_citation:
    regex: '\[(\d+)[-–](\d+)\]'
    type: 'range'
    priority: 2
    
  multiple_citation:
    regex: '\[(\d+(?:,\s*\d+)*)\]'
    type: 'multiple'
    priority: 3
    
  footnote_citation:
    regex: '\[\^(\d+)\]'
    type: 'footnote'
    priority: 4
    
  linked_citation:
    regex: '\[(\d+|\^?\d+)\]\([^)]+\)'
    type: 'linked'
    priority: 5

output_formats:
  standard:
    single: '[{number}]'
    multiple: '[{numbers}]'
    separator: ','
    
conversion_rules:
  expand_ranges: true
  remove_spaces: false
  sort_numbers: true
```

## 実装詳細

### 1. パターンマッチング

#### 正規表現パターン定義
```python
CITATION_PATTERNS = {
    'single': r'\[(\d+)\]',
    'range': r'\[(\d+)[-–](\d+)\]',
    'multiple': r'\[(\d+(?:[,\s]+\d+)*)\]',
    'footnote': r'\[\^(\d+)\]',
    'linked': r'\[(\^?\d+)\]\(([^)]+)\)',
    'mixed_footnote': r'\[\^(\d+(?:,\^?\d+)*)\]'
}
```

#### パターン優先順位
1. リンク付き引用（最優先）
2. 脚注引用
3. 範囲引用
4. 複数引用
5. 単一引用

### 2. 変換アルゴリズム

#### 範囲展開
```python
def expand_range(start: int, end: int) -> List[int]:
    """範囲引用を個別の引用番号に展開"""
    return list(range(start, end + 1))

def process_range_citation(match: str) -> str:
    """[1-5] → [1,2,3,4,5]"""
    numbers = expand_range(start, end)
    return f"[{','.join(map(str, numbers))}]"
```

#### リンク処理
```python
def extract_links(text: str) -> Tuple[str, List[LinkEntry]]:
    """リンク付き引用を処理し、テキストとリンク表を返す"""
    links = []
    clean_text = text
    
    for match in find_linked_citations(text):
        citation_num = match.citation_numbers[0]
        url = match.link_url
        
        # リンクを除去
        clean_text = clean_text.replace(match.original_text, 
                                      f'[{citation_num}]')
        
        # リンク表に追加
        links.append(LinkEntry(citation_num, url))
    
    return clean_text, links
```

### 3. エラー処理

#### エラータイプ
```python
class ProcessingError(Exception):
    ERROR_TYPES = {
        'INVALID_RANGE': '無効な範囲指定',
        'MISSING_CITATION': '引用番号なし',
        'DUPLICATE_LINK': '重複リンク',
        'MALFORMED_PATTERN': '不正なパターン'
    }
```

#### バリデーション
```python
def validate_citation_range(start: int, end: int) -> bool:
    """範囲引用の妥当性チェック"""
    return start <= end and start > 0

def validate_citation_sequence(numbers: List[int]) -> bool:
    """引用番号シーケンスの妥当性チェック"""
    return all(n > 0 for n in numbers)
```

## API仕様

### 1. 基本API

#### パース実行
```python
parser = CitationParser()
result = parser.parse_document(markdown_text)

# 結果アクセス
converted_text = result.converted_text
link_table = result.link_table
errors = result.errors
```

#### 設定変更
```python
parser.set_output_format('compact')  # [1,2,3] 形式
parser.set_output_format('spaced')   # [1, 2, 3] 形式
parser.add_custom_pattern(pattern_config)
```

### 2. 高度なAPI

#### バッチ処理
```python
def process_directory(directory_path: str) -> Dict[str, CitationResult]:
    """ディレクトリ内の全markdownファイルを処理"""
    
def generate_unified_link_table(results: List[CitationResult]) -> str:
    """複数ファイルから統合リンク表を生成"""
```

#### 統計情報
```python
def get_processing_stats(result: CitationResult) -> ProcessingStats:
    """処理統計を取得"""
    return ProcessingStats(
        total_citations=100,
        converted_citations=95,
        errors=5,
        pattern_breakdown={'single': 60, 'range': 25, 'linked': 10}
    )
```

## テスト仕様

### 1. 単体テスト

#### パターン検出テスト
```python
def test_single_citation_detection():
    text = "This is referenced [1] in the paper."
    matches = detector.detect_patterns(text)
    assert len(matches) == 1
    assert matches[0].citation_numbers == [1]

def test_range_citation_conversion():
    text = "Studies [1-3] show that..."
    result = converter.convert_to_unified(text)
    assert "[1,2,3]" in result.converted_text
```

#### エラーケーステスト
```python
def test_invalid_range_handling():
    text = "Invalid range [5-3] citation"
    result = parser.parse_document(text)
    assert len(result.errors) > 0
    assert result.errors[0].type == 'INVALID_RANGE'
```

### 2. 統合テスト

#### 実論文テスト
```python
def test_real_paper_processing():
    """実際の論文ファイルでのテスト"""
    with open('test_papers/liQ2016Oncotarget.md') as f:
        content = f.read()
    
    result = parser.parse_document(content)
    assert result.statistics.total_citations > 0
    assert len(result.errors) == 0
```

## 拡張性設計

### 1. プラグインアーキテクチャ

#### パターンプラグイン
```python
class PatternPlugin:
    def get_pattern_name(self) -> str
    def get_regex_pattern(self) -> str
    def process_match(self, match: re.Match) -> CitationMatch
```

#### フォーマッタープラグイン
```python
class FormatterPlugin:
    def get_format_name(self) -> str
    def format_citation(self, numbers: List[int]) -> str
```

### 2. 設定ベース拡張

#### 新パターン追加
```yaml
# custom_patterns.yaml
custom_patterns:
  author_year:
    regex: '\(([A-Za-z]+\s+et\s+al\.,\s+\d{4})\)'
    type: 'author_year'
    converter: 'author_year_to_numeric'
```

## パフォーマンス要件

### 1. 処理速度
- **小規模文書** (< 100KB): < 1秒
- **中規模文書** (< 1MB): < 5秒
- **大規模文書** (< 10MB): < 30秒

### 2. メモリ使用量
- **基本処理**: < 100MB
- **バッチ処理**: < 500MB

### 3. 最適化手法
- 正規表現コンパイル結果のキャッシュ
- 大文書の分割処理
- 並列処理サポート

## セキュリティ考慮事項

### 1. 入力検証
- ファイルサイズ制限
- 悪意あるパターンの検出
- メモリ消費量の監視

### 2. 出力検証
- URLの妥当性チェック
- XSSの防止（HTML出力時）

## 運用・保守

### 1. ログ出力
```python
# 処理ログ
logger.info(f"Processed {total_citations} citations")
logger.warning(f"Found {error_count} errors")
logger.error(f"Failed to process: {error_detail}")
```

### 2. 監視項目
- 処理成功率
- エラー発生頻度
- パフォーマンス指標

### 3. アップデート対応
- パターン定義の更新
- 新しい論文形式への対応
- バグ修正とセキュリティパッチ

## 実装優先度

### Phase 1（必須機能）
1. 基本パターン検出
2. 統一フォーマット変換
3. リンク抽出と対応表生成
4. エラー処理

### Phase 2（拡張機能）
1. 設定ファイル対応
2. バッチ処理
3. プラグインシステム
4. 詳細な統計情報

### Phase 3（高度機能）
1. 複数フォーマット間変換
2. 機械学習による自動パターン検出
3. リアルタイム処理
4. Web API提供

## main.py統合仕様

### 1. 統合アーキテクチャ

#### ワークフローベース統合
citation_parserはObsClippingsManager v2.0の統合アーキテクチャに従い、専用ワークフローとして統合されます。

```
modules/workflows/citation_parser_workflow.py
├── CitationParserWorkflow       # ワークフロー実行クラス
├── workflow_executor()          # メイン実行関数
├── validate_inputs()           # 入力検証
└── generate_report()           # 実行結果レポート
```

#### 統合ポイント
1. **main.pyコマンド**: `parse-citations`コマンドとして追加
2. **IntegratedController**: `execute_citation_parser_workflow()`メソッド追加
3. **統合実行**: `run-integrated`コマンドでのオプション統合

### 2. CLIコマンド仕様

#### 基本コマンド
```bash
PYTHONPATH=code/py uv run python code/py/main.py parse-citations [OPTIONS]
```

#### 主要オプション
- `--input-file PATH`: 入力Markdownファイルパス（必須）
- `--output-file PATH`: 出力ファイルパス（省略時は標準出力）
- `--pattern-type [basic|advanced|all]`: パース対象パターン（デフォルト: all）
- `--output-format [unified|table|json]`: 出力フォーマット（デフォルト: unified）
- `--enable-link-extraction`: リンク抽出・対応表生成（デフォルト: False）
- `--expand-ranges`: 範囲引用の個別展開（デフォルト: True）
- `--config-file PATH`: カスタム設定ファイル
- `--dry-run`: ドライラン実行
- `--verbose`: 詳細出力

### 3. 設定統合

#### ConfigManager統合
```python
# デフォルト設定（ConfigManagerに追加）
"citation_parser": {
    "default_pattern_type": "all",
    "default_output_format": "unified",
    "enable_link_extraction": False,
    "expand_ranges": True,
    "max_file_size_mb": 10,
    "output_encoding": "utf-8",
    "pattern_config_file": "modules/citation_parser/patterns.yaml"
}
```

#### 設定アクセス
```python
parser_config = config.get_citation_parser_config()
pattern_type = config.get('citation_parser.default_pattern_type')
```

### 4. ワークフロー統合

#### CitationParserWorkflow実装
```python
class CitationParserWorkflow:
    def __init__(self, config: ConfigManager, logger: IntegratedLogger):
        self.config = config
        self.logger = logger
        self.parser = CitationParser(config.get_citation_parser_config())
    
    def execute(self, input_file: str, **options) -> WorkflowResult:
        """メイン実行メソッド"""
        
    def validate_inputs(self, input_file: str) -> bool:
        """入力ファイル検証"""
        
    def generate_report(self, result: CitationResult) -> str:
        """実行結果レポート生成"""
```

#### 統合実行での実行順序
```python
# run-integrated コマンドでの実行順序
def execute_integrated_workflow(self, include_citation_parser=False):
    workflows = []
    
    if self.config.get('workflows.integrated_order') == 'citation_first':
        workflows = ['citation_fetcher', 'organization']
    else:
        workflows = ['organization', 'citation_fetcher']
    
    if include_citation_parser:
        workflows.append('citation_parser')
    
    # 各ワークフローを順次実行
    for workflow_name in workflows:
        self.execute_workflow(workflow_name)
```

### 5. IntegratedController統合

#### メソッド追加
```python
class IntegratedController:
    def execute_citation_parser_workflow(self, input_file: str, **options) -> bool:
        """引用文献パースワークフロー実行"""
        try:
            workflow = CitationParserWorkflow(self.config, self.logger)
            result = workflow.execute(input_file, **options)
            
            self.logger.log_workflow_end('citation_parser', 
                                       result.success, 
                                       result.duration)
            return result.success
            
        except Exception as e:
            self.logger.error(f"Citation parser workflow failed: {e}")
            return False
```

### 6. エラーハンドリング統合

#### 例外クラス追加
```python
# modules/shared/exceptions.py に追加
class CitationParserError(ObsClippingsManagerError):
    """引用文献パース関連エラー"""
    pass

class InvalidCitationPatternError(CitationParserError):
    """無効な引用パターンエラー"""
    pass

class CitationParseTimeoutError(CitationParserError):
    """パース処理タイムアウトエラー"""
    pass
```

### 7. ログ統合

#### ワークフローログ
```python
# 実行開始ログ
self.logger.log_workflow_start('citation_parser')

# 処理中ログ
self.logger.info(f"Processing file: {input_file}")
self.logger.info(f"Found {total_citations} citations")
self.logger.info(f"Converted {converted_count} citations")

# 実行終了ログ
self.logger.log_workflow_end('citation_parser', success=True, duration=elapsed_time)
```

### 8. 統計情報統合

#### システム統計への統合
```python
def get_system_stats(self):
    stats = super().get_system_stats()
    
    # citation_parser統計を追加
    parser_stats = self.get_citation_parser_stats()
    stats.update({
        'citation_parser_executions': parser_stats.total_executions,
        'citation_parser_success_rate': parser_stats.success_rate,
        'total_citations_processed': parser_stats.total_citations,
        'average_processing_time': parser_stats.avg_processing_time
    })
    
    return stats
```

### 9. 実行例

#### 基本実行
```bash
# 基本的な引用文献パース
PYTHONPATH=code/py uv run python code/py/main.py parse-citations --input-file paper.md

# リンク抽出付きパース
PYTHONPATH=code/py uv run python code/py/main.py parse-citations \
  --input-file paper.md \
  --output-file processed.md \
  --enable-link-extraction

# 統合実行に含める
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
  --include-citation-parser
```

### 10. 独立性の確保

#### モジュール独立性
- citation_parserモジュールは他のモジュールに依存しない
- 共有モジュール（shared）のみに依存
- main.pyから切り離し可能な設計

#### 設定独立性
- 専用設定セクションでの分離
- 他機能の設定に影響しない
- デフォルト設定での単独動作保証

この統合仕様により、citation_parser機能を既存システムに拡張性と独立性を保ちながら統合できる。 