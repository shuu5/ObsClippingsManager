# AI理解支援引用文献パーサー機能仕様書 v4.0

## 概要
YAMLヘッダーに完全な引用文献情報を統合し、AIが直接Markdownファイルを読むだけで引用文献を完全理解できる自己完結型システム。

## 主要機能

### 完全統合引用マッピング機能
- YAMLヘッダーに全ての引用文献情報を完全統合
- references.bibから一度読み込み、Markdownファイルに永続化
- 外部ファイル依存を排除した自己完結型設計
- AIが直接Markdownファイルを読むだけで完全理解可能

## 機能詳細仕様

### YAMLヘッダー完全統合形式
```yaml
---
title: "論文タイトル"
doi: "10.1093/jrr/rrac091"
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

citation_metadata:
  total_citations: 2
  last_updated: "2024-01-15T10:30:00"
  source_bibtex: "references.bib"
  mapping_version: "2.0"
---
```

### 実装クラス
```python
class CompleteCitationManager:
    """完全統合引用管理エンジン"""
    
    def create_complete_mapping(self, markdown_file: str, references_bib: str) -> CompleteCitationMapping:
        """references.bibから完全な引用情報を読み込みYAMLヘッダーに統合"""
        
    def update_yaml_header_complete(self, markdown_file: str, mapping: CompleteCitationMapping) -> bool:
        """YAMLヘッダーに完全な引用情報を追加・更新"""
        
    def extract_citation_from_yaml(self, markdown_file: str, citation_number: int) -> CitationInfo:
        """YAMLヘッダーから特定の引用情報を取得"""
        
    def validate_self_contained_file(self, markdown_file: str) -> bool:
        """ファイルが自己完結型かどうかを検証"""
```

## コマンドライン仕様

### 基本コマンド

#### 完全統合マッピング作成
```bash
PYTHONPATH=code/py uv run python code/py/main.py create-complete-mapping \
    --input paper.md \
    --references references.bib
```

#### 自己完結性検証
```bash
PYTHONPATH=code/py uv run python code/py/main.py validate-self-contained \
    --input paper.md
```

#### 統合処理
```bash
PYTHONPATH=code/py uv run python code/py/main.py parse-citations \
    --input paper.md \
    --references references.bib
```

### 統合ワークフロー組み込み
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --enable-self-contained-citations
```

## 設定仕様

```yaml
# config/self_contained_citation_parser.yaml
self_contained_citation_parser:
  complete_mapping:
    auto_create: true
    update_yaml_header: true
    backup_original: true
    include_abstracts: true
    
  self_contained:
    strict_validation: true
    allow_partial_info: false
    require_abstracts: true
```

## データ構造

### CompleteCitationMapping
```python
@dataclass
class CompleteCitationMapping:
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

## テスト仕様

### 完全マッピング作成テスト
```python
def test_complete_mapping_creation():
    mapping = manager.create_complete_mapping("test_paper.md", "test_references.bib")
    assert mapping.total_citations == 3
    assert mapping.is_self_contained == True
    assert 1 in mapping.citations
    assert mapping.citations[1].title == "Novel Method for Cancer Analysis"
```

### 自己完結性検証テスト
```python
def test_self_contained_validation():
    assert manager.validate_self_contained_file("complete_file.md") == True
    assert manager.validate_self_contained_file("incomplete_file.md") == False
```

### AI理解度テスト
```python
def test_ai_understanding():
    manager.create_complete_mapping("test_paper.md", "references.bib")
    with open("test_paper.md", 'r') as f:
        content = f.read()
    assert "citations:" in content
    assert "title: \"Novel Method for Cancer Analysis\"" in content
    assert "abstract:" in content
```

## 実装ロードマップ

### Phase 1: 完全統合マッピング機能（2週間）
1. CompleteCitationManagerクラス実装
2. YAMLヘッダー完全統合機能
3. references.bib読み込み・変換機能

### Phase 2: 統合・最適化（1週間）
1. 既存ワークフローへの統合
2. 包括的テスト実行

### Phase 3: リリース準備（1週間）
1. ドキュメント更新
2. 設定システム整備
3. 最終検証

## 使用例

```bash
# 初回セットアップ
PYTHONPATH=code/py uv run python code/py/main.py create-complete-mapping \
    --input "paper.md" \
    --references "references.bib"

# 以降はMarkdownファイルを直接AIに提供
# → AIが引用文献を完全理解
```