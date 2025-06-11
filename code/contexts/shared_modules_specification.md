# 共有モジュール仕様書 v3.0

## 概要
ObsClippingsManager v3.0の共有モジュールは、全システムで使用される基盤機能を提供します。統一設定管理、ログシステム、BibTeX解析、例外処理などの重要な機能を独立したモジュールとして実装し、システム全体の一貫性を保証します。

## モジュール構成

### 共有モジュール一覧
```
modules/shared/
├── config_manager.py      # 統一設定管理システム
├── logger.py             # 統合ログシステム
├── bibtex_parser.py      # BibTeX解析エンジン
├── utils.py              # 共通ユーティリティ
└── exceptions.py         # 階層的例外管理
```

## ConfigManager - 統一設定管理

### 基本機能
- **ワークスペース統一管理**: 単一パス設定での全パス自動導出
- **設定階層**: コマンドライン引数 > 設定ファイル > デフォルト値
- **設定検証**: 実行前の設定妥当性チェック

### 設定構造
```yaml
# config/config.yaml（デフォルト設定）
workspace_path: "/home/user/ManuscriptsManager"

# 自動導出設定（内部処理）
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"

# API設定
api_settings:
  request_delay: 1.0
  max_retries: 3
  timeout: 30

# 処理設定
processing:
  similarity_threshold: 0.8
  auto_approve: false

# AI理解支援設定（v3.0新機能）
ai_citation_support:
  enabled: false                    # デフォルトは無効
  complete_mapping: true            # 完全統合マッピング作成
  update_yaml_header: true          # YAMLヘッダー更新
  backup_original: true             # 元ファイルバックアップ
  include_abstracts: true           # 要約情報の含有
```

### 主要メソッド
```python
class ConfigManager:
    def __init__(self, config_file: str = None)
    def get_setting(self, key: str, default: Any = None) -> Any
    def resolve_paths(self, workspace_path: str = None, **overrides) -> Dict[str, str]
    def validate_configuration(self, paths: Dict[str, str]) -> Dict[str, Any]
    def merge_options(self, **options) -> Dict[str, Any]
```

## IntegratedLogger - 統合ログシステム

### 基本機能
- **統一ログ形式**: 全モジュール共通のログフォーマット
- **ファイル出力**: ログファイルへの永続化
- **レベル制御**: debug/info/warning/error
- **モジュール分離**: モジュール別ログ出力

### ログ設定
```python
class IntegratedLogger:
    def __init__(self, log_level: str = 'info', verbose: bool = False, 
                 log_file: str = None)
    def get_logger(self, module_name: str) -> logging.Logger
    def set_log_level(self, level: str)
    def configure_file_output(self, log_file: str)
```

### ログフォーマット
```
2025-01-15 10:30:00 [INFO] IntegratedWorkflow: Starting integrated workflow execution
2025-01-15 10:30:01 [DEBUG] StatusManager: Loading status from /path/to/clippings
2025-01-15 10:30:02 [WARNING] OrganizeWorkflow: Paper smith2023 already organized, skipping
```

## BibTeXParser - BibTeX解析エンジン

### 基本機能
- **ファイル解析**: BibTeXファイルの読み込み・パース
- **エントリ抽出**: 個別論文エントリの取得
- **メタデータ正規化**: タイトル、DOI等の正規化
- **エラーハンドリング**: 構文エラーの適切な処理

### 主要メソッド
```python
class BibTeXParser:
    def __init__(self, logger: logging.Logger)
    def parse_file(self, bibtex_file: str) -> Dict[str, Dict[str, str]]
    def extract_citation_keys(self, bibtex_file: str) -> List[str]
    def get_entry_by_key(self, bibtex_file: str, citation_key: str) -> Dict[str, str]
    def normalize_title(self, title: str) -> str
    def extract_doi_from_entry(self, entry: Dict[str, str]) -> str
```

### 解析結果形式
```python
{
    "smith2023test": {
        "title": "Example Paper Title",
        "author": "Smith, John and Jones, Mary",
        "year": "2023",
        "doi": "10.1000/example.doi",
        "journal": "Example Journal",
        "volume": "42",
        "pages": "123-145"
    }
}
```

## Utils - 共通ユーティリティ

### ファイルシステム操作
```python
def ensure_directory(path: str) -> bool
def safe_file_move(src: str, dst: str) -> bool
def get_file_hash(file_path: str) -> str
def find_files_by_pattern(directory: str, pattern: str) -> List[str]
```

### 文字列処理
```python
def normalize_filename(filename: str) -> str
def sanitize_path(path: str) -> str
def calculate_similarity(text1: str, text2: str) -> float
def extract_year_from_string(text: str) -> str
```

