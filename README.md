# ObsClippingsManager v2.0

ObsClippingsManager v2.0は、学術研究における文献管理とMarkdownファイル整理を自動化する統合システムです。BibTeX文献データベースと連携し、引用文献の自動取得からファイル整理まで一貫した研究支援機能を提供します。

## 主要機能

### 1. 引用文献自動取得
- CrossRef API + OpenCitations APIのフォールバック戦略
- BibTeXファイルからDOIを抽出して引用文献を自動取得
- 取得した引用文献のBibTeX形式出力

### 2. ファイル自動整理
- Markdownファイル名とBibTeX titleの自動照合
- ファジーマッチングによる類似度計算
- Citation keyベースのディレクトリ構造での整理
- ファイル名の自動リネームとディレクトリ作成

### 3. 同期チェック機能
- BibTeXファイルとClippingsディレクトリの整合性チェック
- 不足論文の検出と詳細報告（タイトル、DOI、ウェブリンク）
- 孤立ファイルの通知

### 4. 統合ワークフロー管理
- 単一エントリーポイント（main.py）による簡素化
- 8つの専用コマンドによる機能分離
- 詳細なログシステムと実行履歴追跡

## インストール

### 1. 依存関係のインストール（uvパッケージマネージャー使用）

```bash
# 依存関係の同期
uv sync

# または手動でパッケージをインストール
uv pip install -r requirements.txt
```

### 2. プロジェクトの設定

デフォルトでは以下のパスが設定されています：
- BibTeXファイル: `/home/user/ManuscriptsManager/CurrentManuscript.bib`
- Clippingsディレクトリ: `/home/user/ManuscriptsManager/Clippings/`
- 出力ディレクトリ: `/home/user/ManuscriptsManager/References/`

## 使用方法

### 基本実行コマンド

```bash
# 基本構文（ルートディレクトリから実行）
PYTHONPATH=code/py uv run python code/py/main.py [COMMAND] [OPTIONS]
```

### 利用可能コマンド

#### 1. システム管理コマンド

```bash
# バージョン情報
PYTHONPATH=code/py uv run python code/py/main.py version

# 設定ファイル検証
PYTHONPATH=code/py uv run python code/py/main.py validate-config

# システム統計表示
PYTHONPATH=code/py uv run python code/py/main.py show-stats

# 実行履歴表示
PYTHONPATH=code/py uv run python code/py/main.py show-history --limit 10
```

#### 2. 主要機能コマンド

```bash
# ファイル整理ワークフロー（ドライラン）
PYTHONPATH=code/py uv run python code/py/main.py organize-files --dry-run --verbose

# ファイル整理ワークフロー（実行）
PYTHONPATH=code/py uv run python code/py/main.py organize-files --threshold 0.8 --auto-approve

# 同期チェック（新機能）
PYTHONPATH=code/py uv run python code/py/main.py sync-check --show-clickable-links

# 引用文献取得ワークフロー
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --dry-run --auto-approve

# 統合ワークフロー（引用取得 + ファイル整理）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run --auto-approve
```

### グローバルオプション

```bash
Options:
  -c, --config PATH               設定ファイルパス
  -l, --log-level [DEBUG|INFO|WARNING|ERROR]  ログレベル
  -n, --dry-run                   実際の変更を行わないテストモード
  -v, --verbose                   詳細出力を有効化
  --help                          ヘルプメッセージ表示
```

### 設定ファイル

カスタム設定ファイル（JSON形式）を作成できます：

```json
{
  "common": {
    "bibtex_file": "/path/to/your/bibliography.bib",
    "clippings_dir": "/path/to/your/clippings/",
    "output_dir": "/path/to/output/",
    "log_level": "INFO",
    "backup_enabled": true
  },
  "citation_fetcher": {
    "request_delay": 1.0,
    "max_retries": 3,
    "timeout": 30
  },
  "organization": {
    "similarity_threshold": 0.8,
    "auto_approve": false,
    "create_directories": true
  }
}
```

## プロジェクト構造 v2.0

