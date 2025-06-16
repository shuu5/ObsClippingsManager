"""
AI Tagging & Translation Module

このモジュールは Claude 3.5 Haiku を活用した論文の自動タグ生成と要約翻訳機能を提供します。

Classes:
    TaggerWorkflow: 論文タグ生成専用ワークフロー
    TranslateWorkflow: 論文要約翻訳専用ワークフロー
    ClaudeAPIClient: Claude API通信クライアント
"""

from .tagger_workflow import TaggerWorkflow
from .translate_workflow import TranslateWorkflow
from .claude_api_client import ClaudeAPIClient

__all__ = [
    'TaggerWorkflow',
    'TranslateWorkflow', 
    'ClaudeAPIClient'
] 