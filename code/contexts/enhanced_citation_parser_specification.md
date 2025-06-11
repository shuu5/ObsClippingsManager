# AI理解支援引用文献パーサー機能仕様書 v4.0

## 概要
ObsClippingsManager v4.0における引用文献パース機能の革新的強化版です。**AIアシスタント（ChatGPT、Claude等）が引用文献を完全に理解し、適切な引用付き論文を執筆できるよう支援する**ことを主目的とします。

**YAMLヘッダー完全統合方式**により、ファイル単体で全ての引用情報を管理し、外部依存を排除した自己完結型のシステムを実現します。

## 背景と解決すべき課題

### 現在の問題
```
ユーザー → AI：「この論文のIntroductionをまとめて」

AI：「[1],[2],[3]という引用がありますが、これが何の文献なのか分からないため、
     適切な引用付きの文章を作成できません」
```

### 目標：AIが完全理解できる統合ファイル生成
```
ObsClippingsManager処理後:

## 📚 Citation Reference Table
[1] → Smith, J. et al. (2023). "Novel Method for Cancer Analysis". Cancer Research, 83(12), 1234-1245.
[2] → Jones, M. & Wilson, K. (2022). "Advanced Biomarker Techniques". Nature Medicine, 28, 567-578.
[3] → Brown, A. (2021). "Differential Diagnosis in Oncology". Cell, 185, 890-905.

## 📄 Paper Content
Aberrant expression in various cancers makes KRTs useful as biomarkers [1],[2],[3].

AI：「[1]はSmith et al.のがん解析手法の論文、[2]はJonesのバイオマーカー技術論文、
     [3]はBrownの診断学論文ですね。これらを踏まえて適切な論文を執筆します」
```

## 主要機能

### 1. 完全統合引用マッピング機能
- YAMLヘッダーに全ての引用文献情報を完全統合
- references.bibから一度読み込み、Markdownファイルに永続化
- 外部ファイル依存を排除した自己完結型設計

### 2. AI用統合ファイル生成機能（核心機能）
- YAMLヘッダーの情報のみを使用してAI理解用ファイル生成
- Citation Reference Table + Paper Content形式
- 高速で信頼性の高い処理

## 機能詳細仕様

### 1. 完全統合引用マッピング機能

#### YAMLヘッダー完全統合形式
```yaml
---
title: "論文タイトル"
doi: "10.1093/jrr/rrac091"
# 完全統合引用マッピング
citations:
  1:
    citation_key: "smith2023test"
    title: "Novel Method for Cancer Cell Analysis"
    authors: "Smith, J., Wilson, K., & Davis, M."
    year: 2023
    journal: "Cancer Research"
    volume: "83"
    number: "12"
    pages: "1234-1245"
    doi: "10.1158/0008-5472.CAN-23-0123"
    abstract: "This paper introduces innovative methodologies for analyzing cancer cell behavior using advanced computational techniques."
    
  2:
    citation_key: "jones2022biomarkers"
    title: "Advanced Biomarker Techniques in Oncology"
    authors: "Jones, M. & Brown, A."
    year: 2022
    journal: "Nature Medicine"
    volume: "28"
    pages: "567-578"
    doi: "10.1038/s41591-022-0456-7"
    abstract: "Comprehensive review of current biomarker applications in cancer diagnosis and treatment monitoring."
    
  3:
    citation_key: "brown2021diagnosis"
    title: "Differential Diagnosis Methods in Modern Oncology"
    authors: "Brown, A., Lee, S., & Kumar, R."
    year: 2021
    journal: "Cell"
    volume: "185"
    pages: "890-905"
    doi: "10.1016/j.cell.2021.03.012"
    abstract: "Systematic approach to differential diagnosis using molecular markers and advanced imaging techniques."

# メタデータ
citation_metadata:
  total_citations: 3
  last_updated: "2024-01-15T10:30:00"
  source_bibtex: "references.bib"
  mapping_version: "2.0"
---
```

#### 実装クラス
```python
class CompleteCitationManager:
    """完全統合引用管理エンジン"""
    
    def create_complete_mapping(self, markdown_file: str, references_bib: str) -> CompleteCitationMapping:
        """
        references.bibから完全な引用情報を読み込みYAMLヘッダーに統合
        
        Process:
        1. Markdownファイル内の引用番号を検出
        2. references.bibから全ての文献情報を取得
        3. 引用番号順に完全な文献情報をマッピング
        4. YAMLヘッダーに完全な情報を埋め込み
        
        Returns:
            CompleteCitationMapping: 完全な引用マッピング情報
        """
        
    def update_yaml_header_complete(self, markdown_file: str, mapping: CompleteCitationMapping) -> bool:
        """
        YAMLヘッダーに完全な引用情報を追加・更新
        
        Args:
            markdown_file: 対象Markdownファイル
            mapping: 完全な引用マッピング情報
            
        Returns:
            成功フラグ
        """
        
    def extract_citation_from_yaml(self, markdown_file: str, citation_number: int) -> CitationInfo:
        """
        YAMLヘッダーから特定の引用情報を取得
        
        Args:
            markdown_file: 対象Markdownファイル
            citation_number: 引用番号
            
        Returns:
            CitationInfo: 完全な引用文献情報
        """
```

