"""
論文セクション解析ワークフロー

学術論文のMarkdownファイルを解析し、見出し構造に基づいてセクションを特定・分類し、
構造情報をYAMLヘッダーに永続化する機能を提供します。
"""

import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..shared.config_manager import ConfigManager
from ..shared.logger import IntegratedLogger
from ..shared.exceptions import ObsClippingsError
from ..shared.utils import read_yaml_header, update_yaml_header
from .data_structures import Section, PaperStructure


class SectionParserWorkflow:
    """論文セクション解析ワークフロー"""
    
    # セクション識別パターン
    SECTION_TYPE_PATTERNS = {
        'abstract': ['abstract', 'summary'],
        'introduction': ['introduction', 'intro', 'background'],
        'methods': ['methods', 'methodology', 'materials and methods', 'experimental', 'materials', 'experiment'],
        'results': ['results', 'findings'],
        'discussion': ['discussion', 'discussion and conclusions'],
        'conclusion': ['conclusion', 'conclusions', 'summary and conclusions'],
        'references': ['references', 'bibliography', 'citations'],
        'acknowledgments': ['acknowledgments', 'acknowledgements', 'thanks']
    }
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('SectionParserWorkflow')
        
        # 設定値の取得
        self.min_section_words = config_manager.get('section_parsing.min_section_words', 50)
        self.max_heading_level = config_manager.get('section_parsing.max_heading_level', 4)
        self.enable_subsection_analysis = config_manager.get('section_parsing.enable_subsection_analysis', True)
        self.section_type_detection = config_manager.get('section_parsing.section_type_detection', True)
        self.batch_size = config_manager.get('section_parsing.batch_size', 3)
        self.parallel_processing = config_manager.get('section_parsing.parallel_processing', True)
        
        self.logger.info("SectionParserWorkflow initialized successfully")
    
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None, 
                      batch_size: int = None, parallel: bool = None) -> Dict[str, Any]:
        """
        論文の一括セクション解析処理
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト（Noneで全論文）
            batch_size: バッチサイズ（Noneでデフォルト）
            parallel: 並列処理フラグ（Noneでデフォルト）
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Starting section parsing for papers in {clippings_dir}")
            
            # 設定のオーバーライド
            if batch_size is not None:
                self.batch_size = batch_size
            if parallel is not None:
                self.parallel_processing = parallel
            
            # 対象論文の決定
            paper_files = self._get_target_papers(clippings_dir, target_papers)
            
            if not paper_files:
                return {
                    'success': True,
                    'processed_papers': 0,
                    'paper_results': [],
                    'message': 'No papers to process'
                }
            
            self.logger.info(f"Processing {len(paper_files)} papers for section parsing")
            
            # バッチ処理実行
            if self.parallel_processing and len(paper_files) > 1:
                results = self._process_papers_parallel(paper_files)
            else:
                results = self._process_papers_sequential(paper_files)
            
            # 結果集計
            processed_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            
            self.logger.info(f"Section parsing completed: {processed_count} processed, {failed_count} failed")
            
            return {
                'success': failed_count == 0,
                'processed_papers': processed_count,
                'failed_papers': failed_count,
                'paper_results': results,
                'statistics': {
                    'total_papers': len(paper_files),
                    'successful': processed_count,
                    'failed': failed_count
                }
            }
            
        except Exception as e:
            self.logger.error(f"Section parsing process failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_papers': 0,
                'paper_results': []
            }
    
    def parse_paper_structure(self, paper_path: str) -> PaperStructure:
        """
        単一論文の構造解析
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            解析された論文構造
        """
        try:
            self.logger.info(f"Parsing structure for {paper_path}")
            
            # ファイル読み込み
            with open(paper_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAMLヘッダーを除去してMarkdown本文のみ抽出
            markdown_content = self._extract_markdown_content(content)
            
            # セクション抽出
            sections = self.extract_sections_by_heading(markdown_content)
            
            # セクションタイプの識別
            if self.section_type_detection:
                self.identify_section_types(sections)
            
            # 論文構造作成
            section_types_found = list(set(
                section.section_type for section in sections 
                if section.section_type != 'unknown'
            ))
            
            structure = PaperStructure(
                sections=sections,
                total_sections=len(sections),
                section_types_found=section_types_found,
                parsed_at=datetime.now().isoformat()
            )
            
            self.logger.info(f"Parsed {len(sections)} sections with types: {section_types_found}")
            return structure
            
        except Exception as e:
            self.logger.error(f"Failed to parse paper structure for {paper_path}: {e}")
            raise ObsClippingsError(f"Failed to parse paper structure: {e}")
    
    def extract_sections_by_heading(self, content: str) -> List[Section]:
        """
        見出しレベルによるセクション分割
        
        Args:
            content: Markdown本文
            
        Returns:
            抽出されたセクションリスト
        """
        lines = content.split('\n')
        sections = []
        current_section = None
        current_content_lines = []
        
        for line_num, line in enumerate(lines, 1):
            # 見出しの検出（##, ###, ####）
            heading_match = re.match(r'^(#{2,4})\s+(.+)$', line.strip())
            
            if heading_match:
                # 前のセクションを保存
                if current_section is not None:
                    current_section.content = '\n'.join(current_content_lines).strip()
                    current_section.end_line = line_num - 1
                    current_section.word_count = len(current_section.content)
                    
                    # 最小文字数チェック
                    if current_section.word_count >= self.min_section_words:
                        sections.append(current_section)
                    else:
                        self.logger.debug(f"Skipping short section: {current_section.title} ({current_section.word_count} chars)")
                
                # 新しいセクション開始
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 最大見出しレベルチェック
                if level <= self.max_heading_level:
                    current_section = Section(
                        title=title,
                        level=level,
                        content="",
                        start_line=line_num,
                        end_line=line_num,
                        word_count=0,
                        subsections=[],
                        section_type="unknown"
                    )
                    current_content_lines = []
                else:
                    # 最大レベルを超える見出しは本文として扱う
                    current_content_lines.append(line)
            else:
                # 本文行
                current_content_lines.append(line)
        
        # 最後のセクションを保存
        if current_section is not None:
            current_section.content = '\n'.join(current_content_lines).strip()
            current_section.end_line = len(lines)
            current_section.word_count = len(current_section.content)
            
            if current_section.word_count >= self.min_section_words:
                sections.append(current_section)
        
        # 見出しがない場合は全文を単一セクションとして処理
        if not sections and content.strip():
            sections.append(Section(
                title="Full Document",
                level=2,
                content=content.strip(),
                start_line=1,
                end_line=len(lines),
                word_count=len(content.strip()),
                subsections=[],
                section_type="unknown"
            ))
        
        # サブセクション解析
        if self.enable_subsection_analysis:
            sections = self._build_hierarchical_structure(sections)
        
        return sections
    
    def identify_section_types(self, sections: List[Section]) -> None:
        """
        セクションタイプの自動識別（セクションオブジェクトを直接更新）
        
        Args:
            sections: セクションリスト（直接更新される）
        """
        for section in sections:
            section.section_type = self._classify_section_type(section.title)
            
            # サブセクションも処理
            if section.subsections:
                self.identify_section_types(section.subsections)
    
    def update_yaml_with_structure(self, paper_path: str, structure: PaperStructure) -> bool:
        """
        YAMLヘッダーにセクション情報を記録
        
        Args:
            paper_path: 論文ファイルパス
            structure: 論文構造
            
        Returns:
            更新成功フラグ
        """
        try:
            # 現在のファイル内容を読み込み
            with open(paper_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAMLヘッダーの抽出と更新
            yaml_header, markdown_body = read_yaml_header(paper_path)
            
            # セクション構造をYAML形式に変換
            yaml_header['paper_structure'] = structure.to_dict()
            
            # 処理状態を更新
            if 'processing_status' not in yaml_header:
                yaml_header['processing_status'] = {}
            yaml_header['processing_status']['section_parsing'] = 'completed'
            
            # ワークフローバージョンを記録
            yaml_header['workflow_version'] = '3.2'
            
            # ファイルに書き戻し
            update_yaml_header(paper_path, yaml_header, markdown_body)
            
            self.logger.info(f"Updated YAML header with section structure for {paper_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header for {paper_path}: {e}")
            return False
    
    def process_single_paper(self, paper_path: str) -> Dict[str, Any]:
        """
        単一論文の処理
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Processing section parsing for {paper_path}")
            
            # 既に処理済みかチェック
            if self._is_already_processed(paper_path):
                self.logger.info(f"Section parsing already completed for {paper_path}")
                return {
                    'success': True,
                    'paper_path': paper_path,
                    'skipped': True,
                    'reason': 'already_processed'
                }
            
            # 構造解析
            structure = self.parse_paper_structure(paper_path)
            
            # YAML更新
            success = self.update_yaml_with_structure(paper_path, structure)
            
            if success:
                self.logger.info(f"Section parsing completed for {os.path.basename(paper_path)}")
                return {
                    'success': True,
                    'paper_path': paper_path,
                    'sections_found': structure.total_sections,
                    'section_types': structure.section_types_found
                }
            else:
                return {
                    'success': False,
                    'paper_path': paper_path,
                    'error': 'Failed to update YAML header'
                }
                
        except Exception as e:
            self.logger.error(f"Section parsing failed for {paper_path}: {e}")
            return {
                'success': False,
                'paper_path': paper_path,
                'error': str(e)
            }
    
    def _extract_markdown_content(self, content: str) -> str:
        """
        YAMLヘッダーを除去してMarkdown本文のみ抽出
        
        Args:
            content: ファイル全体の内容
            
        Returns:
            Markdown本文
        """
        yaml_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
        if yaml_match:
            return yaml_match.group(2)
        return content
    
    def _classify_section_type(self, title: str) -> str:
        """
        セクションタイトルからタイプを分類
        
        Args:
            title: セクションタイトル
            
        Returns:
            セクションタイプ
        """
        title_normalized = title.lower().strip()
        
        # 記号と数字を除去
        title_clean = re.sub(r'[^\w\s]', '', title_normalized)
        title_clean = re.sub(r'\d+', '', title_clean).strip()
        
        # パターンマッチング
        for section_type, patterns in self.SECTION_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in title_clean:
                    return section_type
        
        return 'unknown'
    
    def _build_hierarchical_structure(self, sections: List[Section]) -> List[Section]:
        """
        階層構造の構築
        
        Args:
            sections: フラットなセクションリスト
            
        Returns:
            階層構造を持つセクションリスト
        """
        if not sections:
            return sections
        
        hierarchical_sections = []
        section_stack = []
        
        for section in sections:
            # 現在のセクションより深いレベルをスタックから除去
            while section_stack and section_stack[-1].level >= section.level:
                section_stack.pop()
            
            # 親セクションがある場合はサブセクションとして追加
            if section_stack:
                section_stack[-1].subsections.append(section)
            else:
                # トップレベルセクション
                hierarchical_sections.append(section)
            
            section_stack.append(section)
        
        return hierarchical_sections
    
    def _is_already_processed(self, paper_path: str) -> bool:
        """
        セクション解析が既に実行済みかチェック
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            処理済みフラグ
        """
        try:
            with open(paper_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            yaml_header, _ = read_yaml_header(paper_path)
            
            processing_status = yaml_header.get('processing_status', {})
            return processing_status.get('section_parsing') == 'completed'
            
        except Exception:
            return False
    
    def _get_target_papers(self, clippings_dir: str, target_papers: Optional[List[str]]) -> List[str]:
        """
        対象論文ファイルのリストを取得
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト
            
        Returns:
            論文ファイルパスのリスト
        """
        paper_files = []
        
        if target_papers:
            # 指定された論文のみ
            for paper_key in target_papers:
                paper_dir = os.path.join(clippings_dir, paper_key)
                paper_file = os.path.join(paper_dir, f"{paper_key}.md")
                
                if os.path.exists(paper_file):
                    paper_files.append(paper_file)
                else:
                    self.logger.warning(f"Paper file not found: {paper_file}")
        else:
            # 全論文を対象
            for item in os.listdir(clippings_dir):
                item_path = os.path.join(clippings_dir, item)
                if os.path.isdir(item_path):
                    paper_file = os.path.join(item_path, f"{item}.md")
                    if os.path.exists(paper_file):
                        paper_files.append(paper_file)
        
        return paper_files
    
    def _process_papers_parallel(self, paper_files: List[str]) -> List[Dict[str, Any]]:
        """
        論文の並列処理
        
        Args:
            paper_files: 論文ファイルパスのリスト
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            # 並列実行のためのfutureを作成
            future_to_file = {
                executor.submit(self.process_single_paper, paper_file): paper_file 
                for paper_file in paper_files
            }
            
            # 結果の収集
            for future in as_completed(future_to_file):
                paper_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Parallel processing failed for {paper_file}: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'paper_file': paper_file
                    })
        
        return results
    
    def _process_papers_sequential(self, paper_files: List[str]) -> List[Dict[str, Any]]:
        """
        論文の順次処理
        
        Args:
            paper_files: 論文ファイルパスのリスト
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        for paper_file in paper_files:
            result = self.process_single_paper(paper_file)
            results.append(result)
        
        return results


def get_section_by_type(paper_path: str, section_type: str) -> Optional[Dict[str, Any]]:
    """
    指定タイプのセクションを取得するユーティリティ関数
    
    Args:
        paper_path: 論文ファイルパス
        section_type: セクションタイプ
        
    Returns:
        セクション辞書または None
    """
    try:
        with open(paper_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        yaml_manager = YAMLManager()
        yaml_header, _ = yaml_manager.extract_yaml_and_content(content)
        
        paper_structure = yaml_header.get('paper_structure', {})
        sections = paper_structure.get('sections', [])
        
        for section in sections:
            if section.get('section_type') == section_type:
                return section
            
            # サブセクションも検索
            subsections = section.get('subsections', [])
            for subsection in subsections:
                if subsection.get('section_type') == section_type:
                    return subsection
        
        return None
        
    except Exception:
        return None 