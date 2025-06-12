# ObsClippingsManager v3.1 統合システム仕様書

## 概要
学術研究における文献管理とMarkdownファイル整理を自動化する統合システム。**シンプル設定**と**デフォルト引数なし実行**を重視し、効率的な状態管理により重複処理を自動回避。

## 特徴
- **シンプル設定**: 単一引数での統一ディレクトリ設定
- **デフォルト実行**: 引数なしでの完全動作
- **効率的処理**: 状態管理による重複処理の自動スキップ
- **独立モジュール**: 各機能の完全な分離を維持
- **AI理解支援**: AIが直接理解できる自己完結型引用文献統合
- **AI論文理解**: Claude 3.5 Sonnetによる自動タグ生成と要約翻訳

## システム構成

### 機能モジュール（7つの独立モジュール）
1. **Citation Fetcher**: 学術論文の引用文献を自動取得
2. **Rename & MkDir Citation Key**: Citation keyベースのファイル整理
3. **同期チェック**: BibTeX ↔ Clippingsディレクトリ整合性確認
4. **AI引用文献パーサー**: AI理解支援の自己完結型ファイル生成
5. **AI Tagging**: Claude 3.5 Sonnetによる自動タグ生成
6. **Abstract Translation**: Claude 3.5 Sonnetによる要約日本語翻訳
7. **状態管理**: 各論文の処理状態をYAMLヘッダーで追跡

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

## 統一設定システム

### 基本設定（デフォルト）
```yaml
# config/config.yaml
workspace_path: "/home/user/ManuscriptsManager"  # 単一設定で全パス自動導出

# 自動導出パス
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"
```

### デフォルト実行
```bash
# 引数なしで完全実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated
```

### カスタム設定（必要時のみ）
```bash
# ワークスペース変更
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"

# 個別ファイル指定
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --bibtex-file "/path/to/file.bib" \
    --clippings-dir "/path/to/clippings"
```

## メイン機能: run-integrated

### 処理フロー
```
organize → sync → fetch → ai-citation-support → tagger → translate_abstract → final-sync
```

### 基本実行
```bash
# デフォルト実行（推奨）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess
```

## YAMLヘッダー形式（v3.1統合形式）

```yaml
---
citation_key: smith2023test
citation_metadata:
  last_updated: '2025-01-15T10:30:00.123456'
  mapping_version: '2.0'
  source_bibtex: references.bib
  total_citations: 2
citations:
  1:
    authors: Smith
    citation_key: smith2023test
    doi: 10.1158/0008-5472.CAN-23-0123
    journal: Cancer Research
    title: Novel Method for Cancer Cell Analysis
    year: 2023
  2:
    authors: Jones
    citation_key: jones2022biomarkers
    doi: 10.1038/s41591-022-0456-7
    journal: Nature Medicine
    title: Advanced Biomarker Techniques in Oncology
    year: 2022
tags:
  - oncology
  - cancer_research
  - machine_learning
  - KRT13
  - EGFR
abstract_japanese: |
  本研究では、がん細胞解析のための新しい手法を開発した。
  機械学習アルゴリズムを用いてTP53およびEGFR遺伝子の発現パターンを解析し、
  診断精度の大幅な向上を実現した。
last_updated: '2025-01-15T10:30:00.654321+00:00'
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  ai-citation-support: completed
  tagger: completed
  translate_abstract: completed
workflow_version: '3.1'
---
```

## テスト環境

```bash
# テスト環境での実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --workspace "/home/user/proj/ObsClippingsManager/TestManuscripts"
```

## AI機能オプション

### AI理解支援引用文献パーサー
- YAMLヘッダーに全引用文献情報を統合
- AIが直接Markdownファイルを読むだけで完全理解可能
- 外部ファイル依存を排除した自己完結型設計

### AI Tagging
- Claude 3.5 Sonnetによる論文内容の自動解析
- 英語・スネークケースでの統一タグ命名
- 10-20個程度の関連トピック・技術・遺伝子名の自動タグ生成

### Abstract Translation
- Claude 3.5 Sonnetによる論文要約の日本語翻訳
- 学術的で自然な日本語表現での翻訳
- 専門用語の正確な翻訳と一貫性確保

## 状態管理

- 各論文の処理状態をYAMLヘッダーで追跡
- 完了済み処理の自動スキップ
- 失敗処理の再実行制御
- 効率的な重複処理回避

---

**統合仕様書バージョン**: 3.0.0

## 関連仕様書
- [統合ワークフロー仕様](./integrated_workflow_specification.md)
- [状態管理システム仕様](./status_management_specification.md)
- [共有モジュール仕様](./shared_modules_specification.md)

