"""
Claude API Client

Claude 3.5 Haiku との統合通信を行うクライアントクラス
"""

import os
import time
import json
from typing import List, Optional, Any
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None

from ..shared_modules.exceptions import APIError
from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger

# .envファイル読み込み（python-dotenvが利用可能な場合）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenvが利用できない場合は手動で.envを読み込み
    env_file = Path(__file__).parents[4] / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    os.environ[key] = value


class ClaudeAPIClient:
    """
    Claude API通信クライアント
    
    Claude 3.5 Haikuとの統合通信、バッチ処理、レート制限制御を提供します。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        ClaudeAPIClient初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('ClaudeAPIClient')
        
        # 設定から値を取得
        self.model = config_manager.get_ai_setting('default_model', default='claude-3-5-haiku-20241022')
        api_key_env = config_manager.get_ai_setting('api_key_env', default='ANTHROPIC_API_KEY')
        self.api_key = os.getenv(api_key_env)
        
        # API設定
        self.timeout = config_manager.get_api_setting('timeout', default=30)
        self.max_retries = config_manager.get_api_setting('max_retries', default=3)
        self.request_delay = config_manager.get_api_setting('request_delay', default=0.5)
        
        # クライアント初期化（遅延初期化）
        self._client = None
        self._last_request_time = 0
        
        # API Key検証
        if not self.api_key:
            raise APIError(
                message=f"API key not found in environment variable: {api_key_env}",
                error_code="MISSING_API_KEY"
            )
        
        self.logger.info(f"ClaudeAPIClient initialized with model: {self.model}")
    
    @property
    def client(self):
        """Anthropicクライアントの遅延初期化"""
        if self._client is None:
            if anthropic is None:
                raise APIError(
                    message="anthropic package is not installed. Please install it with: pip install anthropic",
                    error_code="MISSING_DEPENDENCY"
                )
            
            self._client = anthropic.Anthropic(
                api_key=self.api_key,
                timeout=self.timeout
            )
        
        return self._client
    
    def send_request(self, prompt: str, max_retries: Optional[int] = None) -> str:
        """
        Claude APIにリクエストを送信
        
        Args:
            prompt: 送信するプロンプト
            max_retries: 最大リトライ回数（Noneの場合は設定値を使用）
            
        Returns:
            str: APIレスポンス
            
        Raises:
            APIError: API通信エラーが発生した場合
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        self.logger.debug(f"Sending request to Claude API (max_retries: {max_retries})")
        
        for attempt in range(max_retries + 1):
            try:
                # レート制限適用
                self._apply_rate_limit()
                
                # APIリクエスト実行
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                # レスポンス解析
                response_text = response.content[0].text
                self.logger.debug(f"Received response from Claude API (length: {len(response_text)})")
                return response_text
                
            except Exception as e:
                self.logger.warning(f"API request failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                if attempt == max_retries:
                    # 最後の試行でも失敗した場合
                    raise APIError(
                        message=f"Claude API request failed after {max_retries + 1} attempts: {e}",
                        error_code="API_REQUEST_FAILED",
                        context={"prompt_length": len(prompt), "attempts": attempt + 1}
                    ) from e
                
                # 指数バックオフ
                wait_time = 2 ** attempt
                self.logger.debug(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
    
    def send_batch_requests(self, prompts: List[str]) -> List[str]:
        """
        複数のプロンプトをバッチ処理で送信
        
        Args:
            prompts: 送信するプロンプトのリスト
            
        Returns:
            List[str]: APIレスポンスのリスト
            
        Raises:
            APIError: API通信エラーが発生した場合
        """
        self.logger.info(f"Starting batch request processing for {len(prompts)} prompts")
        
        responses = []
        for i, prompt in enumerate(prompts):
            try:
                self.logger.debug(f"Processing prompt {i + 1}/{len(prompts)}")
                response = self.send_request(prompt)
                responses.append(response)
                
                # 最後のリクエスト以外ではレート制限待機
                if i < len(prompts) - 1:
                    time.sleep(self.request_delay)
                    
            except APIError as e:
                self.logger.error(f"Failed to process prompt {i + 1}: {e}")
                responses.append("")  # エラー時は空文字列
        
        self.logger.info(f"Batch processing completed. Success rate: {len([r for r in responses if r])}/{len(prompts)}")
        return responses
    
    def _apply_rate_limit(self):
        """
        レート制限を適用
        
        リクエスト間隔が設定値を下回る場合は待機します。
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.request_delay:
            wait_time = self.request_delay - time_since_last_request
            self.logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        self._last_request_time = time.time() 