### 2. AI用統合ファイル生成機能（核心機能）

#### 生成される統合ファイル形式
```markdown
# 論文タイトル
*Generated by ObsClippingsManager v4.0 for AI Assistant*
*Self-contained document with embedded citation information*

## 📚 Citation Reference Table
**AI Assistant Reference Guide: This table provides complete citation information for all numbered references in the paper.**

[1] → **Smith, J., Wilson, K., & Davis, M.** (2023). *Novel Method for Cancer Cell Analysis*. **Cancer Research**, 83(12), 1234-1245. DOI: 10.1158/0008-5472.CAN-23-0123
    └─ **Abstract**: This paper introduces innovative methodologies for analyzing cancer cell behavior using advanced computational techniques.

[2] → **Jones, M. & Brown, A.** (2022). *Advanced Biomarker Techniques in Oncology*. **Nature Medicine**, 28, 567-578. DOI: 10.1038/s41591-022-0456-7
    └─ **Abstract**: Comprehensive review of current biomarker applications in cancer diagnosis and treatment monitoring.

[3] → **Brown, A., Lee, S., & Kumar, R.** (2021). *Differential Diagnosis Methods in Modern Oncology*. **Cell**, 185, 890-905. DOI: 10.1016/j.cell.2021.03.012
    └─ **Abstract**: Systematic approach to differential diagnosis using molecular markers and advanced imaging techniques.

---

## 📄 Paper Content

### Introduction
Aberrant expression in various cancers makes KRTs useful as biomarkers for differential diagnoses and metastatic status. Recent studies suggest that KRTs in cancer cells are not only epithelial marker proteins but are also mediators capable of interacting with a range of proteins to regulate signaling networks associated with cell death, survival, proliferation, migration, invasion and metastasis [1],[2],[3].

The established framework [2] provides a foundation for understanding biomarker applications, while novel analytical methods [1] offer new insights into cancer cell behavior. Previous comprehensive studies [3] have demonstrated the importance of systematic diagnostic approaches.

---
*End of AI Assistant Document*
*Original file: paper.md | Generated: 2024-01-15 10:30:00*
*Citation source: Self-contained YAML header*
```

#### 実装クラス
```python
class SelfContainedAIGenerator:
    """自己完結型AI統合ファイル生成器"""
    
    def generate_ai_readable_file(self, markdown_file: str, output_file: str = None) -> str:
        """
        YAMLヘッダーの情報のみを使用してAI理解用ファイルを生成
        
        Args:
            markdown_file: 元のMarkdownファイル（YAMLヘッダーに完全な引用情報を含む）
            output_file: 出力ファイル名（未指定時は自動生成）
            
        Returns:
            生成されたファイルパス
            
        Process:
        1. YAMLヘッダーから完全な引用情報を読み込み
        2. Citation Reference Tableを生成
        3. 元のPaper Contentと統合
        4. AI理解最適化フォーマットで出力
        
        Note: 外部ファイル依存なし、高速処理
        """
        
    def create_citation_reference_table(self, citations: Dict[int, CitationInfo]) -> str:
        """
        YAMLヘッダーの情報からAI理解用Citation Reference Tableを生成
        
        Format:
        [番号] → **著者** (年). *タイトル*. **ジャーナル**, 巻(号), ページ. DOI: xxx
            └─ **Abstract**: 論文の要約
        """
        
    def validate_self_contained_file(self, markdown_file: str) -> bool:
        """
        ファイルが自己完結型かどうかを検証
        
        Returns:
            True: 全ての引用情報がYAMLヘッダーに含まれている
            False: 外部依存または情報不足
        """
```

## コマンドライン仕様

### 基本コマンド

#### 1. 完全統合マッピング作成
```bash
# references.bibから完全な引用情報をYAMLヘッダーに統合
PYTHONPATH=code/py uv run python code/py/main.py create-complete-mapping \
    --input paper.md \
    --references references.bib
```

