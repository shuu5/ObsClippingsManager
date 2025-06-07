# 共通モジュール仕様書 v2.0

## 概要
共通モジュール（shared/）は、ObsClippingsManager v2.0 の核となる基盤機能を提供します。統合設定管理、統合ログシステム、高度BibTeX解析、階層的例外管理を含み、全モジュールで共有される重要な機能群です。

**v2.0 の特徴:**
- 完全統合されたConfigManager
- ファイル出力対応IntegratedLogger  
- 高性能BibTeXParser
- 階層的例外システム
- 共通ユーティリティ関数

## モジュール構成

```
modules/shared/
├── __init__.py               # 統合エクスポート
├── config_manager.py         # 統合設定管理 (ConfigManager)
├── logger.py                 # 統合ログシステム (IntegratedLogger)
├── bibtex_parser.py          # 高度BibTeX解析 (BibTeXParser)
├── utils.py                  # 共通ユーティリティ
└── exceptions.py             # 階層的例外管理
```

## 詳細機能仕様

### 1. 統合設定管理 (`config_manager.py`)
全システムの設定を一元管理する統合設定マネージャーです。

#### 主要機能
- **設定読み込み・保存**: JSON形式設定ファイル管理
- **ドット記法アクセス**: `config.get('common.log_level')` 形式
- **デフォルト設定**: 設定ファイル不要での動作
- **設定検証**: 必須パラメータ・パス存在確認
- **環境変数対応**: 環境変数からの設定上書き

#### デフォルト設定構造
```python
DEFAULT_INTEGRATED_CONFIG = {
    # 共通設定
    "common": {
        "bibtex_file": "/home/user/ManuscriptsManager/CurrentManuscript.bib",
        "clippings_dir": "/home/user/ManuscriptsManager/Clippings/",
        "output_dir": "/home/user/ManuscriptsManager/References/",
        "log_level": "INFO",
        "log_file": None,  # None = stdout only, str = file output
        "backup_enabled": True,
        "dry_run": False,
        "verbose": False
    },
    
    # Citation Fetcher設定
    "citation_fetcher": {
        "request_delay": 1.0,
        "max_retries": 3,
        "timeout": 30,
        "crossref_base_url": "https://api.crossref.org",
        "opencitations_endpoints": [
            "https://opencitations.net/index/api/v1",
            "https://w3id.org/oc/index/coci/api/v1"
        ],
        "user_agent": "ObsClippingsManager/2.0",
        "max_references_per_paper": 1000
    },
    
    # ファイル整理設定
    "organization": {
        "similarity_threshold": 0.8,
        "auto_approve": False,
        "create_directories": True,
        "cleanup_empty_dirs": True,
        "file_extensions": [".md", ".txt"],
        "exclude_patterns": ["*.tmp", ".*"]
    },
    
    # ワークフロー設定
    "workflows": {
        "integrated_order": "citation_first",  # citation_first | organization_first
        "continue_on_error": False,
        "report_format": "summary",  # summary | detailed | minimal
        "history_retention_days": 30
    },
    
    # Citation Parser設定
    "citation_parser": {
        "default_pattern_type": "all",  # basic | advanced | all
        "default_output_format": "unified",  # unified | table | json
        "enable_link_extraction": False,
        "expand_ranges": True,
        "max_file_size_mb": 10,
        "output_encoding": "utf-8",
        "pattern_config_file": "modules/citation_parser/patterns.yaml",
        "processing_timeout": 60
    }
}
```

#### API概要
- `get(key, default=None)`: ドット記法での設定取得
- `set(key, value)`: ドット記法での設定設定
- `get_citation_fetcher_config()`: Citation Fetcher用設定取得
- `get_organization_config()`: ファイル整理用設定取得
- `get_citation_parser_config()`: Citation Parser用設定取得
- `validate()`: 設定妥当性チェック

### 2. 統合ログシステム (`logger.py`)
ファイル出力対応の統合ログシステムです。

#### 主要機能
- **マルチ出力**: コンソール + ファイル出力
- **ログレベル制御**: DEBUG, INFO, WARNING, ERROR
- **ワークフロー専用ログ**: 開始・終了・統計ログ
- **フォーマット統一**: タイムスタンプ付き統一フォーマット
- **非同期書き込み**: 高性能ファイル出力

#### API概要
- `info(message, **kwargs)`: 情報ログ
- `warning(message, **kwargs)`: 警告ログ
- `error(message, **kwargs)`: エラーログ
- `debug(message, **kwargs)`: デバッグログ
- `log_workflow_start(workflow_name)`: ワークフロー開始ログ
- `log_workflow_end(workflow_name, success, duration)`: ワークフロー終了ログ

### 3. 高度BibTeX解析 (`bibtex_parser.py`)
高性能BibTeX解析エンジンです。

#### 主要機能
- **ファイル・文字列解析**: BibTeXデータの柔軟な入力
- **DOI抽出**: 正規化されたDOIの一括抽出
- **タイトル抽出**: 正規化されたタイトルの抽出
- **エントリ検証**: BibTeX項目の妥当性チェック
- **統計生成**: BibTeXデータの統計情報
- **正規化処理**: LaTeX命令・特殊文字の処理

