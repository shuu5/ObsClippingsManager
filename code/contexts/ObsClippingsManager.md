# ObsClippingsManager v3.0 統合システム仕様書

## 概要
ObsClippingsManager v3.0 は、学術研究における文献管理とMarkdownファイル整理を自動化する統合システムです。**シンプルな設定**と**デフォルト引数なし実行**を重視し、効率的な状態管理により重複処理を自動回避します。

**v3.0 の特徴:**
- **シンプル設定**: 単一引数での統一ディレクトリ設定
- **デフォルト実行**: 引数なしでの完全動作
- **効率的処理**: 状態管理による重複処理の自動スキップ
- **独立モジュール**: 各機能の完全な分離を維持
- **AI理解支援**: AIが直接理解できる自己完結型引用文献統合

## システム構成

本システムは以下の5つの独立モジュールで構成され、すべてが`run-integrated`で統合実行されます：

### 1. Citation Fetcher機能
- 学術論文の引用文献を自動取得
- CrossRef API + OpenCitations APIのフォールバック戦略
- メタデータ補完機能（PubMed、Semantic Scholar、OpenAlex API統合）
- 取得した引用文献のBibTeX形式出力

### 2. Rename & MkDir Citation Key機能
- Markdownファイルの整理とBibTeX参照キーとの連携
- YAML frontmatter内のDOIとBibTeX DOIの自動照合
- Citation keyベースのディレクトリ構造での整理

### 3. 同期チェック機能
- BibTeXファイルとClippingsディレクトリの整合性確認
- 不足論文の詳細報告（タイトル、DOI、ウェブリンク）
- ブラウザでのDOIリンク自動開放

### 4. AI理解支援引用文献パーサー機能
- **シンプル引用マッピング**: references.bibの全エントリーを順序通りにYAMLヘッダーに統合
- **自己完結型システム**: AIが直接Markdownファイルを読むだけで引用文献を完全理解
- **永続化**: references.bibから一度読み込み、Markdownファイルに永続化
- **重複包含**: 重複エントリーも含めて全て処理（BibTeXファイルの構造保持）
- **1:1対応**: BibTeXエントリー番号 = 引用番号（1から開始）

### 5. 状態管理システム
- 各論文の処理状態をYAMLヘッダーで追跡
- 完了済み処理の自動スキップ
- 失敗処理の再実行制御

## 全体アーキテクチャ (v4.0)

```
ObsClippingsManager v4.0 統合システム
├── main.py                           # 統合メインプログラム
└── modules/                          # モジュラーアーキテクチャ
    ├── shared/                       # 共有モジュール
    │   ├── config_manager.py         # 統合設定管理
    │   ├── logger.py                 # 統合ログシステム
    │   ├── bibtex_parser.py          # 高度BibTeX解析
    │   ├── utils.py                  # 共通ユーティリティ
    │   └── exceptions.py             # 階層的例外管理
    ├── citation_fetcher/             # 引用文献取得
    ├── rename_mkdir_citation_key/    # ファイル整理
    ├── ai_citation_support/          # AI理解支援引用文献パーサー
    ├── status_management/            # 状態管理
    └── workflows/                    # ワークフロー管理
        └── integrated_workflow.py    # 統合ワークフロー（メイン）
```

## 統一設定システム

### 基本原理
**単一のワークスペースパス設定**ですべてのディレクトリを統一管理：

```yaml
# config/config.yaml（デフォルト設定）
workspace_path: "/home/user/ManuscriptsManager"  # 単一設定

# 自動導出されるパス
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"
```

### デフォルト実行（引数なし）
```bash
# これだけで完全実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated
```

### 個別設定（必要時のみ）
```bash
# ワークスペースパス変更
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/other/workspace"

# 個別ファイル指定（上級者向け）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --bibtex-file "/path/to/specific.bib" \
    --clippings-dir "/path/to/specific/clippings"
```

## テスト環境

### 基本テスト実行
```bash
# テスト環境での実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts"
```

## メイン機能: run-integrated

### 基本実行
```bash
# デフォルト実行（推奨）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess
```

### 処理フロー
1. **organize**: Markdownファイル → citation keyディレクトリ整理
2. **sync**: BibTeX ↔ Clippingsディレクトリ整合性チェック
3. **fetch**: DOI → references.bib引用文献取得
4. **ai-citation-support**: AI理解支援引用文献パーサー（自己完結型ファイル生成）

## AI理解支援引用文献パーサー機能 (v3.0新機能)

### 概要
ObsClippingsManager v3.0では、AI理解支援引用文献パーサー機能を新たに追加しました。この機能により、AIアシスタント（ChatGPT、Claude等）が論文の引用文献を完全に理解できる自己完結型ファイルを生成します。

### 基本原理

