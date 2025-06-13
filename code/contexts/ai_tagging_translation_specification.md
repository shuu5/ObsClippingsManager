# AI Tagging & Translation機能仕様書

## 概要
Claude 3.5 Haikuを活用したAI論文理解支援機能として、自動タグ生成（Tagger）と要約翻訳（Abstract Translation）機能を提供。論文の分類・検索性向上と日本語での理解促進を実現します。

## 基本原理
- **Claude 3.5 Haiku**による高品質で高速な論文理解
- **バッチ処理**による効率的な大量処理
- **並列処理**による処理時間短縮
- **状態管理**による処理済みファイルのスキップ
- **デフォルト有効**: 統合ワークフローでの自動実行

## 処理統合
- run-integratedワークフローにデフォルト統合
- ai-citation-support → tagger → translate_abstract → ochiai_format → final-sync の順序
- 各ステップの独立性保持

## AI Tagging機能（Tagger）

### 概要
論文内容を解析し、関連するトピック・技術・遺伝子名などを自動抽出してタグ化する機能。

### タグ生成ルール

#### 命名規則
- **言語**: 英語のみ
- **形式**: スネークケース（例: machine_learning, cancer_research）
- **遺伝子名**: Gene symbol形式（例: KRT13, EGFR, TP53）
- **数量**: 10-20個程度
- **内容**: 論文理解に重要なキーワード

#### タグカテゴリ
1. **研究分野**: oncology, neuroscience, immunology
2. **技術手法**: machine_learning, crispr_cas9, rna_seq
3. **遺伝子/タンパク質**: KRT13, EGFR, TP53, BRCA1
4. **疾患**: alzheimer_disease, breast_cancer, diabetes
5. **生物学的プロセス**: apoptosis, cell_cycle, immune_response
6. **実験手法**: western_blot, flow_cytometry, mass_spectrometry

### YAMLヘッダー統合形式
```yaml
tags:
  - oncology
  - biomarkers
  - cancer_research
  - machine_learning
  - KRT13
  - EGFR
  - immunotherapy
  - clinical_trials
  - rna_seq
  - apoptosis
```

## Abstract Translation機能

### 概要
論文のabstract部分を自然な日本語に翻訳し、日本語での理解を促進する機能。

### 翻訳品質要件
- **自然性**: 学術論文として適切な日本語表現
- **正確性**: 専門用語の適切な翻訳
- **一貫性**: 同一論文内での用語統一
- **完全性**: 原文の情報量保持

### YAMLヘッダー統合形式
```yaml
abstract_japanese: |
  本研究では、がん研究における先進的なバイオマーカー技術について報告する。
  KRT13およびEGFR遺伝子の発現パターンを機械学習アルゴリズムを用いて解析し、
  診断精度の向上を達成した。
```

## 実装仕様

### ワークフロークラス
各機能は独立したワークフロークラスとして実装されます。

### プロンプト設計

#### タグ生成プロンプト
```
以下の学術論文の内容を分析し、10-20個のタグを生成してください。

ルール:
- 英語でのタグ生成
- スネークケース形式（例: machine_learning）
- 遺伝子名はgene symbol（例: KRT13, EGFR）
- 論文理解に重要なキーワードを抽出
- 研究分野、技術、疾患、遺伝子などを含む

論文内容:
{paper_content}

生成されたタグ（JSON配列形式で返答）:
```

#### 翻訳プロンプト
```
以下の学術論文のabstractを自然で正確な日本語に翻訳してください。

要件:
- 学術論文として適切な日本語表現
- 専門用語の正確な翻訳
- 原文の情報量を保持
- 読みやすく理解しやすい文章

Original Abstract:
{abstract_content}
```

## 設定項目

### バッチ処理設定
```yaml
ai_generation:
  default_model: "claude-3-5-haiku-20241022"
  tagger:
    enabled: true
    batch_size: 8                # Haikuの高速処理により最適化
    parallel_processing: true
    tag_count_range: [10, 20]
    retry_attempts: 3
    request_delay: 0.5           # Haikuの高速応答により短縮
  translate_abstract:
    enabled: true
    batch_size: 5                # Haikuの高速処理により最適化
    parallel_processing: true
    retry_attempts: 3
    request_delay: 0.8           # Haikuの高速応答により短縮
```

### API設定
```yaml
claude_api:
  model: "claude-3-5-haiku-20241022"
  api_key: "your-api-key"
  timeout: 30
  max_retries: 3
```

## エラーハンドリング

### API エラー対応
- **レート制限**: 自動ウェイト・リトライ
- **ネットワークエラー**: 指数バックオフリトライ
- **認証エラー**: エラーログ記録と処理停止
- **リクエスト制限**: バッチサイズ調整

### データ検証
- **タグ形式チェック**: 命名規則違反の修正
- **翻訳品質チェック**: 極端に短い翻訳の再処理
- **文字エンコーディング**: UTF-8エラーの処理

## 使用例

### 統合ワークフローでの使用（推奨）
```bash
# デフォルト実行（AI機能含む）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# AI機能無効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-ai-features
```

### 個別実行（デバッグ用）
```bash
# タグ生成のみ
PYTHONPATH=code/py uv run python code/py/main.py tagger

# 翻訳のみ
PYTHONPATH=code/py uv run python code/py/main.py translate-abstract
```

## 品質保証

### 自動検証項目
- タグ数の適切性（10-20個）
- タグ形式の正確性（スネークケース）
- 翻訳の完全性（極端な短縮の回避）
- 日本語エンコーディングの正確性

### 手動確認推奨項目
- 専門用語の翻訳正確性
- 学術的表現の適切性
- 論文内容との整合性 