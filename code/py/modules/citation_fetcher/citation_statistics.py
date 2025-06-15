"""
Citation Statistics Module

引用文献取得統計情報の管理とレポート生成
"""

from typing import Dict, List, Any


class CitationStatistics:
    """
    引用文献取得統計情報管理
    
    API使用状況、成功率、品質スコアなどの統計情報を記録・管理
    """
    
    def __init__(self):
        """CitationStatistics初期化"""
        self.api_requests = {}
        self.success_counts = {}
        self.failure_counts = {}
        self.quality_scores = {}
        self.error_messages = {}
    
    def record_success(self, api_name: str, quality_score: float):
        """
        成功記録
        
        Args:
            api_name (str): API名（crossref, semantic_scholar, opencitations）
            quality_score (float): データ品質スコア
        """
        self.api_requests[api_name] = self.api_requests.get(api_name, 0) + 1
        self.success_counts[api_name] = self.success_counts.get(api_name, 0) + 1
        
        if api_name not in self.quality_scores:
            self.quality_scores[api_name] = []
        self.quality_scores[api_name].append(quality_score)
    
    def record_failure(self, api_name: str, error_message: str):
        """
        失敗記録
        
        Args:
            api_name (str): API名
            error_message (str): エラーメッセージ
        """
        self.api_requests[api_name] = self.api_requests.get(api_name, 0) + 1
        self.failure_counts[api_name] = self.failure_counts.get(api_name, 0) + 1
        
        if api_name not in self.error_messages:
            self.error_messages[api_name] = []
        self.error_messages[api_name].append(error_message)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        統計サマリー取得
        
        Returns:
            Dict[str, Any]: 統計情報サマリー
        """
        summary = {}
        
        for api_name in self.api_requests:
            requests = self.api_requests[api_name]
            successes = self.success_counts.get(api_name, 0)
            failures = self.failure_counts.get(api_name, 0)
            
            summary[f"{api_name}_requests"] = requests
            summary[f"{api_name}_successes"] = successes
            summary[f"{api_name}_failures"] = failures
            summary[f"{api_name}_success_rate"] = successes / requests if requests > 0 else 0.0
            
            if api_name in self.quality_scores and self.quality_scores[api_name]:
                scores = self.quality_scores[api_name]
                summary[f"{api_name}_avg_quality"] = sum(scores) / len(scores)
                summary[f"{api_name}_min_quality"] = min(scores)
                summary[f"{api_name}_max_quality"] = max(scores)
        
        # 全体統計
        total_requests = sum(self.api_requests.values())
        total_successes = sum(self.success_counts.values())
        total_failures = sum(self.failure_counts.values())
        
        summary['total_requests'] = total_requests
        summary['total_successes'] = total_successes
        summary['total_failures'] = total_failures
        summary['overall_success_rate'] = total_successes / total_requests if total_requests > 0 else 0.0
        
        return summary
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        詳細レポート取得
        
        Returns:
            Dict[str, Any]: 詳細統計情報
        """
        report = {
            'summary': self.get_summary(),
            'api_details': {},
            'error_analysis': {}
        }
        
        # API別詳細
        for api_name in self.api_requests:
            report['api_details'][api_name] = {
                'requests': self.api_requests[api_name],
                'successes': self.success_counts.get(api_name, 0),
                'failures': self.failure_counts.get(api_name, 0),
                'quality_scores': self.quality_scores.get(api_name, []),
                'recent_errors': self.error_messages.get(api_name, [])[-5:]  # 最新5件
            }
        
        # エラー分析
        for api_name, errors in self.error_messages.items():
            # エラータイプ別集計（簡易）
            error_types = {}
            for error in errors:
                error_type = self._categorize_error(error)
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            report['error_analysis'][api_name] = error_types
        
        return report
    
    def reset_statistics(self):
        """統計情報をリセット"""
        self.api_requests.clear()
        self.success_counts.clear()
        self.failure_counts.clear()
        self.quality_scores.clear()
        self.error_messages.clear()
    
    def _categorize_error(self, error_message: str) -> str:
        """
        エラーメッセージの分類
        
        Args:
            error_message (str): エラーメッセージ
            
        Returns:
            str: エラータイプ
        """
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'timed out' in error_lower:
            return 'timeout'
        elif 'rate limit' in error_lower or 'too many requests' in error_lower:
            return 'rate_limit'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'not_found'
        elif 'unauthorized' in error_lower or '401' in error_lower:
            return 'unauthorized'
        elif 'forbidden' in error_lower or '403' in error_lower:
            return 'forbidden'
        elif 'server error' in error_lower or '500' in error_lower:
            return 'server_error'
        elif 'network' in error_lower or 'connection' in error_lower:
            return 'network_error'
        else:
            return 'other' 