### DOI処理
```python
def normalize_doi(doi: str) -> str
def validate_doi_format(doi: str) -> bool
def extract_doi_from_text(text: str) -> str
def doi_to_url(doi: str) -> str
```

## Exceptions - 階層的例外管理

### 例外階層
```python
class ObsClippingsManagerError(Exception):
    """ベース例外クラス"""
    pass

class ConfigurationError(ObsClippingsManagerError):
    """設定関連エラー"""
    pass

class BibTeXParsingError(ObsClippingsManagerError):
    """BibTeX解析エラー"""
    pass

class WorkflowExecutionError(ObsClippingsManagerError):
    """ワークフロー実行エラー"""
    pass

class APIClientError(ObsClippingsManagerError):
    """API通信エラー"""
    pass

class FileOperationError(ObsClippingsManagerError):
    """ファイル操作エラー"""
    pass
```

### エラーハンドリング戦略
```python
def handle_exception(exception: Exception, logger: logging.Logger, 
                    context: str = "") -> Dict[str, Any]:
    """
    統一例外処理
    
    Returns:
        {
            "status": "error",
            "error_type": "ConfigurationError",
            "message": "設定ファイルが見つかりません",
            "context": "config initialization"
        }
    """
```

## 実装例

### 設定初期化
```python
# 基本初期化
config_manager = ConfigManager()
logger = IntegratedLogger(log_level='info', verbose=True)

# パス解決
paths = config_manager.resolve_paths(workspace_path="/home/user/Project")
# → {
#     'workspace_path': '/home/user/Project',
#     'bibtex_file': '/home/user/Project/CurrentManuscript.bib',
#     'clippings_dir': '/home/user/Project/Clippings',
#     'output_dir': '/home/user/Project/Clippings'
# }
```

### BibTeX解析
```python
# BibTeX解析
bibtex_parser = BibTeXParser(logger.get_logger('BibTeXParser'))
entries = bibtex_parser.parse_file(paths['bibtex_file'])

# 特定エントリ取得
smith_entry = bibtex_parser.get_entry_by_key(paths['bibtex_file'], 'smith2023test')
doi = bibtex_parser.extract_doi_from_entry(smith_entry)
```

### ログ出力
```python
# モジュール別ログ
workflow_logger = logger.get_logger('IntegratedWorkflow')
status_logger = logger.get_logger('StatusManager')

workflow_logger.info("Starting workflow execution")
status_logger.debug(f"Loading statuses from {paths['clippings_dir']}")
```

### エラーハンドリング
```python
try:
    entries = bibtex_parser.parse_file(invalid_file)
except BibTeXParsingError as e:
    error_info = handle_exception(e, logger.get_logger('ErrorHandler'), 
                                 "BibTeX file parsing")
    return {"status": "error", "details": error_info}
```

## 依存関係

### 必須パッケージ
```txt
pyyaml>=6.0               # YAML設定ファイル処理
bibtexparser>=1.4.0       # BibTeX解析
fuzzywuzzy>=0.18.0        # 文字列類似度計算
python-levenshtein>=0.12.0 # 高速文字列比較
```

### 内部依存関係
- **ConfigManager**: 基盤クラス（他への依存なし）
- **IntegratedLogger**: 基盤クラス（他への依存なし）
- **BibTeXParser**: IntegratedLogger に依存
- **Utils**: 独立（他への依存なし）
- **Exceptions**: 独立（他への依存なし）

## テスト仕様

### テストカバレッジ
```python
# test_shared_modules.py
class TestConfigManager(unittest.TestCase):
    def test_path_resolution()
    def test_setting_hierarchy()
    def test_configuration_validation()

class TestIntegratedLogger(unittest.TestCase):
    def test_log_level_control()
    def test_file_output()
    def test_module_separation()

class TestBibTeXParser(unittest.TestCase):
    def test_file_parsing()
    def test_entry_extraction()
    def test_metadata_normalization()

class TestUtils(unittest.TestCase):
    def test_file_operations()
    def test_string_processing()
    def test_doi_handling()

class TestExceptions(unittest.TestCase):
    def test_exception_hierarchy()
    def test_error_handling()
```

## 使用ガイドライン

### 新機能実装時
1. **ConfigManager**: 新しい設定項目の追加
2. **IntegratedLogger**: モジュール別ログの設定
3. **BibTeXParser**: 必要に応じて解析機能拡張
4. **Utils**: 共通処理の関数化
5. **Exceptions**: 適切な例外クラスの定義

### パフォーマンス考慮
- **設定読み込み**: 初期化時の一度のみ
- **ログ出力**: レベル別フィルタリング
- **BibTeX解析**: キャッシュ機能の活用
- **ファイル操作**: 効率的なI/O処理

---

**共有モジュール仕様書バージョン**: 3.0.0 