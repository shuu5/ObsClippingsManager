#!/usr/bin/env python3

"""
StatusChecker - Test Suite

StatusCheckerクラスのテストスイート。
重複処理回避のための状態チェック機能をテスト。
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# テスト対象モジュールのパス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from py.modules.status_management.status_checker import StatusChecker
from py.modules.status_management.processing_status import ProcessingStatus
from py.modules.shared.config_manager import ConfigManager
from py.modules.shared.integrated_logger import IntegratedLogger
from py.modules.shared.exceptions import ProcessingError, ValidationError


class TestStatusChecker(unittest.TestCase):
    """StatusCheckerクラスのテスト"""

    def setUp(self):
        """テスト前の初期化処理"""
        # テスト用の一時ディレクトリ作成
        self.test_temp_dir = tempfile.mkdtemp(prefix="ObsClippingsManager_StatusChecker_Test_")
        self.clippings_dir = os.path.join(self.test_temp_dir, "clippings")
        os.makedirs(self.clippings_dir, exist_ok=True)
        
        # モック設定
        self.config_manager = MagicMock(spec=ConfigManager)
        def config_get_side_effect(key, default=None):
            # 状態チェック関連の設定
            if 'skip_completed_operations' in key:
                return True
            elif 'force_reprocessing' in key:
                return False
            elif 'check_modification_time' in key:
                return False  # テストでは修正時刻チェックを無効にする
            return default if default is not None else True
        self.config_manager.get = MagicMock(side_effect=config_get_side_effect)
        self.logger = MagicMock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = MagicMock()
        
        # StatusChecker初期化
        self.status_checker = StatusChecker(self.config_manager, self.logger)

    def tearDown(self):
        """テスト後のクリーンアップ処理"""
        if os.path.exists(self.test_temp_dir):
            shutil.rmtree(self.test_temp_dir)

    def _create_test_markdown_file(self, citation_key, yaml_header):
        """テスト用Markdownファイル作成ヘルパー"""
        md_file_path = os.path.join(self.clippings_dir, f"{citation_key}.md")
        
        yaml_content = "---\n"
        for key, value in yaml_header.items():
            if isinstance(value, dict):
                yaml_content += f"{key}:\n"
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, dict):
                        yaml_content += f"  {subkey}:\n"
                        for sub2key, sub2value in subvalue.items():
                            yaml_content += f"    {sub2key}: {sub2value}\n"
                    else:
                        yaml_content += f"  {subkey}: {subvalue}\n"
            else:
                yaml_content += f"{key}: {value}\n"
        yaml_content += "---\n\n# Test Paper Content"
        
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return md_file_path

    def test_status_checker_import(self):
        """StatusCheckerクラスのインポートテスト"""
        from py.modules.status_management.status_checker import StatusChecker
        self.assertTrue(hasattr(StatusChecker, '__init__'))

    def test_status_checker_initialization(self):
        """StatusCheckerクラスの初期化テスト"""
        self.assertIsNotNone(self.status_checker)
        self.assertEqual(self.status_checker.config_manager, self.config_manager)
        self.assertEqual(self.status_checker.logger, self.logger)

    def test_check_processing_needed_pending_status(self):
        """処理が必要な状態（PENDING）のチェックテスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'pending2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'pending',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('pending2023test', yaml_header)
        
        # 処理必要性チェック
        result = self.status_checker.check_processing_needed(md_file, 'organize')
        
        self.assertTrue(result)

    def test_check_processing_needed_completed_status(self):
        """処理が不要な状態（COMPLETED）のチェックテスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'completed2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('completed2023test', yaml_header)
        
        # 処理必要性チェック
        result = self.status_checker.check_processing_needed(md_file, 'organize')
        
        self.assertFalse(result)

    def test_check_processing_needed_failed_status(self):
        """処理が必要な状態（FAILED）のチェックテスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'failed2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'failed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('failed2023test', yaml_header)
        
        # 処理必要性チェック
        result = self.status_checker.check_processing_needed(md_file, 'organize')
        
        self.assertTrue(result)

    def test_check_processing_needed_force_mode(self):
        """強制実行モードのテスト"""
        # テストファイル作成（完了状態）
        yaml_header = {
            'citation_key': 'force2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            }
        }
        md_file = self._create_test_markdown_file('force2023test', yaml_header)
        
        # 強制実行モードで処理必要性チェック
        result = self.status_checker.check_processing_needed(
            md_file, 'organize', force=True
        )
        
        self.assertTrue(result)

    def test_check_modification_time_recent_change(self):
        """最近変更されたファイルの修正時刻チェックテスト"""
        # 一時的に修正時刻チェックを有効にする
        self.status_checker.check_modification_time = True
        
        # テストファイル作成
        yaml_header = {
            'citation_key': 'modified2023test',
            'workflow_version': '3.2',
            'last_updated': (datetime.now() - timedelta(hours=1)).isoformat(),  # 1時間前
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            }
        }
        md_file = self._create_test_markdown_file('modified2023test', yaml_header)
        
        # ファイルのタイムスタンプを現在時刻に変更（最近の変更をシミュレート）
        current_time = datetime.now().timestamp()
        os.utime(md_file, (current_time, current_time))
        
        # 修正時刻チェック
        result = self.status_checker.check_modification_time_changed(md_file)
        
        self.assertTrue(result)

    def test_get_skip_conditions(self):
        """スキップ条件取得テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'skip2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('skip2023test', yaml_header)
        
        # スキップ条件取得
        conditions = self.status_checker.get_skip_conditions(md_file, 'organize')
        
        self.assertIsNotNone(conditions)
        self.assertIsInstance(conditions, dict)
        expected_keys = ['already_completed', 'no_changes_detected', 'skip_reasons']
        for key in expected_keys:
            self.assertIn(key, conditions)

    def test_should_skip_operation_completed(self):
        """操作スキップ判定テスト（完了済み）"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'shouldskip2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('shouldskip2023test', yaml_header)
        
        # スキップ判定
        result = self.status_checker.should_skip_operation(md_file, 'organize')
        
        self.assertTrue(result)

    def test_should_skip_operation_pending(self):
        """操作スキップ判定テスト（未完了）"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'shouldnotskip2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'pending',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('shouldnotskip2023test', yaml_header)
        
        # スキップ判定
        result = self.status_checker.should_skip_operation(md_file, 'organize')
        
        self.assertFalse(result)

    def test_get_processing_summary(self):
        """処理サマリー取得テスト"""
        # 複数のテストファイル作成
        papers = []
        for i in range(3):
            yaml_header = {
                'citation_key': f'summary2023test{i}',
                'workflow_version': '3.2',
                'last_updated': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'processing_status': {
                    'organize': 'completed' if i == 0 else 'pending',
                    'sync': 'pending'
                }
            }
            md_file = self._create_test_markdown_file(f'summary2023test{i}', yaml_header)
            papers.append(md_file)
        
        # 処理サマリー取得
        summary = self.status_checker.get_processing_summary(papers, 'organize')
        
        self.assertIsNotNone(summary)
        self.assertIsInstance(summary, dict)
        expected_keys = ['total_papers', 'need_processing', 'skip_processing', 'completion_rate']
        for key in expected_keys:
            self.assertIn(key, summary)
        
        # 値の妥当性確認
        self.assertEqual(summary['total_papers'], 3)
        self.assertEqual(summary['need_processing'], 2)  # 2つがpending
        self.assertEqual(summary['skip_processing'], 1)  # 1つがcompleted

    def test_advanced_skip_condition_with_dependencies(self):
        """依存関係を考慮した高度なスキップ条件判定テスト"""
        # 依存関係のあるテストファイル作成
        yaml_header = {
            'citation_key': 'dependency2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'pending',  # organize未完了
                'sync': 'completed',    # syncは完了済み（不正な状態）
                'enhance': 'pending'    # enhance未完了
            }
        }
        md_file = self._create_test_markdown_file('dependency2023test', yaml_header)
        
        # 依存関係チェック付きスキップ条件取得
        conditions = self.status_checker.get_advanced_skip_conditions(
            md_file, 'enhance', check_dependencies=True
        )
        
        self.assertIsNotNone(conditions)
        self.assertIn('dependency_violations', conditions)
        self.assertIn('can_proceed', conditions)
        # organize未完了のため、enhanceも実行できないはず
        self.assertFalse(conditions['can_proceed'])

    def test_advanced_skip_condition_workflow_stage_check(self):
        """ワークフロー段階チェック付きスキップ条件判定テスト"""
        # ワークフロー段階のテストファイル作成
        yaml_header = {
            'citation_key': 'workflow2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed',
                'enhance': 'pending'
            },
            'workflow_stage': 'enhancement'
        }
        md_file = self._create_test_markdown_file('workflow2023test', yaml_header)
        
        # ワークフロー段階チェック付きスキップ条件取得
        conditions = self.status_checker.get_advanced_skip_conditions(
            md_file, 'enhance', check_workflow_stage=True
        )
        
        self.assertIsNotNone(conditions)
        self.assertIn('workflow_stage_compatible', conditions)
        self.assertIn('can_proceed', conditions)
        # 適切なワークフロー段階のため実行可能
        self.assertTrue(conditions['can_proceed'])

    def test_advanced_skip_condition_custom_rules(self):
        """カスタムスキップルールテスト"""
        # カスタムルール用テストファイル作成
        yaml_header = {
            'citation_key': 'customrule2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            },
            'skip_rules': {
                'sync': ['low_priority', 'manual_review_required']
            }
        }
        md_file = self._create_test_markdown_file('customrule2023test', yaml_header)
        
        # カスタムルールチェック付きスキップ条件取得
        conditions = self.status_checker.get_advanced_skip_conditions(
            md_file, 'sync', check_custom_rules=True
        )
        
        self.assertIsNotNone(conditions)
        self.assertIn('custom_skip_rules', conditions)
        self.assertIn('custom_skip_applied', conditions)
        # カスタムスキップルールが適用されるはず
        self.assertTrue(conditions['custom_skip_applied'])

    def test_skip_condition_priority_handling(self):
        """スキップ条件の優先度処理テスト"""
        # 複数の条件が競合するテストファイル作成
        yaml_header = {
            'citation_key': 'priority2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',  # 完了済み（スキップ候補）
                'sync': 'pending'
            },
            'priority_settings': {
                'force_reprocess_organize': True  # 強制再処理フラグ
            }
        }
        md_file = self._create_test_markdown_file('priority2023test', yaml_header)
        
        # 優先度処理付きスキップ条件取得
        conditions = self.status_checker.get_skip_condition_priority(
            md_file, 'organize'
        )
        
        self.assertIsNotNone(conditions)
        self.assertIn('final_decision', conditions)
        self.assertIn('priority_reason', conditions)
        # 強制再処理フラグにより、完了済みでも処理が必要
        self.assertEqual(conditions['final_decision'], 'process')

    def test_batch_skip_condition_analysis(self):
        """バッチファイルのスキップ条件分析テスト"""
        # 複数のテストファイル作成（異なる状態）
        test_files = []
        for i, status in enumerate(['pending', 'completed', 'failed']):
            yaml_header = {
                'citation_key': f'batch2023test{i}',
                'workflow_version': '3.2',
                'last_updated': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'processing_status': {
                    'organize': status,
                    'sync': 'pending'
                }
            }
            md_file = self._create_test_markdown_file(f'batch2023test{i}', yaml_header)
            test_files.append(md_file)
        
        # バッチ分析実行
        analysis = self.status_checker.analyze_batch_skip_conditions(
            test_files, 'organize'
        )
        
        self.assertIsNotNone(analysis)
        self.assertIn('total_files', analysis)
        self.assertIn('skip_breakdown', analysis)
        self.assertIn('processing_recommendations', analysis)
        self.assertEqual(analysis['total_files'], 3)
        # pending と failed は処理が必要、completed はスキップ
        self.assertIn('need_processing', analysis['skip_breakdown'])
        self.assertIn('can_skip', analysis['skip_breakdown'])

    def test_force_execution_global_override(self):
        """グローバル強制実行オーバーライドテスト"""
        # 完了済みファイル作成
        yaml_header = {
            'citation_key': 'global_force2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            }
        }
        md_file = self._create_test_markdown_file('global_force2023test', yaml_header)
        
        # グローバル強制実行の設定
        force_config = {
            'force_all_operations': True,
            'ignore_completion_status': True,
            'force_reasons': ['user_request', 'data_corruption_fix']
        }
        
        # 強制実行制御取得
        force_result = self.status_checker.get_force_execution_control(
            md_file, 'organize', force_config
        )
        
        self.assertIsNotNone(force_result)
        self.assertIn('should_force', force_result)
        self.assertIn('force_reasons', force_result)
        self.assertTrue(force_result['should_force'])
        self.assertIn('user_request', force_result['force_reasons'])

    def test_force_execution_selective_operations(self):
        """選択的操作強制実行テスト"""
        # 部分完了ファイル作成
        yaml_header = {
            'citation_key': 'selective_force2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'failed',
                'enhance': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('selective_force2023test', yaml_header)
        
        # 選択的強制実行設定
        force_config = {
            'force_operations': ['organize'],  # organizeのみ強制実行
            'respect_dependencies': True,
            'dry_run': False
        }
        
        # organize操作の強制実行制御
        force_result_organize = self.status_checker.get_force_execution_control(
            md_file, 'organize', force_config
        )
        
        # sync操作の強制実行制御
        force_result_sync = self.status_checker.get_force_execution_control(
            md_file, 'sync', force_config
        )
        
        # organizeは強制実行、syncは通常処理
        self.assertTrue(force_result_organize['should_force'])
        self.assertFalse(force_result_sync['should_force'])

    def test_force_execution_with_safety_checks(self):
        """安全性チェック付き強制実行テスト"""
        # 重要なファイル作成
        yaml_header = {
            'citation_key': 'safety_force2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            },
            'safety_flags': {
                'critical_data': True,
                'backup_required': True
            }
        }
        md_file = self._create_test_markdown_file('safety_force2023test', yaml_header)
        
        # 安全性チェック付き強制実行設定
        force_config = {
            'force_all_operations': True,
            'enable_safety_checks': True,
            'require_backup': True,
            'confirm_critical_operations': True
        }
        
        # 強制実行制御取得
        force_result = self.status_checker.get_force_execution_control(
            md_file, 'organize', force_config
        )
        
        self.assertIsNotNone(force_result)
        self.assertIn('safety_warnings', force_result)
        self.assertIn('backup_required', force_result)
        self.assertTrue(force_result['backup_required'])
        self.assertIn('critical_data', force_result['safety_warnings'])

    def test_force_execution_dry_run_mode(self):
        """ドライランモード強制実行テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'dryrun_force2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('dryrun_force2023test', yaml_header)
        
        # ドライラン強制実行設定
        force_config = {
            'force_all_operations': True,
            'dry_run': True,
            'show_impact_analysis': True
        }
        
        # ドライラン分析取得
        dry_run_result = self.status_checker.analyze_force_execution_impact(
            [md_file], force_config
        )
        
        self.assertIsNotNone(dry_run_result)
        self.assertIn('affected_files', dry_run_result)
        self.assertIn('operations_to_force', dry_run_result)
        self.assertIn('estimated_impact', dry_run_result)
        self.assertEqual(dry_run_result['affected_files'], 1)

    def test_force_execution_batch_operations(self):
        """バッチ操作強制実行テスト"""
        # 複数のテストファイル作成
        test_files = []
        for i, status in enumerate(['completed', 'failed', 'pending']):
            yaml_header = {
                'citation_key': f'batch_force2023test{i}',
                'workflow_version': '3.2',
                'last_updated': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'processing_status': {
                    'organize': status,
                    'sync': 'pending'
                }
            }
            md_file = self._create_test_markdown_file(f'batch_force2023test{i}', yaml_header)
            test_files.append(md_file)
        
        # バッチ強制実行設定
        force_config = {
            'force_operations': ['organize'],
            'batch_size': 10,
            'parallel_execution': False,
            'stop_on_error': True
        }
        
        # バッチ強制実行計画
        batch_plan = self.status_checker.create_batch_force_execution_plan(
            test_files, force_config
        )
        
        self.assertIsNotNone(batch_plan)
        self.assertIn('execution_batches', batch_plan)
        self.assertIn('total_operations', batch_plan)
        self.assertIn('estimated_duration', batch_plan)
        # completed状態のファイルも強制実行対象に含まれる
        self.assertGreaterEqual(batch_plan['total_operations'], 1)

    def test_force_execution_rollback_capability(self):
        """強制実行ロールバック機能テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'rollback_force2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            }
        }
        md_file = self._create_test_markdown_file('rollback_force2023test', yaml_header)
        
        # ロールバック対応強制実行設定
        force_config = {
            'force_all_operations': True,
            'enable_rollback': True,
            'create_snapshots': True,
            'max_rollback_points': 3
        }
        
        # ロールバック計画取得
        rollback_plan = self.status_checker.create_force_execution_rollback_plan(
            md_file, force_config
        )
        
        self.assertIsNotNone(rollback_plan)
        self.assertIn('snapshot_required', rollback_plan)
        self.assertIn('rollback_steps', rollback_plan)
        self.assertIn('recovery_operations', rollback_plan)
        self.assertTrue(rollback_plan['snapshot_required'])


if __name__ == '__main__':
    unittest.main() 