"""
落合フォーマット要約機能

学術論文の内容を6つの構造化された質問に答える形で要約し、
研究者向けのA4一枚程度の簡潔な論文理解を提供する機能。
"""

from .data_structures import OchiaiFormat
from .ochiai_format_workflow import OchiaiFormatWorkflow

__all__ = [
    'OchiaiFormat',
    'OchiaiFormatWorkflow'
] 