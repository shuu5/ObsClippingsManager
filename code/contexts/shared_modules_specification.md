# 共有モジュール仕様書

## 概要
ObsClippingsManagerの共有モジュールは、全システムで使用される基盤機能を提供し、システム全体の一貫性を保証します。

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
- **AI機能統合**: Claude 3.5 Haiku統一設定

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

# AI機能設定（デフォルト有効）
ai_generation:
  default_model: "claude-3-5-haiku-20241022"
  claude_api_key: "your-api-key"
  tagger:
    enabled: true
    batch_size: 8
    tag_count_range: [10, 20]
  translate_abstract:
    enabled: true
    batch_size: 5
    preserve_formatting: true
  ochiai_format:
    enabled: true
    batch_size: 3
  section_parsing:
    enabled: true
```

## IntegratedLogger - 統合ログシステム

### 基本機能
- **統一ログ形式**: 全モジュール共通のログフォーマット
- **ファイル出力**: ログファイルへの永続化
- **レベル制御**: debug/info/warning/error
- **モジュール分離**: モジュール別ログ出力

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
安全なファイル操作、パス正規化、ディレクトリ管理機能を提供します。

### 文字列処理
ファイル名正規化、類似度計算、DOI処理等の汎用文字列操作機能を提供します。

### DOI処理
DOI形式の正規化、検証、URL変換等のDOI関連ユーティリティを提供します。

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

## ClaudeAPIClient - Claude API統合クライアント

### 基本機能
- **API通信**: Claude 3.5 Haikuとの統合通信
- **バッチ処理**: 複数リクエストの並列処理
- **エラーハンドリング**: API制限・ネットワークエラーの適切な処理
- **レート制限**: API呼び出し頻度制御

### 統一AI技術スタック
- **モデル**: Claude 3.5 Haiku
- **バッチサイズ最適化**: Haikuの高速処理特性を活用
- **並列処理**: 効率的な大量処理実現

### 設定項目
```python
{
    "model": "claude-3-5-haiku-20241022",
    "api_key": "your-claude-api-key",
    "request_delay": 0.5,  # Haikuの高速応答に最適化
    "max_retries": 3,
    "timeout": 30,
    "batch_size": 8  # Haikuの効率性を活用
}
```

## ワークフロークラス実装

### 基本設計パターン
各機能モジュールは以下の統一パターンで実装されます：

#### 共通インターフェース
```python
class BaseWorkflow:
    """ワークフロー基底クラス"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger(self.__class__.__name__)
        
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None) -> Dict[str, Any]:
        """論文の一括処理"""
        
    def process_single_paper(self, paper_path: str) -> Any:
        """単一論文の処理"""
```

#### 具体的ワークフロー実装例
- **OrganizationWorkflow**: ファイル整理
- **SyncCheckWorkflow**: 同期チェック
- **CitationWorkflow**: 引用文献取得
- **SectionParserWorkflow**: セクション分割
- **AICitationSupportWorkflow**: AI理解支援
- **TaggerWorkflow**: タグ生成
- **TranslateAbstractWorkflow**: 要約翻訳
- **OchiaiFormatWorkflow**: 落合フォーマット要約

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

### AI機能統合
- Claude 3.5 Haiku統一による一貫したAI処理
- バッチ処理最適化による効率的実行
- エラーハンドリング統一による安定性確保 