#### 完全統合引用マッピング機能
- YAMLヘッダーに全ての引用文献情報を完全統合
- references.bibから一度読み込み、Markdownファイルに永続化
- 外部ファイル依存を排除した自己完結型設計
- AIが直接Markdownファイルを読むだけで完全理解可能

### YAMLヘッダー完全統合形式
```yaml
---
citation_key: smith2023test
citation_metadata:
  last_updated: '2025-01-15T10:30:00.123456'
  mapping_version: '2.0'
  source_bibtex: references.bib
  total_citations: 1
citations:
  1:
    authors: Smith
    citation_key: smith2023test
    doi: 10.1158/0008-5472.CAN-23-0123
    journal: Cancer Research
    pages: '1234-1245'
    title: Novel Method for Cancer Cell Analysis
    volume: '83'
    year: 2023
last_updated: '2025-01-15T10:30:00.654321+00:00'
processing_status:
  ai-citation-support: completed
  fetch: completed
  organize: completed
  sync: completed
workflow_version: '3.0'
---
```

### 使用例

```bash
# AI理解支援機能を有効化して統合実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-ai-citation-support

# 個別実行（完全統合マッピング作成）
PYTHONPATH=code/py uv run python code/py/main.py create-complete-mapping \
    --input paper.md \
    --references references.bib
```

## 主要オプション

### グローバルオプション
```bash
-w, --workspace PATH     # ワークスペースパス（デフォルト: /home/user/ManuscriptsManager）
-c, --config PATH        # 設定ファイルパス
-l, --log-level LEVEL    # ログレベル [debug|info|warning|error]
-n, --dry-run           # ドライラン実行
-v, --verbose           # 詳細出力
```

### 実行制御オプション
```bash
--show-plan             # 実行計画表示（実行しない）
--force-reprocess       # 全状態リセット後実行
--papers TEXT           # 特定論文のみ処理（カンマ区切り）
--skip-steps TEXT       # 特定ステップをスキップ
```

### 個別設定オプション（上級者向け）
```bash
--bibtex-file PATH      # BibTeXファイル個別指定
--clippings-dir PATH    # Clippingsディレクトリ個別指定
--output-dir PATH       # 出力ディレクトリ個別指定
```

## 使用例

### 基本的な使用方法
```bash
# 初回実行（すべて処理される）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 2回目実行（完了済みはスキップされる）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 実行前に計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 特定論文のみ処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --papers "smith2023,jones2024"

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess
```

### 異なるワークスペースでの実行
```bash
# プロジェクトA
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/home/user/ProjectA"

# プロジェクトB  
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/home/user/ProjectB"
```

### システム管理
```bash
# バージョン確認
PYTHONPATH=code/py uv run python code/py/main.py version

# 設定検証
PYTHONPATH=code/py uv run python code/py/main.py validate-config

# 統計情報
PYTHONPATH=code/py uv run python code/py/main.py show-stats
```

## ディレクトリ構造

### 標準ワークスペース
```
/home/user/ManuscriptsManager/          # ワークスペースルート
├── CurrentManuscript.bib               # メインBibTeXファイル
└── Clippings/                          # 論文ディレクトリ
    ├── smith2023test/
    │   ├── smith2023test.md            # 状態管理ヘッダー付き論文ファイル
    │   └── references.bib              # 引用文献
    ├── jones2024neural/
    │   ├── jones2024neural.md
    │   └── references.bib
    └── ...
```

### 状態管理ヘッダー例
```yaml
---
citation_key: smith2023test
citation_metadata:
  last_updated: '2025-01-15T10:30:00.123456'
  mapping_version: '2.0'
  source_bibtex: references.bib
  total_citations: 0
citations: {}
last_updated: '2025-01-15T10:30:00.654321+00:00'
processing_status:
  ai-citation-support: pending
  fetch: completed
  organize: completed
  sync: completed
workflow_version: '3.0'
---

# Smith et al. (2023) - Example Paper Title

論文の内容...
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
metapub>=0.5.5            # PubMed API クライアント
pyyaml>=6.0               # YAML処理
```

### 実行環境
```bash
uv sync                   # 依存関係同期
```

## v3.0 の改善点

### シンプル化
- **単一設定**: workspace_pathのみでの統一管理
- **デフォルト実行**: 引数なしでの完全動作
- **統合コマンド**: run-integratedへの機能集約

### 効率化
- **状態管理**: YAMLヘッダーによる永続的状態追跡
- **自動スキップ**: 完了済み処理の自動回避
- **依存関係**: 効率的な実行順序制御

### 品質向上
- **モジュール独立性**: 各機能の完全分離維持
- **エラーハンドリング**: 失敗時の適切な状態管理
- **設定検証**: 実行前の設定妥当性チェック

---

**統合仕様書バージョン**: 3.0.0

## 関連仕様書
- [統合ワークフロー仕様](./integrated_workflow_specification.md)
- [状態管理システム仕様](./status_management_specification.md)
- [共有モジュール仕様](./shared_modules_specification.md)

