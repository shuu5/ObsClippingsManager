# メイン統合プログラム仕様書 v2.2

## 概要
メイン統合プログラム（`main.py`）は、ObsClippingsManager v2.2 の単一エントリーポイントとして、Citation Fetcher機能とRename & MkDir Citation Key機能を統合し、9つの専用コマンドを通じて各機能を適切に実行するコントローラーです。

**v2.2 の特徴:**
- 単一ファイル統合システム (1127行)
- 9つの専用コマンドによる機能分離（同期チェック機能追加）
- **Enhanced Integrated Workflow**: 状態管理ベースの効率的な処理システム
- **Smart Skip Logic**: 処理済みステップの自動スキップ機能
- **Status Management**: BibTeX内での処理状態追跡
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
- 引用文献パース・統一化処理

## プログラム構成

```
main.py                           # 統合メインエントリーポイント (1127行)
├── CLI Commands (9 commands)     # 専用コマンドシステム
│   ├── version                   # バージョン情報
│   ├── validate-config           # 設定検証
│   ├── show-stats               # システム統計
│   ├── show-history             # 実行履歴
│   ├── organize-files           # ファイル整理
│   ├── sync-check               # 同期チェック（新機能）
│   ├── fetch-citations          # 引用取得
│   ├── parse-citations          # 引用文献パース（新機能）
│   └── run-integrated           # 統合実行（Enhanced Mode対応）
├── IntegratedController         # 統合実行制御
├── ConfigManager               # 統合設定管理
├── IntegratedLogger            # 統合ログシステム
└── modules/workflows/          # ワークフロー定義
    ├── workflow_manager.py     # ワークフロー管理
    ├── citation_workflow.py   # 引用文献取得ワークフロー
    ├── organization_workflow.py # ファイル整理ワークフロー
    ├── sync_check_workflow.py # 同期チェックワークフロー
    ├── citation_parser_workflow.py # 引用文献パースワークフロー（新機能）
    └── enhanced_integrated_workflow.py # Enhanced統合ワークフロー（v2.2新機能）
```

## 9つの専用コマンド

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

#### 7. fetch-citations - 引用取得・メタデータ補完
```bash
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations [OPTIONS]
```
**主要オプション:**
- `--request-delay FLOAT`: APIリクエスト間隔（秒）
- `--max-retries INT`: 最大リトライ回数
- `--timeout INT`: リクエストタイムアウト（秒）
- `--enable-enrichment/--no-enable-enrichment`: メタデータ補完機能の有効化（デフォルト: 有効）
- `--enrichment-field-type [life_sciences|computer_science|general]`: 分野別API優先順位
- `--enrichment-quality-threshold FLOAT`: 品質スコア閾値（0.0-1.0）
- `--enrichment-max-attempts INT`: 最大API試行回数

#### 8. parse-citations - 引用文献パース（新機能）
```bash
PYTHONPATH=code/py uv run python code/py/main.py parse-citations [OPTIONS]
```
**主要オプション:**
- `--input-file PATH`: 入力Markdownファイルパス
- `--output-file PATH`: 出力ファイルパス（未指定時は標準出力）
- `--pattern-type [basic|advanced|all]`: パース対象パターン
- `--output-format [unified|table|json]`: 出力フォーマット
- `--enable-link-extraction`: リンク抽出・対応表生成
- `--expand-ranges`: 範囲引用の個別展開

#### 9. run-integrated - 統合実行（Enhanced Mode対応）
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated [OPTIONS]
```

##### 従来モード（デフォルト）
**主要オプション:**
- `--citation-first`: 引用取得→ファイル整理の順序（デフォルト）
- `--organize-first`: ファイル整理→引用取得の順序
- `--include-citation-parser`: 引用文献パース処理を統合実行に含める
- `--disable-enrichment`: citation-fetchingでのメタデータ補完を無効化
- `--enrichment-field-type [life_sciences|computer_science|general]`: 分野別API優先順位（デフォルト: general）

##### Enhanced Mode（v2.2新機能）
**状態管理ベースの効率的統合ワークフロー**

**基本使用法:**
```bash
# Enhanced Modeで実行計画を表示
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --show-execution-plan -b CurrentManuscript.bib -d Clippings

# Enhanced Modeで実際に実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode -b CurrentManuscript.bib -d Clippings

# 強制再生成モード（全ステータスリセット）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --force-regenerate -b CurrentManuscript.bib -d Clippings

