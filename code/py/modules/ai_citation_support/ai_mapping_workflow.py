"""
AI理解支援引用文献統合ワークフロー v4.0

統合ワークフローの第5段階として、AI用ファイル生成機能を実行します。
"""

import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .data_structures import AIGenerationResult, MappingStatistics
from .citation_mapping_engine import CitationMappingEngine
from .ai_assistant_file_generator import AIAssistantFileGenerator
from ..shared.logger import get_integrated_logger


class AIMappingWorkflow:
    """AI理解支援引用文献統合ワークフロー"""
    
    def __init__(self, config_manager=None, logger=None):
        """
        初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ロガーインスタンス
        """
        if logger:
            self.logger = logger.get_logger("AICitationSupport.AIMappingWorkflow")
        else:
            self.logger = get_integrated_logger().get_logger("AICitationSupport.AIMappingWorkflow")
        
        self.config_manager = config_manager
        
        # コアエンジンの初期化
        self.mapping_engine = CitationMappingEngine(config_manager)
        self.file_generator = AIAssistantFileGenerator(config_manager)
        
        # ワークフロー統計
        self.execution_statistics = {
            'total_files_processed': 0,
            'successful_mappings': 0,
            'successful_generations': 0,
            'failed_operations': 0,
            'total_citations_processed': 0
        }
        
        self.logger.info("AIMappingWorkflow initialized successfully")
    
    def execute_ai_mapping(self, markdown_file: str, references_bib: str,
                          generate_ai_file: bool = True,
                          output_file: Optional[str] = None) -> AIGenerationResult:
        """
        AI理解支援引用文献統合の完全実行
        
        Args:
            markdown_file: 対象Markdownファイル
            references_bib: 対応するreferences.bibファイル
            generate_ai_file: AI用ファイル生成フラグ
            output_file: 出力ファイル（Noneの場合は自動生成）
            
        Returns:
            AIGenerationResult: 実行結果
            
        Process:
        1. 軽量引用マッピング作成
        2. YAMLヘッダー更新
        3. AI用統合ファイル生成（オプション）
        4. 品質検証
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting AI mapping workflow for {markdown_file}")
            
            # 入力検証
            validation_result = self._validate_inputs(markdown_file, references_bib)
            if not validation_result[0]:
                return AIGenerationResult(
                    success=False,
                    error_message=validation_result[1]
                )
            
            # Step 1: 軽量引用マッピング作成
            self.logger.info("Step 1: Creating citation mapping...")
            citation_mapping = self.mapping_engine.create_citation_mapping(
                markdown_file, references_bib
            )
            
            if citation_mapping.total_citations == 0:
                self.logger.warning("No citations found - creating empty mapping")
            
            # Step 2: YAMLヘッダー更新
            self.logger.info("Step 2: Updating YAML header...")
            update_success = self.mapping_engine.update_yaml_header(
                markdown_file, citation_mapping
            )
            
            if not update_success:
                return AIGenerationResult(
                    success=False,
                    error_message="Failed to update YAML header with citation mapping"
                )
            
            # 統計更新
            self.execution_statistics['total_files_processed'] += 1
            self.execution_statistics['successful_mappings'] += 1
            self.execution_statistics['total_citations_processed'] += citation_mapping.total_citations
            
            # Step 3: AI用統合ファイル生成（オプション）
            if generate_ai_file:
                self.logger.info("Step 3: Generating AI readable file...")
                generation_result = self.file_generator.generate_ai_readable_file(
                    markdown_file, output_file
                )
                
                if generation_result.success:
                    self.execution_statistics['successful_generations'] += 1
                    
                    # Step 4: 品質検証
                    self.logger.info("Step 4: Validating AI file quality...")
                    quality_ok, issues = self.file_generator.validate_ai_file_quality(
                        generation_result.output_file
                    )
                    
                    if not quality_ok:
                        generation_result.warnings.extend(issues)
                        self.logger.warning(f"Quality issues found: {issues}")
                    
                    # 実行時間を追加
                    if generation_result.statistics:
                        generation_result.statistics.processing_time = time.time() - start_time
                    
                    self.logger.info(f"AI mapping workflow completed successfully in {time.time() - start_time:.2f}s")
                    return generation_result
                else:
                    self.execution_statistics['failed_operations'] += 1
                    return generation_result
            else:
                # マッピングのみ実行された場合
                self.logger.info("AI mapping workflow completed (mapping only)")
                return AIGenerationResult(
                    success=True,
                    output_file="",  # AI用ファイルは生成していない
                    statistics=MappingStatistics(
                        created_mappings=1,
                        total_citations_mapped=citation_mapping.total_citations,
                        processing_time=time.time() - start_time
                    )
                )
            
        except Exception as e:
            self.execution_statistics['failed_operations'] += 1
            self.logger.error(f"AI mapping workflow failed: {e}")
            return AIGenerationResult(
                success=False,
                error_message=str(e)
            )
    
    def batch_execute_ai_mapping(self, file_pairs: List[Tuple[str, str]],
                                generate_ai_files: bool = True) -> Dict[str, AIGenerationResult]:
        """
        複数ファイルのAI理解支援引用文献統合をバッチ実行
        
        Args:
            file_pairs: (markdown_file, references_bib) のペアのリスト
            generate_ai_files: AI用ファイル生成フラグ
            
        Returns:
            ファイル名 → AIGenerationResult の辞書
        """
        self.logger.info(f"Starting batch AI mapping for {len(file_pairs)} file pairs")
        
        results = {}
        successful_count = 0
        
        for i, (markdown_file, references_bib) in enumerate(file_pairs, 1):
            self.logger.info(f"Processing {i}/{len(file_pairs)}: {Path(markdown_file).name}")
            
            result = self.execute_ai_mapping(
                markdown_file, references_bib, generate_ai_files
            )
            
            results[markdown_file] = result
            
            if result.success:
                successful_count += 1
                self.logger.info(f"✅ {Path(markdown_file).name} completed successfully")
            else:
                self.logger.error(f"❌ {Path(markdown_file).name} failed: {result.error_message}")
        
        self.logger.info(f"Batch processing completed: {successful_count}/{len(file_pairs)} successful")
        return results
    
    def dry_run_ai_mapping(self, markdown_file: str, references_bib: str) -> str:
        """
        AI理解支援引用文献統合のドライラン実行
        
        Args:
            markdown_file: 対象Markdownファイル
            references_bib: 対応するreferences.bibファイル
            
        Returns:
            ドライラン結果レポート
        """
        try:
            self.logger.info(f"Starting AI mapping dry run for {markdown_file}")
            
            # 入力検証
            validation_result = self._validate_inputs(markdown_file, references_bib)
            if not validation_result[0]:
                return f"❌ Validation failed: {validation_result[1]}"
            
            # 引用マッピング分析（実際の更新は行わない）
            citation_mapping = self.mapping_engine.create_citation_mapping(
                markdown_file, references_bib
            )
            
            # プレビュー生成
            preview = self.file_generator.generate_citation_preview(markdown_file, max_citations=5)
            
            # ドライランレポート作成
            report_lines = [
                "🔍 AI Mapping Workflow Dry Run Analysis",
                "=" * 50,
                f"📄 Markdown File: {Path(markdown_file).name}",
                f"📚 References File: {Path(references_bib).name}",
                f"📊 Citations Found: {citation_mapping.total_citations}",
                f"🔗 Mapping Version: {citation_mapping.mapping_version}",
                "",
                "📋 Citation Mapping Preview:",
                "-" * 30
            ]
            
            # マッピング詳細
            if citation_mapping.index_map:
                for number, key in sorted(citation_mapping.index_map.items()):
                    report_lines.append(f"  [{number}] → {key}")
            else:
                report_lines.append("  No citations found")
            
            report_lines.extend([
                "",
                "📚 Citation Preview:",
                "-" * 20,
                preview,
                "",
                "✅ Dry run completed successfully"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            self.logger.error(f"Dry run failed: {e}")
            return f"❌ Dry run failed: {e}"
    
    def _validate_inputs(self, markdown_file: str, references_bib: str) -> Tuple[bool, str]:
        """入力ファイルの検証"""
        markdown_path = Path(markdown_file)
        bib_path = Path(references_bib)
        
        if not markdown_path.exists():
            return False, f"Markdown file not found: {markdown_file}"
        
        if not bib_path.exists():
            return False, f"References file not found: {references_bib}"
        
        if not markdown_path.suffix.lower() in ['.md', '.markdown']:
            return False, f"Invalid markdown file extension: {markdown_path.suffix}"
        
        if not bib_path.suffix.lower() == '.bib':
            return False, f"Invalid BibTeX file extension: {bib_path.suffix}"
        
        return True, "Validation passed"
    
    def get_workflow_statistics(self) -> Dict[str, any]:
        """ワークフロー実行統計を取得"""
        stats = self.execution_statistics.copy()
        
        # 成功率を追加
        total_processed = stats['total_files_processed']
        if total_processed > 0:
            stats['mapping_success_rate'] = stats['successful_mappings'] / total_processed
            stats['generation_success_rate'] = stats['successful_generations'] / total_processed
        else:
            stats['mapping_success_rate'] = 0.0
            stats['generation_success_rate'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """統計情報をリセット"""
        self.execution_statistics = {
            'total_files_processed': 0,
            'successful_mappings': 0,
            'successful_generations': 0,
            'failed_operations': 0,
            'total_citations_processed': 0
        }
        self.logger.info("Workflow statistics reset") 