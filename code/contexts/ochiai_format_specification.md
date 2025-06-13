# 落合フォーマット要約機能仕様書

## 概要
学術論文の内容を6つの構造化された質問に答える形で要約し、研究者向けのA4一枚程度の簡潔な論文理解を提供する機能。Claude 3.5 Haikuを活用して日本語での学術的要約を自動生成します。

## 落合フォーマット仕様

### 6つの質問項目
1. **どんなもの？** - アブストラクトをさらに短くギュッとまとめた内容
2. **先行研究と比べてどこがすごい？** - 課題と学術的価値
3. **技術や手法のキモはどこ？** - 使用技術・手法の核心
4. **どうやって有効だと検証した？** - 被験者・実験・データによる検証方法
5. **議論はある？** - 結果解釈・研究限界・批判的視点
6. **次に読むべき論文は？** - 参考文献から選出した推奨論文

### 生成ルール
- **簡潔性**: 各項目3-5文程度
- **具体性**: 抽象的でなく具体的な内容
- **日本語**: 学術的で自然な日本語表現
- **構造化**: 6項目の明確な区分

## データ構造

### OchiaiFormat
```python
@dataclass
class OchiaiFormat:
    what_is_this: str            # どんなもの？
    what_is_superior: str        # 先行研究と比べてどこがすごい？
    technical_key: str           # 技術や手法のキモはどこ？
    validation_method: str       # どうやって有効だと検証した？
    discussion_points: str       # 議論はある？
    next_papers: str            # 次に読むべき論文は？
    generated_at: str           # 生成日時
```

## YAMLヘッダー形式

```yaml
---
citation_key: smith2023test
ochiai_format:
  generated_at: '2025-01-15T11:00:00.123456'
  questions:
    what_is_this: |
      KRT13タンパク質の発現パターンを機械学習で解析し、
      がん診断精度を95%まで向上させた新しいバイオマーカー技術。
      従来の組織診断と比較して診断時間を半分に短縮。
    what_is_superior: |
      既存の免疫組織化学的手法と比較して、AI画像解析による
      客観的定量評価を実現。従来の主観的診断の限界を克服し、
      診断者間のばらつきを大幅に削減した点が革新的。
    technical_key: |
      深層学習ベースのConvolutional Neural Networkを用いて、
      KRT13タンパク質の発現パターンを定量化。Transfer learningと
      data augmentationにより少数サンプルでの高精度学習を実現。
    validation_method: |
      500例の組織サンプルを用いた後向き研究。3名の病理医による
      独立診断を gold standard とし、機械学習モデルの診断精度、
      感度、特異度を統計学的に評価。Cross-validationで再現性確認。
    discussion_points: |
      サンプル数の制限により一般化性能に課題。異なる施設・機器での
      検証が必要。また、稀な組織型への適用可能性は今後の検討課題。
      コスト効果分析も実臨床導入には重要。
    next_papers: |
      1. Jones et al. (2022) - KRT13の分子メカニズム詳細
      2. Davis et al. (2023) - 他のがん種での類似手法
      3. Wilson et al. (2024) - AI診断の臨床実装ガイドライン
processing_status:
  ochiai_format: completed
workflow_version: '3.2'
---
```

## 実装クラス

### OchiaiFormatWorkflow
```python
class OchiaiFormatWorkflow:
    """落合フォーマット要約生成ワークフロー"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('OchiaiFormatWorkflow')
        self.claude_client = ClaudeAPIClient(config_manager, logger)
        
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None, 
                      batch_size: int = 2, parallel: bool = False) -> Dict[str, Any]:
        """論文の一括落合フォーマット要約処理"""
        
    def generate_ochiai_summary_single(self, paper_path: str) -> OchiaiFormat:
        """単一論文の落合フォーマット要約生成"""
        
    def extract_paper_content(self, paper_path: str) -> Dict[str, str]:
        """論文内容の抽出（セクション分割機能と連携可能）"""
        
    def update_yaml_with_ochiai(self, paper_path: str, ochiai: OchiaiFormat) -> bool:
        """YAMLヘッダーに落合フォーマットを記録"""
        
    def validate_ochiai_format(self, ochiai: OchiaiFormat) -> bool:
        """生成された要約の品質検証"""
```

## Claude API プロンプト設計

### 基本プロンプト
```
以下の学術論文の内容を、落合フォーマットの6つの質問に答える形で要約してください。

【論文情報】
タイトル: {title}
著者: {authors}
ジャーナル: {journal}

【論文内容】
{paper_content}

【要約ルール】
1. 各項目3-5文程度で簡潔に
2. 具体的で実用的な内容
3. 学術的で自然な日本語
4. 「次に読むべき論文」は参考文献から3本選出

【落合フォーマット6項目】
1. どんなもの？
2. 先行研究と比べてどこがすごい？
3. 技術や手法のキモはどこ？
4. どうやって有効だと検証した？
5. 議論はある？
6. 次に読むべき論文は？

JSON形式で回答してください：
{
  "what_is_this": "...",
  "what_is_superior": "...",
  "technical_key": "...",
  "validation_method": "...",
  "discussion_points": "...",
  "next_papers": "..."
}
```

## 設定項目

```yaml
ochiai_format:
  batch_size: 3                  # バッチサイズ（Haikuの高速処理により最適化）
  parallel_processing: true      # Haikuの効率性を活用
  retry_attempts: 3
  request_delay: 1.0             # Haikuの高速応答により短縮
  max_content_length: 10000      # 論文内容最大文字数制限
  enable_section_integration: true  # セクション分割機能との連携
```

## セクション分割機能との連携

### 連携が有効な場合
- `paper_structure` YAMLフィールドが存在する場合、セクション別にコンテンツを抽出
- より精密な要約生成が可能

### 連携が無効な場合
- 論文全体を単一コンテンツとして処理
- セクション分割機能が未実行でも動作

## エラーハンドリング

- **コンテンツ長すぎ**: 最大文字数制限による内容要約
- **API制限**: レート制限とプロンプトサイズ制限の対応
- **生成品質不良**: 極端に短い要約の再生成
- **JSON形式エラー**: 形式不正レスポンスの再処理
- **参考文献なし**: 「次に読むべき論文」項目の代替処理

## 品質保証

### 自動検証項目
- 各項目の最小文字数チェック
- JSON形式の妥当性検証
- 日本語文字エンコーディング確認

### 手動確認推奨項目
- 専門用語の翻訳正確性
- 学術的表現の適切性
- 論文内容との整合性

## 使用例

### 統合ワークフローでの使用（推奨）
```bash
# デフォルト実行（落合フォーマット含む）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 落合フォーマット無効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-ochiai-format
```

### 個別実行（デバッグ用）
```bash
# 単独実行
PYTHONPATH=code/py uv run python code/py/main.py ochiai-format
``` 