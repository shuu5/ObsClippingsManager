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


from ..ai_citation_support import AIMappingWorkflow

# AI機能ワークフローのインポートを追加
from ..ai_tagging import TaggerWorkflow
from ..abstract_translation import TranslateAbstractWorkflow
from ..section_parsing import SectionParserWorkflow
from ..ochiai_format import OchiaiFormatWorkflow


class IntegratedWorkflow:
    """
    統合ワークフロー実行エンジン v3.0
    
    v3.0の核心機能：
    - workspace_pathベースの統一設定システム
    - YAMLヘッダーベースの状態管理
    - デフォルト引数なし実行
    - 効率的な重複処理回避
    """
    
    # 処理順序の定義（仕様書v3.1統合ワークフロー仕様に準拠）
    PROCESS_ORDER = ['organize', 'sync', 'fetch', 'section-parsing', 'ai-citation-support', 'enhanced-tagger', 'enhanced-translate', 'ochiai-format', 'final-sync']
    
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
        self.ai_citation_support_workflow = AIMappingWorkflow(config_manager, logger)
        
        # AI機能ワークフローの初期化
        self.section_parser_workflow = SectionParserWorkflow(config_manager, logger)
        self.tagger_workflow = TaggerWorkflow(config_manager, logger)
        self.translate_abstract_workflow = TranslateAbstractWorkflow(config_manager, logger)
        self.ochiai_format_workflow = OchiaiFormatWorkflow(config_manager, logger)
        
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
        対象論文の決定（エッジケース処理を含む）
        
        Args:
            paths: 解決済みパス辞書
            papers_option: 指定論文（カンマ区切り文字列）
            
        Returns:
            対象論文のcitation keyリスト（BibTeXとMarkdownの両方に存在する論文のみ）
        """
        try:
            # 整合性チェック実行
            consistency = self.status_manager.check_consistency(
                paths['bibtex_file'], 
                paths['clippings_dir']
            )
            
            # エッジケース検出時の警告表示
            if not consistency['consistent']:
                self._log_edge_cases(consistency['edge_case_details'])
            
            # BibTeXとMarkdownの両方に存在する論文のみを処理対象とする
            valid_papers = consistency['valid_papers']
            
            if papers_option:
                # 特定論文が指定されている場合、valid_papersとの交集合を取る
                specified_papers = [paper.strip() for paper in papers_option.split(',')]
                target_papers = [p for p in specified_papers if p in valid_papers]
                self.logger.info(f"Target papers specified: {specified_papers}")
                self.logger.info(f"Valid target papers (both BibTeX and Markdown exist): {target_papers}")
                return target_papers
            else:
                self.logger.info(f"Found {len(valid_papers)} valid papers (both BibTeX and Markdown exist)")
                return valid_papers
                
        except Exception as e:
            self.logger.error(f"Failed to determine target papers: {e}")
            return []
    
    def _log_edge_cases(self, edge_case_details: Dict[str, Any]) -> None:
        """
        エッジケースの詳細をログに出力
        
        Args:
            edge_case_details: エッジケースの詳細情報
        """
        missing_in_clippings = edge_case_details.get('missing_in_clippings', [])
        orphaned_in_clippings = edge_case_details.get('orphaned_in_clippings', [])
        
        if missing_in_clippings:
            self.logger.warning("Missing markdown files for:")
            for entry in missing_in_clippings:
                citation_key = entry.get('citation_key', 'unknown')
                doi = entry.get('doi', 'No DOI')
                self.logger.warning(f"  - {citation_key} (DOI: {doi})")
        
        if orphaned_in_clippings:
            self.logger.warning("Orphaned markdown files:")
            for entry in orphaned_in_clippings:
                file_path = entry.get('file_path', 'unknown')
                citation_key = entry.get('citation_key', 'unknown')
                self.logger.warning(f"  - {citation_key} ({file_path})")
    
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
            'organize': 2,   # 2秒/論文
            'sync': 1,       # 1秒/論文  
            'fetch': 15,     # 15秒/論文
            'ai-citation-support': 5,     # 5秒/論文
            'tagger': 5,      # 5秒/論文
            'translate_abstract': 5,       # 5秒/論文
            'final-sync': 1               # 1秒/論文
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
                
                # AI機能の条件チェック
                if step == 'tagger':
                    default_enabled = self.config_manager.get_config_value("ai_generation.tagger.enabled", True)
                    tagger_enabled = options.get('enable_tagger', default_enabled)
                    if not tagger_enabled:
                        plan['execution_plan'][step] = {
                            'status': 'skipped',
                            'reason': 'Tagger not enabled (use --enable-tagger to enable)'
                        }
                        continue
                
                if step == 'translate_abstract':
                    default_enabled = self.config_manager.get_config_value("ai_generation.translate_abstract.enabled", True)
                    translate_enabled = options.get('enable_translate_abstract', default_enabled)
                    if not translate_enabled:
                        plan['execution_plan'][step] = {
                            'status': 'skipped',
                            'reason': 'Abstract translation not enabled (use --enable-translate-abstract to enable)'
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
        4. ai-citation-support: AI理解支援統合
        5. tagger: タグ付け
        6. translate_abstract: 要約翻訳
        7. final-sync: 最終同期チェック
        
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
                    # optionsからpapersを除去して引数重複を回避
                    step_options = {k: v for k, v in options.items() if k != 'papers'}
                    step_result = self._execute_step(step, paths, papers_needing_processing, **step_options)
                
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
                # syncステップを拡張：同期チェック後、不足ディレクトリを自動作成
                success, result = self._execute_sync_step_with_directory_creation(paths, **step_options)
            elif step == 'fetch':
                success, result = self.fetch_workflow.execute(**step_options)
            elif step == 'ai-citation-support':
                success, result = self.ai_citation_support_workflow.execute(**step_options)
            elif step == 'section-parsing':
                success, result = self.section_parser_workflow.process_papers(
                    paths['clippings_dir'], papers, **step_options
                )
            elif step == 'enhanced-tagger':
                # ConfigManagerからデフォルト設定を取得し、コマンドラインオプションで上書き
                default_enabled = self.config_manager.get_config_value("ai_generation.tagger.enabled", True)
                # CLIオプションが明示的に設定されていない場合は、デフォルト設定を使用
                is_enabled = options.get('enable_tagger', default_enabled)
                
                if is_enabled:
                    tagger_result = self.tagger_workflow.process_papers(
                        clippings_dir=paths['clippings_dir'],
                        target_papers=papers
                    )
                    success = tagger_result.get('success', False)
                    result = tagger_result
                else:
                    self.logger.info("Enhanced tagger disabled, skipping")
                    return {
                        'success': True,
                        'processed_papers': papers,
                        'details': {'status': 'skipped', 'message': 'Enhanced tagger disabled by user'}
                    }
            elif step == 'enhanced-translate':
                # ConfigManagerからデフォルト設定を取得し、コマンドラインオプションで上書き
                default_enabled = self.config_manager.get_config_value("ai_generation.translate_abstract.enabled", True)
                # CLIオプションが明示的に設定されていない場合は、デフォルト設定を使用
                is_enabled = options.get('enable_translate_abstract', default_enabled)
                
                if is_enabled:
                    translate_result = self.translate_abstract_workflow.process_papers(
                        clippings_dir=paths['clippings_dir'],
                        target_papers=papers
                    )
                    success = translate_result.get('success', False)
                    result = translate_result
                else:
                    self.logger.info("Enhanced abstract translation disabled, skipping")
                    return {
                        'success': True,
                        'processed_papers': papers,
                        'details': {'status': 'skipped', 'message': 'Enhanced abstract translation disabled by user'}
                    }
            elif step == 'ochiai-format':
                # ConfigManagerからデフォルト設定を取得し、コマンドラインオプションで上書き
                default_enabled = self.config_manager.get_config_value("ai_generation.ochiai_format.enabled", True)
                # CLIオプションが明示的に設定されていない場合は、デフォルト設定を使用
                is_enabled = options.get('enable_ochiai_format', default_enabled)
                
                if is_enabled:
                    ochiai_result = self.ochiai_format_workflow.process_papers(
                        clippings_dir=paths['clippings_dir'],
                        target_papers=papers
                    )
                    success = ochiai_result.get('success', False)
                    result = ochiai_result
                else:
                    self.logger.info("Ochiai format disabled, skipping")
                    return {
                        'success': True,
                        'processed_papers': papers,
                        'details': {'status': 'skipped', 'message': 'Ochiai format disabled by user'}
                    }
            elif step == 'final-sync':
                # final-syncは通常のsyncと同じ処理を実行
                success, result = self.sync_workflow.execute(**step_options)
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
    
    def _execute_ai_citation_support_step(self, papers: List[str], paths: Dict[str, str], **options) -> Tuple[bool, Dict[str, Any]]:
        """
        AI理解支援統合ステップ実行
        
        Args:
            papers: 対象論文リスト
            paths: 解決済みパス辞書
            **options: 実行オプション
            
        Returns:
            (成功フラグ, 結果辞書)
        """
        try:
            self.logger.info(f"AI citation support step: processing {len(papers)} papers")
            
            # 各論文のMarkdownファイルとローカルreferences.bibファイルのペアを作成
            file_pairs = []
            for paper in papers:
                paper_dir = os.path.join(paths['clippings_dir'], paper)
                markdown_file = os.path.join(paper_dir, f"{paper}.md")
                local_references_bib = os.path.join(paper_dir, "references.bib")
                
                if os.path.exists(markdown_file):
                    # ローカルreferences.bibが存在するかチェック
                    if os.path.exists(local_references_bib):
                        file_pairs.append((markdown_file, local_references_bib))
                        self.logger.info(f"Using local references.bib for {paper}: {local_references_bib}")
                    else:
                        # ローカルreferences.bibが存在しない場合は、グローバルBibTeXファイルをコピー
                        try:
                            import shutil
                            shutil.copy2(paths['bibtex_file'], local_references_bib)
                            file_pairs.append((markdown_file, local_references_bib))
                            self.logger.info(f"Created local references.bib for {paper} from {paths['bibtex_file']}")
                        except Exception as e:
                            self.logger.warning(f"Failed to create local references.bib for {paper}: {e}")
                            # フォールバックとしてグローバルBibTeXファイルを使用
                            file_pairs.append((markdown_file, paths['bibtex_file']))
                            self.logger.info(f"Using global bibtex file for {paper}: {paths['bibtex_file']}")
                else:
                    self.logger.warning(f"Markdown file not found for {paper}: {markdown_file}")
            
            if not file_pairs:
                self.logger.warning("No valid markdown files found for processing")
                return False, {
                    'status': 'error',
                    'message': 'No valid markdown files found',
                    'processed_papers': 0,
                    'total_papers': len(papers)
                }
            
            # AIMappingWorkflowのバッチ実行
            # 仕様書に従い、AI用ファイル生成は行わない
            generate_ai_files = False
            batch_results = self.ai_citation_support_workflow.batch_execute_ai_mapping(
                file_pairs, generate_ai_files
            )
            
            # 結果の処理
            successful_papers = []
            failed_papers = []
            ai_files_generated = 0
            yaml_headers_updated = 0
            
            for markdown_file, result in batch_results.items():
                paper_name = os.path.basename(os.path.dirname(markdown_file))
                if result.success:
                    successful_papers.append(paper_name)
                    if result.output_file:  # AI用ファイルが生成された場合
                        ai_files_generated += 1
                    yaml_headers_updated += 1
                else:
                    failed_papers.append(paper_name)
                    self.logger.error(f"Failed to process {paper_name}: {result.error_message}")
            
            # 状態更新
            for paper in successful_papers:
                success = self.status_manager.update_status(
                    paths['clippings_dir'], paper, 'ai-citation-support', ProcessStatus.COMPLETED
                )
                if not success:
                    self.logger.warning(f"Failed to update ai-citation-support status for {paper}")
            
            for paper in failed_papers:
                self.status_manager.update_status(
                    paths['clippings_dir'], paper, 'ai-citation-support', ProcessStatus.FAILED
                )
            
            # 結果のまとめ
            overall_success = len(successful_papers) > 0
            result = {
                'status': 'success' if overall_success else 'error',
                'processed_papers': len(successful_papers),
                'failed_papers': len(failed_papers),
                'total_papers': len(papers),
                'ai_files_generated': ai_files_generated,
                'yaml_headers_updated': yaml_headers_updated,
                'message': f'AI citation support completed: {len(successful_papers)}/{len(papers)} papers processed successfully'
            }
            
            self.logger.info(f"AI citation support step completed: {len(successful_papers)}/{len(papers)} papers processed")
            return overall_success, result
                
        except Exception as e:
            self.logger.error(f"AI citation support step failed: {e}")
            
            # 例外の場合も失敗状態に更新
            for paper in papers:
                self.status_manager.update_status(
                    paths['clippings_dir'], paper, 'ai-citation-support', ProcessStatus.FAILED
                )
            
            return False, {
                'status': 'error',
                'message': str(e),
                'processed_papers': 0,
                'total_papers': len(papers)
            }

    def _execute_sync_step_with_directory_creation(self, paths: Dict[str, str], **options) -> Tuple[bool, Dict[str, Any]]:
        """
        syncステップを拡張：同期チェック後、不足ディレクトリを自動作成
        
        Args:
            paths: 解決済みパス辞書
            **options: 実行オプション
            
        Returns:
            (成功フラグ, 結果辞書)
        """
        try:
            self.logger.info("Executing sync step with directory creation")
            
            # 1. 標準のsyncステップ実行（同期チェック）
            success, sync_result = self.sync_workflow.execute(**options)
            
            if not success:
                self.logger.error("Sync step failed")
                return False, sync_result
            
            # 2. 不足している論文のディレクトリとMarkdownファイルを作成
            missing_papers = sync_result.get('missing_in_clippings', [])
            
            if missing_papers:
                self.logger.info(f"Creating directories and markdown files for {len(missing_papers)} missing papers")
                
                # SyncCheckWorkflowのcreate_missing_directoriesメソッドを使用
                creation_result = self.sync_workflow.create_missing_directories(missing_papers, options)
                
                # 結果をマージ
                sync_result['directory_creation'] = creation_result
                
                if creation_result['creation_errors']:
                    self.logger.warning(f"{len(creation_result['creation_errors'])} creation errors occurred")
                    # 部分的失敗として扱う
                    sync_result['status'] = 'partial_success'
                else:
                    self.logger.info(f"Successfully created {len(creation_result['created_directories'])} directories")
            else:
                self.logger.info("No missing directories to create")
                sync_result['directory_creation'] = {
                    'created_directories': [],
                    'created_files': [],
                    'creation_errors': []
                }
            
            self.logger.info("Extended sync step completed successfully")
            return True, sync_result
            
        except Exception as e:
            self.logger.error(f"Extended sync step execution failed: {e}")
            return False, {
                'status': 'error',
                'message': str(e),
                'error': str(e)
            } 