#### 2. AI用統合ファイル生成（核心機能）
```bash
# YAMLヘッダーの情報のみを使用してAI理解用ファイルを生成
PYTHONPATH=code/py uv run python code/py/main.py generate-ai-format \
    --input paper.md \
    --output paper_for_ai.md
```

#### 3. 自己完結性検証
```bash
# ファイルが外部依存なしで完全かどうかを検証
PYTHONPATH=code/py uv run python code/py/main.py validate-self-contained \
    --input paper.md
```

#### 4. 統合処理
```bash
# 完全マッピング作成 + AI形式生成を一括実行
PYTHONPATH=code/py uv run python code/py/main.py parse-citations \
    --input paper.md \
    --references references.bib \
    --generate-ai-format \
    --output-dir ./ai_ready/
```

### 統合ワークフローへの組み込み
```bash
# run-integratedに自動組み込み
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --enable-self-contained-citations
```

## 設定仕様

### 設定ファイル
```yaml
# config/self_contained_citation_parser.yaml
self_contained_citation_parser:
  # 完全統合設定
  complete_mapping:
    auto_create: true                    # 自動完全マッピング作成
    update_yaml_header: true             # YAMLヘッダー自動更新
    backup_original: true                # 元ファイルバックアップ
    include_abstracts: true              # 要約情報を含める
    
  # AI統合ファイル生成設定
  ai_format:
    enable_generation: true              # AI形式生成有効化
    include_abstracts: true              # 要約情報含める
    reference_table_style: "enhanced"    # enhanced | simple
    output_suffix: "_for_ai"             # 出力ファイル接尾辞
    
  # 自己完結性設定
  self_contained:
    strict_validation: true              # 厳密な自己完結性検証
    allow_partial_info: false            # 部分的な情報を許可しない
    require_abstracts: true              # 要約情報を必須とする
```

## データ構造

### CompleteCitationMapping
```python
@dataclass
class CompleteCitationMapping:
    """完全統合引用マッピング情報"""
    citations: Dict[int, CitationInfo]   # 引用番号 → 完全な文献情報
    total_citations: int                 # 総引用数
    last_updated: datetime               # 最終更新時刻
    source_bibtex: str                   # 元のBibTeXファイル
    mapping_version: str                 # マッピングバージョン
    is_self_contained: bool              # 自己完結フラグ
```

### CitationInfo
```python
@dataclass  
class CitationInfo:
    """完全な引用文献情報"""
    citation_key: str                    # BibTeX citation_key
    title: str                           # 論文タイトル
    authors: str                         # 著者情報
    year: int                            # 発行年
    journal: str                         # ジャーナル名
    volume: str                          # 巻号情報
    number: str                          # 号数情報
    pages: str                           # ページ情報
    doi: str                             # DOI
    abstract: str                        # 論文要約
    url: str                             # URL（オプション）
    keywords: List[str]                  # キーワード（オプション）
```

### SelfContainedDocument
```python
@dataclass
class SelfContainedDocument:
    """自己完結型統合文書"""
    original_file: str                   # 元ファイル
    citations: Dict[int, CitationInfo]   # 完全な引用情報
    citation_table: str                  # Citation Reference Table
    paper_content: str                   # 論文内容
    generation_timestamp: datetime      # 生成時刻
    total_citations: int                 # 総引用数
    is_self_contained: bool              # 自己完結フラグ
```

## テスト仕様

### 機能テスト

#### 1. 完全マッピング作成テスト
```python
def test_complete_mapping_creation():
    """完全統合マッピング作成のテスト"""
    markdown_file = "test_paper.md"
    references_bib = "test_references.bib"
    
    mapping = manager.create_complete_mapping(markdown_file, references_bib)
    
    assert mapping.total_citations == 3
    assert mapping.is_self_contained == True
    assert 1 in mapping.citations
    assert mapping.citations[1].title == "Novel Method for Cancer Analysis"
    assert mapping.citations[1].authors == "Smith, J., Wilson, K., & Davis, M."
    assert mapping.citations[1].abstract != ""
```

#### 2. 自己完結型AI統合ファイル生成テスト
```python
def test_self_contained_ai_file_generation():
    """自己完結型AI理解用ファイル生成のテスト"""
    input_file = "test_paper_with_complete_yaml.md"
    output_file = generator.generate_ai_readable_file(input_file)
    
    with open(output_file, 'r') as f:
        content = f.read()
    
    # Citation Reference Table存在確認
    assert "📚 Citation Reference Table" in content
    assert "[1] → **Smith, J." in content
    assert "**Abstract**:" in content
    
    # Paper Content存在確認  
    assert "📄 Paper Content" in content
    assert "Self-contained document" in content
```

