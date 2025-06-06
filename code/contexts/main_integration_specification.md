# メイン統合プログラム仕様書 v2.0

## 概要
メイン統合プログラム（`main.py`）は、ObsClippingsManager v2.0 の単一エントリーポイントとして、Citation Fetcher機能とRename & MkDir Citation Key機能を統合し、8つの専用コマンドを通じて各機能を適切に実行するコントローラーです。

**v2.0 の特徴:**
- 単一ファイル統合システム (615行)
- 8つの専用コマンドによる機能分離（同期チェック機能追加）
- Click ベースの高度CLI
- 統合ログシステム・設定管理
- ワークフロー実行履歴・統計追跡

## 機能目的
- 全機能の統合実行制御
- コマンド別の最適化実行
- ワークフロー管理と追跡
- 統合ユーザーインターフェース提供
- 設定管理・ログの一元化
- システム管理・デバッグ支援

## プログラム構成

```
main.py                           # 統合メインエントリーポイント (615行)
├── CLI Commands (8 commands)     # 専用コマンドシステム
│   ├── version                   # バージョン情報
│   ├── validate-config           # 設定検証
│   ├── show-stats               # システム統計
│   ├── show-history             # 実行履歴
│   ├── organize-files           # ファイル整理
│   ├── sync-check               # 同期チェック（新機能）
│   ├── fetch-citations          # 引用取得
│   └── run-integrated           # 統合実行
├── IntegratedController         # 統合実行制御
├── ConfigManager               # 統合設定管理
├── IntegratedLogger            # 統合ログシステム
└── modules/workflows/          # ワークフロー定義
    ├── workflow_manager.py     # ワークフロー管理
    ├── citation_workflow.py   # 引用文献取得ワークフロー
    ├── organization_workflow.py # ファイル整理ワークフロー
    └── sync_check_workflow.py # 同期チェックワークフロー
```

## 8つの専用コマンド

### システム管理コマンド

#### 1. version - バージョン情報
```bash
PYTHONPATH=code/py uv run python code/py/main.py version
```
- システムバージョン表示
- ビルド情報・アーキテクチャ情報

#### 2. validate-config - 設定検証
```bash
PYTHONPATH=code/py uv run python code/py/main.py validate-config
```
- 設定ファイルの妥当性チェック
- 必須パラメータの存在確認
- パス存在確認

#### 3. show-stats - システム統計
```bash
PYTHONPATH=code/py uv run python code/py/main.py show-stats
```
- BibTeX項目数
- Markdownファイル数
- 総実行回数・成功率

#### 4. show-history - 実行履歴
```bash
PYTHONPATH=code/py uv run python code/py/main.py show-history [--limit N]
```
- ワークフロー実行履歴表示
- 実行時刻・実行結果・所要時間

### 主要機能コマンド

#### 5. organize-files - ファイル整理
```bash
PYTHONPATH=code/py uv run python code/py/main.py organize-files [OPTIONS]
```
**主要オプション:**
- `--threshold FLOAT`: タイトル照合類似度閾値 (0.0-1.0)
- `--auto-approve`: 自動承認
- `--sync-check`: 同期チェック併用
- `--disable-doi-matching`: DOI照合無効化（タイトル照合のみ）
- `--disable-title-sync`: タイトル自動同期無効化

#### 6. sync-check - 同期チェック（新機能）
```bash
PYTHONPATH=code/py uv run python code/py/main.py sync-check [OPTIONS]
```
**主要オプション:**
- `--show-missing-in-clippings`: .bibにあってClippings/にない論文表示
- `--show-missing-in-bib`: Clippings/にあって.bibにない論文表示
- `--open-doi-links`: DOIリンクを自動でブラウザ開放
- `--show-doi-stats`: DOI統計情報表示

#### 7. fetch-citations - 引用取得
```bash
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations [OPTIONS]
```
**主要オプション:**
- `--request-delay FLOAT`: APIリクエスト間隔（秒）
- `--max-retries INT`: 最大リトライ回数
- `--timeout INT`: リクエストタイムアウト（秒）

#### 8. run-integrated - 統合実行
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated [OPTIONS]
```
**主要オプション:**
- `--citation-first`: 引用取得→ファイル整理の順序（デフォルト）
- `--organize-first`: ファイル整理→引用取得の順序

### グローバルオプション（全コマンド共通）
- `-c, --config PATH`: 設定ファイルパス
- `-l, --log-level [debug|info|warning|error]`: ログレベル
- `-n, --dry-run`: ドライラン実行
- `-v, --verbose`: 詳細出力有効

## 統合コントローラーアーキテクチャ

### IntegratedController クラス
全ワークフローの実行を制御し、統合ログ・設定管理を提供します。

**主要メソッド:**
- `execute_integrated_workflow()`: 統合ワークフロー実行
- `execute_citation_workflow()`: 引用取得ワークフロー実行
- `execute_organization_workflow()`: ファイル整理ワークフロー実行
- `execute_sync_check_workflow()`: 同期チェックワークフロー実行
- `get_system_stats()`: システム統計取得
- `get_execution_history()`: 実行履歴取得

### ワークフロー統合管理
WorkflowManagerを通じて各ワークフローを実行し、実行記録・エラーハンドリングを一元管理します。

## 実行例

### 基本的な使用パターン
```bash
# 1. システム確認
PYTHONPATH=code/py uv run python code/py/main.py version
PYTHONPATH=code/py uv run python code/py/main.py validate-config

# 2. ドライラン実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run --verbose

# 3. 実際の統合実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 4. 実行結果確認
PYTHONPATH=code/py uv run python code/py/main.py show-stats
PYTHONPATH=code/py uv run python code/py/main.py show-history
```

### 個別機能実行パターン
```bash
# ファイル整理のみ
PYTHONPATH=code/py uv run python code/py/main.py organize-files --auto-approve

# 同期チェックのみ
PYTHONPATH=code/py uv run python code/py/main.py sync-check --open-doi-links

# 引用取得のみ
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations
```

### トラブルシューティングパターン
```bash
# 詳細ログ付き実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --verbose --log-level debug

# DOI照合無効化（タイトル照合フォールバック）
PYTHONPATH=code/py uv run python code/py/main.py organize-files --disable-doi-matching --threshold 0.8

# 設定ファイル指定実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated -c custom_config.json
```

## エラーハンドリング

### 階層的例外処理
- **ConfigurationError**: 設定関連エラー（終了コード: 1）
- **WorkflowError**: ワークフロー実行エラー（終了コード: 2）
- **APIError**: 外部API関連エラー（終了コード: 3）
- **Exception**: 予期しないエラー（終了コード: 99）

### 実行記録・ログ管理
- 全実行結果の記録・追跡
- 詳細ログファイル出力（オプション）
- 実行統計の自動計算・表示

## パフォーマンス仕様

### 処理時間目標
- **ファイル整理**: 100ファイル/分 （DOI照合時）
- **引用取得**: 1論文あたり2秒以内（CrossRef成功時）
- **同期チェック**: 1000項目/秒

### リソース使用量
- **メモリ使用量**: 100MB以下（通常使用時）
- **ディスク容量**: ログファイル 1MB/日以下
- **ネットワーク**: 控えめなAPI使用（1秒間隔）

---

**メイン統合プログラム仕様書バージョン**: 2.0.0  
**対応システム**: ObsClippingsManager v2.0 