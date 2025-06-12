"""
Claude API クライアント

Claude 3.5 Sonnet を使用したタグ生成とAbstract翻訳機能を提供
"""

import json
import re
import time
from typing import List, Dict, Any, Optional
import anthropic

from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError


class ClaudeAPIClient:
    """Claude API統合クライアント"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        Claude APIクライアントの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ管理オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('ClaudeAPIClient')
        
        # API設定の取得
        self.model = config_manager.get_config_value("claude_api.model", "claude-3-5-sonnet-20241022")
        self.api_key = config_manager.get_config_value("claude_api.api_key", "test-api-key")
        self.timeout = config_manager.get_config_value("claude_api.timeout", 30)
        self.max_retries = config_manager.get_config_value("claude_api.max_retries", 3)
        
        # AI機能設定の取得
        self.tagger_config = config_manager.get_config_value("ai_generation.tagger", {})
        self.translate_config = config_manager.get_config_value("ai_generation.translate_abstract", {})
        
        # Claude クライアント初期化
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.logger.info("Claude API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude API client: {e}")
            raise ObsClippingsError(f"Claude API initialization failed: {e}")
    
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
        # キャメルケースをスネークケースに変換
        tag = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', tag).lower()
        
        # 不要な文字の除去
        tag = re.sub(r'[^a-zA-Z0-9_]', '', tag)
        
        # 遺伝子名は大文字のまま維持（一般的なパターン）
        if re.match(r'^[A-Z0-9]{2,10}$', tag.upper()) and len(tag) <= 10:
            return tag.upper()
        
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
        prompt = f"""以下の学術論文のabstractを自然で正確な日本語に翻訳してください。

要件:
- 学術論文として適切な日本語表現
- 専門用語の正確な翻訳
- 原文の情報量を保持
- 読みやすく理解しやすい文章

Original Abstract:
{abstract_content}

日本語翻訳:"""

        return prompt
    
    def _call_claude_api(self, prompt: str) -> str:
        """
        Claude API 呼び出し
        
        Args:
            prompt: 送信するプロンプト
            
        Returns:
            API レスポンス
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            self.logger.error(f"Claude API call failed: {e}")
            raise
    
    def _parse_tags_response(self, response: str) -> List[str]:
        """
        タグ生成レスポンスの解析
        
        Args:
            response: Claude APIレスポンス
            
        Returns:
            タグリスト
        """
        try:
            # JSON配列として解析を試行
            if '[' in response and ']' in response:
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                json_str = response[json_start:json_end]
                tags = json.loads(json_str)
                
                if isinstance(tags, list):
                    return [str(tag) for tag in tags]
            
            # JSON解析に失敗した場合の代替パース
            lines = response.split('\n')
            tags = []
            for line in lines:
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    tag = line.lstrip('- *').strip().strip('"\'')
                    if tag:
                        tags.append(tag)
            
            return tags
            
        except Exception as e:
            self.logger.warning(f"Failed to parse tags response: {e}")
            return []
    
    def _parse_translation_response(self, response: str) -> str:
        """
        翻訳レスポンスの解析
        
        Args:
            response: Claude APIレスポンス
            
        Returns:
            翻訳結果
        """
        # 翻訳結果のクリーンアップ
        translation = response.strip()
        
        # 不要なプレフィックスの除去
        prefixes_to_remove = ["日本語翻訳:", "翻訳:", "Japanese translation:", "Translation:"]
        for prefix in prefixes_to_remove:
            if translation.startswith(prefix):
                translation = translation[len(prefix):].strip()
        
        return translation 