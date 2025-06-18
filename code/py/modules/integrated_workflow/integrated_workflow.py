"""
IntegratedWorkflow - 統合ワークフロー実行システム

ObsClippingsManager v3.2.0の全機能を統合管理する中核クラス
10段階のワークフローステップを順次実行し、エラーハンドリング・バックアップ・状態管理を統合
"""

import time
import os
import glob
from pathlib import Path
from datetime import datetime

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.shared_modules.exceptions import (
    ObsClippingsManagerError, ProcessingError, APIError, ValidationError, ConfigurationError
)

# 個別ワークフローモジュールのインポート
from code.py.modules.file_organizer.file_organizer import FileOrganizer
from code.py.modules.sync_checker.sync_checker import SyncChecker
from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
from code.py.modules.section_parsing.section_parsing_workflow import SectionParsingWorkflow
from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
from code.py.modules.ai_tagging_translation.translate_workflow import TranslateWorkflow
from code.py.modules.ai_tagging_translation.ochiai_format_workflow import OchiaiFormatWorkflow
from code.py.modules.citation_pattern_normalizer.citation_pattern_normalizer_workflow import CitationPatternNormalizerWorkflow

# 状態管理・ユーティリティ
from code.py.modules.status_management_yaml.status_manager import StatusManager
from code.py.modules.shared_modules.bibtex_parser import BibTeXParser


