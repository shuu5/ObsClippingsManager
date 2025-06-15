"""
section_structure.py - セクション構造定義

論文のセクション情報を構造化するデータクラス群
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Section:
    """論文のセクション情報を表すデータクラス"""
    
    title: str                          # セクションタイトル
    level: int                         # 見出しレベル (2=##, 3=###, 4=####)
    section_type: str                  # セクション種別 (abstract、introduction等)
    start_line: int                    # 開始行番号
    end_line: int                      # 終了行番号
    word_count: int                    # 文字数
    content_lines: List[str] = field(default_factory=list)  # セクション内容の行リスト
    subsections: List['Section'] = field(default_factory=list)  # 子セクション


@dataclass
class PaperStructure:
    """論文構造全体を表すデータクラス"""
    
    sections: List[Section] = field(default_factory=list)  # トップレベルセクション
    total_sections: int = 0            # 総セクション数
    section_types_found: List[str] = field(default_factory=list)  # 発見されたセクションタイプ
    parsed_at: Optional[str] = None    # 解析日時
    
    
    def add_section(self, section: Section) -> None:
        """セクションを追加"""
        self.sections.append(section)
        self.total_sections += 1
        
        if section.section_type not in self.section_types_found:
            self.section_types_found.append(section.section_type)
    
    
    def get_section_by_type(self, section_type: str) -> Optional[Section]:
        """指定されたタイプのセクションを取得"""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None
    
    
    def to_yaml_dict(self) -> dict:
        """YAML出力用の辞書に変換"""
        return {
            'parsed_at': self.parsed_at or datetime.now().isoformat(),
            'total_sections': self.total_sections,
            'sections': [
                {
                    'title': section.title,
                    'level': section.level,
                    'section_type': section.section_type,
                    'start_line': section.start_line,
                    'end_line': section.end_line,
                    'word_count': section.word_count,
                    'subsections': [
                        {
                            'title': subsection.title,
                            'level': subsection.level,
                            'start_line': subsection.start_line,
                            'end_line': subsection.end_line,
                            'word_count': subsection.word_count
                        } for subsection in section.subsections
                    ] if section.subsections else []
                } for section in self.sections
            ],
            'section_types_found': self.section_types_found
        } 