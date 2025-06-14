# ObsClippingsManager v3.2.0 - 統合仕様書

学術研究における文献管理とMarkdownファイル整理を自動化する統合システム。**シンプル設定**と**状態管理による重複処理回避**が特徴。

## 📋 システム概要

### 主要機能
1. **多段階フォールバック引用文献取得** - CrossRef → Semantic Scholar → OpenCitations API
2. **ファイル自動整理** - Citation keyベースのディレクトリ構造
3. **同期チェック** - BibTeX ↔ Clippings整合性確認
4. **論文セクション分割** - Markdownの見出し構造による自動セクション解析
5. **AI理解支援** - YAMLヘッダーに引用文献情報統合
6. **AI論文解析** - Claude 3.5 Haikuによるタグ生成・翻訳・要約
7. **状態管理** - 処理完了済み項目の自動スキップ

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

## 🔗 個別モジュール仕様書

詳細仕様は以下を参照：

### コア機能
- **[統合ワークフロー](code/contexts/integrated_workflow_specification.md)** - 全処理ステップを単一コマンドで実行
- **[状態管理システム](code/contexts/status_management_yaml_specification.md)** - YAMLヘッダーベースの状態管理
- **[共有モジュール](code/contexts/shared_modules_specification.md)** - 基盤機能・設定管理
- **[引用文献取得システム](code/contexts/citation_fetcher_specification.md)** - 多段階フォールバック引用文献取得

### テストシステム
- **[統合テストシステム](code/contexts/integrated_testing_specification.md)** - Python統一テスト実行・品質保証・エンドツーエンド検証

### AI機能
- **[論文セクション分割](code/contexts/section_parsing_specification.md)** - Markdownセクション構造解析
- **[AI理解支援引用文献パーサー](code/contexts/enhanced_citation_parser_specification.md)** - 引用文献統合機能
- **[AI タグ・翻訳](code/contexts/ai_tagging_translation_specification.md)** - 自動タグ生成・要約翻訳
- **[落合フォーマット要約](code/contexts/ochiai_format_specification.md)** - 6項目構造化要約



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

# AI機能無効化（必要な場合）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-ai-features
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

### 環境変数設定（.env）
```bash
# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Workspace Configuration
WORKSPACE_PATH=/home/user/ManuscriptsManager

# Error Handling Configuration
ERROR_HANDLING_ENABLED=true
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=2

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_LOCATION=backups/
BACKUP_RETENTION_DAYS=30
AUTO_BACKUP_BEFORE_PROCESSING=true
```

### デフォルト設定（config/config.yaml）
```yaml
workspace_path: "/home/user/ManuscriptsManager"

# 自動導出パス
# bibtex_file: "{workspace_path}/CurrentManuscript.bib"
# clippings_dir: "{workspace_path}/Clippings"
# output_dir: "{workspace_path}/Clippings"

# エラーハンドリング設定
error_handling:
  enabled: true
  auto_retry_on_transient_errors: true
  max_retry_attempts: 3

# バックアップ設定
backup_settings:
  enabled: true
  auto_backup_before_processing: true
  retention_days: 30
```

### YAML状態管理フォーマット
```yaml
---
citation_key: paper2023key
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  ai_citation_support: completed
workflow_version: '3.2'
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

### テスト環境の安全性
- **テスト専用ディレクトリ**: `/tmp/ObsClippingsManager_Test` での動作検証
- **本番環境への影響回避**: テスト実行時の完全分離
- **自動クリーンアップ**: テスト環境の自動削除

### ユニットテスト実行
```bash
# 全ユニットテスト実行
uv run code/unittest/run_all_tests.py

# 個別テスト実行
uv run python -m unittest code.unittest.test_[module_name]
```

### 統合テスト実行（推奨）
```bash
# 完全統合テスト（Python統一実行）
uv run python code/scripts/run_integrated_test.py --test-type full

# 環境リセット後実行
uv run python code/scripts/run_integrated_test.py --reset-environment

# 特定モジュールテスト
uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules ai_features

# AI機能無効化テスト（API制限時）
uv run python code/scripts/run_integrated_test.py --disable-ai-features

# デバッグモード実行
uv run python code/scripts/run_integrated_test.py --verbose --keep-environment
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
uv run python code/scripts/run_integrated_test.py --test-type full

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
6. **仕様書作成**: `code/contexts/[モジュール名]_specification.md`（統一テンプレート準拠）

## 📋 仕様書構築ルール準拠

このプロジェクトの仕様書は以下のルールに従って構築されています：

### 統一テンプレート
各モジュール仕様書は以下の構成に準拠：
```markdown
# [モジュール名] 仕様書

## 概要
- **責務**: [具体的機能]
- **依存**: [他モジュールとの関係（例：yaml_template_manager → 基本ワークフロー）]
- **実行**: 統合ワークフローで自動実行

## YAMLヘッダー形式

### 入力
```yaml
---
[具体的入力例]
---
```

### 出力
```yaml
---
[具体的出力例]
---
```

## 実装
```python
[実装クラス例]
```

## 設定
```yaml
[設定例]
```
```

### 必須要件
- **YAMLヘッダー形式遵守**: 入力・出力の具体例記載
- **processing_status記録**: 各ステップの状態管理
- **具体的データ例**: 抽象的でなく実際の値使用
- **実装セクション**: クラス構造の明示

---

**重要**: 開発時は必ずTDD（Test-Driven Development）に従い、ユニットテスト・統合テスト両方の成功を維持してください。仕様書更新時は統一テンプレートに準拠し、YAMLヘッダー形式と具体的データ例を適切に記載してください。

## テスト

ObsClippingsManager のテストは、テスト実行時には必ず一時ディレクトリ（例: /tmp/ObsClippingsManager_Test）を使用する設計です。  
これにより、テスト実行後にプロジェクトルート（ワークスペース直下）に空の "clippings" や "backups" ディレクトリが残ることを防ぎ、テスト環境のクリーンアップが徹底されます。  
今後も、テストコードでは、テスト用の一時ディレクトリを明示的に利用するよう統一された設計を維持してください。 