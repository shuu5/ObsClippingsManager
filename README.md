# ObsClippingsManager v3.0

ObsClippingsManager v3.0は、学術研究における文献管理とMarkdownファイル整理を自動化する統合システムです。**シンプルな設定**と**デフォルト引数なし実行**を重視し、効率的な状態管理により重複処理を自動回避します。

## 🔗 仕様書・設計文書

詳細な技術仕様は以下の文書を参照してください：

- **[ObsClippingsManager.md](code/contexts/ObsClippingsManager.md)** - システム全体の概要と基本仕様
- **[integrated_workflow_specification.md](code/contexts/integrated_workflow_specification.md)** - 統合ワークフローの詳細仕様
- **[status_management_yaml_specification.md](code/contexts/status_management_yaml_specification.md)** - 状態管理システムの仕様
- **[shared_modules_specification.md](code/contexts/shared_modules_specification.md)** - 共有モジュールの仕様

## 主要機能

### 統合ワークフロー（run-integrated）
v3.0では、すべての機能が単一の`run-integrated`コマンドで統合実行されます：

1. **引用文献自動取得** - CrossRef API + OpenCitations APIのフォールバック戦略
2. **ファイル自動整理** - Citation keyベースのディレクトリ構造での整理  
3. **同期チェック機能** - BibTeXとClippingsディレクトリの整合性確認
4. **AI理解支援引用文献パーサー** - references.bibの内容をYAMLヘッダーに統合し、AIが直接Markdownファイルを読むだけで引用文献を完全理解できる自己完結型システム
5. **状態管理システム** - YAMLヘッダーで処理状態を追跡し重複処理を自動スキップ

### v3.0の特徴
- **シンプル設定**: 単一引数での統一ディレクトリ設定
- **デフォルト実行**: 引数なしでの完全動作
- **効率的処理**: 状態管理による重複処理の自動スキップ
- **独立モジュール**: 各機能の完全な分離を維持
- **AI理解支援**: AIが直接理解できる自己完結型引用文献統合

## インストール

### 1. 依存関係のインストール（uvパッケージマネージャー使用）

```bash
# 依存関係の同期
uv sync

# または手動でパッケージをインストール
uv pip install -r requirements.txt
```

### 2. プロジェクトの設定

#### デフォルト設定（推奨）
デフォルトでは以下のパスが自動設定されます：

```yaml
# 基本設定（config/config.yaml）
workspace_path: "/home/user/ManuscriptsManager"  # 単一設定

# 自動導出されるパス
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"
```

## 使用方法

### 基本実行（推奨）

```bash
# デフォルト実行（引数なし）- 最もシンプル
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# ワークスペースを変更する場合
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"
```

### 実行オプション

#### 計画確認・ドライラン
```bash
# 実行計画の確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# ドライラン（実際の変更なし）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run

# 詳細ログ
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --verbose --log-level debug
```

#### 強制実行・設定変更
```bash
# 状態管理を無視して強制実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force

# カスタム設定ファイル使用
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --config custom_config.yaml

# 個別パス指定（上級者向け）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --bibtex-file "/path/to/specific.bib" \
    --clippings-dir "/path/to/specific/clippings"
```

### 状態管理システム

v3.0では各論文ファイルのYAMLヘッダーで処理状態を追跡し、完了済み処理を自動スキップします：

```yaml
---
# 論文ファイル（例：smith2023test.md）のヘッダー
processing_status:
  organize_completed: true
  organize_timestamp: "2024-01-15T10:30:00"
  fetch_citations_completed: true
  fetch_citations_timestamp: "2024-01-15T10:35:00"
  sync_check_completed: true
  sync_check_timestamp: "2024-01-15T10:40:00"
last_update: "2024-01-15T10:40:00"
bibtex_key: "smith2023test"
---

# 論文内容...
```

## プロジェクト構造 v3.0

```
code/py/
├── main.py                           # 統合メインプログラム
└── modules/                          # モジュラーアーキテクチャ
    ├── __init__.py                   # v3.0 統合エクスポート
    ├── shared/                       # 共有モジュール
    │   ├── __init__.py
    │   ├── config_manager.py         # 統合設定管理
    │   ├── logger.py                 # 統合ログシステム
    │   ├── bibtex_parser.py          # 高度BibTeX解析
    │   ├── utils.py                  # 共通ユーティリティ
    │   └── exceptions.py             # 階層的例外管理
    ├── citation_fetcher/             # 引用文献取得
    ├── rename_mkdir_citation_key/    # ファイル整理
    ├── ai_citation_support/          # AI理解支援引用文献パーサー
    ├── status_management/            # 状態管理（v3.0新機能）
    └── workflows/                    # ワークフロー管理
        └── integrated_workflow.py    # 統合ワークフロー（メイン）
```

