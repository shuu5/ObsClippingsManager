# ObsClippingsManager v3.2.0 - Claude Code開発ガイド

## 🎯 タスク別詳細ルール参照

### 作業タイプ判定
**コード実装・修正・デバッグ作業の場合:**
- `code/contexts/PROGRESS.md`と各種仕様書を参照してコード実装する場合
- TDD開発、テスト実行、Git操作を行う場合
- **→ @dev-rule.md の詳細ルールに従って作業を進めてください**

**仕様書作成・修正作業の場合:**
- `code/contexts/*.md`内の仕様書を新規作成・更新する場合
- YAMLヘッダー、テンプレート、データ形式を扱う場合
- **→ @spec-rule.md の詳細ルールに従って作業を進めてください**

**どちらにも該当しない場合:**
- 以下の基本ガイドに従って作業を進めてください

## ⚠️ 重要ルール
- ユーザーとは日本語で会話して
- 詳細な作業手順は各専用ルールファイルを参照すること

## 🎯 システム概要

学術研究における文献管理とMarkdownファイル整理を自動化する統合システム。**シンプル設定**と**状態管理による重複処理回避**が特徴。

## 📁 プロジェクト構造

```
code/py/modules/
├── shared_modules/         # 共通基盤（config, logger, parser, utils）
├── citation_fetcher/       # 引用文献取得（CrossRef → Semantic Scholar → OpenCitations）
├── file_organizer/         # Citation keyベースのファイル整理
├── sync_checker/           # BibTeX ↔ Clippings整合性確認
├── section_parsing/        # Markdownセクション構造解析
├── ai_citation_support/    # AI理解支援・引用文献統合
├── ai_tagging_translation/ # AI論文解析（タグ生成・翻訳・要約）
└── status_management_yaml/ # YAML状態管理システム
```

## 📊 統合ワークフロー処理順序

```
organize → sync → fetch → section_parsing → ai_citation_support → enhanced-tagger → enhanced-translate → ochiai-format → final-sync
```

## 🔧 設定ファイル

### メイン設定
- `config/config.yaml`: システム全体設定
- `.env`: 環境変数（API Keys等）

### 重要な環境変数
```bash
# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Workspace Configuration
WORKSPACE_PATH=/home/user/ManuscriptsManager
```

---

**重要**: TDD必須、進捗管理連携、テスト100%成功維持、仕様書同期更新