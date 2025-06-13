"""
Status Management Module

Markdownファイルの状態管理システム。
YAMLヘッダーベースの処理状態追跡を提供。
"""

from .yaml_header_processor import YAMLHeaderProcessor

__all__ = [
    'YAMLHeaderProcessor'
]
