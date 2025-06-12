#!/usr/bin/env python3
"""
統合ワークフロー v3.0 のテスト

v3.0仕様に基づくIntegratedWorkflowクラスのテストを行います。
特に統一設定システムとYAMLヘッダーベースの状態管理をテストします。
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
import sys
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent / 'py'
sys.path.insert(0, str(project_root))

from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.status_manager import StatusManager, ProcessStatus
from modules.workflows.integrated_workflow import IntegratedWorkflow
from modules.shared.exceptions import ObsClippingsError


class TestIntegratedWorkflowV3(unittest.TestCase):
    """統合ワークフロー v3.0 のテスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_path = os.path.join(self.temp_dir, "TestWorkspace")
        os.makedirs(self.workspace_path)
        
        # 統一設定システムテスト用
        self.bibtex_file = os.path.join(self.workspace_path, "CurrentManuscript.bib")
        self.clippings_dir = os.path.join(self.workspace_path, "Clippings")
        os.makedirs(self.clippings_dir)
        
        # テスト用BibTeXファイル作成
        self.sample_bibtex = """@article{smith2023test,
    title={Test Paper by Smith},
    author={Smith, John},
    year={2023},
    doi={10.1000/smith.doi}
}

@article{jones2024neural,
    title={Neural Networks in AI},
    author={Jones, Jane},
    year={2024},
    doi={10.1000/jones.doi}
}"""
        
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write(self.sample_bibtex)
        
        # 設定管理の初期化
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger()
        
        # IntegratedWorkflow初期化
        self.integrated_workflow = IntegratedWorkflow(self.config_manager, self.logger)
    
    def test_path_resolution_from_workspace(self):
        """workspace_pathからの統一パス解決テスト"""
        options = {
            'workspace_path': self.workspace_path
        }
        
        paths = self.integrated_workflow._resolve_paths(**options)
        
        # 正しくパスが導出されることを確認
        self.assertEqual(paths['workspace_path'], self.workspace_path)
        self.assertEqual(paths['bibtex_file'], self.bibtex_file)
        self.assertEqual(paths['clippings_dir'], self.clippings_dir)
        self.assertEqual(paths['output_dir'], self.clippings_dir)
    
    def test_path_resolution_with_individual_override(self):
        """workspace_pathベースの個別パス上書きテスト"""
        custom_bibtex = os.path.join(self.temp_dir, "custom.bib")
        
        options = {
            'workspace_path': self.workspace_path,
            'bibtex_file': custom_bibtex
        }
        
        paths = self.integrated_workflow._resolve_paths(**options)
        
        # workspace_pathから導出されるパスと個別指定パスの混在
        self.assertEqual(paths['workspace_path'], self.workspace_path)
        self.assertEqual(paths['bibtex_file'], custom_bibtex)  # 個別指定
        self.assertEqual(paths['clippings_dir'], self.clippings_dir)  # workspace_pathから導出
    
    def test_path_resolution_default_workspace(self):
        """デフォルトworkspace_pathの使用テスト"""
        options = {}  # workspace_pathを指定しない
        
        paths = self.integrated_workflow._resolve_paths(**options)
        
        # デフォルトワークスペースが使用されることを確認
        expected_default = "/home/user/ManuscriptsManager"
        self.assertEqual(paths['workspace_path'], expected_default)
        self.assertEqual(paths['bibtex_file'], f"{expected_default}/CurrentManuscript.bib")
        self.assertEqual(paths['clippings_dir'], f"{expected_default}/Clippings")
    
    def test_configuration_validation(self):
        """設定検証テスト"""
        paths = {
            'workspace_path': self.workspace_path,
            'bibtex_file': self.bibtex_file,
            'clippings_dir': self.clippings_dir,
            'output_dir': self.clippings_dir
        }
        
        validation_result = self.integrated_workflow._validate_configuration(paths)
        
        self.assertTrue(validation_result['valid'])
        self.assertIn('bibtex_file_exists', validation_result)
        self.assertIn('clippings_dir_exists', validation_result)
    
    def test_configuration_validation_missing_files(self):
        """設定検証（ファイル不存在）テスト"""
        paths = {
            'workspace_path': self.workspace_path,
            'bibtex_file': '/nonexistent/file.bib',
            'clippings_dir': '/nonexistent/dir',
            'output_dir': '/nonexistent/output'
        }
        
        validation_result = self.integrated_workflow._validate_configuration(paths)
        
        self.assertFalse(validation_result['valid'])
        self.assertIn('errors', validation_result)
    
    def test_execution_plan_generation(self):
        """実行計画生成テスト"""
        # テスト用論文ディレクトリを作成
        self._create_sample_papers()
        
        options = {
            'workspace_path': self.workspace_path,
            'show_plan': True
        }
        
        plan = self.integrated_workflow.show_execution_plan(**options)
        
        # 実行計画の構造確認
        self.assertIn('execution_plan', plan)
        self.assertIn('total_papers', plan)
        self.assertIn('estimated_total_time', plan)
        
        # 各ステップの計画確認
        for step in ['organize', 'sync', 'fetch', 'parse']:
            self.assertIn(step, plan['execution_plan'])
    
    def test_workflow_execution_with_status_management(self):
        """状態管理を使用したワークフロー実行テスト"""
        # テスト用論文ディレクトリを作成
        self._create_sample_papers()
        
        options = {
            'workspace_path': self.workspace_path,
            'dry_run': True  # 実際の処理は行わずに状態管理のみテスト
        }
        
        result = self.integrated_workflow.execute(**options)
        
        # 実行結果の基本構造確認
        self.assertIn('status', result)
        self.assertIn('completed_steps', result)
        self.assertIn('total_papers', result)
    
    def test_force_reprocess_mode(self):
        """強制再処理モードテスト"""
        # 既に完了状態の論文を作成
        self._create_completed_paper()
        
        options = {
            'workspace_path': self.workspace_path,
            'force_reprocess': True,
            'dry_run': True
        }
        
        result = self.integrated_workflow.force_reprocess(**options)
        
        # 強制再処理の実行確認
        self.assertIn('reset_count', result)
        self.assertIn('status', result)
    
    def test_target_papers_filtering(self):
        """特定論文のみ処理するフィルタリングテスト"""
        # テスト用論文ディレクトリを作成
        self._create_sample_papers()
        
        options = {
            'workspace_path': self.workspace_path,
            'papers': 'smith2023test',  # smith2023testのみ処理
            'show_plan': True
        }
        
        plan = self.integrated_workflow.show_execution_plan(**options)
        
        # 指定した論文のみが対象になることを確認
        self.assertEqual(plan['total_papers'], 1)
        # 各ステップで処理対象が正しく絞られていることを確認
        for step_plan in plan['execution_plan'].values():
            if isinstance(step_plan, dict) and 'papers_to_process' in step_plan:
                if step_plan['papers_to_process']:  # 空でない場合
                    self.assertIn('smith2023test', step_plan['papers_to_process'])
    
    def test_skip_steps_functionality(self):
        """ステップスキップ機能テスト"""
        options = {
            'workspace_path': self.workspace_path,
            'skip_steps': 'parse,sync',  # parseとsyncをスキップ
            'show_plan': True
        }
        
        plan = self.integrated_workflow.show_execution_plan(**options)
        
        # スキップされたステップが正しく処理されることを確認
        self.assertEqual(plan['execution_plan']['parse']['status'], 'skipped')
        self.assertEqual(plan['execution_plan']['sync']['status'], 'skipped')
        self.assertNotEqual(plan['execution_plan']['organize']['status'], 'skipped')
        self.assertNotEqual(plan['execution_plan']['fetch']['status'], 'skipped')

    def test_process_order_includes_ai_features(self):
        """処理順序にAI機能が含まれていることのテスト"""
        expected_order = ['organize', 'sync', 'fetch', 'ai-citation-support', 'tagger', 'translate_abstract', 'final-sync']
        
        # PROCESS_ORDERが仕様書通りであることを確認
        self.assertEqual(self.integrated_workflow.PROCESS_ORDER, expected_order)
    
    def test_ai_features_disabled_by_default(self):
        """AI機能がデフォルトで無効であることのテスト"""
        options = {
            'workspace_path': self.workspace_path,
            'show_plan': True
        }
        
        plan = self.integrated_workflow.show_execution_plan(**options)
        
        # taggerとtranslate_abstractがデフォルトでスキップされることを確認
        if 'tagger' in plan['execution_plan']:
            self.assertEqual(plan['execution_plan']['tagger']['status'], 'skipped')
        if 'translate_abstract' in plan['execution_plan']:
            self.assertEqual(plan['execution_plan']['translate_abstract']['status'], 'skipped')
    
    def test_ai_features_enabled_explicitly(self):
        """AI機能を明示的に有効化できることのテスト"""
        options = {
            'workspace_path': self.workspace_path,
            'enable_tagger': True,
            'enable_translate_abstract': True,
            'show_plan': True
        }
        
        plan = self.integrated_workflow.show_execution_plan(**options)
        
        # taggerとtranslate_abstractが有効になることを確認
        if 'tagger' in plan['execution_plan']:
            self.assertNotEqual(plan['execution_plan']['tagger']['status'], 'skipped')
        if 'translate_abstract' in plan['execution_plan']:
            self.assertNotEqual(plan['execution_plan']['translate_abstract']['status'], 'skipped')
    
    def test_tagger_only_enabled(self):
        """taggerのみを有効化できることのテスト"""
        options = {
            'workspace_path': self.workspace_path,
            'enable_tagger': True,
            'enable_translate_abstract': False,
            'show_plan': True
        }
        
        plan = self.integrated_workflow.show_execution_plan(**options)
        
        # taggerが有効、translate_abstractが無効であることを確認
        if 'tagger' in plan['execution_plan']:
            self.assertNotEqual(plan['execution_plan']['tagger']['status'], 'skipped')
        if 'translate_abstract' in plan['execution_plan']:
            self.assertEqual(plan['execution_plan']['translate_abstract']['status'], 'skipped')
    
    def test_translate_abstract_only_enabled(self):
        """translate_abstractのみを有効化できることのテスト"""
        options = {
            'workspace_path': self.workspace_path,
            'enable_tagger': False,
            'enable_translate_abstract': True,
            'show_plan': True
        }
        
        plan = self.integrated_workflow.show_execution_plan(**options)
        
        # taggerが無効、translate_abstractが有効であることを確認
        if 'tagger' in plan['execution_plan']:
            self.assertEqual(plan['execution_plan']['tagger']['status'], 'skipped')
        if 'translate_abstract' in plan['execution_plan']:
            self.assertNotEqual(plan['execution_plan']['translate_abstract']['status'], 'skipped')
    
    def test_ai_features_workflow_initialization(self):
        """AI機能ワークフローが初期化されていることのテスト"""
        # TaggerWorkflowとTranslateAbstractWorkflowが初期化されていることを確認
        self.assertTrue(hasattr(self.integrated_workflow, 'tagger_workflow'))
        self.assertTrue(hasattr(self.integrated_workflow, 'translate_abstract_workflow'))
        
        # ワークフローオブジェクトが適切なタイプであることを確認
        from modules.ai_tagging import TaggerWorkflow
        from modules.abstract_translation import TranslateAbstractWorkflow
        
        self.assertIsInstance(self.integrated_workflow.tagger_workflow, TaggerWorkflow)
        self.assertIsInstance(self.integrated_workflow.translate_abstract_workflow, TranslateAbstractWorkflow)
    
    def _create_sample_papers(self):
        """テスト用論文ディレクトリの作成"""
        # smith2023test論文ディレクトリ
        smith_dir = os.path.join(self.clippings_dir, "smith2023test")
        os.makedirs(smith_dir, exist_ok=True)
        
        smith_content = """---
obsclippings_metadata:
  citation_key: "smith2023test"
  processing_status:
    organize: "pending"
    sync: "pending"
    fetch: "pending"
    parse: "pending"
  last_updated: "2025-01-15T10:00:00Z"
  workflow_version: "3.0"
---

# Smith et al. (2023) - Test Paper

論文の内容...
"""
        
        with open(os.path.join(smith_dir, "smith2023test.md"), 'w', encoding='utf-8') as f:
            f.write(smith_content)
        
        # jones2024neural論文ディレクトリ
        jones_dir = os.path.join(self.clippings_dir, "jones2024neural")
        os.makedirs(jones_dir, exist_ok=True)
        
        jones_content = """# Jones et al. (2024) - Neural Networks

YAMLヘッダーなしの論文ファイル
"""
        
        with open(os.path.join(jones_dir, "jones2024neural.md"), 'w', encoding='utf-8') as f:
            f.write(jones_content)
    
    def _create_completed_paper(self):
        """完了状態の論文を作成（強制再処理テスト用）"""
        completed_dir = os.path.join(self.clippings_dir, "completed2023test")
        os.makedirs(completed_dir, exist_ok=True)
        
        completed_content = """---
obsclippings_metadata:
  citation_key: "completed2023test"
  processing_status:
    organize: "completed"
    sync: "completed"
    fetch: "completed"
    parse: "completed"
  last_updated: "2025-01-14T15:30:00Z"
  workflow_version: "3.0"
---

# Completed Test Paper (2023)

すべての処理が完了している論文
"""
        
        with open(os.path.join(completed_dir, "completed2023test.md"), 'w', encoding='utf-8') as f:
            f.write(completed_content)


if __name__ == '__main__':
    unittest.main() 