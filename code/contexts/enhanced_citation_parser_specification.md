# AI理解支援引用文献パーサー機能仕様書

## 概要
references.bibの内容をそのまま順序通りにYAMLヘッダーに統合し、AIが直接Markdownファイルを読むだけで引用文献を理解できるシンプルな自己完結型システム。

## 主要機能

### シンプル引用マッピング機能
- references.bibの全エントリーを順序通りにYAMLヘッダーに統合
- 重複エントリーも含めて全て処理
- プレースホルダー生成なし
- total_citationsはBibTeXエントリー数と一致
- **デフォルト有効**: 統合ワークフローでの自動実行

## YAMLヘッダー統合形式

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
processing_status:
  ai-citation-support: completed
workflow_version: '3.2'
---
```

## 実装仕様

### ワークフロークラス
AI理解支援引用文献パーサー機能は独立したワークフロークラスとして実装されます。

### データ構造
詳細なデータ構造定義は状態管理システム仕様書を参照してください。

## マッピングルール

### シンプルマッピング原則
1. **順序保持**: references.bibのエントリー順序をそのまま維持
2. **重複包含**: 重複エントリーも含めて全て処理（BibTeXファイルの構造保持）
3. **1:1対応**: BibTeXエントリー番号 = 引用番号（1から開始）
4. **プレースホルダーなし**: 存在しないエントリーに対する自動生成なし

### データ一貫性
- `total_citations` = BibTeXファイルのエントリー数
- `citations` の最大キー = `total_citations`
- 欠番なし（1からtotal_citationsまで連続）

## 使用例

### 統合ワークフローでの使用（推奨）
```bash
# デフォルト実行（AI理解支援機能含む）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# AI理解支援機能無効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-ai-citation-support
```

### 個別実行（デバッグ用）
```bash
# 単独実行
PYTHONPATH=code/py uv run python code/py/main.py parse-citations \
    --input paper.md \
    --references references.bib
```

## テスト仕様

### マッピング作成テスト
マッピング機能の正確性とデータ一貫性を検証します。

### 重複処理テスト
重複を含むBibTeXファイルでも全エントリーを正確に処理することを確認します。