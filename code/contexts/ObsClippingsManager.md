# ObsClippingsManager v2.0 統合システム仕様書

## 概要
ObsClippingsManager v2.0 は、学術研究における文献管理とMarkdownファイル整理を自動化する統合システムです。BibTeX文献データベースと連携し、引用文献の自動取得からファイル整理まで一貫した研究支援機能を提供します。

**v2.0 の特徴:**
- 完全統合されたモジュラーアーキテクチャ
- 単一エントリーポイント (`main.py`) による簡素化
- 8つの専用コマンドによる機能分離（同期チェック機能追加）
- レガシーコード完全削除による保守性向上

## システム構成

本システムは以下の5つの主要モジュールで構成されています：

### 1. Citation Fetcher機能
- 学術論文の引用文献を自動取得
- CrossRef API + OpenCitations APIのフォールバック戦略
- 取得した引用文献のBibTeX形式出力

### 2. Rename & MkDir Citation Key機能
- Markdownファイルの整理とBibTeX参照キーとの連携
- YAML frontmatter内のDOIとBibTeX DOIの自動照合
- Citation keyベースのディレクトリ構造での整理

### 3. 同期チェック機能（新機能）
- BibTeXファイルとClippingsディレクトリの整合性確認
- 不足論文の詳細報告（タイトル、DOI、ウェブリンク）
- ブラウザでのDOIリンク自動開放

### 4. 引用文献パース機能（新機能）
- 様々な形式の引用文献を統一フォーマットに変換
- リンク付き引用からの対応表生成
- 複数の引用パターンの自動検出・変換

### 5. 共通モジュール (Shared)
- 統合設定管理 (ConfigManager)
- 統合ログシステム (IntegratedLogger)
- BibTeX解析エンジン (BibTeXParser)

## 全体アーキテクチャ (v2.0)

```
ObsClippingsManager v2.0 統合システム
├── main.py                           # 統合メインプログラム (615行)
└── modules/                          # モジュラーアーキテクチャ (26 files)
    ├── __init__.py                   # v2.0 統合エクスポート
    ├── shared/                       # 共有モジュール (6 files)
    │   ├── config_manager.py         # 統合設定管理
    │   ├── logger.py                 # 統合ログシステム
    │   ├── bibtex_parser.py          # 高度BibTeX解析
    │   ├── utils.py                  # 共通ユーティリティ
    │   └── exceptions.py             # 階層的例外管理
    ├── citation_fetcher/             # 引用文献取得 (5 files)
    ├── rename_mkdir_citation_key/    # ファイル整理 (5 files)
    ├── citation_parser/              # 引用文献パース (3 files)
    │   ├── citation_parser.py        # メインパーサー
    │   ├── pattern_detector.py       # パターン検出エンジン
    │   └── format_converter.py       # フォーマット変換エンジン
    └── workflows/                    # ワークフロー管理 (6 files)
        ├── citation_workflow.py      # 引用文献取得ワークフロー
        ├── organization_workflow.py  # ファイル整理ワークフロー
        ├── sync_check_workflow.py    # 同期チェックワークフロー（新規）
        ├── citation_parser_workflow.py # 引用文献パースワークフロー（新規）
        └── workflow_manager.py       # 統合ワークフロー管理
```

## 主要機能

### 1. 引用文献自動取得
- **入力**: BibTeXファイル内のDOI
- **処理**: CrossRef → OpenCitations フォールバック戦略
- **出力**: 引用文献のBibTeXファイル

### 2. ファイル自動整理
- **入力**: Clippingsディレクトリ内のMarkdownファイル
- **処理**: BibTeX DOIとの照合、citation keyディレクトリ作成
- **出力**: 整理されたディレクトリ構造

### 3. 同期チェック（新機能）
- **入力**: CurrentManuscript.bibファイルとClippings/サブディレクトリ
- **処理**: 双方向整合性チェック、不一致の検出
- **出力**: 不足論文の詳細報告（タイトル、DOI、ウェブリンク）

## 実行方法 (v2.0)

### 基本実行コマンド
```bash
PYTHONPATH=code/py uv run python code/py/main.py [COMMAND] [OPTIONS]
```

### 利用可能コマンド (9コマンド)

```bash
# システム管理
version                    # バージョン情報
validate-config           # 設定ファイル検証
show-stats               # システム統計表示
show-history             # 実行履歴表示

# 主要機能
organize-files           # ファイル整理ワークフロー
sync-check              # 同期チェックワークフロー（新機能）
fetch-citations         # 引用文献取得ワークフロー
parse-citations         # 引用文献パースワークフロー（新機能）
run-integrated          # 統合ワークフロー
```

### グローバルオプション
```bash
Options:
  -c, --config PATH      Configuration file path
  -l, --log-level        Logging level [debug|info|warning|error]
  -n, --dry-run         Perform dry run without changes
  -v, --verbose         Enable verbose output
```

## 使用例

### 基本的な実行
```bash
# 統合実行（推奨）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run --verbose

# 個別機能実行
PYTHONPATH=code/py uv run python code/py/main.py organize-files --auto-approve
PYTHONPATH=code/py uv run python code/py/main.py sync-check --open-doi-links
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations
PYTHONPATH=code/py uv run python code/py/main.py parse-citations --input-file paper.md
```

### システム管理
```bash
# システム情報確認
PYTHONPATH=code/py uv run python code/py/main.py version
PYTHONPATH=code/py uv run python code/py/main.py show-stats
PYTHONPATH=code/py uv run python code/py/main.py show-history
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
```bash
uv sync                   # 依存関係同期
```

## v2.0 の改善点

### アーキテクチャ改善
- **単一エントリーポイント**: main.py への統一
- **モジュール完全分離**: 機能別の明確な境界
- **重複コード削除**: 20.7%のファイル削減

### 機能強化
- **9つの専用コマンド**: 機能別の最適化実行
- **同期チェック機能**: .bibとClippings/の整合性確認、DOIリンク自動開放
- **引用文献パース機能**: 複数引用形式の統一化・リンク抽出
- **統合ログシステム**: ファイル出力対応
- **設定管理強化**: ConfigManager による一元管理

### 運用改善
- **簡素化された実行方法**: 複雑なパス指定の削減
- **エラーハンドリング向上**: 階層的例外管理
- **デバッグ支援**: 詳細ログと統計情報

---

**統合仕様書バージョン**: 2.0.0  

## 関連仕様書
- [メイン統合仕様書](./main_integration_specification.md) - 詳細な実装仕様
- [Citation Fetcher仕様書](./citation_fetcher_specification.md) - 引用取得機能
- [Rename MkDir Citation Key仕様書](./rename_mkdir_citation_key_specification.md) - ファイル整理機能
- [同期チェックワークフロー仕様書](./sync_check_workflow_specification.md) - 同期チェック機能
- [引用文献パーサー仕様書](./citation_parser_specification.md) - 引用文献パース機能
- [共通モジュール仕様書](./shared_modules_specification.md) - 共通モジュール詳細

