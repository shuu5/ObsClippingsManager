#!/usr/bin/env python3
"""
メタデータ補完機能
複数の無料APIを使って、不完全なCrossRefメタデータを補完する
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import time

from .pubmed_client import PubMedClient, PubMedMetadata
from .semantic_scholar_client import SemanticScholarClient, SemanticScholarMetadata
from .openalex_client import OpenAlexClient, OpenAlexMetadata
from .crossref_client import CrossRefClient  # 既存
from .opencitations_client import OpenCitationsClient  # 追加
# from .opencitations_client import OpenCitationsClient  # 未実装

from ..shared.logger import get_integrated_logger
from ..shared.config_manager import ConfigManager


class DataSourceType(Enum):
    """データソースの種類"""
    CROSSREF = "crossref"
    PUBMED = "pubmed"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    OPENCITATIONS = "opencitations"


@dataclass
class EnrichmentResult:
    """メタデータ補完の結果"""
    doi: str
    source_data: Dict[str, Dict] = field(default_factory=dict)
    merged_metadata: Dict = field(default_factory=dict)
    primary_source: Optional[str] = None
    quality_score: float = 0.0
    errors: Dict[str, str] = field(default_factory=dict)
    processing_time: float = 0.0
    
    def add_source_data(self, source: str, data: Dict):
        """ソースデータを追加"""
        self.source_data[source] = data
    
    def add_error(self, source: str, error: str):
        """エラーを追加"""
        self.errors[source] = error
    
    def set_primary_source(self, source: str):
        """プライマリソースを設定"""
        self.primary_source = source
    
    def is_successful(self) -> bool:
        """補完が成功したかチェック"""
        return bool(self.merged_metadata and self.quality_score > 0.5)
    
    def get_complete_fields(self) -> List[str]:
        """完全に取得できたフィールドのリスト"""
        required_fields = ['title', 'author', 'journal', 'year']
        return [field for field in required_fields if self.merged_metadata.get(field)]


@dataclass
class EnrichmentStatistics:
    """メタデータ補完の統計情報"""
    total_processed: int = 0
    crossref_complete: int = 0
    enrichment_success: int = 0
    api_success_rates: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        'crossref': {'attempts': 0, 'successes': 0},
        'pubmed': {'attempts': 0, 'successes': 0},
        'semantic_scholar': {'attempts': 0, 'successes': 0},
        'openalex': {'attempts': 0, 'successes': 0},
        'opencitations': {'attempts': 0, 'successes': 0}
    })
    
    def record_attempt(self, source: str):
        """API試行を記録"""
        if source in self.api_success_rates:
            self.api_success_rates[source]['attempts'] += 1
    
    def record_success(self, source: str):
        """API成功を記録"""
        if source in self.api_success_rates:
            self.api_success_rates[source]['successes'] += 1
    
    def get_success_rate(self, source: str) -> float:
        """指定ソースの成功率を取得"""
        if source not in self.api_success_rates:
            return 0.0
        
        attempts = self.api_success_rates[source]['attempts']
        if attempts == 0:
            return 0.0
        
        successes = self.api_success_rates[source]['successes']
        return (successes / attempts) * 100
    
    def get_enrichment_improvement_rate(self) -> float:
        """メタデータ補完による改善率"""
        if self.total_processed == 0:
            return 0.0
        incomplete_count = self.total_processed - self.crossref_complete
        if incomplete_count == 0:
            return 100.0
        return (self.enrichment_success / incomplete_count) * 100


class MetadataEnricher:
    """メタデータ補完エンジン"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初期化
        
        Args:
            config_manager: 設定マネージャー
        """
        self.logger = get_integrated_logger().get_logger("CitationFetcher.MetadataEnricher")
        self.config = config_manager or ConfigManager()
        
        # APIクライアントの初期化
        self.clients = {}
        self._initialize_clients()
        
        # 設定の読み込み
        self.enabled = self.config.get_config_value(
            'citation_fetcher.enable_enrichment', 
            True
        )
        
        self.quality_threshold = self.config.get_config_value(
            'citation_fetcher.enrichment_quality_threshold', 
            0.8
        )
        
        self.max_fallback_attempts = self.config.get_config_value(
            'citation_fetcher.enrichment_max_attempts', 
            3
        )
        
        # API優先順位の設定（実データカバレッジ分析に基づく最適化）
        self.api_priorities = self.config.get_config_value(
            'citation_fetcher.api_priorities',
            {
                'life_sciences': ['crossref', 'opencitations', 'openalex', 'semantic_scholar', 'pubmed'],
                'computer_science': ['crossref', 'opencitations', 'openalex', 'semantic_scholar', 'pubmed'],
                'general': ['crossref', 'opencitations', 'openalex', 'semantic_scholar', 'pubmed']
            }
        )
        
        # 統計情報
        self.statistics = EnrichmentStatistics()
        
        self.logger.info("MetadataEnricher initialized successfully")
    
    def _initialize_clients(self):
        """APIクライアントを初期化"""
        try:
            # CrossRefClientは個別の引数を受け取る
            self.clients['crossref'] = CrossRefClient(
                base_url=self.config.get_config_value('citation_fetcher.crossref.base_url', 'https://api.crossref.org'),
                user_agent=self.config.get_config_value('citation_fetcher.user_agent', 'ObsClippingsManager/2.2'),
                request_delay=self.config.get_config_value('citation_fetcher.crossref.request_delay', 1.0),
                timeout=self.config.get_config_value('citation_fetcher.crossref.timeout', 30)
            )
            self.logger.info("CrossRef client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize CrossRef client: {e}")
        
        try:
            self.clients['pubmed'] = PubMedClient(self.config)
            self.logger.info("PubMed client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize PubMed client: {e}")
        
        try:
            self.clients['semantic_scholar'] = SemanticScholarClient(self.config)
            self.logger.info("Semantic Scholar client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Semantic Scholar client: {e}")
        
        try:
            self.clients['openalex'] = OpenAlexClient(self.config)
            self.logger.info("OpenAlex client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAlex client: {e}")
        
        try:
            self.clients['opencitations'] = OpenCitationsClient(self.config)
            self.logger.info("OpenCitations client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenCitations client: {e}")
    
    def _is_complete_metadata(self, metadata: Dict) -> bool:
        """メタデータが完全かチェック"""
        required_fields = ['title', 'author', 'journal', 'year']
        return all(
            field in metadata and metadata[field] and str(metadata[field]).strip()
            for field in required_fields
        )
    
    def _get_api_priority(self, field_type: str = 'general') -> List[str]:
        """分野に応じたAPI優先順位を取得"""
        return self.api_priorities.get(field_type, self.api_priorities['general'])
    
    def _normalize_metadata(self, raw_metadata: Any, source: str) -> Dict:
        """各ソースのメタデータを共通形式に正規化"""
        if not raw_metadata:
            return {}
        
        normalized = {}
        
        if source == 'pubmed' and isinstance(raw_metadata, PubMedMetadata):
            normalized = raw_metadata.to_dict()
        elif source == 'semantic_scholar' and isinstance(raw_metadata, SemanticScholarMetadata):
            normalized = raw_metadata.to_dict()
        elif source == 'openalex' and isinstance(raw_metadata, OpenAlexMetadata):
            normalized = raw_metadata.to_dict()
        elif isinstance(raw_metadata, dict):
            normalized = raw_metadata
        else:
            self.logger.warning(f"Unknown metadata type from {source}: {type(raw_metadata)}")
            return {}
        
        # 共通フィールドへの正規化
        result = {}
        
        # タイトル
        if normalized.get('title'):
            result['title'] = normalized['title']
        
        # 著者（筆頭著者のみをauthorフィールドに統一）
        if normalized.get('authors'):
            if isinstance(normalized['authors'], list) and normalized['authors']:
                # リストの場合は筆頭著者（最初の要素）のみを取得
                result['author'] = str(normalized['authors'][0])
            else:
                result['author'] = str(normalized['authors'])
        elif normalized.get('author'):
            # 既にauthorフィールドがある場合はそのまま使用
            result['author'] = str(normalized['author'])
        
        # ジャーナル
        if normalized.get('journal'):
            result['journal'] = normalized['journal']
        elif normalized.get('venue'):  # Semantic Scholar
            result['journal'] = normalized['venue']
        
        # 年
        if normalized.get('year'):
            result['year'] = str(normalized['year'])
        
        # ボリューム・号・ページ
        if normalized.get('volume'):
            result['volume'] = str(normalized['volume'])
        if normalized.get('issue'):
            result['issue'] = str(normalized['issue'])
        if normalized.get('pages'):
            result['pages'] = str(normalized['pages'])
        
        # DOI
        if normalized.get('doi'):
            result['doi'] = normalized['doi']
        
        # 追加情報
        result['source'] = source
        
        return result
    
    def _merge_metadata(self, source_data: Dict[str, Dict]) -> Dict:
        """複数ソースのメタデータをマージ"""
        merged = {}
        
        # 分野判定（仮実装：PubMedが成功した場合は生命科学分野と判定）
        field_type = 'life_sciences' if 'pubmed' in source_data else 'general'
        
        # 優先順位に従ってフィールドを補完（実データ分析に基づく最適化）
        field_priorities = {
            'title': self._get_api_priority(field_type),
            'author': self._get_api_priority(field_type),
            'journal': self._get_api_priority(field_type),
            'year': self._get_api_priority(field_type),
            'volume': ['crossref', 'opencitations', 'openalex', 'semantic_scholar', 'pubmed'],
            'issue': ['crossref', 'opencitations', 'openalex', 'semantic_scholar', 'pubmed'],
            'pages': ['crossref', 'opencitations', 'openalex', 'semantic_scholar', 'pubmed'],
            'doi': ['crossref', 'opencitations', 'openalex', 'semantic_scholar', 'pubmed']
        }
        
        for field, priority_list in field_priorities.items():
            for source in priority_list:
                if source in source_data and field in source_data[source]:
                    value = source_data[source][field]
                    if value and str(value).strip():
                        merged[field] = value
                        merged[f'{field}_source'] = source
                        break
        
        return merged
    
    def _calculate_quality_score(self, metadata: Dict) -> float:
        """メタデータの品質スコアを計算"""
        if not metadata:
            return 0.0
        
        required_fields = ['title', 'author', 'journal', 'year']
        optional_fields = ['volume', 'issue', 'pages', 'doi']
        
        # 必須フィールドのスコア（80%）
        required_score = 0.0
        for field in required_fields:
            if metadata.get(field) and str(metadata[field]).strip():
                required_score += 0.8 / len(required_fields)
        
        # オプションフィールドのスコア（20%）
        optional_score = 0.0
        for field in optional_fields:
            if metadata.get(field) and str(metadata[field]).strip():
                optional_score += 0.2 / len(optional_fields)
        
        return required_score + optional_score
    
    def enrich_metadata(self, doi: str, field_type: str = 'general') -> EnrichmentResult:
        """
        DOIからメタデータを補完
        
        Args:
            doi: DOI文字列
            field_type: 分野タイプ（'life_sciences', 'computer_science', 'general'）
            
        Returns:
            EnrichmentResult: 補完結果
        """
        start_time = time.time()
        result = EnrichmentResult(doi=doi)
        
        if not self.enabled:
            self.logger.debug("Metadata enrichment is disabled")
            return result
        
        self.statistics.total_processed += 1
        
        # API優先順位を取得
        api_priority = self._get_api_priority(field_type)
        
        self.logger.info(f"Starting metadata enrichment for {doi} (field: {field_type})")
        
        # 各APIを優先順位に従って試行
        for source_name in api_priority:  # OpenCitationsは未実装のため除外
            if source_name not in self.clients:
                continue
            
            client = self.clients[source_name]
            
            # 利用可能性チェック
            if hasattr(client, 'is_available') and not client.is_available():
                self.logger.debug(f"{source_name} client is not available")
                continue
            
            self.statistics.record_attempt(source_name)
            
            try:
                self.logger.debug(f"Trying {source_name} API for {doi}")
                
                # メタデータ取得
                raw_metadata = None
                if hasattr(client, 'get_metadata_by_doi'):
                    raw_metadata = client.get_metadata_by_doi(doi)
                
                if raw_metadata:
                    # 正規化してソースデータに追加
                    normalized_metadata = self._normalize_metadata(raw_metadata, source_name)
                    if normalized_metadata:
                        result.add_source_data(source_name, normalized_metadata)
                        self.statistics.record_success(source_name)
                        
                        # 完全なメタデータが得られた場合は早期終了
                        if self._is_complete_metadata(normalized_metadata):
                            result.set_primary_source(source_name)
                            self.logger.info(f"Complete metadata found from {source_name}")
                            
                            # CrossRefが完全だった場合の統計
                            if source_name == 'crossref':
                                self.statistics.crossref_complete += 1
                            
                            break
                
            except Exception as e:
                error_msg = f"Error accessing {source_name}: {str(e)}"
                result.add_error(source_name, error_msg)
                self.logger.warning(error_msg)
                continue
        
        # 複数ソースの情報をマージ
        if result.source_data:
            result.merged_metadata = self._merge_metadata(result.source_data)
            result.quality_score = self._calculate_quality_score(result.merged_metadata)
            
            # 成功統計の更新
            if result.is_successful():
                self.statistics.enrichment_success += 1
        
        result.processing_time = time.time() - start_time
        
        self.logger.info(
            f"Enrichment completed for {doi}: "
            f"sources={len(result.source_data)}, "
            f"quality={result.quality_score:.2f}, "
            f"time={result.processing_time:.2f}s"
        )
        
        return result
    
    def get_statistics(self) -> EnrichmentStatistics:
        """統計情報を取得"""
        return self.statistics
    
    def get_available_clients(self) -> List[str]:
        """利用可能なクライアントのリストを取得"""
        available = []
        for name, client in self.clients.items():
            if hasattr(client, 'is_available'):
                if client.is_available():
                    available.append(name)
            else:
                available.append(name)  # 利用可能性チェックがない場合は利用可能と仮定
        return available
    
    def test_clients(self) -> Dict[str, Dict]:
        """全クライアントのテスト実行"""
        results = {}
        test_doi = "10.1038/nature12373"  # 有名な論文でテスト
        
        for name, client in self.clients.items():
            try:
                start_time = time.time()
                
                if hasattr(client, 'get_client_info'):
                    info = client.get_client_info()
                else:
                    info = {'name': name, 'available': 'unknown'}
                
                # 簡単なメタデータ取得テスト
                metadata = None
                if hasattr(client, 'get_metadata_by_doi'):
                    metadata = client.get_metadata_by_doi(test_doi)
                
                results[name] = {
                    'client_info': info,
                    'test_successful': metadata is not None,
                    'response_time': time.time() - start_time,
                    'metadata_sample': str(metadata)[:100] if metadata else None
                }
                
            except Exception as e:
                results[name] = {
                    'client_info': {'name': name, 'available': False},
                    'test_successful': False,
                    'error': str(e),
                    'response_time': 0
                }
        
        return results 