#### API概要
- `parse_file(file_path)`: BibTeXファイル解析
- `parse_string(bibtex_string)`: BibTeX文字列解析
- `extract_dois(entries)`: DOIリスト抽出
- `extract_titles(entries)`: タイトル辞書抽出
- `validate_entry(entry)`: エントリ妥当性チェック
- `get_statistics(entries)`: 統計情報生成

### 4. 階層的例外管理 (`exceptions.py`)
システム全体で使用される階層的例外クラスです。

#### 例外クラス階層
```python
ObsClippingsManagerError           # 基底例外クラス
├── ConfigurationError             # 設定関連エラー
├── BibTeXParsingError            # BibTeX解析エラー
├── LoggingError                  # ログシステムエラー
├── ValidationError               # バリデーションエラー
└── FileOperationError            # ファイル操作エラー
```

### 5. 共通ユーティリティ (`utils.py`)
システム全体で使用される共通ユーティリティ関数群です。

#### 主要機能
- **安全ファイル操作**: 例外処理付きファイル操作
- **バックアップ作成**: 自動バックアップ機能
- **プログレス表示**: 進捗バーとパーセンテージ表示
- **パス検証**: パス存在・権限チェック
- **ハッシュ計算**: ファイル整合性チェック
- **時間フォーマット**: 人間が読みやすい時間表示
- **辞書マージ**: 深い階層の辞書マージ

## モジュール間の依存関係

### 統合エクスポート
```python
# modules/shared/__init__.py
from .config_manager import ConfigManager
from .logger import IntegratedLogger
from .bibtex_parser import BibTeXParser
from .utils import *
from .exceptions import *
```

### 使用例
```python
# 基本的な使用パターン
from modules.shared import ConfigManager, IntegratedLogger, BibTeXParser
from modules.shared import safe_file_operation, show_progress
from modules.shared import ConfigurationError, BibTeXParsingError

# 設定・ログ・解析の統合使用
config = ConfigManager('config.json')
logger = IntegratedLogger(level='INFO', log_file='app.log')
parser = BibTeXParser()

# 設定取得と処理
citation_config = config.get_citation_fetcher_config()
parser_config = config.get_citation_parser_config()
entries = parser.parse_file(config.get('common.bibtex_file'))
dois = parser.extract_dois(entries)

logger.info(f"Processed {len(entries)} entries, found {len(dois)} DOIs")
```

## パフォーマンス仕様

### 処理時間目標
- **BibTeX解析**: 1,000エントリ < 5秒
- **設定読み込み**: < 100ms
- **ログ出力**: < 10ms per message

### リソース使用量
- **メモリ使用量**: 50MB以下（通常使用時）
- **ディスク容量**: ログファイル管理により制御
- **CPU使用率**: 解析時のみ高負荷

## v2.0 の改善点

### アーキテクチャ改善
- **完全統合**: 重複コード削除によるシンプル化
- **階層的例外**: 体系的エラーハンドリング
- **性能最適化**: キャッシュ・非同期処理の活用

### 機能強化
- **ドット記法**: 設定アクセスの簡素化
- **ファイルログ**: 永続的ログ保存
- **統計機能**: BibTeXデータの分析
- **バリデーション**: 厳密な入力チェック

### 運用改善
- **エラー追跡**: 詳細な例外情報
- **設定管理**: 環境別設定の柔軟な管理
- **デバッグ支援**: 詳細ログとプログレス表示

### テスト品質保証
- **包括的テストカバレッジ**: 共通モジュール全機能のユニットテスト
- **Python 3.x互換性**: 例外チェーン構文の最適化 (`test_shared_exceptions.py`)
- **エッジケース対応**: Unicode、空ファイル、境界値テスト (`test_edge_cases.py`)
- **統合テスト**: 他モジュールとの連携テスト
- **TDDアプローチ**: 仕様先行の品質重視開発

## テスト仕様

### テストファイル構成
```
code/unittest/
├── test_shared_config_manager.py     # ConfigManager テスト (10 tests)
├── test_shared_logger.py             # IntegratedLogger テスト (12 tests)
├── test_shared_bibtex_parser.py      # BibTeXParser テスト (14 tests)
├── test_shared_utils.py              # Utils テスト (17 tests)
├── test_shared_exceptions.py         # Exceptions テスト (3 tests)
└── test_edge_cases.py                # 共通エッジケーステスト (5 tests)
```

### テストカバレッジ詳細
1. **ConfigManager**: 設定読み込み・マージ・検証・セクション取得テスト
2. **IntegratedLogger**: ログレベル・ファイル出力・モジュール別ログテスト
3. **BibTeXParser**: ファイル解析・DOI抽出・統計生成・エントリ検証テスト
4. **Utils**: ファイル操作・プログレス表示・テキスト正規化・バリデーションテスト
5. **Exceptions**: 例外クラス・継承関係・コンテキスト情報テスト

### 品質保証メトリクス
- **テスト成功率**: 100% (61/61 共通モジュールテスト)
- **実行時間**: < 0.5秒
- **例外カバレッジ**: 全例外パス網羅
- **境界値テスト**: ファイルサイズ・文字列長制限・Unicode対応

---

**共通モジュール仕様書バージョン**: 2.0.0  
**対応システム**: ObsClippingsManager v2.0 