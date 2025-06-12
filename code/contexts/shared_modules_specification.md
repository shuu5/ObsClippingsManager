# 共有モジュール仕様書 v3.1

## 概要
ObsClippingsManager v3.1の共有モジュールは、全システムで使用される基盤機能を提供し、システム全体の一貫性を保証します。

## モジュール構成
```
modules/shared/
├── config_manager.py      # 統一設定管理システム
├── logger.py             # 統合ログシステム
├── bibtex_parser.py      # BibTeX解析エンジン
├── utils.py              # 共通ユーティリティ
├── exceptions.py         # 階層的例外管理
└── claude_api_client.py  # Claude API統合クライアント
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

# AI機能設定
ai_generation:
  claude_api_key: "your-api-key"
  tagger:
    enabled: false
    model: "claude-3-5-sonnet-20241022"
    batch_size: 5
    tag_count_range: [10, 20]
  translate_abstract:
    enabled: false
    model: "claude-3-5-sonnet-20241022"
    batch_size: 3
    preserve_formatting: true
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
        "journal": "Example Journal"
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
- **階層的処理**: 具体的なエラーから汎用的なエラーへの段階的処理
- **ログ記録**: 全例外の適切なログ出力
- **ユーザー通知**: わかりやすいエラーメッセージの提供
- **復旧処理**: 可能な場合の自動復旧実行

## ClaudeAPIClient - Claude API統合クライアント（v3.1新機能）

### 基本機能
- **API通信**: Claude 3.5 Sonnetとの統合通信
- **バッチ処理**: 複数リクエストの並列処理
- **エラーハンドリング**: API制限・ネットワークエラーの適切な処理
- **レート制限**: API呼び出し頻度制御

### 主要メソッド
```python
class ClaudeAPIClient:
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger)
    async def generate_tags_batch(self, papers_content: List[str]) -> List[List[str]]
    async def translate_abstracts_batch(self, abstracts: List[str]) -> List[str]
    def handle_api_errors(self, error: Exception) -> Dict[str, Any]
```

### 設定項目
```python
{
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "your-claude-api-key",
    "request_delay": 1.0,
    "max_retries": 3,
    "timeout": 30,
    "batch_size": 5
}
```

## 使用パターン

### 基本的な初期化
```python
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.bibtex_parser import BibTeXParser

# 基本設定
config_manager = ConfigManager()
logger = IntegratedLogger()
bibtex_parser = BibTeXParser(logger.get_logger('BibTeXParser'))
```

### エラーハンドリング例
```python
try:
    # 何らかの処理
    result = process_something()
except BibTeXParsingError as e:
    logger.error(f"BibTeX parsing failed: {e}")
    # BibTeX特有の処理
except FileOperationError as e:
    logger.error(f"File operation failed: {e}")
    # ファイル操作特有の処理
except ObsClippingsManagerError as e:
    logger.error(f"General error: {e}")
    # 汎用エラー処理
```

## 設計原則

### 単一責任原則
- 各モジュールは明確に定義された単一の責任を持つ
- 機能の重複を避け、保守性を向上

### 依存性の最小化
- モジュール間の依存関係を最小限に抑制
- 変更の影響範囲を制限

### 設定の一元化
- 全設定をConfigManagerで一元管理
- 環境による設定切り替えの容易性確保

### ログの統一
- 全モジュールでIntegratedLoggerを使用
- 一貫したログフォーマットでデバッグ効率向上

---

**共有モジュール仕様書バージョン**: 3.1.0 