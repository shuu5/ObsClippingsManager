# AI理解支援引用文献パーサー機能仕様書 v3.0

## 概要
references.bibの内容をそのまま順序通りにYAMLヘッダーに統合し、AIが直接Markdownファイルを読むだけで引用文献を理解できるシンプルな自己完結型システム。

## 主要機能

### シンプル引用マッピング機能
- references.bibの全エントリーを順序通りにYAMLヘッダーに統合
- 重複エントリーも含めて全て処理
- プレースホルダー生成なし
- total_citationsはBibTeXエントリー数と一致

## 機能詳細仕様

### YAMLヘッダー統合形式
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
    pages: '1234-1245'
    title: Novel Method for Cancer Cell Analysis
    volume: '83'
    year: 2023
  2:
    authors: Jones
    citation_key: jones2022biomarkers
    doi: 10.1038/s41591-022-0456-7
    journal: Nature Medicine
    pages: '567-578'
    title: Advanced Biomarker Techniques in Oncology
    volume: '28'
    year: 2022
last_updated: '2025-01-15T10:30:00.654321+00:00'
processing_status:
  ai-citation-support: completed
  fetch: completed
  organize: completed
  sync: completed
workflow_version: '3.0'
---
```

### 実装クラス
```python
class CitationMappingEngine:
    """シンプル引用マッピングエンジン"""
    
    def create_citation_mapping(self, markdown_file: str, references_bib: str = None) -> CitationMapping:
        """references.bibから引用情報を順序通り読み込みマッピング作成"""
        
    def update_yaml_header(self, markdown_file: str, mapping: CitationMapping) -> bool:
        """YAMLヘッダーのcitationsフィールドに引用情報を追加・更新"""
```

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

## コマンドライン仕様

### 基本コマンド

#### AI理解支援機能有効化（統合ワークフロー）
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --enable-ai-citation-support
```

#### 個別実行（デバッグ用）
```bash
PYTHONPATH=code/py uv run python code/py/main.py parse-citations \
    --input paper.md \
    --references references.bib
```

## データ構造

### CitationMapping
```python
@dataclass
class CitationMapping:
    index_map: Dict[int, CitationInfo]   # 引用番号 → 文献情報
    total_citations: int                 # 総引用数（BibTeXエントリー数）
    last_updated: str                    # 最終更新時刻
    references_file: str                 # 元のBibTeXファイルパス
    mapping_version: str                 # マッピングバージョン
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
    pages: str                           # ページ情報
    doi: str                             # DOI
    url: str                             # URL（オプション）
```

## テスト仕様

### マッピング作成テスト
```python
def test_simple_mapping_creation():
    mapping = engine.create_citation_mapping("test_paper.md", "test_references.bib")
    assert mapping.total_citations == len(bib_entries)
    assert len(mapping.index_map) == mapping.total_citations
    assert 1 in mapping.index_map
```

### 重複処理テスト
```python
def test_duplicate_handling():
    # 重複を含むBibTeXファイルでも全エントリーを処理
    mapping = engine.create_citation_mapping("test_paper.md", "duplicates.bib")
    assert mapping.total_citations == total_bib_entries  # 重複含む
```

## 使用例

```bash
# AI理解支援機能を有効化した統合ワークフロー実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --enable-ai-citation-support

# 結果: YAMLヘッダーのcitationsフィールドに
#       references.bibの全エントリーが順序通り統合
```