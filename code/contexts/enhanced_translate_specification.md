---
title: "Enhanced Translate機能仕様書"
version: "3.2.0"
module: "ai_tagging_translation.translate_workflow"
last_updated: "2025-06-16"
status: "completed"
---

# Enhanced Translate機能仕様書

## 概要

Enhanced Translate機能は、学術論文のAbstractを自然で正確な日本語に翻訳する機能です。Claude 3.5 Haiku APIを活用し、4軸品質評価システムによる翻訳品質管理を提供します。

## モジュール構成

### コード収納場所
```
code/py/modules/ai_tagging_translation/
├── translate_workflow.py     # TranslateWorkflowクラス（メイン実装）
├── claude_api_client.py      # Claude APIクライアント（共有）
└── __init__.py              # モジュール初期化
```

### テスト収納場所
```
code/unittest/
└── test_translate_workflow.py  # TranslateWorkflow専用テスト（21テスト）
```

## 機能仕様

### 1. TranslateWorkflowクラス

#### 1.1 基本設定
```python
class TranslateWorkflow:
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.enabled = config_manager.get_ai_setting('translate_abstract', 'enabled', default=True)
        self.batch_size = config_manager.get_ai_setting('translate_abstract', 'batch_size', default=5)
```

**設定項目:**
- **enabled**: 翻訳機能の有効/無効（デフォルト: True）
- **batch_size**: バッチ処理サイズ（デフォルト: 5）
- **API統合**: Claude 3.5 Haiku API遅延初期化

#### 1.2 主要メソッド

##### process_items()
```python
def process_items(self, input_dir: str, target_items: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    論文の一括要約翻訳処理
    
    Returns:
        {
            'status': 'completed',
            'processed': 処理成功件数,
            'skipped': スキップ件数,
            'failed': 失敗件数,
            'total_papers': 総論文数
        }
    """
```

##### translate_abstract_single()
```python
def translate_abstract_single(self, paper_path: str) -> str:
    """
    単一論文のabstract翻訳
    
    処理フロー:
    1. Abstract抽出（extract_abstract_content）
    2. プロンプト構築（_build_translation_prompt）
    3. Claude API呼び出し
    4. レスポンス解析（_parse_translation_response）
    """
```

##### extract_abstract_content()
```python
def extract_abstract_content(self, paper_path: str) -> str:
    """
    論文からabstractセクションを抽出
    
    データソース: YAMLヘッダーのpaper_structure.sections
    対象セクション: section_type='abstract'
    前提条件: section_parsing処理完了済み
    """
```

### 2. 翻訳プロンプト設計

#### 2.1 プロンプト構造
```python
def _build_translation_prompt(self, abstract_content: str) -> str:
    """
    高品質翻訳のための詳細プロンプト構築
    """
```

**プロンプト要素:**
- **品質基準**: 自然性・正確性・完全性・読みやすさ
- **翻訳指針**: 専門用語処理・文体表現・数値統計・文章構成
- **具体的ルール**: 遺伝子名保持・疾患名標準訳語・技術手法日本語化

#### 2.2 実際のプロンプト例
```
以下の学術論文のabstractを自然で正確な日本語に翻訳してください。

## **翻訳要件**

**品質基準:**
- **自然性**: 学術論文として適切な日本語表現を使用
- **正確性**: 専門用語の適切な翻訳と一貫性の維持
- **完全性**: 原文の情報量を保持し、詳細な内容を省略しない
- **読みやすさ**: 理解しやすい文章構成と適切な文体

**翻訳指針:**
1. **専門用語処理**: 
   - 遺伝子名・タンパク質名: 原文のまま保持（例: KRT13, EGFR, TP53）
   - 疾患名: 日本語標準訳語を使用（例: breast cancer → 乳癌）
   - 技術手法: 一般的な日本語訳語を使用（例: Western blot → ウエスタンブロット）

## **Original Abstract:**
---
{abstract_content}
---

**日本語翻訳:**
```

### 3. 4軸品質評価システム

#### 3.1 品質評価指標
```python
def evaluate_translation_quality(self, translation: str, original: str) -> float:
    """
    4軸による重み付き品質スコア算出
    
    評価軸:
    1. 完全性（重み: 0.3） - 原文の情報量保持
    2. 自然性（重み: 0.25）- 日本語として自然
    3. 一貫性（重み: 0.25）- 用語統一・英語混入度
    4. 正確性（重み: 0.2） - 専門用語・数値保持
    """
```

#### 3.2 各評価軸の詳細

##### 完全性評価 (_evaluate_completeness)
```python
# 理想的な長さ比率: 0.8-1.5
if 0.8 <= length_ratio <= 1.5:
    return 1.0
elif length_ratio < 0.8:
    return max(0.0, length_ratio / 0.8)  # 短すぎる場合の減点
```

##### 自然性評価 (_evaluate_fluency)
```python
# 評価要素:
# - 日本語文字の存在（0.4点）
# - 適切な句読点使用（0.3点）
# - 文の長さ適切性（0.3点）
```

##### 一貫性評価 (_evaluate_consistency)
```python
# 英語混入度合いの評価
# 適度な専門用語混入は許容（遺伝子名等）
if english_ratio <= 0.5:
    return 1.0
elif english_ratio <= 1.0:
    return 0.7
```

##### 正確性評価 (_evaluate_accuracy)
```python
# 評価要素:
# - 数値保持率（0.5点）
# - 遺伝子名保持率（0.5点）
```

### 4. YAMLヘッダー統合仕様

