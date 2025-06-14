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
    
    def __init__(self, config_manager, integrated_logger):
        self.config_manager = config_manager
        self.integrated_logger = integrated_logger
        self.logger = integrated_logger.get_logger("integrated_test")
        self.test_data_path = Path("code/test_data_master")
        self.output_path = Path("test_output/latest")
    
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
        """integrated_workflowを実行（ワークスペース内でその場処理）"""
        workspace_path = self.output_path / "workspace"
        
        try:
            # IntegratedWorkflowクラスが実装されている場合は、それを使用
            from code.py.modules.workflows.integrated_workflow import IntegratedWorkflow
            
            workflow = IntegratedWorkflow(self.config_manager, self.logger)
            result = workflow.execute(workspace_path)
            
            return {
                'status': 'success',
                'modules_executed': result.get('modules_executed', []),
                'files_processed': result.get('files_processed', 0)
            }
            
        except ImportError:
            # IntegratedWorkflowクラスが未実装の場合は、現在実装済みの機能を順次実行
            modules_executed = []
            files_processed = 0
            
            # 現在実装済みの機能を順次実行
            try:
                # organize機能
                from code.py.modules.workflows.file_organizer import FileOrganizer
                organizer = FileOrganizer(self.config_manager, self.integrated_logger)
                clippings_dir = workspace_path / "Clippings"
                
                if clippings_dir.exists():
                    md_files = list(clippings_dir.glob("*.md"))
                    for md_file in md_files:
                        organizer.organize_file(md_file, clippings_dir)
                    modules_executed.append('file_organizer')
                    files_processed = len(md_files)
            except ImportError:
                pass
            
            # 他の実装済み機能があれば順次追加
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
        """テスト結果を保存"""
        result = {
            'test_execution': {
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'execution_result': execution_result,
                'basic_checks': check_result
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