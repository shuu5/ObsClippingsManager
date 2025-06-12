# メタデータ補完機能仕様書 v2.0

## 概要
メタデータ補完機能は、ObsClippingsManager v2.0のcitation_fetcherモジュール内の機能として、CrossRefで不完全なメタデータしか取得できない引用文献に対して、複数の無料APIを使って包括的な書誌情報を補完する機能です。

## 背景・課題
lennartzM2023APMIS論文で発見された問題：
- 67個の引用文献のうち60個が`@misc`タイプ（DOIとnoteのみ）
- CrossRefAPIから不完全なメタデータしか取得できない
- 他の論文と比較して明らかに情報が欠損している

## モジュール構造

```
modules/citation_fetcher/
├── metadata_enricher.py         # メタデータ補完メインクラス
├── pubmed_client.py            # PubMed API クライアント
├── semantic_scholar_client.py  # Semantic Scholar API クライアント
├── openalex_client.py          # OpenAlex API クライアント
├── crossref_client.py          # CrossRef API クライアント（既存）
├── opencitations_client.py     # OpenCitations API クライアント（既存）
├── fallback_strategy.py        # 拡張フォールバック戦略
└── reference_formatter.py      # BibTeX変換（拡張）
```

## 設計方針

### 無料APIのみ使用
- **PubMed API**: 生命科学・医学分野に強い
- **Semantic Scholar API**: 計算機科学分野に強い、無料
- **OpenAlex API**: 包括的な学術データベース、完全無料
- **OpenCitations API**: 引用関係に特化

### フォールバック戦略
```
CrossRef (メイン)
    ↓ (不完全な場合)
Semantic Scholar API
    ↓ (失敗時)
OpenAlex API
    ↓ (失敗時)
PubMed API
    ↓ (失敗時)
OpenCitations API (既存)
```

### メタデータ品質判定
完全なメタデータとして以下の必須フィールドを定義：
- title（タイトル）
- author（著者）
- journal（ジャーナル名）
- year（発行年）

## 機能要件

### 主要機能
1. **メタデータ完全性チェック**: CrossRefデータの完全性を判定
2. **多重API補完**: 不完全な場合に複数APIで順次補完
3. **メタデータマージ**: 複数ソースの情報を統合
4. **品質スコアリング**: 補完されたメタデータの品質評価
5. **フォールバック統計**: 各APIの成功率追跡

### 性能要件
- **処理速度**: 1DOIあたり平均3秒以内（複数API使用時）
- **成功率**: 90%以上のメタデータ補完成功率
- **API制限遵守**: 各APIのレート制限を遵守
- **エラー耐性**: 一時的なAPI障害に対する復旧機能

## 詳細機能仕様

### 1. PubMed APIクライアント (`pubmed_client.py`)

#### 主要機能
- **DOI→PMID変換**: DOIからPubMed IDを取得
- **メタデータ取得**: PMIDから詳細な書誌情報を取得
- **著者名正規化**: PubMedの標準化された著者名を使用
- **ジャーナル名標準化**: NLM Title Abbreviationを使用

#### API仕様
- **ライブラリ**: metapub（eutils wrapper）
- **制限**: 3リクエスト/秒（API key未使用時）
- **対象分野**: 生命科学・医学・バイオエンジニアリング
- **レスポンス**: PubMedArticleオブジェクト

#### 実装例
```python
from metapub import PubMedFetcher

class PubMedClient:
    def __init__(self):
        self.fetcher = PubMedFetcher()
    
    def get_metadata_by_doi(self, doi: str) -> Optional[Dict]:
        try:
            article = self.fetcher.article_by_doi(doi)
            if article:
                return {
                    'title': article.title,
                    'authors': article.authors,
                    'journal': article.journal,
                    'year': article.year,
                    'volume': article.volume,
                    'issue': article.issue,
                    'pages': article.pages,
                    'pmid': article.pmid
                }
        except Exception as e:
            self.logger.warning(f"PubMed API error for {doi}: {e}")
        return None
```

### 2. Semantic Scholar APIクライアント (`semantic_scholar_client.py`)

#### 主要機能
- **DOI検索**: DOIから論文情報を取得
- **著者情報**: 著者のORCID、affiliation情報
- **影響力指標**: 被引用数、影響力スコア
- **分野情報**: 研究分野の自動分類

