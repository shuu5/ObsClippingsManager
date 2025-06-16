"""
AI Tagging & Translation Module

このモジュールは Claude 3.5 Haiku を活用した論文の自動タグ生成と要約翻訳機能を提供します。

Classes:
    TaggerWorkflow: 論文タグ生成専用ワークフロー
    ClaudeAPIClient: Claude API通信クライアント
"""

from .tagger_workflow import TaggerWorkflow
from .claude_api_client import ClaudeAPIClient

__all__ = [
    'TaggerWorkflow', 
    'ClaudeAPIClient'
] 