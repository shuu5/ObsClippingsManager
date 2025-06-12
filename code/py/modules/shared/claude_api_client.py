"""
Claude API 統合クライアント - 共有モジュール

Claude 3.5 Haiku を使用した AI 機能の統合クライアント。
ObsClippingsManager v3.1 の共有モジュールとして設計。
"""

import json
import os
import re
import time
from typing import List, Dict, Any, Optional

# オプショナルなanthropic インポート（テスト環境対応）
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

from .config_manager import ConfigManager
from .logger import IntegratedLogger
from .exceptions import ObsClippingsError


class ClaudeAPIClient:
    """Claude API統合クライアント（共有モジュール）"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        Claude APIクライアントの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ管理オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('ClaudeAPIClient')
        
        # API設定の取得（仕様書v3.1に従いclaude-3-5-haikuをデフォルト）
        self.model = config_manager.get_config_value("ai_generation.tagger.model", "claude-3-5-haiku-20241022")
        # 環境変数ANTHROPIC_API_KEYを優先し、なければ設定ファイルから取得
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or config_manager.get_config_value("ai_generation.claude_api_key", "test-api-key")
        self.timeout = config_manager.get_config_value("api_settings.timeout", 30)
        self.max_retries = config_manager.get_config_value("api_settings.max_retries", 3)
        
        # AI機能設定の取得
        self.tagger_config = config_manager.get_config_value("ai_generation.tagger", {})
        self.translate_config = config_manager.get_config_value("ai_generation.translate_abstract", {})
        self.ochiai_config = config_manager.get_config_value("ai_generation.ochiai_format", {})
        
        # Claude クライアント初期化
        try:
            if not ANTHROPIC_AVAILABLE:
                self.logger.warning("Anthropic library not available. AI features will not work in production.")
                self.client = None
            else:
                self.client = anthropic.Anthropic(api_key=self.api_key)
            self.logger.info("Claude API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude API client: {e}")
            raise ObsClippingsError(f"Claude API initialization failed: {e}")
    
    async def generate_tags_batch(self, papers_content: List[str]) -> List[List[str]]:
        """
        複数論文のバッチタグ生成
        
        Args:
            papers_content: 論文内容のリスト
            
        Returns:
            各論文に対する生成タグリストのリスト
        """
        try:
            results = []
            batch_size = self.tagger_config.get("batch_size", 5)
            
            for i in range(0, len(papers_content), batch_size):
                batch = papers_content[i:i + batch_size]
                batch_results = []
                
                for paper_content in batch:
                    tags = self.generate_tags_single(paper_content)
                    batch_results.append(tags)
                    
                    # API レート制限対応
                    if i + 1 < len(batch):
                        time.sleep(1.0)
                
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch tag generation failed: {e}")
            raise ObsClippingsError(f"Batch tag generation failed: {e}")
    
    async def translate_abstracts_batch(self, abstracts: List[str]) -> List[str]:
        """
        複数抄録のバッチ翻訳
        
        Args:
            abstracts: 英語抄録のリスト
            
        Returns:
            日本語翻訳のリスト
        """
        try:
            results = []
            batch_size = self.translate_config.get("batch_size", 3)
            
            for i in range(0, len(abstracts), batch_size):
                batch = abstracts[i:i + batch_size]
                batch_results = []
                
                for abstract in batch:
                    translation = self.translate_abstract_single(abstract)
                    batch_results.append(translation)
                    
                    # API レート制限対応
                    if i + 1 < len(batch):
                        time.sleep(1.0)
                
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch abstract translation failed: {e}")
            raise ObsClippingsError(f"Batch abstract translation failed: {e}")
    
    def generate_tags_single(self, paper_content: str) -> List[str]:
        """
        単一論文のタグ生成
        
        Args:
            paper_content: 論文内容
            
        Returns:
            生成されたタグのリスト
        """
        try:
            self.logger.info("Generating tags for paper content")
            
            # プロンプト作成
            prompt = self._create_tagging_prompt(paper_content)
            
            # Claude API 呼び出し
            response = self._call_claude_api(prompt)
            
            # レスポンス解析
            tags = self._parse_tags_response(response)
            
            # タグ検証・正規化
            validated_tags = self.validate_tags(tags)
            
            self.logger.info(f"Generated {len(validated_tags)} tags")
            return validated_tags
            
        except Exception as e:
            self.logger.error(f"Tag generation failed: {e}")
            raise ObsClippingsError(f"Tag generation failed: {e}")
    
    def translate_abstract_single(self, abstract_content: str) -> str:
        """
        単一抄録の翻訳
        
        Args:
            abstract_content: 英語の抄録内容
            
        Returns:
            日本語翻訳
        """
        try:
            self.logger.info("Translating abstract content")
            
            # プロンプト作成
            prompt = self._create_translation_prompt(abstract_content)
            
            # Claude API 呼び出し
            response = self._call_claude_api(prompt)
            
            # レスポンス解析
            translation = self._parse_translation_response(response)
            
            self.logger.info("Abstract translation completed")
            return translation
            
        except Exception as e:
            self.logger.error(f"Abstract translation failed: {e}")
            raise ObsClippingsError(f"Abstract translation failed: {e}")
    
    def handle_api_errors(self, error: Exception) -> Dict[str, Any]:
        """
        API エラーの適切なハンドリング
        
        Args:
            error: 発生したエラー
            
        Returns:
            エラー情報辞書
        """
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': time.time(),
            'recoverable': False
        }
        
        # エラー種別に応じた分類
        if 'rate limit' in str(error).lower():
            error_info['error_category'] = 'rate_limit'
            error_info['recoverable'] = True
            error_info['retry_after'] = 60  # 60秒後にリトライ
        elif 'timeout' in str(error).lower():
            error_info['error_category'] = 'timeout'
            error_info['recoverable'] = True
            error_info['retry_after'] = 30
        elif 'api key' in str(error).lower():
            error_info['error_category'] = 'authentication'
            error_info['recoverable'] = False
        else:
            error_info['error_category'] = 'unknown'
            error_info['recoverable'] = False
        
        self.logger.error(f"API error handled: {error_info}")
        return error_info
    
    def validate_tags(self, tags: List[str]) -> List[str]:
        """
        タグの検証・正規化
        
        Args:
            tags: 生成されたタグリスト
            
        Returns:
            検証・正規化されたタグリスト
        """
        validated_tags = []
        
        for tag in tags:
            if not tag or not isinstance(tag, str):
                continue
            
            # タグの正規化
            normalized_tag = self._normalize_tag(tag)
            
            if normalized_tag and normalized_tag not in validated_tags:
                validated_tags.append(normalized_tag)
        
        return validated_tags
    
    def _normalize_tag(self, tag: str) -> str:
        """
        単一タグの正規化
        
        Args:
            tag: 正規化するタグ
            
        Returns:
            正規化されたタグ
        """
        # 不要な文字の除去
        tag = re.sub(r'[^a-zA-Z0-9_]', '', tag)
        
        # 遺伝子名は大文字のまま維持（元のタグが大文字で始まる場合のみ）
        if re.match(r'^[A-Z][A-Z0-9]{1,9}$', tag) and len(tag) <= 10:
            return tag.upper()
        
        # キャメルケースをスネークケースに変換して小文字化
        tag = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', tag).lower()
        
        return tag
    
    def _create_tagging_prompt(self, paper_content: str) -> str:
        """
        タグ生成用プロンプトの作成
        
        Args:
            paper_content: 論文内容
            
        Returns:
            プロンプト文字列
        """
        tag_count_range = self.tagger_config.get("tag_count_range", [10, 20])
        
        prompt = f"""以下の学術論文の内容を分析し、{tag_count_range[0]}-{tag_count_range[1]}個のタグを生成してください。

