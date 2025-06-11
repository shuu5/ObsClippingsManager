# ObsClippingsManager v3.0 統合システム仕様書

## 概要
ObsClippingsManager v3.0 は、学術研究における文献管理とMarkdownファイル整理を自動化する統合システムです。**シンプルな設定**と**デフォルト引数なし実行**を重視し、効率的な状態管理により重複処理を自動回避します。

**v3.0 の特徴:**
- **シンプル設定**: 単一引数での統一ディレクトリ設定
- **デフォルト実行**: 引数なしでの完全動作
- **効率的処理**: 状態管理による重複処理の自動スキップ
- **独立モジュール**: 各機能の完全な分離を維持

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

### 4. 引用文献パース機能
- 様々な形式の引用文献を統一フォーマットに変換
- エスケープされた引用形式（\[[1]\]）への完全対応  
- リンク付き引用からの対応表生成とクリーンアップ
- 複数の引用パターンの自動検出・完全統一化変換

### 5. 状態管理システム
- 各論文の処理状態をYAMLヘッダーで追跡
- 完了済み処理の自動スキップ
- 失敗処理の再実行制御

## 全体アーキテクチャ (v3.0)

```
ObsClippingsManager v3.0 統合システム
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
    ├── citation_parser/              # 引用文献パース
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

## テスト環境構築・管理

### テスト環境の概要
ObsClippingsManager v3.0 では、本番環境を模したテスト環境を簡単に構築・管理できます。テスト環境は本番データの複製または疑似データを使用して、安全にシステムの動作検証を行えます。

### テスト環境セットアップ

#### 1. 初期構築
```bash
# 本番環境からテストデータを作成
python code/scripts/setup_test_env.py

# カスタムパスでの構築
python code/scripts/setup_test_env.py \
    --source "/path/to/production" \
    --test-dir "/path/to/test/environment"
```

#### 2. テスト環境リセット
```bash
# テスト環境を初期状態に戻す
python code/scripts/setup_test_env.py --reset

# カスタムテストディレクトリのリセット
python code/scripts/setup_test_env.py --reset --test-dir "/path/to/test/environment"
```

### テスト環境での実行

#### 基本的なテスト実行
```bash
# テスト環境での統合ワークフロー実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts"

# 簡略コマンド（エイリアス推奨）
TEST_WS="/home/user/proj/ObsClippingsManager/TestManuscripts"
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "$TEST_WS"
```

#### テスト実行オプション
```bash
# 実行計画確認（テスト環境）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "$TEST_WS" --show-plan

# ドライラン実行（テスト環境）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "$TEST_WS" --dry-run

# 詳細ログでテスト実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "$TEST_WS" --log-level debug --verbose
```

### テスト環境構造
```
TestManuscripts/                        # テストワークスペース
├── .test_env_info.txt                  # テスト環境情報
├── CurrentManuscript.bib               # テスト用BibTeXファイル
└── Clippings/                          # テスト用論文ディレクトリ
    ├── sample_paper1.md               # サンプル論文1
    ├── sample_paper2.md               # サンプル論文2
    └── ...                            # その他のテストファイル
```

### テスト環境管理

#### 環境情報確認
```bash
# テスト環境の詳細確認
cat TestManuscripts/.test_env_info.txt

# テスト環境の状態確認
ls -la TestManuscripts/
ls -la TestManuscripts/Clippings/
```

#### テストサイクル
```bash
# 1. テスト環境リセット
python code/scripts/setup_test_env.py --reset

# 2. テスト実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts"

# 3. 結果確認
ls -la TestManuscripts/Clippings/  # 処理後の状態確認

# 4. 次回テストのためのリセット
python code/scripts/setup_test_env.py --reset
```

### テスト推奨ワークフロー

#### 開発時テスト
```bash
# 新機能開発後の基本テスト
python code/scripts/setup_test_env.py --reset
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts" \
    --log-level debug
```

#### デバッグ用テスト
```bash
# 問題特定のための詳細テスト
python code/scripts/setup_test_env.py --reset
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts" \
    --dry-run --show-plan --verbose
```

#### 本番前最終確認
```bash
# 本番環境と同等データでのテスト
python code/scripts/setup_test_env.py  # 本番データコピー
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
4. **parse**: Markdownファイル内引用解析・統一化

## 引用文献パース機能 (v3.0強化版)

### 概要
ObsClippingsManager v3.0では、引用文献パース機能を大幅に強化し、現存するあらゆる引用形式を完全に統一された形式に変換します。

### 対応する引用形式

#### 入力形式（検出・変換対象）
1. **エスケープされた基本形式**
   - `\[[1]\]` → `[1]`
   - `\[[2], [3]\]` → `[2], [3]`

2. **エスケープされたURL付き形式**
   - `\[[1](https://example.com)\]` → `[1]`
   - `\[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\]` → `[4], [5], [6], [7], [8]`

3. **エスケープされた脚注形式**
   - `\[[^1]\]` → `[1]`
   - `\[[^1],[^2],[^3]\]` → `[1], [2], [3]`

4. **通常の形式**
   - `[1]` → `[1]` (そのまま)
   - `[2, 3]` → `[2], [3]` (スペース統一)
   - `[1-5]` → `[1], [2], [3], [4], [5]` (範囲展開)

#### 最終統一形式（目標出力）
- **単一引用**: `[1]`
- **複数引用**: `[2], [3], [4]` (カンマ+スペース区切り)
- **連続番号**: `[1], [2], [3]` (範囲は常に展開)

### 変換ルール

#### 1. エスケープ解除
```
入力: \[[1]\]
処理: エスケープバックスラッシュを除去
出力: [1]
```

#### 2. URL抽出とクリーンアップ
```
入力: \[[4,5,6,7,8](https://academic.oup.com/jrr/article/64/2/284/)\]
処理: 
  1. URLを抽出してリンク表に保存
  2. 引用番号のみ残す
  3. 個別の引用に分離
出力: [4], [5], [6], [7], [8]
```

#### 3. 脚注記号除去
```
入力: \[[^1],[^2],[^3]\]
処理: 
  1. エスケープ解除
  2. ^記号を除去  
  3. 個別の引用に分離
出力: [1], [2], [3]
```

#### 4. スペース統一化
```
入力: [2,3] または [2 ,3] または [2, 3]
出力: [2], [3] (常に「, 」区切り)
```

#### 5. 範囲展開
```
入力: [1-5]
出力: [1], [2], [3], [4], [5]
```

### 処理アルゴリズム

#### フェーズ1: パターン検出
1. エスケープされた引用パターンの検出
2. URL付き引用の特定
3. 脚注形式の識別
4. 標準形式の確認

#### フェーズ2: 前処理
1. エスケープの解除
2. URLの抽出とリンク表への保存
3. 脚注記号の除去

#### フェーズ3: 統一化変換
1. 引用番号の抽出と検証
2. 範囲の展開
3. 重複の除去とソート
4. 統一フォーマットでの出力

### 状態管理による効率化
- **自動スキップ**: 完了済み処理は自動的にスキップ
- **失敗再実行**: 失敗した処理のみ再実行
- **依存関係**: 前段階完了後に次段階を実行
- **状態追跡**: 各論文の.mdファイルのYAMLヘッダーで状態管理

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
obsclippings_metadata:
  citation_key: "smith2023test"
  processing_status:
    organize: "completed"
    sync: "completed" 
    fetch: "completed"
    parse: "completed"
  last_updated: "2025-01-15T10:30:00Z"
  workflow_version: "3.0"
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

