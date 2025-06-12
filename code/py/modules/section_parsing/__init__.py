"""
論文セクション分割機能モジュール

Markdownファイルの見出し構造を解析し、学術論文の標準的なセクションを自動識別・分割する機能を提供します。
"""

from .data_structures import Section, PaperStructure
from .section_parser_workflow import SectionParserWorkflow

__all__ = ['Section', 'PaperStructure', 'SectionParserWorkflow'] 