## データフロー v3.0

### 統合ワークフロー（run-integrated）
```
1. 設定読み込み & 実行計画作成
   ↓
2. 状態管理システム初期化
   ├── 各論文のYAMLヘッダー確認
   └── 未完了処理の特定
   ↓
3. ファイル整理（organize）
   ├── 未完了の論文のみ処理
   ├── BibTeX ←→ Markdown照合
   ├── Citation keyディレクトリ作成
   └── 処理状態をYAMLヘッダーに記録
   ↓
4. 同期チェック（sync-check）
   ├── .bib ←→ Clippings 整合性確認
   ├── 不足論文の検出・報告
   └── 処理状態をYAMLヘッダーに記録
   ↓
5. 引用文献取得（fetch-citations）
   ├── 未完了の論文のみ処理
   ├── CrossRef API → OpenCitations API
   ├── BibTeX形式で出力
   └── 処理状態をYAMLヘッダーに記録
   ↓
6. AI理解支援引用文献パーサー（ai-citation-support）
   ├── YAMLヘッダーに完全な引用文献情報を統合
   ├── references.bibから一度読み込み、Markdownファイルに永続化
   └── 処理状態をYAMLヘッダーに記録
   ↓
7. 最終同期チェック（final-sync）
   ├── 全処理完了後の最終整合性確認
   ├── .bib ←→ Clippings 整合性確認
   └── 処理状態をYAMLヘッダーに記録
```

## テスト環境 v3.0

### 🧪 固定マスターデータシステム

ObsClippingsManager v3.0では、**本番データから独立した固定テストデータ**を使用することで、**一貫性のあるテスト環境**を提供します。

#### 特徴
- **本番データ独立**: 本番データの変更がテスト結果に影響しない
- **再現性保証**: 常に同じテストデータで検証可能
- **エッジケース対応**: 意図的な不整合データでエラーハンドリングをテスト
- **簡単リセット**: ワンコマンドで初期状態に復元

#### テストデータ構成

```
code/test_data_master/          # 固定マスターデータ（本番独立）
├── CurrentManuscript.bib       # 5つのBibTeXエントリ
└── Clippings/                  # 3つのMarkdownファイル
    ├── KRT13 is upregulated in pancreatic cancer...md
    ├── KRT13 promotes stemness and drives...md
    └── Keratin Profiling by Single-Cell...md

TestManuscripts/                # 実際のテスト実行環境
├── CurrentManuscript.bib       # マスターからコピー
├── Clippings/                  # マスターからコピー
└── .test_env_info.txt          # テスト環境情報
```

#### エッジケース設計
```
BibTeX エントリ（5つ）:
├── huWY2021IJMS                ✅ 対応Markdownあり
├── lennartzM2023APMIS          ❌ 対応Markdownなし（エッジケース）
├── liQ2016Oncotarget           ❌ 対応Markdownなし（エッジケース）
├── takenakaW2023J.Radiat...    ✅ 対応Markdownあり
└── yinL2022BreastCancerRes     ✅ 対応Markdownあり

Markdownファイル（3つ）:
└── 意図的な不整合でマッチングロジックをテスト
```

### テスト環境構築

#### 1. 固定テストデータからテスト環境作成
```bash
# 固定マスターデータからテスト環境を作成
python code/scripts/setup_test_env.py

# テスト環境の確認
ls -la TestManuscripts/
cat TestManuscripts/.test_env_info.txt
```

#### 2. 簡便なテスト実行
```bash
# 基本テスト実行
./code/scripts/test_run.sh

# テスト環境をリセット後実行
./code/scripts/test_run.sh --reset --run

# ドライラン実行
./code/scripts/test_run.sh --dry-run

# デバッグモード実行
./code/scripts/test_run.sh --debug
```

#### 3. 手動テスト実行
```bash
# テスト環境での統合ワークフロー実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts"

# エッジケースのテスト（強制実行）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts" \
    --force-reprocess

# 詳細ログでテスト実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts" \
    --log-level debug --verbose
```

