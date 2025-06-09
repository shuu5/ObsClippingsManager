#!/usr/bin/env python3
"""
状態管理ベースのrun-integrated機能のテスト

状態管理フラグを使用した新しいrun-integrated機能をテストします。
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent / 'py'
sys.path.insert(0, str(project_root))

from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.status_manager import StatusManager, ProcessStatus
from modules.workflows.enhanced_integrated_workflow import EnhancedIntegratedWorkflow


class TestEnhancedIntegratedWorkflow(unittest.TestCase):
    """状態管理ベースの統合ワークフローのテスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.bibtex_file = os.path.join(self.temp_dir, "CurrentManuscript.bib")
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        
        os.makedirs(self.clippings_dir)
        
        # テスト用BibTeXファイル作成
        self.sample_bibtex = """@article{paper1,
    title={Paper One},
    author={Author, First},
    year={2023},
    doi={10.1000/paper1.doi}
}

@article{paper2,
    title={Paper Two},
    author={Author, Second},
    year={2024},
    obsclippings_organize_status={completed},
    obsclippings_sync_status={pending}
}

@article{paper3,
    title={Paper Three},
    author={Author, Third},
    year={2024},
    obsclippings_organize_status={completed},
    obsclippings_sync_status={completed},
    obsclippings_fetch_status={failed}
}"""
        
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write(self.sample_bibtex)
        
        # テスト用設定
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger()
        self.enhanced_workflow = EnhancedIntegratedWorkflow(
            self.config_manager, self.logger
        )
    
    def test_workflow_initialization(self):
        """ワークフロー初期化のテスト"""
        self.assertIsInstance(self.enhanced_workflow, EnhancedIntegratedWorkflow)
        self.assertIsInstance(self.enhanced_workflow.status_manager, StatusManager)
    
    def test_analyze_paper_status(self):
        """論文状態分析のテスト"""
        analysis = self.enhanced_workflow.analyze_paper_status(self.bibtex_file)
        
        self.assertIn('needs_organize', analysis)
        self.assertIn('needs_sync', analysis)
        self.assertIn('needs_fetch', analysis)
        self.assertIn('needs_parse', analysis)
        
        # paper1: すべて未実行
        self.assertIn('paper1', analysis['needs_organize'])
        
        # paper2: organize完了、sync必要
        self.assertNotIn('paper2', analysis['needs_organize'])
        self.assertIn('paper2', analysis['needs_sync'])
        
        # paper3: fetch失敗、リトライ必要
        self.assertIn('paper3', analysis['needs_fetch'])
    
    def test_execute_step_by_step(self):
        """ステップ別実行のテスト"""
        # WorkflowManagerのexecute_workflowメソッドをモック
        with patch.object(self.enhanced_workflow.workflow_manager, 'execute_workflow') as mock_execute:
            mock_execute.return_value = (True, {'organized_files': 1})
            
            # ステップ別実行
            result = self.enhanced_workflow.execute_step_by_step(
                self.bibtex_file, self.clippings_dir
            )
            
            self.assertTrue(result['overall_success'])
            self.assertIn('organize', result['steps_executed'])
            self.assertIn('sync', result['steps_executed'])
            self.assertIn('fetch', result['steps_executed'])
            self.assertIn('parse', result['steps_executed'])
    
    def test_execute_with_status_tracking(self):
        """状態追跡付き実行のテスト"""
        # WorkflowManagerのexecute_workflowメソッドをモック
        with patch.object(self.enhanced_workflow.workflow_manager, 'execute_workflow') as mock_execute:
            mock_execute.return_value = (True, {'organized_files': 1})
            
            with patch.object(self.enhanced_workflow.status_manager, 'update_status') as mock_update:
                mock_update.return_value = True
                
                result = self.enhanced_workflow.execute_with_status_tracking(
                    self.bibtex_file, self.clippings_dir, ['paper1']
                )
                
                self.assertTrue(result['success'])
                # 状態更新が呼ばれることを確認
                self.assertTrue(mock_update.called)
    
    def test_get_execution_plan(self):
        """実行計画生成のテスト"""
        plan = self.enhanced_workflow.get_execution_plan(self.bibtex_file)
        
        self.assertIn('total_papers', plan)
        self.assertIn('execution_steps', plan)
        self.assertIn('organize', plan['execution_steps'])
        self.assertIn('sync', plan['execution_steps'])
        self.assertIn('fetch', plan['execution_steps'])
        self.assertIn('parse', plan['execution_steps'])
        
        # paper1は全ステップ必要
        organize_step = plan['execution_steps']['organize']
        self.assertIn('paper1', organize_step['papers'])
        
    def test_force_regenerate_mode(self):
        """強制再生成モードのテスト"""
        # 強制再生成モードでは、すべてのフラグをリセットしてから実行
        with patch.object(self.enhanced_workflow.status_manager, 'reset_statuses') as mock_reset:
            mock_reset.return_value = True
            
            result = self.enhanced_workflow.execute_force_regenerate(
                self.bibtex_file, self.clippings_dir
            )
            
            # リセットが呼ばれることを確認
            mock_reset.assert_called_with(self.bibtex_file)
    
    def test_smart_skip_logic(self):
        """スマートスキップロジックのテスト"""
        # paper2は既にorganize完了なので、organizeステップはスキップされるべき
        plan = self.enhanced_workflow.get_execution_plan(self.bibtex_file)
        organize_papers = plan['execution_steps']['organize']['papers']
        
        self.assertNotIn('paper2', organize_papers)  # paper2はスキップ
        self.assertIn('paper1', organize_papers)     # paper1は実行必要


class TestStatusConsistencyChecks(unittest.TestCase):
    """状態整合性チェックのテスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.bibtex_file = os.path.join(self.temp_dir, "CurrentManuscript.bib")
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        
        os.makedirs(self.clippings_dir)
        
        # 設定とワークフロー
        config_manager = ConfigManager()
        logger = IntegratedLogger()
        self.enhanced_workflow = EnhancedIntegratedWorkflow(config_manager, logger)
    
    def test_consistency_check_with_missing_directories(self):
        """ディレクトリ不足の整合性チェック"""
        # BibTeXファイル作成（organize完了となっているが実際のディレクトリなし）
        bibtex_content = """@article{missing_dir_paper,
    title={Missing Directory Paper},
    author={Author, Test},
    year={2023},
    obsclippings_organize_status={completed}
}"""
        
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write(bibtex_content)
        
        consistency = self.enhanced_workflow.check_consistency(
            self.bibtex_file, self.clippings_dir
        )
        
        self.assertIn('status_inconsistencies', consistency)
        # organize完了だがディレクトリが存在しない矛盾を検出
        inconsistencies = consistency['status_inconsistencies']
        self.assertTrue(any(
            inc['issue'] == 'organize_completed_but_no_directory' 
            for inc in inconsistencies
        ))
    
    def test_consistency_check_with_orphaned_directories(self):
        """孤立ディレクトリの整合性チェック"""
        # BibTeXファイル作成（空）
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write("")
        
        # 孤立ディレクトリ作成
        orphan_dir = os.path.join(self.clippings_dir, "orphan_paper")
        os.makedirs(orphan_dir)
        with open(os.path.join(orphan_dir, "orphan_paper.md"), 'w') as f:
            f.write("# Orphaned paper")
        
        consistency = self.enhanced_workflow.check_consistency(
            self.bibtex_file, self.clippings_dir
        )
        
        self.assertIn('orphaned_directories', consistency)
        self.assertIn('orphan_paper', consistency['orphaned_directories'])


if __name__ == '__main__':
    unittest.main() 