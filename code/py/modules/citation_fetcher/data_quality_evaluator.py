"""
Data Quality Evaluator Module

引用文献データの品質評価とスコア計算
"""

from typing import List, Dict, Any


class DataQualityEvaluator:
    """
    データ品質評価
    
    引用文献データの完全性、正確性、有用性を評価してスコアを算出
    """
    
    def __init__(self, config_manager, logger):
        """
        DataQualityEvaluator初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログシステムインスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('DataQualityEvaluator')
        
        # 評価重み設定（設定ファイルから取得可能）
        self.weights = {
            'required_fields': 0.4,    # 必須フィールド存在
            'optional_fields': 0.2,    # オプションフィールド存在
            'data_validity': 0.3,      # データ妥当性
            'metadata_richness': 0.1   # メタデータの豊富さ
        }
        
        # 必須フィールド
        self.required_fields = ['title', 'authors', 'year']
        
        # 優先フィールド（あると品質が向上）
        self.preferred_fields = ['doi', 'journal', 'volume', 'pages', 'publisher']
        
        self.logger.debug("DataQualityEvaluator initialized")
    
    def evaluate(self, citation_data: List[Dict[str, Any]]) -> float:
        """
        引用文献データの品質スコア計算
        
        Args:
            citation_data (List[Dict[str, Any]]): 引用文献データリスト
            
        Returns:
            float: 品質スコア（0.0-1.0）
        """
        try:
            if not citation_data:
                self.logger.debug("No citation data provided for evaluation")
                return 0.0
            
            total_score = 0.0
            
            for citation in citation_data:
                # 各引用文献の品質スコア計算
                citation_score = self._evaluate_single_citation(citation)
                total_score += citation_score
            
            # 平均品質スコア
            average_score = total_score / len(citation_data)
            
            self.logger.debug(f"Evaluated {len(citation_data)} citations, average quality: {average_score:.3f}")
            return average_score
            
        except Exception as e:
            self.logger.error(f"Error evaluating citation data quality: {e}")
            return 0.0
    
    def _evaluate_single_citation(self, citation: Dict[str, Any]) -> float:
        """
        単一引用文献の品質評価
        
        Args:
            citation (Dict[str, Any]): 単一引用文献データ
            
        Returns:
            float: 品質スコア（0.0-1.0）
        """
        try:
            scores = {}
            
            # 1. 必須フィールドスコア
            scores['required_fields'] = self._evaluate_required_fields(citation)
            
            # 2. オプションフィールドスコア
            scores['optional_fields'] = self._evaluate_optional_fields(citation)
            
            # 3. データ妥当性スコア
            scores['data_validity'] = self._evaluate_data_validity(citation)
            
            # 4. メタデータ豊富さスコア
            scores['metadata_richness'] = self._evaluate_metadata_richness(citation)
            
            # 重み付き合計スコア
            total_score = sum(scores[key] * self.weights[key] for key in scores)
            
            return min(1.0, max(0.0, total_score))  # 0.0-1.0の範囲にクランプ
            
        except Exception as e:
            self.logger.warning(f"Error evaluating single citation: {e}")
            return 0.0
    
    def _evaluate_required_fields(self, citation: Dict[str, Any]) -> float:
        """
        必須フィールドの存在評価
        
        Args:
            citation (Dict[str, Any]): 引用文献データ
            
        Returns:
            float: 必須フィールドスコア（0.0-1.0）
        """
        present_count = 0
        
        for field in self.required_fields:
            if field in citation and citation[field] and str(citation[field]).strip():
                present_count += 1
        
        return present_count / len(self.required_fields)
    
    def _evaluate_optional_fields(self, citation: Dict[str, Any]) -> float:
        """
        オプションフィールドの存在評価
        
        Args:
            citation (Dict[str, Any]): 引用文献データ
            
        Returns:
            float: オプションフィールドスコア（0.0-1.0）
        """
        present_count = 0
        
        for field in self.preferred_fields:
            if field in citation and citation[field] and str(citation[field]).strip():
                present_count += 1
        
        return present_count / len(self.preferred_fields)
    
    def _evaluate_data_validity(self, citation: Dict[str, Any]) -> float:
        """
        データ妥当性の評価
        
        Args:
            citation (Dict[str, Any]): 引用文献データ
            
        Returns:
            float: データ妥当性スコア（0.0-1.0）
        """
        validity_score = 0.0
        checks_count = 0
        
        # 年の妥当性チェック
        if 'year' in citation:
            checks_count += 1
            try:
                year = int(citation['year'])
                if 1800 <= year <= 2030:  # 合理的な年の範囲
                    validity_score += 1.0
            except (ValueError, TypeError):
                pass
        
        # DOIの妥当性チェック
        if 'doi' in citation and citation['doi']:
            checks_count += 1
            doi = str(citation['doi']).strip()
            if self._is_valid_doi_format(doi):
                validity_score += 1.0
        
        # タイトルの長さチェック
        if 'title' in citation and citation['title']:
            checks_count += 1
            title = str(citation['title']).strip()
            if 10 <= len(title) <= 500:  # 合理的なタイトル長
                validity_score += 1.0
        
        # 著者フィールドの妥当性チェック
        if 'authors' in citation and citation['authors']:
            checks_count += 1
            authors = str(citation['authors']).strip()
            if len(authors) >= 3 and (',' in authors or ' ' in authors):  # 著者らしい形式
                validity_score += 1.0
        
        return validity_score / checks_count if checks_count > 0 else 0.0
    
    def _evaluate_metadata_richness(self, citation: Dict[str, Any]) -> float:
        """
        メタデータの豊富さ評価
        
        Args:
            citation (Dict[str, Any]): 引用文献データ
            
        Returns:
            float: メタデータ豊富さスコア（0.0-1.0）
        """
        # 存在するフィールド数
        valid_fields = 0
        total_possible_fields = len(self.required_fields) + len(self.preferred_fields)
        
        all_fields = self.required_fields + self.preferred_fields
        
        for field in all_fields:
            if field in citation and citation[field] and str(citation[field]).strip():
                valid_fields += 1
        
        # 追加のリッチネス要素
        bonus_score = 0.0
        
        # URLやリンクがある
        if any(field in citation and citation[field] for field in ['url', 'link', 'pdf_url']):
            bonus_score += 0.1
        
        # 抄録がある
        if 'abstract' in citation and citation['abstract']:
            bonus_score += 0.1
        
        # キーワードがある
        if 'keywords' in citation and citation['keywords']:
            bonus_score += 0.05
        
        base_score = valid_fields / total_possible_fields
        return min(1.0, base_score + bonus_score)
    
    def _is_valid_doi_format(self, doi: str) -> bool:
        """
        DOI形式の基本検証
        
        Args:
            doi (str): 検証対象のDOI文字列
            
        Returns:
            bool: 有効なDOI形式かどうか
        """
        import re
        
        if not doi or not isinstance(doi, str):
            return False
        
        # DOIの基本パターン（10.で始まり、/を含む）
        doi_pattern = r'(?:https?://(?:dx\.)?doi\.org/|doi:)?10\.\d+/.+'
        
        return bool(re.match(doi_pattern, doi.strip(), re.IGNORECASE))
    
    def get_quality_breakdown(self, citation_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        品質評価の詳細な内訳を取得
        
        Args:
            citation_data (List[Dict[str, Any]]): 引用文献データリスト
            
        Returns:
            Dict[str, Any]: 詳細な品質評価結果
        """
        try:
            if not citation_data:
                return {'overall_score': 0.0, 'breakdown': {}}
            
            breakdown = {
                'overall_score': self.evaluate(citation_data),
                'total_citations': len(citation_data),
                'field_coverage': {},
                'validity_issues': [],
                'recommendations': []
            }
            
            # フィールドカバレッジ分析
            all_fields = self.required_fields + self.preferred_fields
            for field in all_fields:
                present_count = sum(1 for citation in citation_data 
                                  if field in citation and citation[field] and str(citation[field]).strip())
                coverage = present_count / len(citation_data)
                breakdown['field_coverage'][field] = {
                    'present': present_count,
                    'coverage_rate': coverage
                }
            
            # 改善提案
            for field, info in breakdown['field_coverage'].items():
                if info['coverage_rate'] < 0.5:
                    breakdown['recommendations'].append(f"Improve {field} field coverage (currently {info['coverage_rate']:.1%})")
            
            return breakdown
            
        except Exception as e:
            self.logger.error(f"Error generating quality breakdown: {e}")
            return {'overall_score': 0.0, 'breakdown': {}, 'error': str(e)} 