```
code/py/
├── main.py                           # 統合メインプログラム (602行)
└── modules/                          # モジュラーアーキテクチャ
    ├── __init__.py                   # v2.0 統合エクスポート
    ├── shared/                       # 共有モジュール
    │   ├── __init__.py
    │   ├── config_manager.py         # 統合設定管理
    │   ├── logger.py                 # 統合ログシステム
    │   ├── bibtex_parser.py          # 高度BibTeX解析
    │   ├── utils.py                  # 共通ユーティリティ
    │   └── exceptions.py             # 階層的例外管理
    ├── citation_fetcher/             # 引用文献取得
    │   ├── __init__.py
    │   ├── crossref_client.py        # CrossRef API クライアント
    │   ├── opencitations_client.py   # OpenCitations API クライアント
    │   ├── reference_formatter.py    # BibTeX変換・整形
    │   ├── fallback_strategy.py      # フォールバック戦略
    │   └── exceptions.py             # 専用例外
    ├── rename_mkdir_citation_key/    # ファイル整理
    │   ├── __init__.py
    │   ├── file_matcher.py           # 高度ファイルマッチング
    │   ├── markdown_manager.py       # Markdown管理
    │   ├── directory_organizer.py    # ディレクトリ組織化
    │   └── exceptions.py             # 専用例外
    └── workflows/                    # ワークフロー管理
        ├── __init__.py
        ├── citation_workflow.py      # 引用文献取得ワークフロー
        ├── organization_workflow.py  # ファイル整理ワークフロー
        ├── sync_check_workflow.py    # 同期チェックワークフロー
        └── workflow_manager.py       # 統合ワークフロー管理
```

## データフロー

### 統合ワークフロー
```
1. BibTeXファイル読み込み (BibTeXParser)
   ↓
2. DOI抽出
   ↓
3. 引用文献取得 (CitationWorkflow)
   ├── CrossRef API呼び出し
   ├── フォールバック: OpenCitations API
   └── BibTeX形式で出力
   ↓
4. Markdownファイル整理 (OrganizationWorkflow)
   ├── ファイル名・タイトル照合
   ├── Citation keyディレクトリ作成
   └── ファイル移動・リネーム
   ↓
5. 同期チェック (SyncCheckWorkflow) ※オプション
   ├── .bib ←→ Clippings 整合性確認
   ├── 不足論文の検出・報告
   └── DOIリンクの自動開放
```

## 使用例

### 基本的な実行例

```bash
# 1. 設定確認（ドライラン）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run --verbose

# 2. ファイル整理のみ実行
PYTHONPATH=code/py uv run python code/py/main.py organize-files --threshold 0.8 --auto-approve

# 3. 同期チェック（.bibとClippings/の整合性確認）
PYTHONPATH=code/py uv run python code/py/main.py sync-check

# 4. 引用文献取得のみ実行
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --auto-approve

# 5. 統合実行（引用取得 + ファイル整理）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --auto-approve
```

### 出力例

```
ObsClippingsManager v2.0.0
==================================================

✓ Configuration loaded from: config.json
✓ Log level: INFO

🔍 Starting integrated workflow...

📊 Citation Fetching Results:
  - DOIs processed: 25
  - References found: 234
  - Success rate: 92%

📁 File Organization Results:
  - Files processed: 18
  - Files renamed: 15
  - Directories created: 12
  - Match rate: 83.3%

✅ Integrated workflow completed successfully!
Execution time: 2.45 seconds
```

## トラブルシューティング

### 一般的な問題

1. **BibTeXファイルが見つからない**
   ```bash
   # 設定ファイルでパスを指定
   PYTHONPATH=code/py uv run python code/py/main.py --config custom_config.json organize-files
   ```

2. **マッチング精度が低い**
   ```bash
   # 類似度閾値を調整
   PYTHONPATH=code/py uv run python code/py/main.py organize-files --threshold 0.9
   ```

3. **API接続エラー**
   ```bash
   # リトライ回数を増やす
   PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --max-retries 5
   ```

4. **権限エラー**
   - ディレクトリとファイルの読み書き権限を確認
   - バックアップディレクトリが作成可能か確認

### ログファイル

詳細なログは`logs/obsclippings.log`に保存されます。問題が発生した場合は、このファイルを確認してください。

```bash
# ログレベルを詳細に設定
PYTHONPATH=code/py uv run python code/py/main.py --log-level DEBUG organize-files
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
```

### 実行環境
- Python 3.6+
- UV パッケージマネージャー

## 開発者向け情報

### テスト実行
```bash
# 設定検証テスト
PYTHONPATH=code/py uv run python code/py/main.py validate-config

# ドライランテスト
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run --verbose
```

### 新機能の追加
新しい機能を追加する場合は、`code/py/modules/`ディレクトリの適切なサブディレクトリに新しいモジュールを追加し、ワークフローマネージャーを更新してください。

## v2.0の新機能

- **統合エントリーポイント**: 単一のmain.pyで全機能を管理
- **モジュラーアーキテクチャ**: 機能別に分離されたモジュール構成
- **同期チェック機能**: BibTeXとClippingsディレクトリの整合性確認
- **高度なワークフロー管理**: 実行履歴とシステム統計の追跡
- **統合設定管理**: 一元化された設定システム
- **改良されたAPI**: フォールバック戦略とエラーハンドリング

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグレポートや機能リクエストは、GitHubのIssueで受け付けています。プルリクエストも歓迎します。 