### テスト環境管理

#### テスト環境リセット
```bash
# テスト環境を固定マスターデータから復元
python code/scripts/setup_test_env.py --reset

# 簡便スクリプトでリセット
./code/scripts/test_run.sh --reset
```

#### テスト結果確認
```bash
# テスト環境の状態確認
cat TestManuscripts/.test_env_info.txt

# 処理前の初期状態
ls -la TestManuscripts/Clippings/

# 処理後のディレクトリ構造確認
find TestManuscripts/Clippings -type d | sort

# Citation keyディレクトリ内容確認
ls -la TestManuscripts/Clippings/*/
```

### 開発時のテストワークフロー

#### TDD (Test-Driven Development) サイクル
```bash
# 1. 全ユニットテスト実行（必須）
uv run code/unittest/run_all_tests.py

# 2. 固定テストデータでの統合テスト
./code/scripts/test_run.sh --reset --debug

# 3. エッジケースの動作確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace TestManuscripts --force-reprocess

# 4. 本番前最終確認（ドライラン）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run
```

#### 基本的な開発サイクル
```bash
# 1. コード変更後のテスト
./code/scripts/test_run.sh --reset --debug

# 2. 結果確認とデバッグ
find TestManuscripts/Clippings -name "*.md" -exec head -10 {} \;

# 3. 問題があれば修正してテスト再実行
./code/scripts/test_run.sh --reset --run

# 4. エッジケースの確認
grep -E "(lennartzM2023APMIS|liQ2016Oncotarget)" TestManuscripts/CurrentManuscript.bib
```

### 固定テストデータの利点

#### 1. **再現性の保証**
```bash
# 何度実行しても同じ結果
python code/scripts/setup_test_env.py --reset
./code/scripts/test_run.sh --run  # 毎回同じ初期条件
```

#### 2. **本番環境からの独立**
```bash
# 本番データが変更されてもテストは影響を受けない
ls -la code/test_data_master/     # 固定データは変更されない
ls -la /home/user/ManuscriptsManager/  # 本番データは自由に変更可能
```

#### 3. **エッジケースの検証**
```bash
# 意図的な不整合データでエラーハンドリングをテスト
echo "BibTeX entries: $(grep -c '@article' TestManuscripts/CurrentManuscript.bib)"
echo "Markdown files: $(find TestManuscripts/Clippings -name '*.md' | wc -l)"
# Output: BibTeX entries: 5, Markdown files: 3 (意図的な不整合)
```

#### 4. **高速なテストサイクル**
```bash
# 軽量な固定データで高速テスト
time python code/scripts/setup_test_env.py --reset  # < 1秒
time ./code/scripts/test_run.sh --run               # < 30秒
```

## 使用例

### 基本的な実行例

```bash
# 1. 初回実行（すべての処理を実行）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 2. 2回目以降（完了済み処理は自動スキップ）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 3. 強制再実行（状態管理を無視）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force

# 4. ドライラン（実際の変更なし）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run --verbose
```

### 出力例

```
ObsClippingsManager v3.0.0
==================================================

✓ Configuration loaded from: config.yaml
✓ Workspace: /home/user/ManuscriptsManager
✓ Log level: INFO

🔍 Starting integrated workflow...

📊 Processing Plan:
  - Papers to organize: 3/25 (22 already completed)
  - Papers requiring citation fetch: 5/25 (20 already completed)
  - Sync check: Required
  - Estimated time: 1.2 minutes

📁 File Organization Results:
  - Files processed: 3
  - Files skipped (completed): 22
  - Directories created: 2
  - Success rate: 100%

📖 Citation Fetching Results:
  - DOIs processed: 5
  - References found: 47
  - Files skipped (completed): 20
  - Success rate: 94%

🔄 Sync Check Results:
  - Consistency: 96% (24/25 papers)
  - Missing papers: 1 (details in log)

✅ Integrated workflow completed successfully!
Execution time: 1.15 minutes
```

## 設定ファイル

### 基本設定（config/config.yaml）

