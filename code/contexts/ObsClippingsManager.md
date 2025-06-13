# ObsClippingsManager システム仕様書

## 概要
学術研究における文献管理とMarkdownファイル整理を自動化する統合システム。シンプル設定と状態管理による重複処理回避が特徴。

## 基本原理
- **シンプル設定**: 単一`workspace_path`設定で全パス自動導出
- **デフォルト実行**: 引数なしでの完全動作
- **効率的処理**: 状態管理による重複処理の自動スキップ
- **独立モジュール**: 各機能の完全な分離を維持
- **AI統合**: Claude 3.5 Haikuによる自動解析・翻訳・要約
- **安全性**: テスト環境での完全動作検証

## システム構成

### 処理フロー
```
organize → sync → fetch → section-parsing → ai-citation-support → enhanced-tagger → enhanced-translate → ochiai-format → final-sync
```

### 機能モジュール（9つの独立モジュール）
1. **Citation Fetcher**: 学術論文の引用文献を自動取得
2. **Rename & MkDir Citation Key**: Citation keyベースのファイル整理
3. **同期チェック**: BibTeX ↔ Clippingsディレクトリ整合性確認
4. **論文セクション分割**: Markdownの見出し構造による自動セクション解析
5. **AI引用文献パーサー**: AI理解支援の自己完結型ファイル生成
6. **AI Tagging**: セクション対応の精密タグ生成
7. **Abstract Translation**: セクション対応の精密要約翻訳
8. **落合フォーマット要約**: 6項目構造化論文要約生成
9. **状態管理**: 各論文の処理状態をYAMLヘッダーで追跡

### アーキテクチャ
```
ObsClippingsManager
├── main.py                    # 統合メインプログラム
└── modules/
    ├── shared/                # 共有モジュール
    ├── citation_fetcher/      # 引用文献取得
    ├── rename_mkdir_citation_key/ # ファイル整理
    ├── ai_citation_support/   # AI理解支援
    ├── ai_tagging/           # AI論文タグ生成
    ├── abstract_translation/ # AI要約翻訳
    ├── ochiai_format/        # 落合フォーマット要約
    ├── section_parsing/      # 論文セクション分割
    ├── status_management/    # 状態管理
    └── workflows/            # ワークフロー管理
```

## 基本実行

### デフォルト実行（推奨）
```bash
# 引数なしで完全実行（AI機能含む）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated
```

### 実行オプション
```bash
# 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess

# ワークスペース変更
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"

# AI機能無効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-ai-features
```

## 設定システム

### デフォルト設定
- **workspace_path**: `/home/user/ManuscriptsManager`（単一設定で全パス自動導出）
- **引数なし実行**: 完全なデフォルト動作
- **AI機能**: デフォルト有効（Claude 3.5 Haiku 使用）

### 設定優先順位
1. **コマンドライン引数** (最高優先度)
2. **設定ファイル** (config.yaml)
3. **デフォルト値** (最低優先度)

## AI機能統合

### 統一AI技術スタック
- **モデル**: Claude 3.5 Haiku
- **言語**: 日本語出力対応
- **処理方式**: バッチ・並列処理

### AI機能一覧
1. **論文セクション分割**: 見出し構造解析による学術論文の自動セクション識別
2. **AI理解支援引用文献パーサー**: YAMLヘッダーに全引用文献情報を統合
3. **AI Tagging**: 論文内容の自動解析による英語タグ生成
4. **Abstract Translation**: 論文要約の日本語翻訳
5. **落合フォーマット要約**: 6つの構造化された質問による論文要約

## エッジケース処理

### 処理方針
- **missing_in_clippings**: DOI情報表示後スキップ
- **orphaned_in_clippings**: ファイル情報表示後スキップ
- **安全性優先**: 不完全なデータでの処理回避
- **処理継続**: 一部問題で全体停止せず

## 詳細仕様書

### コア機能仕様
- **[統合ワークフロー仕様](./integrated_workflow_specification.md)**: ワークフロー詳細・エッジケース処理
- **[状態管理システム仕様](./status_management_yaml_specification.md)**: YAMLヘッダー形式・状態管理
- **[共有モジュール仕様](./shared_modules_specification.md)**: 基盤機能・設定管理

### AI機能仕様
- **[論文セクション分割仕様](./section_parsing_specification.md)**: Markdownセクション構造解析機能
- **[AI理解支援引用文献パーサー仕様](./enhanced_citation_parser_specification.md)**: 引用文献統合機能
- **[AI タグ・翻訳仕様](./ai_tagging_translation_specification.md)**: AI機能詳細
- **[落合フォーマット要約仕様](./ochiai_format_specification.md)**: 6項目構造化要約機能

