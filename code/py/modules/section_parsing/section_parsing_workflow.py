"""
section_parsing_workflow.py - セクション分割ワークフロー

学術論文のMarkdownファイルからセクション構造を解析・抽出する機能
"""

import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger
from ..shared_modules.exceptions import ProcessingError
from ..status_management_yaml.yaml_header_processor import YAMLHeaderProcessor
from .section_structure import Section, PaperStructure


class SectionParsingWorkflow:
    """論文セクション分割ワークフロークラス"""
    
    # セクション種別識別パターン
    SECTION_TYPE_PATTERNS = {
        'abstract': ['abstract', 'summary'],
        'introduction': ['introduction', 'intro', 'background'],
        'methods': ['methods', 'methodology', 'materials and methods', 'experimental'],
        'results': ['results', 'findings'],
        'discussion': ['discussion', 'discussion and conclusions'],
        'conclusion': ['conclusion', 'conclusions', 'summary and conclusions'],
        'references': ['references', 'bibliography', 'citations'],
        'acknowledgments': ['acknowledgments', 'acknowledgements', 'thanks']
    }
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """初期化"""
        self.config_manager = config_manager
        self.logger = logger.get_logger('SectionParsingWorkflow')
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        
        # 設定読み込み
        self.config = self.config_manager.get_config().get('section_parsing', {})
        self.min_section_words = self.config.get('min_section_words', 50)
        self.max_heading_level = self.config.get('max_heading_level', 4)
        self.enable_subsection_analysis = self.config.get('enable_subsection_analysis', True)
        
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None) -> Dict[str, Any]:
        """論文の一括セクション分割処理"""
        self.logger.info(f"Starting section parsing for directory: {clippings_dir}")
        
        # 処理対象論文の取得
        if target_papers is None:
            # ディレクトリから論文リストを取得
            target_papers = self._get_paper_list(clippings_dir)
        
        results = {
            'processed_papers': 0,
            'failed_papers': 0,
            'papers_with_sections': 0,
            'papers_without_sections': 0,
            'total_sections_found': 0,
            'section_types_found': set()
        }
        
        for paper_name in target_papers:
            paper_path = os.path.join(clippings_dir, paper_name, f"{paper_name}.md")
            
            if not os.path.exists(paper_path):
                self.logger.warning(f"Paper file not found: {paper_path}")
                results['failed_papers'] += 1
                continue
                
            try:
                paper_structure = self.parse_sections_single(paper_path)
                self.update_yaml_with_structure(paper_path, paper_structure)
                
                results['processed_papers'] += 1
                if paper_structure.total_sections > 0:
                    results['papers_with_sections'] += 1
                    results['total_sections_found'] += paper_structure.total_sections
                    results['section_types_found'].update(paper_structure.section_types_found)
                else:
                    results['papers_without_sections'] += 1
                    
                self.logger.info(f"Successfully parsed sections for: {paper_name} "
                               f"({paper_structure.total_sections} sections)")
                
            except Exception as e:
                self.logger.error(f"Failed to parse sections for {paper_name}: {e}")
                results['failed_papers'] += 1
        
        # section_types_found を list に変換（JSON serializable）
        results['section_types_found'] = list(results['section_types_found'])
        
        self.logger.info(f"Section parsing completed: {results['processed_papers']} papers processed, "
                        f"{results['total_sections_found']} total sections found")
        
        return results
    
    def parse_sections_single(self, paper_path: str) -> PaperStructure:
        """単一論文のセクション分割処理"""
        self.logger.debug(f"Parsing sections for: {paper_path}")
        
        try:
            # Markdownファイル読み込み
            content_lines = self._read_markdown_content(paper_path)
            
            # セクション抽出
            sections = self._extract_sections(content_lines)
            
            # 論文構造構築
            paper_structure = self._build_paper_structure(sections)
            paper_structure.parsed_at = datetime.now().isoformat()
            
            return paper_structure
            
        except Exception as e:
            raise ProcessingError(f"Failed to parse sections for {paper_path}: {e}")
    
    def update_yaml_with_structure(self, paper_path: str, paper_structure: PaperStructure) -> None:
        """YAMLヘッダーにセクション構造を更新"""
        try:
            from pathlib import Path
            yaml_data, content = self.yaml_processor.parse_yaml_header(Path(paper_path))
            
            # paper_structure セクション更新
            yaml_data['paper_structure'] = paper_structure.to_yaml_dict()
            
            # processing_status 更新
            if 'processing_status' not in yaml_data:
                yaml_data['processing_status'] = {}
            yaml_data['processing_status']['section_parsing'] = 'completed'
            
            # last_updated 更新
            yaml_data['last_updated'] = datetime.now().isoformat()
            
            # ファイル保存
            self.yaml_processor.write_yaml_header(Path(paper_path), yaml_data, content)
            
            self.logger.debug(f"Updated YAML header with section structure: {paper_path}")
            
        except Exception as e:
            raise ProcessingError(f"Failed to update YAML header for {paper_path}: {e}")
    
    def _get_paper_list(self, clippings_dir: str) -> List[str]:
        """処理対象論文リストを取得"""
        papers = []
        
        for item in os.listdir(clippings_dir):
            item_path = os.path.join(clippings_dir, item)
            if os.path.isdir(item_path):
                # サブディレクトリ内の.mdファイルを検索
                for file in os.listdir(item_path):
                    if file.endswith('.md'):
                        papers.append(item)
                        break  # 最初の.mdファイルが見つかったらOK
        
        return papers
    
    def _read_markdown_content(self, paper_path: str) -> List[str]:
        """Markdownファイル読み込み"""
        try:
            with open(paper_path, 'r', encoding='utf-8') as f:
                return f.readlines()
        except Exception as e:
            raise ProcessingError(f"Failed to read markdown file {paper_path}: {e}")
    
    def _extract_sections(self, content_lines: List[str]) -> List[Section]:
        """見出し構造からセクションを抽出"""
        sections = []
        current_section = None
        in_yaml_header = False
        yaml_header_count = 0
        yaml_header_end_line = 0  # YAMLヘッダー終了行を記録
        
        for line_num, line in enumerate(content_lines, 1):
            line_stripped = line.strip()
            
            # YAMLヘッダーのスキップ処理
            if line_stripped == '---':
                yaml_header_count += 1
                if yaml_header_count == 1:
                    in_yaml_header = True
                    continue
                elif yaml_header_count == 2:
                    in_yaml_header = False
                    yaml_header_end_line = line_num  # YAMLヘッダー終了行を記録
                    continue
            
            if in_yaml_header:
                continue
            
            # YAMLヘッダー終了後のMarkdown部分の相対行数を計算
            markdown_line_num = line_num - yaml_header_end_line
            
            # 見出し行の処理
            if self._is_heading(line_stripped):
                # 前のセクションを完了
                if current_section:
                    current_section.end_line = markdown_line_num - 1
                    current_section.word_count = self._count_words_from_markdown_lines(
                        content_lines, yaml_header_end_line, current_section.start_line, current_section.end_line
                    )
                    
                    # 階層構造の処理
                    self._add_section_with_hierarchy(sections, current_section)
                
                # 新しいセクション開始
                current_section = Section(
                    title=self._extract_title(line_stripped),
                    level=self._get_heading_level(line_stripped),
                    section_type=self._identify_section_type(line_stripped),
                    start_line=markdown_line_num,
                    end_line=0,  # 後で設定
                    word_count=0,  # 後で計算
                    content_lines=[]
                )
                
                self.logger.debug(f"Found section: {current_section.title} at markdown line {markdown_line_num} (file line {line_num})")
        
        # 最後のセクションを完了
        if current_section:
            markdown_total_lines = len(content_lines) - yaml_header_end_line
            current_section.end_line = markdown_total_lines
            current_section.word_count = self._count_words_from_markdown_lines(
                content_lines, yaml_header_end_line, current_section.start_line, current_section.end_line
            )
            self._add_section_with_hierarchy(sections, current_section)
        
        return sections
    
    def _add_section_with_hierarchy(self, sections: List[Section], new_section: Section) -> None:
        """階層構造を考慮してセクションを追加"""
        if not self.enable_subsection_analysis:
            sections.append(new_section)
            return
        
        # レベル2の場合は常にトップレベル
        if new_section.level == 2:
            sections.append(new_section)
            return
        
        # レベル3以上の場合、親セクションを探す
        if sections:
            parent_section = sections[-1]  # 直前のセクション
            
            # 親セクションのレベルより1つ深い場合のみ子セクションとして追加
            if new_section.level == parent_section.level + 1:
                parent_section.subsections.append(new_section)
                return
        
        # 条件に合わない場合はトップレベルに追加
        sections.append(new_section)
    
    def _is_heading(self, line: str) -> bool:
        """見出し行の判定"""
        return bool(re.match(r'^#{2,4}\s+.+', line))
    
    def _get_heading_level(self, line: str) -> int:
        """見出しレベルの取得"""
        match = re.match(r'^(#{2,4})\s+', line)
        return len(match.group(1)) if match else 0
    
    def _extract_title(self, line: str) -> str:
        """見出しからタイトルを抽出"""
        match = re.match(r'^#{2,4}\s+(.+)', line)
        return match.group(1).strip() if match else ""
    
    def _identify_section_type(self, line: str) -> str:
        """セクション種別の識別"""
        title = self._extract_title(line).lower()
        
        for section_type, patterns in self.SECTION_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in title:
                    return section_type
        
        return "unknown"
    
    def _count_words_from_markdown_lines(self, content_lines: List[str], yaml_header_end_line: int, start_line: int, end_line: int) -> int:
        """指定された行範囲の文字数をカウント（YAMLヘッダー除外）"""
        word_count = 0
        # YAMLヘッダー終了後のMarkdown部分でのstart/end indexを計算
        markdown_start_index = yaml_header_end_line + start_line - 1
        markdown_end_index = yaml_header_end_line + end_line
        
        # 実際の配列範囲チェック
        if markdown_start_index < len(content_lines) and markdown_end_index <= len(content_lines):
            for line in content_lines[markdown_start_index:markdown_end_index]:
                word_count += len(line.split())
        
        return word_count
    
    def _build_paper_structure(self, sections: List[Section]) -> PaperStructure:
        """論文構造を構築"""
        paper_structure = PaperStructure()
        
        for section in sections:
            paper_structure.add_section(section)
        
        return paper_structure 