# 特定論文のみ処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --papers "smith2023,jones2024" -b CurrentManuscript.bib -d Clippings

# 整合性チェック
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --check-consistency -b CurrentManuscript.bib -d Clippings
```

**Enhanced Modeオプション:**
- `--enhanced-mode`: Enhanced統合ワークフローを有効化
- `--force-regenerate`: 全処理状態フラグをリセットして実行
- `--papers TEXT`: カンマ区切りで特定論文のみ処理（citation key指定）
- `--show-execution-plan`: 実行計画のみ表示（実際には実行しない）
- `--check-consistency`: BibTeXファイルとClippingsディレクトリの整合性チェック
- `-b, --bibtex-file PATH`: BibTeXファイルパス（Enhanced Mode用）
- `-d, --clippings-dir PATH`: Clippingsディレクトリパス（Enhanced Mode用）

**処理フロー:**
1. **organize**: ファイル整理（Markdownファイル → citation keyディレクトリ）
2. **sync**: 同期チェック（BibTeX ↔ Clippingsディレクトリ対応確認）
3. **fetch**: 引用文献取得（DOI → references.bib生成）
4. **parse**: 引用文献解析（Markdownファイル内の引用パース）

**Smart Skip Logic:**
- 各論文の各ステップごとに処理状態を追跡
- 完了済みステップは自動スキップ
- 失敗したステップのみ再実行
- 依存関係に基づく効率的な実行順序

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
- `execute_citation_parser_workflow()`: 引用文献パースワークフロー実行
- `get_system_stats()`: システム統計取得
- `get_execution_history()`: 実行履歴取得

### ワークフロー統合管理
WorkflowManagerを通じて各ワークフローを実行し、実行記録・エラーハンドリングを一元管理します。

### Enhanced Integrated Workflow アーキテクチャ（v2.2新機能）

#### StatusManager - 状態管理システム
論文の処理状態をBibTeXファイル内で管理し、効率的な処理の再開・スキップを実現します。

**状態フィールド:**
- `obsclippings_organize_status`: ファイル整理状態（pending/completed/failed）
- `obsclippings_sync_status`: 同期チェック状態（pending/completed/failed）
- `obsclippings_fetch_status`: 引用取得状態（pending/completed/failed）
- `obsclippings_parse_status`: 引用解析状態（pending/completed/failed）

**主要メソッド:**
- `load_bib_statuses()`: BibTeXから状態情報を読み込み
- `update_status()`: 処理完了・失敗時に状態を更新
- `reset_statuses()`: 強制再生成時に全状態をリセット
- `check_status_consistency()`: BibTeX ↔ Clippingsディレクトリの整合性チェック

#### EnhancedIntegratedWorkflow - 状態ベース実行エンジン
処理状態に基づいて必要な処理のみを効率的に実行します。

**主要メソッド:**
- `analyze_paper_status()`: 各論文の処理必要性を解析
- `get_execution_plan()`: 実行計画を生成
- `execute_step_by_step()`: ステップ別に統合ワークフローを実行
- `execute_with_status_tracking()`: 状態追跡付きで実行
- `execute_force_regenerate()`: 強制再生成モード実行
- `check_consistency()`: 状態整合性チェック

**Smart Skip Logic:**
```
論文A: organize(completed) → sync(pending) → fetch(pending) → parse(pending)
論文B: organize(pending) → sync(pending) → fetch(pending) → parse(pending)

実行計画:
1. organize: 論文B のみ実行
2. sync: 論文A, B を実行
3. fetch: 論文A, B を実行
4. parse: 論文A, B を実行
```

#### 状態管理の仕組み
1. **初期状態**: 全論文のステータスが未設定（"pending"として扱う）
2. **実行中**: 各ステップ成功時に"completed"、失敗時に"failed"に更新
3. **再実行**: "pending"と"failed"の論文のみ処理対象
4. **強制再生成**: 全ステータスを"pending"にリセットして実行

## 実行例

### 基本的な使用パターン

#### 従来モード
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

#### Enhanced Mode（v2.2推奨）
```bash
# 1. システム確認（共通）
PYTHONPATH=code/py uv run python code/py/main.py version
PYTHONPATH=code/py uv run python code/py/main.py validate-config

# 2. 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --show-execution-plan \
  -b /path/to/CurrentManuscript.bib -d /path/to/Clippings

# 3. 整合性チェック
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --check-consistency \
  -b /path/to/CurrentManuscript.bib -d /path/to/Clippings

