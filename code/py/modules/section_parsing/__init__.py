"""
section_parsing - 論文セクション分割機能

学術論文のMarkdownファイルの見出し構造を解析し、セクションを自動識別・分割する機能を提供。

Classes:
    SectionParsingWorkflow: メインワークフロークラス
    Section: セクション情報を表すデータクラス
    PaperStructure: 論文構造全体を表すデータクラス
"""

from .section_parsing_workflow import SectionParsingWorkflow
from .section_structure import Section, PaperStructure

__all__ = [
    'SectionParsingWorkflow',
    'Section',
    'PaperStructure'
] 