ルール:
- 英語でのタグ生成
- スネークケース形式（例: machine_learning）
- 遺伝子名はgene symbol（例: KRT13, EGFR）
- 論文理解に重要なキーワードを抽出
- 研究分野、技術、疾患、遺伝子などを含む

論文内容:
{paper_content[:4000]}  # 内容を制限

生成されたタグ（JSON配列形式で返答）:"""

        return prompt
    
    def _create_translation_prompt(self, abstract_content: str) -> str:
        """
        翻訳用プロンプトの作成
        
        Args:
            abstract_content: 英語抄録内容
            
        Returns:
            プロンプト文字列
        """
        prompt = f"""以下の英語抄録を学術的で自然な日本語に翻訳してください。

要求:
- 学術論文として適切な日本語表現
- 専門用語の正確な翻訳
- 読みやすい自然な日本語
- 元の意味を忠実に保持

英語抄録:
{abstract_content}

日本語翻訳:"""

        return prompt
    
    def _call_claude_api(self, prompt: str) -> str:
        """
        Claude API への呼び出し
        
        Args:
            prompt: API に送信するプロンプト
            
        Returns:
            API からのレスポンス
        """
        if not ANTHROPIC_AVAILABLE:
            # テスト環境での模擬レスポンス
            if "タグ" in prompt:
                return '["machine_learning", "neural_networks", "deep_learning"]'
            else:
                return "これは模擬翻訳です。"
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            self.logger.error(f"Claude API call failed: {e}")
            raise ObsClippingsError(f"Claude API call failed: {e}")
    
    def _parse_tags_response(self, response: str) -> List[str]:
        """
        タグ生成レスポンスの解析
        
        Args:
            response: Claude API からのレスポンス
            
        Returns:
            パースされたタグリスト
        """
        try:
            # JSON配列の抽出を試行
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                tags_json = json_match.group(0)
                tags = json.loads(tags_json)
                return [tag.strip() for tag in tags if tag.strip()]
            
            # JSON形式でない場合の代替解析
            lines = response.split('\n')
            tags = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('生成') and not line.startswith('ルール'):
                    # リスト形式の解析
                    if line.startswith('-') or line.startswith('*'):
                        tag = line[1:].strip()
                        tags.append(tag)
            
            return tags
            
        except Exception as e:
            self.logger.error(f"Failed to parse tags response: {e}")
            return []
    
    def _parse_translation_response(self, response: str) -> str:
        """
        翻訳レスポンスの解析
        
        Args:
            response: Claude API からのレスポンス
            
        Returns:
            抽出された翻訳テキスト
        """
        # 翻訳部分のみを抽出（プロンプト部分を除去）
        lines = response.split('\n')
        translation_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('日本語翻訳:') and not line.startswith('要求:'):
                translation_lines.append(line)
        
        return '\n'.join(translation_lines).strip() 