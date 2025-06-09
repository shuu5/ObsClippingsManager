#!/usr/bin/env python3
"""
状態管理ベースの統合ワークフロー

状態管理フラグを使用してスマートにタスクを実行する新しいrun-integrated機能
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from ..shared.config_manager import ConfigManager
from ..shared.logger import IntegratedLogger
from ..shared.status_manager import StatusManager, ProcessStatus
from ..shared.bibtex_parser import BibTeXParser
from ..shared.exceptions import ObsClippingsError
from .workflow_manager import WorkflowManager, WorkflowType


class EnhancedIntegratedWorkflow:
    """
    状態管理ベースの統合ワークフロー
    
    各論文の処理状態を追跡し、必要な処理のみを効率的に実行します。
    """
    
    # 処理順序の定義
    PROCESS_ORDER = ['organize', 'sync', 'fetch', 'parse']
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        EnhancedIntegratedWorkflowの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ管理オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('EnhancedIntegratedWorkflow')
        self.status_manager = StatusManager(config_manager, logger)
        self.bibtex_parser = BibTeXParser()
        self.workflow_manager = WorkflowManager(config_manager, logger)
        
        self.logger.info("EnhancedIntegratedWorkflow initialized successfully")
    
    def analyze_paper_status(self, bibtex_file: str, clippings_dir: str) -> Dict[str, List[str]]:
        """
        論文の現在の状態を分析し、必要な処理を特定
        
        Args:
            bibtex_file: BibTeXファイルパス
            clippings_dir: Clippingsディレクトリパス
            
        Returns:
            Dict[process_type, List[citation_key]]: 各処理が必要な論文のリスト
        """
        try:
            analysis = {
                'needs_organize': [],
                'needs_sync': [],
                'needs_fetch': [],
                'needs_parse': []
            }
            
            # BibTeXファイルから論文リストを取得
            entries = self.bibtex_parser.parse_file(bibtex_file)
            all_papers = list(entries.keys())
            
            # 各処理タイプで必要な論文を取得
            analysis['needs_organize'] = self.status_manager.get_papers_needing_processing(
                clippings_dir, 'organize'
            )
            analysis['needs_sync'] = self.status_manager.get_papers_needing_processing(
                clippings_dir, 'sync'
            )
            analysis['needs_fetch'] = self.status_manager.get_papers_needing_processing(
                clippings_dir, 'fetch', include_failed=True
            )
            analysis['needs_parse'] = self.status_manager.get_papers_needing_processing(
                clippings_dir, 'parse', include_failed=True
            )
            
            # BibTeXにあるが状態管理に記録されていない論文も追加
            existing_papers = set()
            for papers_list in analysis.values():
                existing_papers.update(papers_list)
            
            missing_papers = set(all_papers) - existing_papers
            if missing_papers:
                # 新しい論文は全ステップが必要
                analysis['needs_organize'].extend(missing_papers)
                analysis['needs_sync'].extend(missing_papers)
                analysis['needs_fetch'].extend(missing_papers)
                analysis['needs_parse'].extend(missing_papers)
            
            total_work = sum(len(papers) for papers in analysis.values())
            self.logger.info(f"Status analysis completed: {total_work} processing tasks identified")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze paper status: {e}")
            raise ObsClippingsError(f"Failed to analyze paper status: {e}")
    
    def get_execution_plan(self, bibtex_file: str, clippings_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        実行計画を生成
        
        Args:
            bibtex_file: BibTeXファイルパス
            clippings_dir: Clippingsディレクトリパス（Noneの場合はbibtex_fileと同じディレクトリのClippings）
            
        Returns:
            Dict: 実行計画の詳細
        """
        try:
            # clippings_dirが指定されていない場合は推測
            if clippings_dir is None:
                clippings_dir = str(Path(bibtex_file).parent / "Clippings")
            
            analysis = self.analyze_paper_status(bibtex_file, clippings_dir)
            
            # BibTeX内の総論文数を取得
            entries = self.bibtex_parser.parse_file(bibtex_file)
            total_papers = len(entries)
            
            plan = {
                'total_papers': total_papers,
                'execution_steps': {}
            }
            
            # 各ステップの実行計画を作成
            for process_type in self.PROCESS_ORDER:
                papers_needed = analysis[f'needs_{process_type}']
                
                # 実行計画では全ての必要な論文を含める
                # 実際の実行時に依存関係をチェック
                eligible_papers = papers_needed
                
                plan['execution_steps'][process_type] = {
                    'papers': eligible_papers,
                    'count': len(eligible_papers),
                    'required': len(papers_needed) > 0
                }
            
            total_tasks = sum(step['count'] for step in plan['execution_steps'].values())
            self.logger.info(f"Execution plan generated: {total_tasks} tasks across {len(self.PROCESS_ORDER)} steps")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to generate execution plan: {e}")
            raise ObsClippingsError(f"Failed to generate execution plan: {e}")
    
    def execute_step_by_step(self, bibtex_file: str, clippings_dir: str, 
                           **options) -> Dict[str, Any]:
        """
        ステップ別に統合ワークフローを実行
        
        Args:
            bibtex_file: BibTeXファイルパス
            clippings_dir: Clippingsディレクトリパス
            **options: 実行オプション
            
        Returns:
            Dict: 実行結果
        """
        try:
            plan = self.get_execution_plan(bibtex_file, clippings_dir)
            
            results = {
                'overall_success': True,
                'steps_executed': [],
                'step_results': {},
                'total_papers_processed': 0
            }
            
            # 各ステップを順番に実行
            executed_steps = {}
            
            for process_type in self.PROCESS_ORDER:
                step_info = plan['execution_steps'][process_type]
                
                if step_info['count'] == 0:
                    self.logger.info(f"Skipping {process_type}: no papers need processing")
                    continue
                
                self.logger.info(
                    f"Executing {process_type} step for {step_info['count']} papers: "
                    f"{step_info['papers']}"
                )
                
                # ステップ実行
                step_success, step_result = self._execute_single_step(
                    process_type, bibtex_file, clippings_dir, step_info['papers'], **options
                )
                
                results['steps_executed'].append(process_type)
                results['step_results'][process_type] = step_result
                results['total_papers_processed'] += step_info['count']
                
                # 実行情報を保存（状態更新は後で一括）
                executed_steps[process_type] = {
                    'success': step_success,
                    'papers': step_info['papers']
                }
                
                if not step_success:
                    results['overall_success'] = False
                    if not options.get('continue_on_failure', False):
                        self.logger.warning(f"Stopping execution due to {process_type} failure")
                        break
            
            # 全ステップ完了後に状態を一括更新
            for process_type, step_info in executed_steps.items():
                if step_info['success']:
                    for paper in step_info['papers']:
                        self.status_manager.update_status(
                            clippings_dir, paper, process_type, ProcessStatus.COMPLETED
                        )
                else:
                    for paper in step_info['papers']:
                        self.status_manager.update_status(
                            clippings_dir, paper, process_type, ProcessStatus.FAILED
                        )
            
            if results['overall_success']:
                self.logger.info(
                    f"Enhanced integrated workflow completed successfully: "
                    f"{results['total_papers_processed']} papers processed"
                )
            else:
                self.logger.warning(
                    f"Enhanced integrated workflow completed with failures: "
                    f"{results['total_papers_processed']} papers processed"
                )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Enhanced integrated workflow failed: {e}")
            return {
                'overall_success': False,
                'error': str(e),
                'steps_executed': [],
                'step_results': {},
                'total_papers_processed': 0
            }
    
    def _execute_single_step(self, process_type: str, bibtex_file: str, 
                           clippings_dir: str, papers: List[str], 
                           **options) -> Tuple[bool, Dict[str, Any]]:
        """
        単一ステップの実行
        
        Args:
            process_type: 処理タイプ
            bibtex_file: BibTeXファイルパス  
            clippings_dir: Clippingsディレクトリパス
            papers: 対象論文リスト
            **options: 実行オプション
            
        Returns:
            Tuple[bool, Dict]: (成功/失敗, 結果詳細)
        """
        try:
            # WorkflowTypeへの変換
            workflow_type_map = {
                'organize': WorkflowType.FILE_ORGANIZATION,
                'sync': WorkflowType.SYNC_CHECK,
                'fetch': WorkflowType.CITATION_FETCHING,
                'parse': WorkflowType.CITATION_PARSER
            }
            
            if process_type not in workflow_type_map:
                raise ValueError(f"Unknown process type: {process_type}")
            
            workflow_type = workflow_type_map[process_type]
            
            # ステップ固有のオプション設定（全ワークフローで共通パラメータを設定）
            step_options = dict(options)
            step_options.update({
                'bibtex_file': bibtex_file,
                'clippings_dir': clippings_dir
            })
            
            if process_type == 'organize':
                step_options.update({
                    'target_papers': papers  # 対象論文を制限
                })
            elif process_type == 'sync':
                # syncは追加パラメータなし
                pass
            elif process_type == 'fetch':
                step_options.update({
                    'target_papers': papers,
                    'use_sync_integration': True
                })
            elif process_type == 'parse':
                # parse処理は論文単位では実行できないため、全体実行
                pass
            
            self.logger.info(f"Executing {process_type} with bibtex_file={bibtex_file}, clippings_dir={clippings_dir}")
            
            # ワークフロー実行
            success, result = self.workflow_manager.execute_workflow(
                workflow_type, **step_options
            )
            
            return success, result
            
        except Exception as e:
            self.logger.error(f"Failed to execute {process_type} step: {e}")
            return False, {'error': str(e)}
    
    def execute_with_status_tracking(self, bibtex_file: str, clippings_dir: str,
                                   target_papers: Optional[List[str]] = None,
                                   **options) -> Dict[str, Any]:
        """
        状態追跡付きで実行（特定の論文のみに対象を限定可能）
        
        Args:
            bibtex_file: BibTeXファイルパス
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト（Noneの場合は全論文）
            **options: 実行オプション
            
        Returns:
            Dict: 実行結果
        """
        try:
            if target_papers:
                self.logger.info(f"Executing workflow for specific papers: {target_papers}")
            else:
                self.logger.info("Executing workflow for all papers")
            
            # 対象論文の制限
            if target_papers:
                options['target_papers'] = target_papers
            
            result = self.execute_step_by_step(bibtex_file, clippings_dir, **options)
            
            return {
                'success': result['overall_success'],
                'results': result
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute with status tracking: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_force_regenerate(self, bibtex_file: str, clippings_dir: str, 
                               **options) -> Dict[str, Any]:
        """
        強制再生成モード：全ての状態をリセットしてから実行
        
        Args:
            bibtex_file: BibTeXファイルパス
            clippings_dir: Clippingsディレクトリパス
            **options: 実行オプション
            
        Returns:
            Dict: 実行結果
        """
        try:
            self.logger.info("Starting force regenerate mode: resetting all statuses")
            
            # 全ての状態をリセット
            reset_success = self.status_manager.reset_statuses(clippings_dir)
            if not reset_success:
                return {
                    'success': False,
                    'error': 'Failed to reset statuses'
                }
            
            # 通常の実行を行う
            result = self.execute_step_by_step(bibtex_file, clippings_dir, **options)
            
            self.logger.info("Force regenerate mode completed")
            return {
                'success': result['overall_success'],
                'results': result,
                'force_regenerate': True
            }
            
        except Exception as e:
            self.logger.error(f"Force regenerate mode failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_consistency(self, bibtex_file: str, clippings_dir: str) -> Dict[str, Any]:
        """
        状態の整合性をチェック
        
        Args:
            bibtex_file: BibTeXファイルパス
            clippings_dir: Clippingsディレクトリパス
            
        Returns:
            Dict: 整合性チェック結果
        """
        try:
            return self.status_manager.check_status_consistency(bibtex_file, clippings_dir)
            
        except Exception as e:
            self.logger.error(f"Consistency check failed: {e}")
            return {
                'error': str(e),
                'missing_directories': [],
                'orphaned_directories': [],
                'status_inconsistencies': []
            }
    
    def get_workflow_summary(self, clippings_dir: str) -> Dict[str, Any]:
        """
        ワークフロー全体のサマリーを取得
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            
        Returns:
            Dict: ワークフローサマリー
        """
        try:
            return self.status_manager.get_workflow_summary(clippings_dir)
            
        except Exception as e:
            self.logger.error(f"Failed to get workflow summary: {e}")
            return {'error': str(e)} 