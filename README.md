# ObsClippingsManager v3.2.0

学術研究における文献管理とMarkdownファイル整理を自動化する統合システム。**シンプル設定**と**状態管理による重複処理回避**が特徴。

## 📋 システム概要

### 主要機能
1. **引用文献自動取得** - CrossRef/OpenCitations API
2. **ファイル自動整理** - Citation keyベースのディレクトリ構造
3. **同期チェック** - BibTeX ↔ Clippings整合性確認
4. **AI理解支援** - YAMLヘッダーに引用文献情報統合（タグ生成・抄録翻訳）
5. **状態管理** - 処理完了済み項目の自動スキップ

### アーキテクチャ
```
code/py/
├── main.py                     # エントリーポイント
└── modules/
    ├── shared/                 # 共通基盤（config, logger, parser, utils）
    ├── citation_fetcher/       # 引用文献取得
    ├── rename_mkdir_citation_key/  # ファイル整理
    ├── ai_citation_support/    # AI理解支援
    ├── status_management/      # 状態管理
    └── workflows/              # 統合ワークフロー
```

## 🔗 技術仕様書

詳細仕様は以下を参照：
- **[ObsClippingsManager.md](code/contexts/ObsClippingsManager.md)** - システム全体概要・設計思想
- **[integrated_workflow_specification.md](code/contexts/integrated_workflow_specification.md)** - 統合ワークフロー・統合テストシステム
- **[status_management_yaml_specification.md](code/contexts/status_management_yaml_specification.md)** - 状態管理・YAMLフォーマット
- **[shared_modules_specification.md](code/contexts/shared_modules_specification.md)** - 共有モジュール
- **[enhanced_citation_parser_specification.md](code/contexts/enhanced_citation_parser_specification.md)** - AI理解支援機能

## ⚡ クイックスタート

### 1. セットアップ
```bash
# 依存関係インストール
uv sync

# デフォルト設定確認
cat config/config.yaml
```

### 2. 基本実行
```bash
# 統合ワークフロー実行（推奨）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# カスタムワークスペース指定
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"

# AI機能有効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-tagger --enable-translate-abstract
```

### 3. 実行オプション
```bash
# 実行計画確認
--show-plan

# ドライラン
--dry-run

# 強制実行（状態管理無視）
--force

# 詳細ログ
--verbose --log-level debug
```

## 🔧 設定

### デフォルト設定（config/config.yaml）
```yaml
workspace_path: "/home/user/ManuscriptsManager"

# 自動導出パス
# bibtex_file: "{workspace_path}/CurrentManuscript.bib"
# clippings_dir: "{workspace_path}/Clippings"
# output_dir: "{workspace_path}/Clippings"
```

### YAML状態管理フォーマット
```yaml
---
citation_key: paper2023key
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  ai-citation-support: completed
workflow_version: '3.1'
last_updated: '2025-01-15T10:30:00Z'
citations:
  1:
    citation_key: reference2023
    title: "Reference Paper Title"
    # ... 引用文献詳細
---
```

## 🧪 テストシステム

### 2層テスト構成
1. **ユニットテスト**: 個別モジュールの単体テスト
2. **統合テスト**: マスターテストデータによるエンドツーエンドテスト

### ユニットテスト実行
```bash
# 全ユニットテスト実行
uv run code/unittest/run_all_tests.py

# 個別テスト実行
uv run python -m unittest code.unittest.test_[module_name]
```

### 統合テスト実行（推奨）
```bash
# 標準統合テスト
./code/scripts/test_run.sh

# 環境リセット後実行
./code/scripts/test_run.sh --reset --run

# ドライラン実行（安全確認）
./code/scripts/test_run.sh --dry-run

# デバッグモード実行
./code/scripts/test_run.sh --debug

# 実行計画表示
./code/scripts/test_run.sh --plan
```

### テストデータ構造
```
code/test_data_master/          # 固定マスターデータ（Git管理）
├── CurrentManuscript.bib       # 5 BibTeXエントリ
└── Clippings/                  # 3 Markdownファイル（意図的不整合）

TestManuscripts/                # 実行環境（自動生成・Git除外）
```

**エッジケーステスト**: BibTeX↔Clippings間の不整合処理を検証

## 🔄 開発ワークフロー

### TDD開発サイクル
```bash
# 1. ユニットテスト実行（必須）
uv run code/unittest/run_all_tests.py

# 2. 統合テスト実行（推奨）
./code/scripts/test_run.sh --reset --debug

# 3. 本番前確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --dry-run
```

### Git操作
```bash
git add -A
git commit -m "[種類]: 変更内容（50文字以内）"
git push
```

**種類**: feat, fix, docs, test, refactor, style, chore

## 📦 依存関係

### Python要件
```txt
click>=8.0.0              # CLI
bibtexparser>=1.4.0       # BibTeX解析
fuzzywuzzy>=0.18.0        # 文字列類似度
python-levenshtein>=0.12.0 # 高速文字列比較
requests>=2.25.0          # HTTP API
pydantic>=1.8.0           # 設定バリデーション
pyyaml>=5.4.0             # YAML処理
```

### 実行環境
- Python 3.6+
- UV パッケージマネージャー

## 🚨 トラブルシューティング

| 問題 | 解決方法 |
|------|----------|
| ワークスペース不明 | `--workspace` でパス指定 |
| 処理スキップ | `--force` で強制実行 |
| YAMLエラー | `--repair-headers` で修復 |
| API接続エラー | 設定でリトライ回数調整 |
| テスト失敗 | `--reset` でテスト環境再構築 |

ログ確認: `logs/obsclippings.log`

## 📝 新機能追加手順

1. `code/py/modules/` 配下に新モジュール作成
2. `workflows/integrated_workflow.py` に統合ロジック追加
3. 状態管理システムに処理状態追加
4. ユニットテスト作成・実行
5. 統合テスト実行・確認
6. 仕様書更新

---

**重要**: 開発時は必ずTDD（Test-Driven Development）に従い、ユニットテスト・統合テスト両方の成功を維持してください。 