#### 3. 自己完結性検証テスト
```python
def test_self_contained_validation():
    """自己完結性検証のテスト"""
    complete_file = "test_complete.md"
    incomplete_file = "test_incomplete.md"
    
    assert generator.validate_self_contained_file(complete_file) == True
    assert generator.validate_self_contained_file(incomplete_file) == False
```

### 統合テスト

#### 外部依存なし高速処理テスト
```python
def test_no_external_dependency():
    """外部ファイル依存なしで処理できることのテスト"""
    
    # references.bibを削除
    os.remove("references.bib")
    
    # YAMLヘッダーのみでAI用ファイル生成
    ai_file = generator.generate_ai_readable_file("complete_paper.md")
    
    # 成功することを確認
    assert os.path.exists(ai_file)
    
    # 処理時間が高速であることを確認
    start_time = time.time()
    generator.generate_ai_readable_file("complete_paper.md")
    processing_time = time.time() - start_time
    
    assert processing_time < 0.01  # 10ms以内
```

## 実装ロードマップ

### Phase 1: 完全統合マッピング機能（2週間）
1. CompleteCitationManagerクラス実装
2. YAMLヘッダー完全統合機能
3. references.bib読み込み・変換機能
4. 基本テスト作成・実行

### Phase 2: 自己完結型AI統合ファイル生成機能（2週間）
1. SelfContainedAIGeneratorクラス実装
2. YAMLヘッダーのみからのCitation Reference Table生成
3. 高速処理最適化
4. 自己完結性検証機能

### Phase 3: 統合・最適化（1週間）
1. 既存ワークフローへの統合
2. パフォーマンス最適化
3. 包括的テスト実行

### Phase 4: リリース準備（1週間）
1. ドキュメント更新
2. 設定システム整備
3. 最終検証

## 期待される効果

### 自己完結性による利点
- **外部依存排除**: references.bibがなくても完全動作
- **高速処理**: ファイルI/O削減により大幅な処理時間短縮
- **データ整合性**: 全情報がYAMLヘッダーに統合され、整合性保証
- **ポータビリティ**: ファイル単体で完結、移動・共有が容易

### AIアシスタント利用の革命的改善
- **完全な引用理解**: AIが[1],[2],[3]の意味を完全把握
- **適切な論文生成**: 引用情報を理解した高品質な論文作成
- **作業効率向上**: 準備不要でAIに論文執筆依頼が可能

### ワークフロー改善
- **シンプルなコマンド**: 1つのコマンドでAI用ファイル生成
- **統合実行**: run-integratedに自動組み込み
- **メンテナンス不要**: 外部ファイル同期の問題解消

## 使用例

### 基本的な使用フロー

```bash
# 1. 初回セットアップ：references.bibから完全な引用情報をYAMLヘッダーに統合
PYTHONPATH=code/py uv run python code/py/main.py create-complete-mapping \
    --input "pancreatic_cancer_analysis.md" \
    --references "references.bib"

# 2. 以降は外部ファイル不要：AI用ファイル生成
PYTHONPATH=code/py uv run python code/py/main.py generate-ai-format \
    --input "pancreatic_cancer_analysis.md" \
    --output "pancreatic_cancer_for_ai.md"

# 3. 生成されたファイルをAIアシスタントに提供
# → AIが引用文献を完全理解
# → 高品質な論文執筆・要約・分析が可能
```

### 出力例比較

#### Before（従来）
```
# AIに提供するファイル
Recent studies suggest that KRTs are mediators [1],[2],[3].

# AIの反応
AI: 「[1],[2],[3]が何の文献か分からないため、適切な引用付き文章を作成できません」
```

#### After（v4.0自己完結型）
```
# AIに提供するファイル（自動生成、外部依存なし）
## 📚 Citation Reference Table
[1] → Smith, J. et al. (2023). "Novel Method for Cancer Analysis". Cancer Research, 83(12), 1234-1245.
    └─ **Abstract**: This paper introduces innovative methodologies for analyzing cancer cell behavior...

[2] → Jones, M. & Wilson, K. (2022). "Advanced Biomarker Techniques". Nature Medicine, 28, 567-578.
    └─ **Abstract**: Comprehensive review of current biomarker applications in cancer diagnosis...

## 📄 Paper Content
Recent studies suggest that KRTs are mediators [1],[2],[3].

# AIの反応
AI: 「Smith et al.の癌細胞解析手法[1]、Jonesのバイオマーカー技術[2]、Brownの診断手法[3]を踏まえて、
     適切な引用付きの論文を執筆いたします」
```

---

**v4.0の革新ポイント：完全自己完結型でAIが引用文献を瞬時に理解、外部依存ゼロの高速処理を実現**