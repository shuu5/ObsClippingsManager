# ObsClippingsManager v3.2 統合システム仕様書

## 概要
学術研究における文献管理とMarkdownファイル整理を自動化する統合システム。**シンプル設定**と**デフォルト引数なし実行**を重視し、効率的な状態管理により重複処理を自動回避。

## 特徴
- **シンプル設定**: 単一引数での統一ディレクトリ設定
- **デフォルト実行**: 引数なしでの完全動作
- **効率的処理**: 状態管理による重複処理の自動スキップ
- **独立モジュール**: 各機能の完全な分離を維持
- **AI理解支援**: AIが直接理解できる自己完結型引用文献統合
- **AI論文理解**: Claude 3.5 Sonnetによる自動タグ生成と要約翻訳
- **エッジケース対応**: 不整合データの適切な処理とスキップ

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
6. **AI Tagging (Enhanced)**: セクション対応の精密タグ生成
7. **Abstract Translation (Enhanced)**: セクション対応の精密要約翻訳
8. **落合フォーマット要約**: 6項目構造化論文要約生成
9. **状態管理**: 各論文の処理状態をYAMLヘッダーで追跡

### アーキテクチャ
```
ObsClippingsManager v3.1
├── main.py                    # 統合メインプログラム
└── modules/
    ├── shared/                # 共有モジュール
    ├── citation_fetcher/      # 引用文献取得
    ├── rename_mkdir_citation_key/ # ファイル整理
    ├── ai_citation_support/   # AI理解支援
    ├── ai_tagging/           # AI論文タグ生成
    ├── abstract_translation/ # AI要約翻訳
    ├── status_management/    # 状態管理
    └── workflows/            # ワークフロー管理
```

## 基本実行

### デフォルト実行（推奨）
```bash
# 引数なしで完全実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated
```

### 実行オプション
```bash
# 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess

# AI機能無効化（明示的に無効化したい場合）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-tagger --disable-translate-abstract --disable-section-parsing --disable-ochiai-format

# ワークスペース変更
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"
```

### テスト環境
```bash
# テスト環境での実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts"
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

## AI機能

### 論文セクション分割
- Markdownの見出し構造解析による学術論文の自動セクション識別
- YAMLヘッダーへの構造情報永続化により他AI機能の精度向上

### AI理解支援引用文献パーサー
- YAMLヘッダーに全引用文献情報を統合した自己完結型設計
- AIが直接Markdownファイルを読むだけで完全理解可能

### AI Tagging (Enhanced)
- Claude 3.5 Haiku (claude-3-5-haiku-20241022) による論文内容の自動解析（セクション対応）
- 英語・スネークケースでの統一タグ命名（10-20個程度）

### Abstract Translation (Enhanced)
- Claude 3.5 Haiku (claude-3-5-haiku-20241022) による論文要約の日本語翻訳（セクション対応）
- 学術的で自然な日本語表現での翻訳

### 落合フォーマット要約
- 論文内容を6つの構造化された質問で要約
- 研究者向けのA4一枚程度の簡潔な論文理解支援

## エッジケース処理

### 処理方針
- **missing_in_clippings**: DOI情報表示後スキップ
- **orphaned_in_clippings**: ファイル情報表示後スキップ
- **安全性優先**: 不完全なデータでの処理回避
- **処理継続**: 一部問題で全体停止せず

詳細仕様は [統合ワークフロー仕様書](./integrated_workflow_specification.md#エッジケース処理仕様-v31) を参照。

## 詳細仕様書

### 個別機能仕様
- **[統合ワークフロー仕様](./integrated_workflow_specification.md)**: ワークフロー詳細・エッジケース処理
- **[状態管理システム仕様](./status_management_yaml_specification.md)**: YAMLヘッダー形式・状態管理
- **[論文セクション分割仕様](./section_parsing_specification.md)**: Markdownセクション構造解析機能
- **[落合フォーマット要約仕様](./ochiai_format_specification.md)**: 6項目構造化要約機能
- **[AI タグ・翻訳仕様](./ai_tagging_translation_specification.md)**: AI機能詳細
- **[共有モジュール仕様](./shared_modules_specification.md)**: 基盤機能・設定管理

### アーカイブ仕様書
v2.0時代の詳細仕様は [archive_v2/](./archive_v2/) ディレクトリを参照。

---

**統合仕様書バージョン**: 3.2.0

## 関連仕様書
- [統合ワークフロー仕様](./integrated_workflow_specification.md)
- [状態管理システム仕様](./status_management_yaml_specification.md)
- [論文セクション分割仕様](./section_parsing_specification.md)
- [落合フォーマット要約仕様](./ochiai_format_specification.md)
- [AI タグ・翻訳仕様](./ai_tagging_translation_specification.md)
- [共有モジュール仕様](./shared_modules_specification.md)

