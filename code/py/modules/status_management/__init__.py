"""
状態管理システム v4.0

各論文の処理状態をMarkdownファイルのYAMLヘッダーに記録し、
効率的な重複処理回避を実現する統合状態管理システム。
"""

from .status_manager import StatusManager, ProcessStatus

__version__ = "4.0.0"
__author__ = "ObsClippingsManager Team"

__all__ = [
    'StatusManager',
    'ProcessStatus'
] 