#### API仕様
- **エンドポイント**: `https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}`
- **制限**: 100リクエスト/5分（登録不要）
- **対象分野**: 計算機科学、AI、工学系
- **レスポンス**: JSON形式

#### 実装例
```python
import requests
import time

class SemanticScholarClient:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper"
        self.rate_limit_delay = 1.0  # 1秒間隔
    
    def get_metadata_by_doi(self, doi: str) -> Optional[Dict]:
        url = f"{self.base_url}/DOI:{doi}"
        params = {
            'fields': 'title,authors,journal,year,venue,citationCount'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self._normalize_metadata(data)
        except Exception as e:
            self.logger.warning(f"Semantic Scholar API error for {doi}: {e}")
        
        time.sleep(self.rate_limit_delay)
        return None
```

### 3. OpenAlex APIクライアント (`openalex_client.py`)

#### 主要機能
- **包括的検索**: 全分野の学術論文を対象
- **機関情報**: 著者の所属機関情報
- **オープンアクセス情報**: OA status、リポジトリ情報
- **概念分類**: 研究トピックの自動分類

#### API仕様
- **エンドポイント**: `https://api.openalex.org/works/https://doi.org/{doi}`
- **制限**: なし（完全無料）
- **対象分野**: 全学術分野
- **レスポンス**: JSON形式

#### 実装例
```python
import requests

class OpenAlexClient:
    def __init__(self):
        self.base_url = "https://api.openalex.org/works"
    
    def get_metadata_by_doi(self, doi: str) -> Optional[Dict]:
        url = f"{self.base_url}/https://doi.org/{doi}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self._normalize_metadata(data)
        except Exception as e:
            self.logger.warning(f"OpenAlex API error for {doi}: {e}")
        return None
```

### 4. メタデータ統合・補完機能 (`metadata_enricher.py`)

#### 主要機能
- **完全性判定**: メタデータが完全かどうかの判定
- **フォールバック制御**: API呼び出しの順序制御
- **データマージ**: 複数ソースからの情報統合
- **品質評価**: 補完されたメタデータの品質スコア

#### 核心アルゴリズム
```python
class MetadataEnricher:
    def __init__(self):
        self.clients = [
            ('crossref', CrossRefClient()),
            ('pubmed', PubMedClient()),
            ('semantic_scholar', SemanticScholarClient()),
            ('openalex', OpenAlexClient()),
            ('opencitations', OpenCitationsClient())
        ]
    
    def enrich_metadata(self, doi: str) -> EnrichmentResult:
        """DOIからメタデータを補完"""
        result = EnrichmentResult(doi=doi)
        
        for source_name, client in self.clients:
            try:
                metadata = client.get_metadata_by_doi(doi)
                if metadata:
                    result.add_source_data(source_name, metadata)
                    
                    # 完全なメタデータが得られた場合は早期終了
                    if self._is_complete_metadata(metadata):
                        result.set_primary_source(source_name)
                        break
                        
            except Exception as e:
                result.add_error(source_name, str(e))
                continue
        
        # 複数ソースの情報をマージ
        result.merged_metadata = self._merge_metadata(result.source_data)
        result.quality_score = self._calculate_quality_score(result.merged_metadata)
        
        return result
    
    def _is_complete_metadata(self, metadata: Dict) -> bool:
        """メタデータが完全かチェック"""
        required_fields = ['title', 'authors', 'journal', 'year']
        return all(
            field in metadata and metadata[field] 
            for field in required_fields
        )
    
    def _merge_metadata(self, source_data: Dict[str, Dict]) -> Dict:
        """複数ソースのメタデータをマージ"""
        merged = {}
        
        # 優先順位に従ってフィールドを補完
        field_priorities = {
            'title': ['crossref', 'semantic_scholar', 'openalex', 'pubmed'],
            'authors': ['crossref', 'semantic_scholar', 'openalex', 'pubmed'],
            'journal': ['crossref', 'semantic_scholar', 'openalex', 'pubmed'],
            'year': ['crossref', 'semantic_scholar', 'openalex', 'pubmed']
        }
        
        for field, priority_list in field_priorities.items():
            for source in priority_list:
                if source in source_data and field in source_data[source]:
                    merged[field] = source_data[source][field]
                    break
        
        return merged
```

### 5. 拡張フォールバック戦略 (`fallback_strategy.py` - 拡張)

