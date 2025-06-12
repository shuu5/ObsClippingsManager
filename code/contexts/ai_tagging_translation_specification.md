# AI Tagging & Translation機能仕様書 v3.1

## 概要
Claude API 3.5 Sonnetを活用したAI論文理解支援機能として、自動タグ生成（Tagger）と要約翻訳（Abstract Translation）機能を提供。論文の分類・検索性向上と日本語での理解促進を実現します。

## 基本原理
- **Claude 3.5 Sonnet**による高品質な論文理解
- **バッチ処理**による効率的な大量処理
- **並列処理**による処理時間短縮
- **状態管理**による処理済みファイルのスキップ

## 処理統合
- run-integratedワークフローに統合
- ai-citation-support → tagger → translate_abstract → final-sync の順序
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

### 実装仕様

#### TaggerWorkflow クラス
```python
class TaggerWorkflow:
    """AI論文タグ生成ワークフロー"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('TaggerWorkflow')
        self.claude_client = ClaudeAPIClient(config_manager, logger)
        
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None, 
                      batch_size: int = 5, parallel: bool = True) -> Dict[str, Any]:
        """論文の一括タグ生成処理"""
        
    def generate_tags_single(self, paper_path: str) -> List[str]:
        """単一論文のタグ生成"""
        
    def validate_tags(self, tags: List[str]) -> List[str]:
        """生成タグの検証・正規化"""
```

#### バッチ処理設計
```python
def process_batch(self, paper_batch: List[str]) -> Dict[str, List[str]]:
    """
    複数論文の並列タグ生成処理
    
    Args:
        paper_batch: 処理対象論文パスのリスト
    
    Returns:
        {paper_path: [tags], ...}
    
    処理フロー:
    1. 各論文の内容抽出
    2. Claude APIに並列リクエスト
    3. レスポンス結果の検証・正規化
    4. YAMLヘッダーへの統合
    """
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

### 実装仕様

#### TranslateAbstractWorkflow クラス
```python
class TranslateAbstractWorkflow:
    """AI要約翻訳ワークフロー"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('TranslateAbstractWorkflow')
        self.claude_client = ClaudeAPIClient(config_manager, logger)
        
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None,
                      batch_size: int = 3, parallel: bool = True) -> Dict[str, Any]:
        """論文の一括要約翻訳処理"""
        
    def translate_abstract_single(self, paper_path: str) -> str:
        """単一論文の要約翻訳"""
        
    def extract_abstract(self, paper_content: str) -> str:
        """論文からabstract部分を抽出"""
```

## Claude API Client設計

### 基本クラス構造
```python
class ClaudeAPIClient:
    """Claude API統合クライアント"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('ClaudeAPIClient')
        self.model = "claude-3-5-sonnet-20241022"
        
    async def generate_tags_batch(self, papers_content: List[str]) -> List[List[str]]:
        """バッチタグ生成"""
        
    async def translate_abstracts_batch(self, abstracts: List[str]) -> List[str]:
        """バッチ要約翻訳"""
        
    def handle_api_errors(self, error: Exception) -> Dict[str, Any]:
        """API エラーハンドリング"""
```

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
  tagger:
    batch_size: 5
    parallel_processing: true
    tag_count_range: [10, 20]
    retry_attempts: 3
    request_delay: 1.0
  translate_abstract:
    batch_size: 3
    parallel_processing: true
    retry_attempts: 3
    request_delay: 1.5
```

### API設定
```yaml
claude_api:
  model: "claude-3-5-sonnet-20241022"
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

### 基本的な使用方法
```python
# ワークフロー初期化
tagger_workflow = TaggerWorkflow(config_manager, logger)
translate_workflow = TranslateAbstractWorkflow(config_manager, logger)

# タグ生成
tag_results = tagger_workflow.process_papers(
    clippings_dir="/path/to/clippings",
    target_papers=["smith2023test"],
    batch_size=5
)

# 要約翻訳
translation_results = translate_workflow.process_papers(
    clippings_dir="/path/to/clippings",
    target_papers=["smith2023test"],
    batch_size=3
)
```

### 統合実行
```bash
# AI機能を有効化した統合ワークフロー実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --enable-tagger \
    --enable-translate-abstract
```

## 品質保証

### タグ品質管理
- **一貫性チェック**: 類似論文での共通タグ確認
- **完全性チェック**: 重要カテゴリの漏れ確認
- **正確性チェック**: 遺伝子名・専門用語の確認

### 翻訳品質管理
- **自然性チェック**: 日本語として自然な文章
- **正確性チェック**: 原文との意味一致確認
- **専門用語チェック**: 学術分野での適切な翻訳

---

**AI Tagging & Translation機能仕様書バージョン**: 3.1.0 