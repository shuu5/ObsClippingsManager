"""
シンプル統合テストランナー

現在実装中のintegrated_workflowをテストデータで実際に実行して動作確認する
最小限の機能に特化した統合テストシステム
"""

import shutil
import yaml
from datetime import datetime
from pathlib import Path


class SimpleIntegratedTestRunner:
    """シンプル統合テストランナー"""
    
    def __init__(self, config_manager, integrated_logger, ai_controller=None):
        self.config_manager = config_manager
        self.integrated_logger = integrated_logger
        self.logger = integrated_logger.get_logger("integrated_test")
        self.test_data_path = Path("code/test_data_master")
        self.output_path = Path("test_output/latest")
        # AI機能制御インスタンス（デフォルトは全機能有効）
        if ai_controller is None:
            from code.integrated_test.ai_feature_controller import get_default_ai_controller
            self.ai_controller = get_default_ai_controller()
        else:
            self.ai_controller = ai_controller
    
    def run_test(self):
        """シンプルな統合テスト実行"""
        try:
            # 1. 出力ディレクトリ準備
            self._prepare_output_directory()
            
            # 2. テストデータをワークスペースにコピー
            self._copy_test_data_to_workspace()
            
            # 3. 処理前データをバックアップ
            self._backup_original_data()
            
            # 4. integrated_workflow実行（その場処理）
            result = self._run_integrated_workflow()
            
            # 5. 基本チェック
            check_result = self._basic_check()
            
            # 6. 結果保存
            self._save_test_result(result, check_result)
            
            self.logger.info("統合テスト完了")
            return True
            
        except Exception as e:
            self.logger.error(f"統合テスト失敗: {e}")
            self._save_error_result(str(e))
            return False
    
    def _prepare_output_directory(self):
        """出力ディレクトリ準備"""
        if self.output_path.exists():
            shutil.rmtree(self.output_path)
        
        self.output_path.mkdir(parents=True, exist_ok=True)
        (self.output_path / "workspace").mkdir(exist_ok=True)
        (self.output_path / "backup").mkdir(exist_ok=True)
    
    def _copy_test_data_to_workspace(self):
        """テストデータをワークスペースにコピー"""
        workspace_path = self.output_path / "workspace"
        
        # CurrentManuscript.bibをコピー
        bib_source = self.test_data_path / "CurrentManuscript.bib"
        if bib_source.exists():
            shutil.copy2(bib_source, workspace_path / "CurrentManuscript.bib")
        
        # Clippingsディレクトリをコピー
        clippings_source = self.test_data_path / "Clippings"
        if clippings_source.exists():
            shutil.copytree(clippings_source, workspace_path / "Clippings")
    
    def _backup_original_data(self):
        """処理前データをバックアップ"""
        workspace_path = self.output_path / "workspace"
        backup_path = self.output_path / "backup"
        
        # ワークスペースの内容をバックアップ
        shutil.copytree(workspace_path, backup_path, dirs_exist_ok=True)
    
    def _run_integrated_workflow(self):
        """integrated_workflowを実行（AI機能制御対応）"""
        workspace_path = self.output_path / "workspace"
        
        # AI機能設定をログ出力
        self.logger.info(f"統合テスト実行設定: {self.ai_controller.get_summary()}")
        
        try:
            # IntegratedWorkflowクラスが実装されている場合は、それを使用
            from code.py.modules.integrated_workflow.integrated_workflow import IntegratedWorkflow
            
            workflow = IntegratedWorkflow(
                config_manager=self.config_manager, 
                logger=self.logger,
                ai_feature_controller=self.ai_controller  # AI機能制御を渡す
            )
            result = workflow.execute(workspace_path)
            
            return {
                'status': 'success',
                'modules_executed': result.get('modules_executed', []),
                'files_processed': result.get('files_processed', 0),
                'ai_features_used': result.get('ai_features_used', [])
            }
            
        except ImportError:
            # IntegratedWorkflowクラスが未実装の場合は、現在実装済みの機能を順次実行
            modules_executed = []
            files_processed = 0
            
            # 現在実装済みの機能を順次実行
            try:
                # organize機能
                self.logger.info("Attempting to import FileOrganizer")
                from code.py.modules.file_organizer.file_organizer import FileOrganizer
                self.logger.info("FileOrganizer imported successfully")
                
                organizer = FileOrganizer(self.config_manager, self.integrated_logger)
                self.logger.info("FileOrganizer initialized")
                
                # DOIマッチングベースのorganize処理
                bibtex_file = workspace_path / "CurrentManuscript.bib"
                clippings_dir = workspace_path / "Clippings"
                
                self.logger.info(f"Checking files: bibtex={bibtex_file.exists()}, clippings={clippings_dir.exists()}")
                
                if bibtex_file.exists() and clippings_dir.exists():
                    self.logger.info("Starting organize_workspace")
                    result = organizer.organize_workspace(
                        str(workspace_path), 
                        str(bibtex_file), 
                        str(clippings_dir)
                    )
                    self.logger.info(f"organize_workspace completed: {result}")
                    modules_executed.append('file_organizer')
                    files_processed = result.get('processed_papers', 0)
                    
                    # エッジケース情報をログ出力
                    skipped = result.get('skipped_papers', {})
                    if skipped.get('missing_in_clippings'):
                        self.integrated_logger.get_logger('integrated_test').warning(
                            f"Missing markdown files: {len(skipped['missing_in_clippings'])}"
                        )
                    if skipped.get('orphaned_in_clippings'):
                        self.integrated_logger.get_logger('integrated_test').warning(
                            f"Orphaned markdown files: {len(skipped['orphaned_in_clippings'])}"
                        )
                else:
                    self.logger.warning(f"Required files missing: bibtex={bibtex_file.exists()}, clippings={clippings_dir.exists()}")
            except ImportError as e:
                self.logger.warning(f"ImportError: {e}")
            except Exception as e:
                self.logger.error(f"Error in organize processing: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            # 他の実装済み機能があれば順次追加
            # sync機能
            try:
                self.logger.info("Attempting to import SyncChecker")
                from code.py.modules.sync_checker.sync_checker import SyncChecker
                self.logger.info("SyncChecker imported successfully")
                
                sync_checker = SyncChecker(self.config_manager, self.integrated_logger)
                self.logger.info("SyncChecker initialized")
                
                self.logger.info("Starting sync consistency check")
                # 必要なファイルパスを定義
                bibtex_file = workspace_path / "CurrentManuscript.bib"
                clippings_dir = workspace_path / "Clippings"
                
                sync_result = sync_checker.check_workspace_consistency(
                    str(workspace_path), 
                    str(bibtex_file), 
                    str(clippings_dir)
                )
                self.logger.info(f"Sync consistency check completed: {sync_result.get('consistency_status', 'unknown')}")
                
                if sync_result.get('consistency_status') == 'issues_detected':
                    # DOIリンク表示
                    missing_files = sync_result.get('missing_markdown_files', [])
                    orphaned_files = sync_result.get('orphaned_markdown_files', [])
                    
                    if missing_files or orphaned_files:
                        self.logger.info(f"Displaying DOI links for {len(missing_files)} missing and {len(orphaned_files)} orphaned files")
                        sync_checker.display_doi_links(missing_files, orphaned_files)
                    
                    # auto-fix試行
                    self.logger.info("Attempting auto-fix for detected issues")
                    fix_result = sync_checker.auto_fix_minor_inconsistencies(sync_result)
                    self.logger.info(f"Auto-fix completed: {len(fix_result.get('corrections_applied', []))} corrections applied")
                
                modules_executed.append('sync_checker')
                
            except ImportError as e:
                self.logger.warning(f"SyncChecker ImportError: {e}")
            except Exception as e:
                self.logger.error(f"Error in sync processing: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            # fetch機能
            try:
                self.logger.info("Attempting to import CitationFetcherWorkflow")
                from code.py.modules.citation_fetcher.citation_fetcher_workflow import CitationFetcherWorkflow
                self.logger.info("CitationFetcherWorkflow imported successfully")
                
                citation_fetcher = CitationFetcherWorkflow(self.config_manager, self.integrated_logger)
                self.logger.info("CitationFetcherWorkflow initialized")
                
                self.logger.info("Starting citation fetcher workflow")
                # 処理対象のmarkdownファイルを取得してfetch処理実行
                # clippings_dir内のorganized markdownファイルを対象とする
                clippings_dir = workspace_path / "Clippings"
                if clippings_dir.exists():
                    # サブディレクトリ内のmarkdownファイルを対象とする
                    processed_count = 0
                    for subdir in clippings_dir.iterdir():
                        if subdir.is_dir():
                            for md_file in subdir.glob("*.md"):
                                try:
                                    self.logger.debug(f"Processing fetch for: {md_file}")
                                    
                                    # DOI抽出
                                    doi = citation_fetcher.extract_doi_from_paper(str(md_file))
                                    if doi:
                                        self.logger.debug(f"Found DOI: {doi} for {md_file.name}")
                                        
                                        # 引用文献取得（フォールバック戦略）
                                        citation_data = citation_fetcher.fetch_citations_with_fallback(doi)
                                        
                                        if citation_data:
                                            # references.bib生成
                                            references_bib_path = citation_fetcher.generate_references_bib(str(md_file), citation_data)
                                            
                                            # YAMLヘッダー更新
                                            citation_fetcher.update_yaml_with_fetch_results(str(md_file), citation_data, references_bib_path)
                                            
                                            processed_count += 1
                                            self.logger.info(f"Successfully processed fetch for: {md_file.name}")
                                        else:
                                            self.logger.warning(f"Failed to fetch citations for {md_file.name}")
                                    else:
                                        self.logger.warning(f"No DOI found for {md_file.name}")
                                        
                                except Exception as e:
                                    self.logger.error(f"Error processing {md_file}: {e}")
                    
                    self.logger.info(f"Citation fetcher workflow completed: {processed_count} papers processed")
                    modules_executed.append('citation_fetcher')
                    
                else:
                    self.logger.warning("Clippings directory not found for fetch processing")
                    
            except ImportError as e:
                self.logger.warning(f"CitationFetcherWorkflow ImportError: {e}")
            except Exception as e:
                self.logger.error(f"Error in fetch processing: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            # section_parsing機能
            try:
                self.logger.info("Attempting to import SectionParsingWorkflow")
                from code.py.modules.section_parsing.section_parsing_workflow import SectionParsingWorkflow
                self.logger.info("SectionParsingWorkflow imported successfully")
                
                section_parser = SectionParsingWorkflow(self.config_manager, self.integrated_logger)
                self.logger.info("SectionParsingWorkflow initialized")
                
                self.logger.info("Starting section parsing workflow")
                # 処理対象のmarkdownファイルを取得してsection_parsing処理実行
                clippings_dir = workspace_path / "Clippings"
                if clippings_dir.exists():
                    # サブディレクトリ内のmarkdownファイルを対象とする
                    target_papers = []
                    for subdir in clippings_dir.iterdir():
                        if subdir.is_dir():
                            # サブディレクトリ名をtarget_papersに追加
                            target_papers.append(subdir.name)
                    
                    if target_papers:
                        self.logger.info(f"Processing section parsing for {len(target_papers)} papers")
                        section_result = section_parser.process_papers(str(clippings_dir), target_papers)
                        
                        processed_papers = section_result.get('processed_papers', 0)
                        total_sections = section_result.get('total_sections_found', 0)
                        section_types = section_result.get('section_types_found', [])
                        
                        self.logger.info(f"Section parsing completed: {processed_papers} papers processed, "
                                       f"{total_sections} total sections found")
                        self.logger.info(f"Section types found: {', '.join(section_types)}")
                        
                        modules_executed.append('section_parsing')
                    else:
                        self.logger.warning("No organized papers found for section parsing")
                        
                else:
                    self.logger.warning("Clippings directory not found for section parsing")
                    
            except ImportError as e:
                self.logger.warning(f"SectionParsingWorkflow ImportError: {e}")
            except Exception as e:
                self.logger.error(f"Error in section_parsing processing: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            # ai_citation_support機能
            try:
                self.logger.info("Attempting to import AICitationSupportWorkflow")
                from code.py.modules.ai_citation_support.ai_citation_support_workflow import AICitationSupportWorkflow
                self.logger.info("AICitationSupportWorkflow imported successfully")
                
                ai_citation_support = AICitationSupportWorkflow(self.config_manager, self.integrated_logger)
                self.logger.info("AICitationSupportWorkflow initialized")
                
                self.logger.info("Starting AI citation support workflow")
                # 処理対象のmarkdownファイルを取得してai_citation_support処理実行
                clippings_dir = workspace_path / "Clippings"
                if clippings_dir.exists():
                    # サブディレクトリ内のmarkdownファイルを対象とする
                    target_papers = []
                    for subdir in clippings_dir.iterdir():
                        if subdir.is_dir():
                            # サブディレクトリ名をtarget_papersに追加
                            target_papers.append(subdir.name)
                    
                    if target_papers:
                        self.logger.info(f"Processing AI citation support for {len(target_papers)} papers")
                        ai_citation_support.process_items(str(clippings_dir), target_papers)
                        modules_executed.append('ai_citation_support')
                        self.logger.info("AI citation support workflow completed")
                    else:
                        self.logger.warning("No organized papers found for AI citation support")
                else:
                    self.logger.warning("Clippings directory not found for AI citation support")
                    
            except ImportError as e:
                self.logger.warning(f"AICitationSupportWorkflow ImportError: {e}")
            except Exception as e:
                self.logger.error(f"Error in ai_citation_support processing: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            # enhanced-tagger機能 (ai_tagging_translation) - AI機能制御対応
            if self.ai_controller.is_tagger_enabled():
                try:
                    self.logger.info("Attempting to import TaggerWorkflow")
                    from code.py.modules.ai_tagging_translation.tagger_workflow import TaggerWorkflow
                    self.logger.info("TaggerWorkflow imported successfully")
                    
                    tagger_workflow = TaggerWorkflow(self.config_manager, self.integrated_logger)
                    self.logger.info("TaggerWorkflow initialized")
                    
                    self.logger.info("Starting enhanced-tagger workflow")
                    # 処理対象のmarkdownファイルを取得してenhanced-tagger処理実行
                    clippings_dir = workspace_path / "Clippings"
                    if clippings_dir.exists():
                        # サブディレクトリ内のmarkdownファイルを対象とする
                        target_papers = []
                        for subdir in clippings_dir.iterdir():
                            if subdir.is_dir():
                                # サブディレクトリ名をtarget_papersに追加
                                target_papers.append(subdir.name)
                        
                        if target_papers:
                            self.logger.info(f"Processing enhanced-tagger for {len(target_papers)} papers")
                            tagger_result = tagger_workflow.process_items(str(clippings_dir), target_papers)
                            
                            processed_papers = tagger_result.get('processed_papers', 0)
                            skipped_papers = tagger_result.get('skipped_papers', 0)
                            failed_papers = tagger_result.get('failed_papers', 0)
                            
                            self.logger.info(f"Enhanced-tagger completed: {processed_papers} papers processed, "
                                           f"{skipped_papers} skipped, {failed_papers} failed")
                            
                            modules_executed.append('enhanced-tagger')
                        else:
                            self.logger.warning("No organized papers found for enhanced-tagger")
                    else:
                        self.logger.warning("Clippings directory not found for enhanced-tagger")
                        
                except ImportError as e:
                    self.logger.warning(f"TaggerWorkflow ImportError: {e}")
                except Exception as e:
                    self.logger.error(f"Error in enhanced-tagger processing: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.info("Enhanced-tagger機能は無効化されています（API利用料金削減）")
            
            # enhanced-translate機能 - AI機能制御対応
            if self.ai_controller.is_translate_enabled():
                try:
                    self.logger.info("Attempting to import TranslateWorkflow")
                    from code.py.modules.ai_tagging_translation.translate_workflow import TranslateWorkflow
                    self.logger.info("TranslateWorkflow imported successfully")
                    
                    translate_workflow = TranslateWorkflow(self.config_manager, self.integrated_logger)
                    self.logger.info("TranslateWorkflow initialized")
                    
                    self.logger.info("Starting enhanced-translate workflow")
                    translate_result = translate_workflow.process_items(str(workspace_path), target_papers)
                    self.logger.info(f"Enhanced-translate processing completed: {translate_result}")
                    modules_executed.append('enhanced-translate')
                    
                except ImportError as e:
                    self.logger.warning(f"TranslateWorkflow ImportError: {e}")
                except Exception as e:
                    self.logger.error(f"Error in enhanced-translate processing: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.info("Enhanced-translate機能は無効化されています（API利用料金削減）")
            
            # ochiai-format機能 - AI機能制御対応（未実装）
            if self.ai_controller.is_ochiai_enabled():
                try:
                    self.logger.info("Attempting to import OchiaiFormatWorkflow")
                    from code.py.modules.ai_tagging_translation.ochiai_format_workflow import OchiaiFormatWorkflow
                    self.logger.info("OchiaiFormatWorkflow imported successfully")
                    
                    ochiai_workflow = OchiaiFormatWorkflow(self.config_manager, self.integrated_logger)
                    self.logger.info("OchiaiFormatWorkflow initialized")
                    
                    self.logger.info("Starting ochiai-format workflow")
                    # 処理対象のmarkdownファイルを取得してochiai-format処理実行
                    clippings_dir = workspace_path / "Clippings"
                    if clippings_dir.exists():
                        # サブディレクトリ内のmarkdownファイルを対象とする
                        target_papers = []
                        for subdir in clippings_dir.iterdir():
                            if subdir.is_dir():
                                # サブディレクトリ名をtarget_papersに追加
                                target_papers.append(subdir.name)
                        
                        if target_papers:
                            self.logger.info(f"Processing ochiai-format for {len(target_papers)} papers")
                            ochiai_result = ochiai_workflow.process_items(str(clippings_dir), target_papers)
                            
                            processed_papers = ochiai_result.get('processed', 0)
                            skipped_papers = ochiai_result.get('skipped', 0)
                            failed_papers = ochiai_result.get('failed', 0)
                            
                            self.logger.info(f"Ochiai-format completed: {processed_papers} papers processed, "
                                           f"{skipped_papers} skipped, {failed_papers} failed")
                            
                            modules_executed.append('ochiai-format')
                        else:
                            self.logger.warning("No organized papers found for ochiai-format")
                    else:
                        self.logger.warning("Clippings directory not found for ochiai-format")
                    
                except ImportError as e:
                    self.logger.warning(f"OchiaiFormatWorkflow ImportError (未実装): {e}")
                except Exception as e:
                    self.logger.error(f"Error in ochiai-format processing: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.info("Ochiai-format機能は無効化されています（API利用料金削減）")
            
            # TODO: 新しいモジュールが実装されたら追加
            
            return {
                'status': 'success',
                'modules_executed': modules_executed,
                'files_processed': files_processed
            }
    
    def _basic_check(self):
        """基本的なチェックを実行"""
        workspace_path = self.output_path / "workspace"
        backup_path = self.output_path / "backup"
        
        checks = {
            'workspace_exists': workspace_path.exists(),
            'backup_exists': backup_path.exists(),
            'clippings_processed': False
        }
        
        # Clippingsディレクトリに処理結果があるかチェック
        workspace_clippings = workspace_path / "Clippings"
        if workspace_clippings.exists():
            # サブディレクトリが作成されているかチェック（file_organizerの結果）
            subdirs = [d for d in workspace_clippings.iterdir() if d.is_dir()]
            checks['clippings_processed'] = len(subdirs) > 0
        
        return checks
    
    def _save_test_result(self, execution_result, check_result):
        """テスト結果を保存（AI機能制御情報含む）"""
        result = {
            'test_execution': {
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'execution_result': execution_result,
                'basic_checks': check_result,
                'ai_feature_control': {  # 新規追加
                    'mode': 'development' if self.ai_controller.is_development_mode() else 'production',
                    'enabled_features': self.ai_controller.get_enabled_features(),
                    'disabled_features': self.ai_controller.get_disabled_features(),
                    'api_cost_savings': self.ai_controller.has_api_cost_savings(),
                    'summary': self.ai_controller.get_summary()
                }
            }
        }
        
        result_file = self.output_path / "test_result.yaml"
        with open(result_file, 'w', encoding='utf-8') as f:
            yaml.dump(result, f, default_flow_style=False, allow_unicode=True)
    
    def _save_error_result(self, error_msg):
        """エラー結果を保存"""
        result = {
            'test_execution': {
                'timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'error': error_msg
            }
        }
        
        result_file = self.output_path / "test_result.yaml"
        with open(result_file, 'w',  encoding='utf-8') as f:
            yaml.dump(result, f, default_flow_style=False, allow_unicode=True) 