#### 新機能
- **メタデータ品質チェック**: CrossRefデータの完全性判定
- **条件付きフォールバック**: 不完全な場合のみ追加API呼び出し
- **統計追跡**: 各APIの成功率、補完率の追跡
- **適応的制御**: 分野に応じたAPI優先順位の調整

#### 統計情報
```python
class EnrichmentStatistics:
    def __init__(self):
        self.total_processed = 0
        self.crossref_complete = 0
        self.enrichment_success = 0
        self.api_success_rates = {
            'crossref': {'attempts': 0, 'successes': 0},
            'pubmed': {'attempts': 0, 'successes': 0},
            'semantic_scholar': {'attempts': 0, 'successes': 0},
            'openalex': {'attempts': 0, 'successes': 0},
            'opencitations': {'attempts': 0, 'successes': 0}
        }
    
    def get_enrichment_improvement_rate(self) -> float:
        """メタデータ補完による改善率"""
        if self.total_processed == 0:
            return 0.0
        incomplete_count = self.total_processed - self.crossref_complete
        if incomplete_count == 0:
            return 100.0
        return (self.enrichment_success / incomplete_count) * 100
```

## 期待される効果

### lennartzM2023APMIS論文での期待値
- **現状**: 6/67個の完全エントリ（8.9%）
- **目標**: 50-60個の完全エントリ（75-90%）
- **改善率**: 650-900%の改善

### 全体的な効果
- **メタデータ品質向上**: 不完全なエントリの大幅削減
- **研究効率向上**: 正確な書誌情報による論文検索・引用の効率化
- **データ整合性**: 他の論文との品質格差解消

## 実装順序

### Phase 1: PubMed API統合（優先度：高）
- metapubライブラリの統合
- PubMedClientの実装
- 既存フォールバック戦略への統合

### Phase 2: Semantic Scholar API統合（優先度：中）
- SemanticScholarClientの実装
- フォールバック順序の調整
- 分野別優先順位の実装

### Phase 3: OpenAlex API統合（優先度：中）
- OpenAlexClientの実装
- 包括的フォールバック戦略の完成
- 統計追跡機能の強化

### Phase 4: 品質向上機能（優先度：低）
- メタデータ品質スコアリング
- 著者名・ジャーナル名の正規化強化
- 分野別適応制御

## テスト戦略

### 単体テスト
- 各APIクライアントの独立テスト
- メタデータマージ機能のテスト
- エラーハンドリングのテスト

### 統合テスト
- フォールバック戦略の統合テスト
- lennartzM2023APMIS実データでのテスト
- 他の論文での回帰テスト

### 性能テスト
- 大量DOIでの処理速度測定
- API制限遵守の確認
- メモリ使用量の監視

## 設定項目

### config.json統合設定
```json
{
  "citation_fetcher": {
    "enable_enrichment": true,
    "enrichment_field_type": "general",
    "enrichment_quality_threshold": 0.8,
    "enrichment_max_attempts": 3,
    "api_priorities": {
      "life_sciences": ["crossref", "semantic_scholar", "openalex", "pubmed", "opencitations"],
      "computer_science": ["crossref", "semantic_scholar", "openalex", "pubmed", "opencitations"],
      "general": ["crossref", "semantic_scholar", "openalex", "pubmed", "opencitations"]
    },
    "rate_limits": {
      "pubmed": 1.0,
      "semantic_scholar": 1.0,
      "openalex": 0.1,
      "opencitations": 0.5
    }
  }
}
```

## ログ出力例

```
2024-01-15 10:30:45 INFO Starting metadata enrichment for lennartzM2023APMIS
2024-01-15 10:30:45 INFO Found 60 incomplete references in CrossRef data
2024-01-15 10:30:46 INFO [ref_0] PubMed enrichment successful: 10.1007/s12038-019-9864-8
2024-01-15 10:30:47 WARN [ref_1] PubMed failed, trying Semantic Scholar: 10.1016/j.ceb.2014.12.008
2024-01-15 10:30:48 INFO [ref_1] Semantic Scholar enrichment successful
2024-01-15 10:31:20 INFO Enrichment completed: 54/60 references enriched (90% success rate)
2024-01-15 10:31:20 INFO API usage: PubMed 45/60, Semantic Scholar 9/15, OpenAlex 0/6
``` 