# 4. Enhanced Mode実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode \
  -b /path/to/CurrentManuscript.bib -d /path/to/Clippings

# 5. 特定論文のみ処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode \
  --papers "smith2023,jones2024" -b /path/to/CurrentManuscript.bib -d /path/to/Clippings

# 6. 強制再生成（全ステータスリセット）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --force-regenerate \
  -b /path/to/CurrentManuscript.bib -d /path/to/Clippings
```

### 個別機能実行パターン
```bash
# ファイル整理のみ
PYTHONPATH=code/py uv run python code/py/main.py organize-files --auto-approve

# 同期チェックのみ
PYTHONPATH=code/py uv run python code/py/main.py sync-check --open-doi-links

# 引用取得のみ（デフォルトでメタデータ補完有効）
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations

# 引用取得のみ（メタデータ補完無効）
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --no-enable-enrichment

# 引用文献パースのみ
PYTHONPATH=code/py uv run python code/py/main.py parse-citations --input-file example.md --enable-link-extraction
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
- **メタデータ補完**: 1論文あたり3秒以内（複数API使用時）
- **同期チェック**: 1000項目/秒

### リソース使用量
- **メモリ使用量**: 100MB以下（通常使用時）
- **ディスク容量**: ログファイル 1MB/日以下
- **ネットワーク**: 控えめなAPI使用（1秒間隔）

## テスト仕様とカバレッジ

### テストアーキテクチャ
メイン統合プログラムの品質保証は、TDDアプローチによる包括的テストスイートで実現されています。

### テストカバレッジ状況
- **総テスト数**: 136個
- **成功率**: 100% (136/136)
- **テスト実行時間**: 約0.8秒
- **Enhanced Workflow専用テスト**: 19個（状態管理+統合ワークフロー）

### テストファイル構成
```
code/unittest/
├── test_main_cli.py                  # CLI機能統合テスト (21KB)
├── test_shared_config_manager.py     # 設定管理テスト
├── test_shared_logger.py             # ログシステムテスト  
├── test_shared_bibtex_parser.py      # BibTeX解析テスト
├── test_shared_utils.py              # ユーティリティテスト
├── test_shared_exceptions.py         # 例外処理テスト
├── test_citation_fetcher.py          # 引用取得テスト
├── test_citation_parser.py           # 引用パースエンジンテスト
├── test_citation_parser_workflow.py  # 引用パースワークフローテスト
├── test_workflow_manager.py          # ワークフロー管理テスト
├── test_sync_check_workflow.py       # 同期チェックテスト
├── test_rename_mkdir_citation_key.py # ファイル整理テスト
├── test_status_management.py         # 状態管理システムテスト（v2.2新規）
├── test_enhanced_run_integrated.py   # Enhanced統合ワークフローテスト（v2.2新規）
├── test_edge_cases.py                # エッジケース・境界値テスト
└── run_all_tests.py                  # テスト実行スクリプト
```

### CLI機能テストカバレッジ
`test_main_cli.py` では以下をテスト：

#### 1. システム管理コマンド
- `version`: バージョン情報表示
- `validate-config`: 設定ファイル検証
- `show-stats`: システム統計表示  
- `show-history`: 実行履歴表示

#### 2. 主要機能コマンド
- `organize-files`: ファイル整理ワークフロー
- `sync-check`: 同期チェック（オプション網羅）
- `fetch-citations`: 引用取得（基本・拡張・ドライラン）
- `parse-citations`: 引用文献パース
- `run-integrated`: 統合ワークフロー（従来モード・Enhanced Mode両対応）

#### 3. エラーハンドリング
- 設定ファイル不正時の適切なエラー処理
- ワークフロー失敗時の適切な終了コード
- 必須パラメータ不足時の処理

### テスト実行方法
```bash
# 全テスト実行
cd /home/user/proj/ObsClippingsManager
uv run code/unittest/run_all_tests.py

# 個別モジュールテスト実行
uv run code/unittest/run_all_tests.py shared_config_manager
```

### テスト品質保証
- **Click CliRunner**: CLIテストフレームワーク使用
- **Mock/Patch**: 外部依存関係の分離
- **Temporary Files**: テスト環境の独立性
- **Python 3.x互換性**: 例外チェーン構文最適化
- **エッジケース**: Unicode、空ファイル、境界値テスト

---

**メイン統合プログラム仕様書バージョン**: 2.2.0  
**対応システム**: ObsClippingsManager v2.2  
**Enhanced Integrated Workflow**: 状態管理ベース効率化システム実装済み 