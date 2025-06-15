"""
Rate Limiter Module

API呼び出しのレート制限管理とトラフィック制御
"""

import time
from typing import Dict


class RateLimiter:
    """
    レート制限管理
    
    API別のレート制限を管理し、適切な待機時間を制御
    """
    
    def __init__(self, config_manager, logger):
        """
        RateLimiter初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログシステムインスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('RateLimiter')
        
        # 最終リクエスト時刻を記録
        self.last_request_times: Dict[str, float] = {}
        
        self.logger.debug("RateLimiter initialized")
    
    def wait_if_needed(self, api_name: str, requests_per_second: int):
        """
        レート制限に基づく待機制御
        
        Args:
            api_name (str): API名（crossref, semantic_scholar, opencitations）
            requests_per_second (int): 1秒間の最大リクエスト数
        """
        try:
            current_time = time.time()
            min_interval = 1.0 / requests_per_second
            
            if api_name in self.last_request_times:
                elapsed = current_time - self.last_request_times[api_name]
                
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {api_name}")
                    time.sleep(wait_time)
            
            # 現在時刻を記録
            self.last_request_times[api_name] = time.time()
            
        except Exception as e:
            self.logger.warning(f"Error in rate limiting for {api_name}: {e}")
            # エラーが発生しても処理を止めない（保守的に1秒待機）
            time.sleep(1.0)
    
    def get_wait_time(self, api_name: str, requests_per_second: int) -> float:
        """
        必要な待機時間を計算（実際には待機しない）
        
        Args:
            api_name (str): API名
            requests_per_second (int): 1秒間の最大リクエスト数
            
        Returns:
            float: 必要な待機時間（秒）
        """
        try:
            current_time = time.time()
            min_interval = 1.0 / requests_per_second
            
            if api_name in self.last_request_times:
                elapsed = current_time - self.last_request_times[api_name]
                
                if elapsed < min_interval:
                    return min_interval - elapsed
            
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating wait time for {api_name}: {e}")
            return 1.0  # 保守的に1秒の待機時間を返す
    
    def reset_api_timer(self, api_name: str):
        """
        特定APIのタイマーをリセット
        
        Args:
            api_name (str): API名
        """
        if api_name in self.last_request_times:
            del self.last_request_times[api_name]
            self.logger.debug(f"Reset timer for {api_name}")
    
    def reset_all_timers(self):
        """全APIのタイマーをリセット"""
        self.last_request_times.clear()
        self.logger.debug("Reset all API timers")
    
    def get_last_request_time(self, api_name: str) -> float:
        """
        最終リクエスト時刻を取得
        
        Args:
            api_name (str): API名
            
        Returns:
            float: 最終リクエスト時刻（UNIX時刻、未記録の場合は0.0）
        """
        return self.last_request_times.get(api_name, 0.0)
    
    def get_status_summary(self) -> Dict[str, float]:
        """
        レート制限状況のサマリーを取得
        
        Returns:
            Dict[str, float]: API名とその最終リクエスト時刻のマッピング
        """
        current_time = time.time()
        summary = {}
        
        for api_name, last_time in self.last_request_times.items():
            time_since_last = current_time - last_time
            summary[api_name] = {
                'last_request_time': last_time,
                'seconds_since_last_request': time_since_last
            }
        
        return summary 