class IntegratedWorkflow:
    """統合ワークフローの実行と管理を行う中核クラス"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger, ai_feature_controller=None):
        """統合ワークフローの初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ログシステムインスタンス
            ai_feature_controller: AI機能制御インスタンス（オプション）
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('IntegratedWorkflow')
        # IntegratedLoggerインスタンスを保存（個別モジュール初期化で使用）
        self._original_logger = logger
        
        # AI機能制御（デフォルトは全機能有効）
        if ai_feature_controller is None:
            # 相対インポートの代わりに、デフォルトのAI制御設定を直接実装
            self.ai_feature_controller = self._create_default_ai_controller()
        else:
            self.ai_feature_controller = ai_feature_controller
        
        # 状態管理システム（IntegratedLoggerをそのまま渡す）
        self.status_manager = StatusManager(config_manager, logger)
        # BibTeXParserには単一ロガーを渡す
        self.bibtex_parser = BibTeXParser(self.logger)
        
        # 各ワークフローモジュールを初期化（遅延初期化）
        self._workflow_modules = {}
        
        self.logger.info("IntegratedWorkflow initialized with AI feature control")
        self.logger.info(f"AI feature settings: {self.ai_feature_controller.get_summary()}")
    
    def execute(self, workspace_path: str, **options) -> dict:
        """統合ワークフローの実行
        
        Args:
            workspace_path: ワークスペースディレクトリパス
            **options: 実行オプション
                - force_reprocess: 強制再処理フラグ
                - target_papers: 処理対象論文リスト
                - show_plan: 実行計画表示のみ
                - dry_run: ドライラン実行
        
        Returns:
            dict: 実行結果
        """
        start_time = time.time()
        execution_results = {
            'status': 'running',
            'executed_steps': [],
            'skipped_steps': [],
            'failed_steps': [],
            'total_papers_processed': 0,
            'execution_time': 0,
            'edge_cases': {},
            'ai_features_used': self.ai_feature_controller.get_enabled_features()
        }
        
        try:
            self.logger.info(f"Starting integrated workflow execution in: {workspace_path}")
            
            # 1. 設定とパスの解決
            workspace_path = Path(workspace_path)
            bibtex_file = workspace_path / "CurrentManuscript.bib"
            clippings_dir = workspace_path / "Clippings"
            
            # 2. 初期エッジケース検出（参考情報のみ）
            initial_valid_papers, initial_edge_cases = self._detect_edge_cases_and_get_valid_papers(
                bibtex_file, clippings_dir
            )
            
            if options.get('show_plan'):
                self._show_execution_plan(initial_valid_papers, self.ai_feature_controller)
                return execution_results
            
            if options.get('dry_run'):
                self.logger.info("Dry-run mode: Simulating workflow execution")
                execution_results['status'] = 'completed'
                execution_results['processed'] = len(initial_valid_papers)
                execution_results['failed'] = 0
                execution_results['steps_completed'] = [step[0] for step in self._get_workflow_steps()]
                return execution_results
            
            # 3. 順次ワークフロー実行
            workflow_steps = self._get_workflow_steps()
            valid_papers = []  # organizeステップ後に更新される
            
            # 各ステップを順次実行
            for step_name, workflow_method in workflow_steps:
                step_start_time = time.time()
                
                try:
                    self.logger.info(f"Starting step: {step_name}")
                    
                    # 進捗コールバック呼び出し
                    if 'progress_callback' in options:
                        options['progress_callback'](step_name, 'started')
                    
                    # ステップ実行
                    step_result = workflow_method(workspace_path, valid_papers, **options)
                    
                    # organizeステップ完了後、有効論文リストを更新
                    if step_name == 'organize':
                        self.logger.info("Re-detecting valid papers after organize step")
                        valid_papers, edge_cases = self._detect_edge_cases_and_get_valid_papers(
                            bibtex_file, clippings_dir
                        )
                        execution_results['edge_cases'] = edge_cases
                        execution_results['total_papers_processed'] = len(valid_papers)
                        self.logger.info(f"Updated valid papers list: {len(valid_papers)} papers found")
                    
                    step_execution_time = time.time() - step_start_time
                    execution_results['executed_steps'].append({
                        'name': step_name,
                        'status': 'completed',
                        'execution_time': step_execution_time,
                        'result': step_result
                    })
                    
                    self.logger.info(f"Step {step_name} completed successfully ({step_execution_time:.2f}s)")
                    
                    # 進捗コールバック呼び出し
                    if 'progress_callback' in options:
                        options['progress_callback'](step_name, 'completed')
                    
                except (ProcessingError, APIError, ValidationError) as e:
                    # 既知のエラー：標準的な処理
                    self.logger.error(f"Step {step_name} failed with known error: {e}")
                    
                    step_execution_time = time.time() - step_start_time
                    execution_results['failed_steps'].append({
                        'name': step_name,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'error_code': getattr(e, 'error_code', None),
                        'execution_time': step_execution_time
                    })
                    
                    # 進捗コールバック呼び出し
                    if 'progress_callback' in options:
                        options['progress_callback'](step_name, 'failed')
                    
                    # 重要でないエラーは継続、重要なエラーは中断
                    if isinstance(e, (APIError, ConfigurationError)):
                        self.logger.error(f"Critical error in {step_name}, stopping workflow")
                        break  # 重要なエラーで中断
                    
                except Exception as e:
                    # 未知のエラー：標準例外に変換
                    step_execution_time = time.time() - step_start_time
                    error = ProcessingError(
                        f"Unexpected error in step {step_name}: {str(e)}",
                        error_code="UNEXPECTED_STEP_ERROR",
                        context={"step": step_name, "execution_time": step_execution_time}
                    )
                    self.logger.error(f"Step {step_name} failed with unexpected error: {error}")
                    
                    execution_results['failed_steps'].append({
                        'name': step_name,
                        'error': str(error),
                        'error_type': 'ProcessingError',
                        'error_code': error.error_code,
                        'execution_time': step_execution_time
                    })
                    break
            
            execution_results['status'] = 'completed'
            self.logger.info("Integrated workflow execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"Integrated workflow failed: {e}")
            execution_results['status'] = 'failed'
            execution_results['error'] = str(e)
        
        finally:
            execution_results['execution_time'] = time.time() - start_time
            
        return execution_results
    
    def _get_workflow_steps(self) -> list:
        """ワークフローステップの定義と順序を返す"""
        workflow_steps = [
            ('organize', self._execute_organize),
            ('sync', self._execute_sync),
            ('fetch', self._execute_fetch),
            ('section_parsing', self._execute_section_parsing),
            ('ai_citation_support', self._execute_ai_citation_support),
        ]
        
        # AI機能ステップ（制御設定に応じて追加）
        if self.ai_feature_controller.is_tagger_enabled():
            workflow_steps.append(('enhanced-tagger', self._execute_tagger))
        
        if self.ai_feature_controller.is_translate_enabled():
            workflow_steps.append(('enhanced-translate', self._execute_translate))
        
        if self.ai_feature_controller.is_ochiai_enabled():
            workflow_steps.append(('ochiai-format', self._execute_ochiai))
        
        # 非AI機能ステップ
        workflow_steps.extend([
            ('citation_pattern_normalizer', self._execute_citation_normalizer),
            ('final-sync', self._execute_final_sync)
        ])
        
        return workflow_steps
    
    def _detect_edge_cases_and_get_valid_papers(self, bibtex_file: Path, clippings_dir: Path) -> tuple:
        """エッジケース検出と有効論文リスト取得"""
        try:
            # BibTeXエントリー取得
            bibtex_entries = self.bibtex_parser.parse_file(str(bibtex_file))
            bibtex_keys = set(bibtex_entries.keys())
            self.logger.info(f"BibTeX keys found: {bibtex_keys}")
            
            # Clippingsディレクトリの論文取得
            clippings_keys = set()
            if clippings_dir.exists():
                for md_file in clippings_dir.rglob("*.md"):
                    citation_key = self._extract_citation_key_from_path(md_file)
                    self.logger.debug(f"MD file: {md_file}, extracted key: {citation_key}")
                    if citation_key:
                        clippings_keys.add(citation_key)
            
            self.logger.info(f"Clippings keys found: {clippings_keys}")
            
            # エッジケース検出
            missing_in_clippings = bibtex_keys - clippings_keys
            orphaned_in_clippings = clippings_keys - bibtex_keys
            valid_papers = bibtex_keys.intersection(clippings_keys)
            
            edge_cases = {
                'missing_in_clippings': list(missing_in_clippings),
                'orphaned_in_clippings': list(orphaned_in_clippings)
            }
            
            self.logger.info(f"Edge case analysis: {len(valid_papers)} valid papers, "
                           f"{len(missing_in_clippings)} missing, {len(orphaned_in_clippings)} orphaned")
            self.logger.info(f"Valid papers: {list(valid_papers)}")
            
            return list(valid_papers), edge_cases
            
        except Exception as e:
            self.logger.error(f"Failed to detect edge cases: {e}")
            return [], {'missing_in_clippings': [], 'orphaned_in_clippings': []}
    
    def _extract_citation_key_from_path(self, md_file: Path) -> str:
        """MarkdownファイルパスからCitation keyを抽出"""
        # ディレクトリ名をcitation_keyとして使用
        if md_file.parent.name != "Clippings":
            return md_file.parent.name
        return None
    
    def _show_execution_plan(self, valid_papers: list, ai_controller) -> None:
        """実行計画を表示"""
        self.logger.info("=== Execution Plan ===")
        self.logger.info(f"Target papers: {len(valid_papers)}")
        self.logger.info(f"AI features: {ai_controller.get_summary()}")
        
        steps = self._get_workflow_steps()
        self.logger.info("Workflow steps:")
        for i, (step_name, _) in enumerate(steps, 1):
            self.logger.info(f"  {i:2d}. {step_name}")
    
    # 個別ステップ実行メソッド
    def _execute_organize(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """organize機能実行"""
        organizer = self._get_workflow_module('organize', FileOrganizer)
        bibtex_file = workspace_path / "CurrentManuscript.bib"
        clippings_dir = workspace_path / "Clippings"
        
        result = organizer.organize_workspace(
            str(workspace_path), str(bibtex_file), str(clippings_dir)
        )
        return result
    
    def _execute_sync(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """sync機能実行"""
        sync_checker = self._get_workflow_module('sync', SyncChecker)
        bibtex_file = workspace_path / "CurrentManuscript.bib"
        clippings_dir = workspace_path / "Clippings"
        
        result = sync_checker.check_workspace_consistency(
            str(workspace_path), str(bibtex_file), str(clippings_dir)
        )
        return result
    
    def _execute_fetch(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """fetch機能実行"""
        citation_fetcher = self._get_workflow_module('fetch', CitationFetcherWorkflow)
        clippings_dir = workspace_path / "Clippings"
        
        citation_fetcher.process_items(str(clippings_dir), target_papers)
        return {'status': 'completed', 'papers_processed': len(target_papers)}
    
    def _execute_section_parsing(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """section_parsing機能実行"""
        section_parser = self._get_workflow_module('section_parsing', SectionParsingWorkflow)
        clippings_dir = workspace_path / "Clippings"
        
        result = section_parser.process_papers(str(clippings_dir), target_papers)
        return result
    
    def _execute_ai_citation_support(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """ai_citation_support機能実行"""
        ai_citation_support = self._get_workflow_module('ai_citation_support', AICitationSupportWorkflow)
        clippings_dir = workspace_path / "Clippings"
        
        ai_citation_support.process_items(str(clippings_dir), target_papers)
        return {'status': 'completed', 'papers_processed': len(target_papers)}
    
    def _execute_tagger(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """enhanced-tagger機能実行"""
        tagger_workflow = self._get_workflow_module('tagger', TaggerWorkflow)
        clippings_dir = workspace_path / "Clippings"
        
        result = tagger_workflow.process_items(str(clippings_dir), target_papers)
        return result
    
    def _execute_translate(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """enhanced-translate機能実行"""
        translate_workflow = self._get_workflow_module('translate', TranslateWorkflow)
        
        result = translate_workflow.process_items(str(workspace_path), target_papers)
        return result
    
    def _execute_ochiai(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """ochiai-format機能実行"""
        ochiai_workflow = self._get_workflow_module('ochiai', OchiaiFormatWorkflow)
        clippings_dir = workspace_path / "Clippings"
        
        result = ochiai_workflow.process_items(str(clippings_dir), target_papers)
        return result
    
    def _execute_citation_normalizer(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """citation_pattern_normalizer機能実行"""
        citation_normalizer = self._get_workflow_module('citation_normalizer', CitationPatternNormalizerWorkflow)
        clippings_dir = workspace_path / "Clippings"
        
        result = citation_normalizer.process_items(str(clippings_dir), target_papers)
        return result
    
    def _execute_final_sync(self, workspace_path: Path, target_papers: list, **options) -> dict:
        """final-sync機能実行（syncを再実行）"""
        sync_checker = self._get_workflow_module('final_sync', SyncChecker)
        bibtex_file = workspace_path / "CurrentManuscript.bib"
        clippings_dir = workspace_path / "Clippings"
        
        result = sync_checker.check_workspace_consistency(
            str(workspace_path), str(bibtex_file), str(clippings_dir)
        )
        return result
    
    def _get_workflow_module(self, module_name: str, module_class):
        """ワークフローモジュールの遅延初期化"""
        if module_name not in self._workflow_modules:
            # CitationFetcherWorkflowは特別処理が必要
            if module_class.__name__ == 'CitationFetcherWorkflow':
                # IntegratedLoggerインスタンスを渡す
                logger_instance = self._original_logger
            else:
                # その他のモジュールは通常のロガーを渡す
                logger_instance = self._original_logger
                
            self._workflow_modules[module_name] = module_class(
                self.config_manager, 
                logger_instance
            )
        return self._workflow_modules[module_name]
    
    def _create_default_ai_controller(self):
        """デフォルトAI機能制御の作成"""
        class DefaultAIController:
            def get_summary(self):
                return "AI機能: すべて有効（デフォルト動作）"
            
            def get_enabled_features(self):
                return ['tagger', 'translate', 'ochiai']
            
            def is_tagger_enabled(self):
                return True
            
            def is_translate_enabled(self):
                return True
            
            def is_ochiai_enabled(self):
                return True
        
        return DefaultAIController()