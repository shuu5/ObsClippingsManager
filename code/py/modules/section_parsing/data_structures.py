"""
論文セクション分割機能のデータ構造

Sectionクラス、PaperStructureクラスの定義を提供します。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Section:
    """
    論文セクションを表すデータクラス
    
    Attributes:
        title: セクションタイトル
        level: 見出しレベル (2=##, 3=###, 4=####)
        content: セクション本文
        start_line: 開始行番号
        end_line: 終了行番号
        word_count: 文字数
        subsections: 子セクション
        section_type: abstract, introduction, results等
    """
    title: str
    level: int
    content: str
    start_line: int
    end_line: int
    word_count: int
    subsections: List['Section'] = field(default_factory=list)
    section_type: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'title': self.title,
            'level': self.level,
            'section_type': self.section_type,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'word_count': self.word_count,
            'subsections': [sub.to_dict() for sub in self.subsections]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Section':
        """辞書から復元"""
        subsections = []
        if 'subsections' in data:
            subsections = [cls.from_dict(sub_data) for sub_data in data['subsections']]
        
        return cls(
            title=data['title'],
            level=data['level'],
            content=data.get('content', ''),
            start_line=data['start_line'],
            end_line=data['end_line'],
            word_count=data['word_count'],
            subsections=subsections,
            section_type=data.get('section_type', 'unknown')
        )


@dataclass
class PaperStructure:
    """
    論文全体の構造を表すデータクラス
    
    Attributes:
        sections: トップレベルセクション
        total_sections: 総セクション数
        section_types_found: 発見されたセクションタイプ
        parsed_at: 解析日時
    """
    sections: List[Section]
    total_sections: int
    section_types_found: List[str]
    parsed_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（YAML保存用）"""
        return {
            'parsed_at': self.parsed_at,
            'total_sections': self.total_sections,
            'sections': [section.to_dict() for section in self.sections],
            'section_types_found': self.section_types_found
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaperStructure':
        """辞書から復元"""
        sections = [Section.from_dict(section_data) for section_data in data['sections']]
        
        return cls(
            sections=sections,
            total_sections=data['total_sections'],
            section_types_found=data['section_types_found'],
            parsed_at=data['parsed_at']
        )
    
    def get_section_by_type(self, section_type: str) -> Optional[Section]:
        """指定タイプのセクションを取得"""
        for section in self.sections:
            if section.section_type == section_type:
                return section
            # 子セクションも検索
            for subsection in section.subsections:
                if subsection.section_type == section_type:
                    return subsection
        return None
    
    def get_sections_by_types(self, section_types: List[str]) -> List[Section]:
        """指定タイプのセクションを複数取得"""
        result = []
        for section_type in section_types:
            section = self.get_section_by_type(section_type)
            if section:
                result.append(section)
        return result 