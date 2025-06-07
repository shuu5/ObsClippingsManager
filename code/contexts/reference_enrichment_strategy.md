# 引用文献メタデータ補完戦略

## 問題の概要

lennartzM2023APMISのreferences.bibで発見された問題：
- 67個の引用文献のうち、60個が`@misc`タイプでDOIとnoteのみ
- 6個のみが`@article`タイプで完全な書誌情報
- CrossRefAPIから不完全なメタデータしか取得できない場合の対処法が必要

## 原因分析

### CrossRefでメタデータが不完全な理由
1. **出版社の登録品質**：出版社がCrossRefに完全なメタデータを送信していない
2. **歴史的要因**：古い論文では当時の登録基準が現在と異なる
3. **選択的登録**：DOIマッチングが確認できた参考文献のみを提出する出版社の方針

## 代替データソース

### 1. PubMed API
```python
# metapubライブラリを使用
from metapub import PubMedFetcher

fetch = PubMedFetcher()
article = fetch.article_by_doi('10.1007/s12038-019-9864-8')
if article:
    print(f"Title: {article.title}")
    print(f"Authors: {article.authors}")
    print(f"Journal: {article.journal}")
    print(f"Year: {article.year}")
```

**利点**：
- 生命科学分野で高い網羅性
- 標準化された著者名とジャーナル名
- PMIDとの相互変換が可能

**制限**：
- 主に生命科学・医学分野
- 一部の工学・物理学系ジャーナルは未収録

### 2. Scopus API
```python
import requests

def get_scopus_metadata(doi):
    url = f"https://api.elsevier.com/content/search/scopus"
    params = {
        'query': f'DOI({doi})',
        'apikey': 'YOUR_API_KEY'
    }
    response = requests.get(url, params=params)
    return response.json()
```

**利点**：
- 幅広い分野をカバー
- 被引用数情報も取得可能
- 著者のaffiliation情報が豊富

**制限**：
- 有料API（制限あり）
- 1990年代以前の古い文献は限定的

### 3. Semantic Scholar API
```python
import requests

def get_semantic_scholar_metadata(doi):
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    params = {
        'fields': 'title,authors,journal,year,venue,citationCount'
    }
    response = requests.get(url, params=params)
    return response.json()
```

**利点**：
- 無料でアクセス可能
- Computer Scienceに強い
- 機械学習による著者名の正規化

**制限**：
- 比較的新しいサービス
- 一部分野での網羅性に課題

### 4. OpenAlex API
```python
import requests

def get_openalex_metadata(doi):
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    response = requests.get(url)
    return response.json()
```

**利点**：
- 完全に無料・オープン
- 包括的な学術データベース
- 機関・研究者のID統合

**制限**：
- 比較的新しいサービス
- データ品質にばらつき

## 実装戦略

### フォールバック方式
```python
def enrich_reference_metadata(doi):
    """複数のAPIを順番に試してメタデータを補完"""
    
    # 1. まずCrossRefを試行（既存の実装）
    crossref_data = get_crossref_metadata(doi)
    if is_complete_metadata(crossref_data):
        return crossref_data
    
    # 2. PubMedで補完を試行
    pubmed_data = get_pubmed_metadata(doi)
    if pubmed_data:
        return merge_metadata(crossref_data, pubmed_data)
    
    # 3. Semantic Scholarで補完を試行
    semantic_data = get_semantic_scholar_metadata(doi)
    if semantic_data:
        return merge_metadata(crossref_data, semantic_data)
    
    # 4. OpenAlexで補完を試行
    openalex_data = get_openalex_metadata(doi)
    if openalex_data:
        return merge_metadata(crossref_data, openalex_data)
    
    # 5. すべて失敗した場合はCrossRefの不完全データを返す
    return crossref_data

def is_complete_metadata(data):
    """メタデータが完全かチェック"""
    required_fields = ['title', 'author', 'journal', 'year']
    return all(field in data and data[field] for field in required_fields)

def merge_metadata(primary, secondary):
    """複数ソースのメタデータをマージ"""
    merged = primary.copy()
    
    # 不足している必須フィールドを補完
    if not merged.get('title') and secondary.get('title'):
        merged['title'] = secondary['title']
    
    if not merged.get('author') and secondary.get('author'):
        merged['author'] = secondary['author']
    
    if not merged.get('journal') and secondary.get('journal'):
        merged['journal'] = secondary['journal']
    
    if not merged.get('year') and secondary.get('year'):
        merged['year'] = secondary['year']
    
    # 追加情報の補完
    if secondary.get('volume'):
        merged['volume'] = secondary['volume']
    
    if secondary.get('pages'):
        merged['pages'] = secondary['pages']
    
    return merged
```

### 優先順位の設定

1. **生命科学・医学分野**：PubMed → Scopus → Semantic Scholar → OpenAlex
2. **Computer Science分野**：Semantic Scholar → Scopus → OpenAlex → PubMed  
3. **一般的な学術分野**：Scopus → OpenAlex → Semantic Scholar → PubMed

### バッチ処理の実装

```python
def batch_enrich_references(incomplete_refs, batch_size=10, delay=1):
    """不完全な引用文献を一括で補完"""
    enriched_refs = []
    
    for i in range(0, len(incomplete_refs), batch_size):
        batch = incomplete_refs[i:i+batch_size]
        
        for ref in batch:
            if ref.get('doi'):
                enriched = enrich_reference_metadata(ref['doi'])
                enriched_refs.append(enriched)
            else:
                enriched_refs.append(ref)  # DOIがない場合はそのまま
        
        # API制限を考慮した遅延
        time.sleep(delay)
    
    return enriched_refs
```

## 実装計画

### Phase 1: PubMed統合
- metapubライブラリの統合
- DOI→PMID変換機能
- PubMedメタデータ取得・変換機能

### Phase 2: 複数ソース対応
- Semantic Scholar API統合
- OpenAlex API統合
- フォールバック機能の実装

### Phase 3: 品質向上
- メタデータ品質スコアリング
- 著者名・ジャーナル名の正規化
- 重複除去・統合機能

## 期待される効果

lennartzM2023APMISの場合：
- 現在の6個の完全エントリ → 50-60個程度に改善見込み
- @miscエントリの大部分を@articleエントリに変換
- 他の論文との整合性向上

## 注意事項

1. **API制限**：各サービスのレート制限を遵守
2. **データ品質**：複数ソースの情報が矛盾する場合の処理
3. **ライセンス**：商用利用の際のAPI利用規約確認
4. **エラーハンドリング**：ネットワークエラーや一時的な障害への対応

## 参考リンク

- [metapub GitHub](https://github.com/metapub/metapub)
- [Semantic Scholar API](https://api.semanticscholar.org/)
- [OpenAlex API](https://docs.openalex.org/)
- [CrossRef community forum](https://community.crossref.org/) 