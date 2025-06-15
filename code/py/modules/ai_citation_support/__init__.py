"""
AI Citation Support Module

AI理解支援引用文献パーサー機能
- fetch機能で生成されたreferences.bibの内容をYAMLヘッダーに統合
- AI理解支援機能を提供
"""

from .ai_citation_support_workflow import AICitationSupportWorkflow

__all__ = [
    'AICitationSupportWorkflow'
]

__version__ = '3.2.0' 