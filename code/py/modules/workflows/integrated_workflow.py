#!/usr/bin/env python3
"""
統合ワークフロー v3.0

ObsClippingsManager v3.0の中核機能である統合ワークフロー。
単一のrun-integratedコマンドで全機能を統合実行し、
workspace_pathベースの統一設定システムと状態管理による効率化を提供します。
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone

from ..shared.config_manager import ConfigManager
from ..shared.logger import IntegratedLogger
from ..shared.status_manager import StatusManager, ProcessStatus
from ..shared.bibtex_parser import BibTeXParser
from ..shared.exceptions import ObsClippingsError

# 既存ワークフローのインポート
from .organization_workflow import OrganizationWorkflow
from .sync_check_workflow import SyncCheckWorkflow
from .citation_workflow import CitationWorkflow
from .citation_parser_workflow import CitationParserWorkflow


class IntegratedWorkflow:
    """
    統合ワークフロー実行エンジン v3.0
    
    v3.0の核心機能：
    - workspace_pathベースの統一設定システム
    - YAMLヘッダーベースの状態管理
    - デフォルト引数なし実行
    - 効率的な重複処理回避
    """
    
    # 処理順序の定義
    PROCESS_ORDER = ['organize', 'sync', 'fetch', 'parse']
    
    # デフォルト設定
    DEFAULT_WORKSPACE_PATH = "/home/user/ManuscriptsManager"
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        IntegratedWorkflowの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ管理オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('IntegratedWorkflow')
        self.status_manager = StatusManager(config_manager, logger)
        self.bibtex_parser = BibTeXParser()
        
        # 各ワークフローの初期化
        self.organize_workflow = OrganizationWorkflow(config_manager, logger)
        self.sync_workflow = SyncCheckWorkflow(config_manager, logger)
        self.fetch_workflow = CitationWorkflow(config_manager, logger)
        self.parse_workflow = CitationParserWorkflow(config_manager, logger)
        
        self.logger.info("IntegratedWorkflow v3.0 initialized successfully")
    
    def _resolve_paths(self, **options) -> Dict[str, str]:
        """
        統一パス解決システム v3.0
        
        workspace_path一つから全てのパスを自動導出し、
        必要に応じて個別パスで上書き可能。
        
        Args:
            workspace_path: ワークスペースルートパス
            **kwargs: 個別指定パス (bibtex_file, clippings_dir等)
        
        Returns:
            解決済みパス辞書
        """
        # 1. workspace_pathの決定
        workspace_path = options.get('workspace_path')
        if not workspace_path:
            # 設定ファイルから取得を試行
            workspace_path = self.config_manager.get('common.workspace_path')
            if not workspace_path:
                # デフォルトワークスペースを使用
                workspace_path = self.DEFAULT_WORKSPACE_PATH
        
        # 2. 基本パスの自動導出
        paths = {
            'workspace_path': workspace_path,
            'bibtex_file': options.get('bibtex_file') or f"{workspace_path}/CurrentManuscript.bib",
            'clippings_dir': options.get('clippings_dir') or f"{workspace_path}/Clippings",
            'output_dir': options.get('output_dir') or f"{workspace_path}/Clippings"
        }
        
        self.logger.debug(f"Resolved paths: {paths}")
        return paths
    
    def _validate_configuration(self, paths: Dict[str, str]) -> Dict[str, Any]:
        """
        設定検証
        
        Args:
            paths: 解決済みパス辞書
            
        Returns:
            検証結果辞書
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # BibTeXファイルの存在確認
        bibtex_path = Path(paths['bibtex_file'])
        validation_result['bibtex_file_exists'] = bibtex_path.exists()
        if not validation_result['bibtex_file_exists']:
            validation_result['errors'].append(f"BibTeX file not found: {paths['bibtex_file']}")
        
        # Clippingsディレクトリの存在確認
        clippings_path = Path(paths['clippings_dir'])
        validation_result['clippings_dir_exists'] = clippings_path.exists()
        if not validation_result['clippings_dir_exists']:
            validation_result['warnings'].append(f"Clippings directory not found: {paths['clippings_dir']} (will be created)")
        
        # 全体の検証結果
        validation_result['valid'] = len(validation_result['errors']) == 0
        
        return validation_result
    
    def _determine_target_papers(self, paths: Dict[str, str], papers_option: Optional[str]) -> List[str]:
        """
        対象論文の決定
        
        Args:
            paths: 解決済みパス辞書
            papers_option: 指定論文（カンマ区切り文字列）
            
        Returns:
            対象論文のcitation keyリスト
        """
        if papers_option:
            # 特定論文が指定されている場合
            target_papers = [paper.strip() for paper in papers_option.split(',')]
            self.logger.info(f"Target papers specified: {target_papers}")
            return target_papers
        
        # BibTeXファイルから全論文を取得
        try:
            entries = self.bibtex_parser.parse_file(paths['bibtex_file'])
            all_papers = list(entries.keys())
            self.logger.info(f"Found {len(all_papers)} papers in BibTeX file")
            return all_papers
        except Exception as e:
            self.logger.error(f"Failed to parse BibTeX file: {e}")
            return []
    
    def _parse_skip_steps(self, skip_steps_option: str) -> List[str]:
        """
        スキップステップの解析
        
        Args:
            skip_steps_option: スキップステップ（カンマ区切り文字列）
            
        Returns:
            スキップステップリスト
        """
        if not skip_steps_option:
            return []
        
        skip_steps = [step.strip() for step in skip_steps_option.split(',')]
        
        # 有効なステップのみフィルタ
        valid_skip_steps = [step for step in skip_steps if step in self.PROCESS_ORDER]
        
        if len(valid_skip_steps) != len(skip_steps):
            invalid_steps = set(skip_steps) - set(valid_skip_steps)
            self.logger.warning(f"Invalid skip steps ignored: {invalid_steps}")
        
        return valid_skip_steps
    
    def _get_step_time_estimate(self, step: str) -> int:
        """
        ステップの処理時間見積もり（秒）
        
        Args:
            step: 処理ステップ名
            
        Returns:
            見積もり時間（秒）
        """
        estimates = {
            'organize': 5,   # 5秒/論文
            'sync': 2,       # 2秒/論文  
            'fetch': 30,     # 30秒/論文（API呼び出し）
            'parse': 10      # 10秒/論文
        }
        
        return estimates.get(step, 5)
    
    def execute(self, **options) -> Dict[str, Any]:
        """
        統合ワークフロー実行
        
        Args:
            workspace_path: ワークスペースパス
            papers: 対象論文リスト (カンマ区切り文字列)
            skip_steps: スキップステップリスト (カンマ区切り文字列)
            force_reprocess: 強制再処理フラグ
            show_plan: 実行計画表示フラグ
            dry_run: ドライランフラグ
            **kwargs: 個別設定パラメータ
        
        Returns:
            実行結果辞書
        """
        try:
            # 1. パス解決
            paths = self._resolve_paths(**options)
            
            # 2. 設定検証
            validation_result = self._validate_configuration(paths)
            if not validation_result['valid']:
                return {
                    'status': 'error',
                    'error': f"Configuration validation failed: {validation_result['errors']}",
                    'details': validation_result
                }
            
            # 3. 実行計画表示
            if options.get('show_plan'):
                return self.show_execution_plan(**options)
            
            # 4. 強制再処理モード
            if options.get('force_reprocess'):
                return self.force_reprocess(**options)
            
            # 5. 通常実行
            return self._execute_workflow(paths, **options)
            
        except Exception as e:
            self.logger.error(f"IntegratedWorkflow execution failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def show_execution_plan(self, **options) -> Dict[str, Any]:
        """
        実行計画表示（実行なし）
        
        Args:
            **options: 実行オプション
            
        Returns:
            実行計画辞書
        """
        try:
            paths = self._resolve_paths(**options)
            target_papers = self._determine_target_papers(paths, options.get('papers'))
            skip_steps = self._parse_skip_steps(options.get('skip_steps', ''))
            
            plan = {
                'workspace_path': paths['workspace_path'],
                'total_papers': len(target_papers),
                'target_papers': target_papers,
                'skip_steps': skip_steps,
                'execution_plan': {},
                'estimated_total_time': ""
            }
            
            total_estimated_seconds = 0
            
            # 各ステップの計画生成
            for step in self.PROCESS_ORDER:
                if step in skip_steps:
                    plan['execution_plan'][step] = {
                        'status': 'skipped',
                        'reason': 'User requested skip'
                    }
                    continue
                
                # 処理が必要な論文を特定
                papers_needing_processing = self.status_manager.get_papers_needing_processing(
                    paths['clippings_dir'], step, target_papers
                )
                
                papers_completed = [p for p in target_papers if p not in papers_needing_processing]
                
                estimated_seconds = len(papers_needing_processing) * self._get_step_time_estimate(step)
                total_estimated_seconds += estimated_seconds
                
                plan['execution_plan'][step] = {
                    'status': 'planned',
                    'papers_to_process': papers_needing_processing,
                    'papers_completed': papers_completed,
                    'papers_count': len(papers_needing_processing),
                    'estimated_time': f"{estimated_seconds // 60} minutes {estimated_seconds % 60} seconds"
                }
            
            plan['estimated_total_time'] = f"{total_estimated_seconds // 60} minutes {total_estimated_seconds % 60} seconds"
            
            return {
                'status': 'success',
                'plan': plan
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate execution plan: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def force_reprocess(self, **options) -> Dict[str, Any]:
        """
        強制再処理実行
        
        Args:
            **options: 実行オプション
            
        Returns:
            実行結果辞書
        """
        try:
            paths = self._resolve_paths(**options)
            target_papers = self._determine_target_papers(paths, options.get('papers'))
            
            # 状態リセット
            reset_success = self.status_manager.reset_statuses(
                paths['clippings_dir'], target_papers
            )
            
            if not reset_success:
                return {
                    'status': 'error',
                    'error': 'Failed to reset statuses for force reprocess'
                }
            
            result = {
                'status': 'success',
                'reset_count': len(target_papers),
                'reset_papers': target_papers
            }
            
            # ドライランでない場合は実際のワークフローを実行
            if not options.get('dry_run'):
                # force_reprocessフラグを削除してワークフローを実行
                workflow_options = {k: v for k, v in options.items() if k != 'force_reprocess'}
                workflow_result = self._execute_workflow(paths, **workflow_options)
                result.update(workflow_result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Force reprocess failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _execute_workflow(self, paths: Dict[str, str], **options) -> Dict[str, Any]:
        """
        実際のワークフロー実行
        
        処理順序:
        1. organize: ファイル整理
        2. sync: 同期チェック
        3. fetch: 引用文献取得
        4. parse: 引用文献解析
        
        Args:
            paths: 解決済みパス辞書
            **options: 実行オプション
            
        Returns:
            実行結果辞書
        """
        results = {
            'status': 'success',
            'completed_steps': [],
            'skipped_steps': [],
            'failed_steps': [],
            'total_papers': 0,
            'processed_papers': 0,
            'step_results': {}
        }
        
        try:
            # 対象論文決定
            target_papers = self._determine_target_papers(paths, options.get('papers'))
            results['total_papers'] = len(target_papers)
            
            # スキップステップ処理
            skip_steps = self._parse_skip_steps(options.get('skip_steps', ''))
            
            # ドライランモード
            is_dry_run = options.get('dry_run', False)
            
            # ステップ実行
            for step in self.PROCESS_ORDER:
                if step in skip_steps:
                    self.logger.info(f"Skipping step: {step}")
                    results['skipped_steps'].append(step)
                    continue
                
                # 処理が必要な論文を特定
                papers_needing_processing = self.status_manager.get_papers_needing_processing(
                    paths['clippings_dir'], step, target_papers
                )
                
                if not papers_needing_processing:
                    self.logger.info(f"Step {step}: All papers already processed")
                    results['skipped_steps'].append(step)
                    continue
                
                # ステップ実行
                self.logger.info(f"Executing step: {step} for {len(papers_needing_processing)} papers")
                
                if is_dry_run:
                    # ドライランモードでは実際の処理をスキップ
                    step_result = {
                        'success': True,
                        'processed_papers': papers_needing_processing,
                        'message': f'Dry run: would process {len(papers_needing_processing)} papers'
                    }
                else:
                    # 実際のステップ実行
                    step_result = self._execute_step(step, paths, papers_needing_processing, **options)
                
                results['step_results'][step] = step_result
                
                if step_result.get('success', False):
                    results['completed_steps'].append(step)
                    results['processed_papers'] += len(papers_needing_processing)
                else:
                    results['failed_steps'].append(step)
                    # 依存関係により後続ステップは実行しない
                    remaining_steps = self.PROCESS_ORDER[self.PROCESS_ORDER.index(step) + 1:]
                    results['skipped_steps'].extend(remaining_steps)
                    break
            
            # 全体の成功判定
            if results['failed_steps']:
                results['status'] = 'partial_failure' if results['completed_steps'] else 'failure'
            
            return results
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            results['status'] = 'error'
            results['error'] = str(e)
            return results
    
    def _execute_step(self, step: str, paths: Dict[str, str], papers: List[str], **options) -> Dict[str, Any]:
        """
        個別ステップの実行
        
        Args:
            step: 実行するステップ名
            paths: 解決済みパス辞書
            papers: 処理対象論文リスト
            **options: 実行オプション
            
        Returns:
            ステップ実行結果
        """
        try:
            # ステップ固有のオプション構築
            step_options = {
                'dry_run': options.get('dry_run', False),
                'auto_approve': options.get('auto_approve', False),
                **paths
            }
            
            # ステップに応じた実行
            if step == 'organize':
                success, result = self.organize_workflow.execute(**step_options)
            elif step == 'sync':
                success, result = self.sync_workflow.execute(**step_options)
            elif step == 'fetch':
                success, result = self.fetch_workflow.execute(**step_options)
            elif step == 'parse':
                # parseは個別ファイル処理が必要なため特別処理
                success, result = self._execute_parse_step(papers, paths, **step_options)
            else:
                raise ValueError(f"Unknown step: {step}")
            
            # 成功時は状態を更新
            if success and not options.get('dry_run', False):
                for paper in papers:
                    self.status_manager.update_status(
                        paths['clippings_dir'], paper, step, ProcessStatus.COMPLETED
                    )
            
            return {
                'success': success,
                'processed_papers': papers,
                'details': result
            }
            
        except Exception as e:
            self.logger.error(f"Step {step} execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_papers': []
            }
    
    def _execute_parse_step(self, papers: List[str], paths: Dict[str, str], **options) -> Tuple[bool, Dict[str, Any]]:
        """
        引用文献解析ステップの実行
        
        Args:
            papers: 処理対象論文リスト
            paths: 解決済みパス辞書
            **options: 実行オプション
            
        Returns:
            (成功フラグ, 実行結果)
        """
        # 現在は簡単な実装。実際の引用文献解析は将来実装
        self.logger.info(f"Parse step: processing {len(papers)} papers")
        
        return True, {
            'processed_papers': len(papers),
            'message': 'Citation parsing completed (placeholder implementation)'
        } 