```yaml
# ObsClippingsManager v3.0 Configuration
workspace_path: "/home/user/ManuscriptsManager"  # 基本設定

# 詳細設定（通常変更不要）
common:
  log_level: "INFO"
  backup_enabled: true
  
citation_fetcher:
  request_delay: 1.0
  max_retries: 3
  timeout: 30
  
organization:
  similarity_threshold: 0.8
  auto_approve: false
  create_directories: true

status_management:
  yaml_header_enabled: true
  auto_skip_completed: true
  backup_headers: true
```

### カスタム設定例

```yaml
# カスタム設定ファイル（custom_config.yaml）
workspace_path: "/path/to/custom/workspace"

common:
  log_level: "DEBUG"
  backup_enabled: true

organization:
  similarity_threshold: 0.9
  auto_approve: true
  
status_management:
  auto_skip_completed: false  # 常に全処理を実行
```

## トラブルシューティング

### 一般的な問題

1. **ワークスペースが見つからない**
   ```bash
   # カスタムワークスペースを指定
   PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
       --workspace "/path/to/your/workspace"
   ```

2. **処理がスキップされる**
   ```bash
   # 強制実行で状態管理を無視
   PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force
   ```

3. **YAMLヘッダーエラー**
   ```bash
   # ヘッダー修復モード
   PYTHONPATH=code/py uv run python code/py/main.py run-integrated --repair-headers
   ```

4. **API接続エラー**
   ```bash
   # リトライ回数を増やす
   PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
       --config custom_config.yaml  # max_retries: 5を設定
   ```

### ログファイル

詳細なログは`logs/obsclippings.log`に保存されます：

```bash
# デバッグログで問題を特定
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --log-level DEBUG --verbose
```

## 依存関係

### Pythonパッケージ
```txt
click>=8.0.0              # コマンドライン引数処理
bibtexparser>=1.4.0       # BibTeX解析
fuzzywuzzy>=0.18.0        # 文字列類似度計算
python-levenshtein>=0.12.0 # 高速文字列比較
requests>=2.25.0          # HTTP APIクライアント
pydantic>=1.8.0           # 設定バリデーション
pyyaml>=5.4.0             # YAML処理（v3.0新機能）
```

### 実行環境
- Python 3.6+
- UV パッケージマネージャー

## 開発者向け情報

### 開発時のワークフロー
```bash
# 1. 全ユニットテスト実行（必須）
uv run code/unittest/run_all_tests.py

# 2. テスト環境での動作確認
./code/scripts/test_run.sh --reset --debug

# 3. 本番前最終確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run
```

### 新機能の追加
新しい機能を追加する場合は、以下の手順に従ってください：

1. `code/py/modules/`の適切なサブディレクトリに新しいモジュールを追加
2. `workflows/integrated_workflow.py`に統合ロジックを追加
3. 状態管理システムに対応する処理状態を追加
4. テストケースを作成・実行

## v3.0の新機能

- **統合実行**: 単一の`run-integrated`コマンドですべての機能を統合実行
- **シンプル設定**: `workspace_path`一つですべてのパスを自動設定
- **状態管理**: YAMLヘッダーベースの処理状態追跡と自動スキップ
- **デフォルト実行**: 引数なしでの完全動作サポート
- **効率的処理**: 重複処理の自動回避で実行時間を大幅短縮
- **固定テストシステム**: 本番データから独立した一貫性のあるテスト環境
- **エッジケーステスト**: 意図的な不整合データでエラーハンドリングを検証

## 移行ガイド（v2.0 → v3.0）

### コマンド変更
```bash
# v2.0（複数コマンド）
PYTHONPATH=code/py uv run python code/py/main.py organize-files
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations
PYTHONPATH=code/py uv run python code/py/main.py sync-check

# v3.0（統合コマンド）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated
```

### 設定変更
```yaml
# v2.0（個別設定）
bibtex_file: "/path/to/file.bib"
clippings_dir: "/path/to/clippings"
output_dir: "/path/to/output"

# v3.0（統一設定）
workspace_path: "/path/to/workspace"  # 自動的にすべてのパスを導出
```

### テスト環境の変更
```bash
# v2.0（本番データ依存テスト）
# 本番データが変更されるとテスト結果も変わる

# v3.0（固定マスターデータシステム）
python code/scripts/setup_test_env.py    # 固定データから生成
./code/scripts/test_run.sh --reset       # 常に同じ初期状態
# エッジケース対応：BibTeX 5エントリ vs Markdown 3ファイル
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグレポートや機能リクエストは、GitHubのIssueで受け付けています。プルリクエストも歓迎します。 