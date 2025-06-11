"""
AI用統合ファイル生成機能 v4.0

Citation Reference Table + Paper Contentを結合し、
AIアシスタントが完全に理解できる統合文書を生成します。
"""

import time
import re
from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from .data_structures import (
    AIReadableDocument, 
    CitationInfo, 
    AIGenerationResult, 
    MappingStatistics
)
from .citation_resolver import CitationResolver
from .citation_mapping_engine import CitationMappingEngine
from ..shared.logger import get_integrated_logger


class AIAssistantFileGenerator:
    """AI理解用統合ファイル生成エンジン"""
    
    def __init__(self, config_manager=None):
        """
        初期化
        
        Args:
            config_manager: 設定管理インスタンス
        """
        self.logger = get_integrated_logger().get_logger("AICitationSupport.AIFileGenerator")
        self.config_manager = config_manager
        self.citation_resolver = CitationResolver(config_manager)
        self.mapping_engine = CitationMappingEngine(config_manager)
        
        # 生成設定
        self.max_title_length = 80
        self.context_enhancement = True
        self.sorting_method = "numeric"  # "numeric" | "alphabetic" | "relevance"
        
        self.logger.info("AIAssistantFileGenerator initialized")
    
    def generate_ai_readable_file(self, markdown_file: str, 
                                 output_file: Optional[str] = None) -> AIGenerationResult:
        """
        AI理解用統合ファイルを生成
        
        Args:
            markdown_file: 元のMarkdownファイル
            output_file: 出力ファイル（Noneの場合は自動生成）
            
        Returns:
            AIGenerationResult: 生成結果と統計情報
            
        Process:
        1. YAMLヘッダーから引用マッピング情報を取得
        2. 全引用番号に対して動的解決を実行
        3. Citation Reference Tableを生成
        4. Paper Contentから不要情報を除去
        5. AI最適化統合文書として出力
        """
        start_time = time.time()
        statistics = MappingStatistics()
        
        try:
            self.logger.info(f"Generating AI readable file from {markdown_file}")
            
            # Step 1: 入力ファイル検証
            if not Path(markdown_file).exists():
                return AIGenerationResult(
                    success=False,
                    error_message=f"Input file not found: {markdown_file}"
                )
            
            # Step 2: 出力ファイル決定
            if not output_file:
                output_file = self._generate_output_filename(markdown_file)
            
            # Step 3: YAMLヘッダーから引用マッピング取得
            citation_mapping = self.mapping_engine.get_mapping_from_file(markdown_file)
            if not citation_mapping:
                return AIGenerationResult(
                    success=False,
                    error_message="No citation mapping found in file. Run ai-mapping first."
                )
            
            self.logger.info(f"Found {len(citation_mapping.index_map)} citation mappings")
            
            # Step 4: 全引用番号の動的解決
            citation_numbers = list(citation_mapping.index_map.keys())
            resolved_citations = self.citation_resolver.batch_resolve_citations(
                citation_numbers, markdown_file
            )
            
            statistics.total_citations_mapped = len(citation_numbers)
            statistics.created_mappings = len(resolved_citations)
            statistics.failed_mappings = len(citation_numbers) - len(resolved_citations)
            
            self.logger.info(f"Resolved {len(resolved_citations)}/{len(citation_numbers)} citations")
            
            # Step 5: Citation Reference Tableを生成
            citation_table = self._generate_citation_reference_table(resolved_citations)
            
            # Step 6: Paper Contentを最適化
            paper_content = self._extract_and_optimize_content(markdown_file)
            
            # Step 7: AI用統合文書オブジェクト作成
            ai_document = AIReadableDocument(
                original_file=markdown_file,
                references_file=citation_mapping.references_file,
                citation_table=citation_table,
                paper_content=paper_content,
                generation_timestamp=datetime.now(),
                total_citations=len(resolved_citations),
                ai_optimization_level="enhanced"
            )
            
            # Step 8: Markdownファイルとして出力
            output_content = ai_document.to_markdown()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            # 統計情報完成
            statistics.processing_time = time.time() - start_time
            
            self.logger.info(f"AI readable file generated successfully: {output_file}")
            self.logger.info(f"Generation completed in {statistics.processing_time:.2f}s")
            
            return AIGenerationResult(
                success=True,
                output_file=output_file,
                statistics=statistics
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI readable file: {e}")
            return AIGenerationResult(
                success=False,
                error_message=str(e),
                statistics=statistics
            )
    
    def _generate_citation_reference_table(self, resolved_citations: dict) -> str:
        """Citation Reference Tableを生成"""
        if not resolved_citations:
            return "**No citations found in this document.**"
        
        self.logger.info(f"Generating citation reference table for {len(resolved_citations)} citations")
        
        # ソート方法に応じて並び替え
        if self.sorting_method == "numeric":
            sorted_citations = sorted(resolved_citations.items(), key=lambda x: x[0])
        elif self.sorting_method == "alphabetic":
            sorted_citations = sorted(resolved_citations.items(), 
                                    key=lambda x: x[1].authors)
        elif self.sorting_method == "relevance":
            sorted_citations = sorted(resolved_citations.items(), 
                                    key=lambda x: x[1].relevance_score, reverse=True)
        else:
            sorted_citations = list(resolved_citations.items())
        
        # テーブル行を生成
        table_lines = []
        for number, citation_info in sorted_citations:
            reference_line = citation_info.to_reference_line()
            table_lines.append(reference_line)
        
        # 統計情報を追加
        stats_line = f"\n**📊 Citation Statistics**: {len(resolved_citations)} references"
        
        return "\n\n".join(table_lines) + stats_line
    
    def _extract_and_optimize_content(self, markdown_file: str) -> str:
        """Paper Contentを抽出し、AI理解用に最適化"""
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Step 1: YAMLヘッダーを除去
            yaml_pattern = r'^---\s*\n.*?\n---\s*\n'
            content = re.sub(yaml_pattern, '', content, flags=re.DOTALL)
            
            # Step 2: AI理解支援のための最適化
            if self.context_enhancement:
                content = self._enhance_citation_context(content)
            
            # Step 3: 不要な空白行を整理
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = content.strip()
            
            self.logger.debug("Content extraction and optimization completed")
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {markdown_file}: {e}")
            return f"**Error: Could not extract content from {markdown_file}**"
    
    def _enhance_citation_context(self, content: str) -> str:
        """引用文脈をAI理解用に拡張"""
        # 引用箇所に説明的なマーカーを追加
        enhanced_content = content
        
        # [数字] パターンを強調
        citation_pattern = r'\[(\d+)\]'
        enhanced_content = re.sub(
            citation_pattern,
            r'[**\1**]',  # [1] → [**1**]
            enhanced_content
        )
        
        # 脚注引用も強調
        footnote_pattern = r'\[\^(\d+)\]'
        enhanced_content = re.sub(
            footnote_pattern,
            r'[^**\1**]',  # [^1] → [^**1**]
            enhanced_content
        )
        
        return enhanced_content
    
    def _generate_output_filename(self, input_file: str) -> str:
        """AI用ファイルの出力ファイル名を生成"""
        input_path = Path(input_file)
        stem = input_path.stem
        
        # タイムスタンプを追加
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # AI用ファイル名として生成
        output_filename = f"{stem}_AI_Readable_{timestamp}.md"
        output_path = input_path.parent / output_filename
        
        return str(output_path)
    
    def generate_citation_preview(self, markdown_file: str, 
                                 max_citations: int = 5) -> str:
        """引用情報のプレビューを生成（デバッグ用）"""
        try:
            citation_mapping = self.mapping_engine.get_mapping_from_file(markdown_file)
            if not citation_mapping:
                return "❌ No citation mapping found"
            
            # 最初のN個の引用番号を解決
            citation_numbers = sorted(list(citation_mapping.index_map.keys()))[:max_citations]
            resolved_citations = self.citation_resolver.batch_resolve_citations(
                citation_numbers, markdown_file
            )
            
            # プレビュー文字列を生成
            preview_lines = [
                f"📚 Citation Preview ({len(resolved_citations)}/{len(citation_numbers)} resolved):",
                "=" * 60
            ]
            
            for number in citation_numbers:
                if number in resolved_citations:
                    citation = resolved_citations[number]
                    preview_lines.append(f"[{number}] {citation.authors} ({citation.year})")
                    preview_lines.append(f"    {citation.title[:60]}...")
                else:
                    preview_lines.append(f"[{number}] ❌ Resolution failed")
                
                preview_lines.append("")
            
            return "\n".join(preview_lines)
            
        except Exception as e:
            return f"❌ Preview generation failed: {e}"
    
    def validate_ai_file_quality(self, ai_file: str) -> Tuple[bool, List[str]]:
        """生成されたAIファイルの品質を検証"""
        issues = []
        
        try:
            with open(ai_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # チェック1: Citation Reference Tableの存在
            if "## 📚 Citation Reference Table" not in content:
                issues.append("Missing Citation Reference Table section")
            
            # チェック2: Paper Contentの存在
            if "## 📄 Paper Content" not in content:
                issues.append("Missing Paper Content section")
            
            # チェック3: 引用番号の一貫性
            citation_pattern = r'\[(\d+)\]'
            citations_in_table = set()
            citations_in_content = set()
            
            # テーブル内の引用番号を抽出
            table_start = content.find("## 📚 Citation Reference Table")
            table_end = content.find("## 📄 Paper Content")
            if table_start >= 0 and table_end >= 0:
                table_section = content[table_start:table_end]
                citations_in_table.update(
                    int(match.group(1)) for match in re.finditer(citation_pattern, table_section)
                )
            
            # Content内の引用番号を抽出
            content_start = content.find("## 📄 Paper Content")
            if content_start >= 0:
                content_section = content[content_start:]
                citations_in_content.update(
                    int(match.group(1)) for match in re.finditer(citation_pattern, content_section)
                )
            
            # 一貫性チェック
            missing_in_table = citations_in_content - citations_in_table
            if missing_in_table:
                issues.append(f"Citations missing in table: {sorted(missing_in_table)}")
            
            self.logger.info(f"AI file quality validation completed: {len(issues)} issues found")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Validation failed: {e}")
            return False, issues 