#### 4.1 翻訳結果統合
```yaml
ai_content:
  abstract_japanese:
    generated_at: '2025-06-16T15:47:40.123456'
    content: |
      これは翻訳されたアブストラクトの内容です。
      学術論文として適切な日本語表現を使用しており、
      専門用語の正確な翻訳と読みやすい文章構成を実現しています。
```

#### 4.2 品質情報統合
```yaml
translation_quality:
  quality_score: 0.85              # 総合品質スコア
  completeness_score: 0.9          # 完全性スコア
  fluency_score: 0.8               # 自然性スコア
  consistency_score: 0.85          # 一貫性スコア
  accuracy_score: 0.9             # 正確性スコア
  original_length: 500             # 原文文字数
  translation_length: 450          # 翻訳文字数
  length_ratio: 0.9                # 長さ比率
  evaluation_timestamp: '2025-06-16T15:47:40.123456'
  has_suggestions: false           # 改善提案の有無
```

#### 4.3 処理状態更新
```yaml
processing_status:
  translate_abstract: completed    # 翻訳処理完了
```

### 5. エラーハンドリング

#### 5.1 翻訳レスポンス検証
```python
def _parse_translation_response(self, response: str) -> str:
    """
    Claude APIレスポンス検証
    
    検証項目:
    1. 最小長さチェック（50文字以上）
    2. 日本語文字存在確認
    3. ラベル除去処理
    """
```

#### 5.2 例外処理体系
```python
# ProcessingError継承による統一例外処理
raise ProcessingError(
    message=f"Abstract translation failed for {paper_path}",
    error_code="TRANSLATION_FAILED",
    context={"paper_path": paper_path}
)
```

### 6. 改善提案システム

#### 6.1 改善提案生成
```python
def suggest_translation_improvements(self, translation: str, original: str) -> List[str]:
    """
    翻訳改善提案の自動生成
    
    提案内容:
    1. 長さ比率の適切性
    2. 日本語文字の確認
    3. 専門用語保持状況
    4. 数値保持状況
    5. 文章の自然性
    """
```

#### 6.2 提案例
```python
suggestions = [
    "Translation appears shorter than expected - check for missing content",
    "Consider preserving gene symbols: KRT13, EGFR",
    "Consider preserving numerical values: 95%, 0.001",
    "Consider breaking down very long sentences for readability"
]
```

## 統合ワークフロー仕様

### 処理順序
```
organize → sync → fetch → section_parsing → ai_citation_support → enhanced-tagger → **enhanced-translate**
```

### AI機能制御対応
```bash
# 翻訳機能のみ有効化
uv run python code/scripts/run_integrated_test.py --enable-only-translate

# 翻訳機能無効化
uv run python code/scripts/run_integrated_test.py --disable-translate

# 全AI機能無効化
uv run python code/scripts/run_integrated_test.py --disable-ai
```

## テスト仕様

### ユニットテスト構成（21テスト）

#### TestTranslateWorkflow（13テスト）
- 初期化テスト
- Claude APIクライアント遅延初期化
- 機能無効時の動作
- Abstract抽出機能
- プロンプト構築
- レスポンス解析（有効・無効・短すぎる・ラベル付き）
- 品質評価基本機能
- フィードバックレポート生成
- 改善提案生成

#### TestTranslateWorkflowQualityEvaluation（5テスト）
- 完全性評価（理想・短すぎる）
- 自然性評価（良い日本語・日本語なし）
- 一貫性評価（適切な英語混入）
- 正確性評価（数値・遺伝子名保持・重要情報欠落）

#### TestTranslateWorkflowYAMLIntegration（3テスト）
- YAML翻訳・品質情報更新機能

### 統合テスト仕様
```bash
# enhanced-translate単体テスト
uv run python code/scripts/run_integrated_test.py --enable-only-translate

# 期待される結果:
# - TranslateWorkflow正常初期化
# - Abstract抽出機能動作
# - API連携基盤確認（APIキー設定時）
# - 品質評価システム動作
# - YAML統合機能確認
```

## 設定仕様

### config.yaml設定項目
```yaml
ai_generation:
  translate_abstract:
    enabled: true
    batch_size: 5
    parallel_processing: true
    retry_attempts: 3
    request_delay: 0.8
    error_handling:
      validate_translation_quality: true
      backup_on_translation_failure: true
      preserve_original_on_error: true
      handle_encoding_errors: true
    backup_strategy:
      backup_before_translation: true
      keep_translation_versions: true
      preserve_original_abstract: true
```

### 環境変数
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

## パフォーマンス仕様

### API効率
- **バッチサイズ**: 5（コストと効率のバランス）
- **レート制限**: Claude API標準制限準拠
- **リトライ機構**: 最大3回の自動リトライ

### 品質基準
- **総合品質スコア**: 0.7以上を高品質とする
- **各軸最低基準**: 0.5以上
- **翻訳長さ比率**: 0.8-1.5を理想範囲とする

## 実装完了ステータス

### ✅ 完了機能
1. **TranslateWorkflowクラス**: 完全実装
2. **4軸品質評価システム**: 完全実装
3. **Claude API連携**: 完全実装
4. **YAML統合機能**: 完全実装
5. **エラーハンドリング**: 完全実装
6. **統合ワークフロー組み込み**: 完全実装
7. **AI機能制御対応**: 完全実装
8. **ユニットテスト**: 21テスト全成功
9. **統合テスト**: 成功確認済み

### 📊 品質指標
- **テストカバレッジ**: 100%（全メソッド網羅）
- **テスト成功率**: 100%（356/356テスト成功）
- **統合テスト**: 成功（--enable-only-translate）
- **AI機能制御**: 全オプション対応完了

---

**最終更新**: 2025-06-16
**実装ステータス**: 完了
**次期開発対象**: 2.8 ochiai-format（落合フォーマット要約）