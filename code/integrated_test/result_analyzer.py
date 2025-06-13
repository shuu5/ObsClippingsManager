"""
結果分析

統合テストの実行結果の分析、レポート生成を担当。
"""

import json
import time
import psutil
from datetime import datetime
from pathlib import Path


class ResultAnalyzer:
    """結果分析クラス"""
    
    def __init__(self, config_manager, logger):
        """
        結果分析の初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger
        
        # 設定値の取得
        self.config = config_manager.get_config().get('integrated_testing', {})
        self.report_config = self.config.get('reporting', {})
        
        self.logger.info("ResultAnalyzer initialized")
    
    def analyze_test_results(self, test_workspace, workflow_result, validation_result):
        """
        テスト結果の分析
        
        Args:
            test_workspace (Path): テストワークスペースパス
            workflow_result (dict): ワークフロー実行結果
            validation_result (dict): 検証結果
        
        Returns:
            dict: 分析結果
        """
        self.logger.info("Analyzing test results")
        
        analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'workspace_path': str(test_workspace),
            'workflow_analysis': self._analyze_workflow_result(workflow_result),
            'validation_analysis': self._analyze_validation_result(validation_result),
            'performance_metrics': self._collect_performance_metrics(test_workspace),
            'summary': {}
        }
        
        # 総合評価
        analysis_result['summary'] = self._generate_summary(analysis_result)
        
        # レポート生成
        if self.report_config.get('detailed_logs', True):
            self._generate_detailed_report(test_workspace, analysis_result)
        
        self.logger.info("Test result analysis completed")
        return analysis_result
    
    def analyze_performance_metrics(self, performance_result):
        """
        パフォーマンスメトリクスの分析
        
        Args:
            performance_result (dict): パフォーマンステスト結果
        
        Returns:
            dict: パフォーマンス分析結果
        """
        self.logger.info("Analyzing performance metrics")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'metrics_summary': {},
            'performance_grade': 'unknown',
            'recommendations': []
        }
        
        if 'metrics' in performance_result:
            metrics = performance_result['metrics']
            
            # メモリ使用量分析
            if 'memory_usage_mb' in metrics:
                memory_mb = metrics['memory_usage_mb']
                memory_threshold = self.config.get('performance_monitoring', {}).get('memory_threshold_mb', 512)
                
                analysis['metrics_summary']['memory_usage'] = {
                    'value_mb': memory_mb,
                    'threshold_mb': memory_threshold,
                    'status': 'good' if memory_mb < memory_threshold else 'warning'
                }
                
                if memory_mb >= memory_threshold:
                    analysis['recommendations'].append(f"Memory usage ({memory_mb}MB) exceeds threshold ({memory_threshold}MB)")
            
            # 実行時間分析
            if 'execution_time_seconds' in metrics:
                exec_time = metrics['execution_time_seconds']
                time_threshold = self.config.get('performance_monitoring', {}).get('execution_time_threshold_seconds', 300)
                
                analysis['metrics_summary']['execution_time'] = {
                    'value_seconds': exec_time,
                    'threshold_seconds': time_threshold,
                    'status': 'good' if exec_time < time_threshold else 'warning'
                }
                
                if exec_time >= time_threshold:
                    analysis['recommendations'].append(f"Execution time ({exec_time}s) exceeds threshold ({time_threshold}s)")
        
        # 総合グレード判定
        warning_count = sum(1 for metric in analysis['metrics_summary'].values() 
                          if metric.get('status') == 'warning')
        
        if warning_count == 0:
            analysis['performance_grade'] = 'excellent'
        elif warning_count <= 1:
            analysis['performance_grade'] = 'good'
        else:
            analysis['performance_grade'] = 'poor'
        
        self.logger.info(f"Performance analysis completed: Grade = {analysis['performance_grade']}")
        return analysis
    
    def _analyze_workflow_result(self, workflow_result):
        """
        ワークフロー結果の分析
        
        Args:
            workflow_result (dict): ワークフロー実行結果
        
        Returns:
            dict: ワークフロー分析結果
        """
        analysis = {
            'status': workflow_result.get('status', 'unknown'),
            'steps_executed': len(workflow_result.get('steps_executed', [])),
            'success_rate': 0.0,
            'issues': []
        }
        
        # 成功率計算
        if analysis['steps_executed'] > 0:
            analysis['success_rate'] = 100.0  # 基本実装では成功と仮定
        
        # ステータス判定
        if analysis['status'] != 'completed':
            analysis['issues'].append(f"Workflow status is not completed: {analysis['status']}")
        
        return analysis
    
    def _analyze_validation_result(self, validation_result):
        """
        検証結果の分析
        
        Args:
            validation_result (dict): 検証結果
        
        Returns:
            dict: 検証分析結果
        """
        analysis = {
            'overall_valid': validation_result.get('overall_valid', False),
            'validation_score': 0.0,
            'error_count': len(validation_result.get('validation_errors', [])),
            'warning_count': len(validation_result.get('validation_warnings', [])),
            'critical_issues': []
        }
        
        # 検証スコア計算
        checks = ['yaml_headers_valid', 'file_structure_correct', 'citation_data_complete']
        passed_checks = sum(1 for check in checks if validation_result.get(check, False))
        analysis['validation_score'] = (passed_checks / len(checks)) * 100.0
        
        # 重大な問題の特定
        if analysis['error_count'] > 0:
            analysis['critical_issues'].extend(validation_result['validation_errors'])
        
        return analysis
    
    def _collect_performance_metrics(self, test_workspace):
        """
        パフォーマンスメトリクスの収集
        
        Args:
            test_workspace (Path): テストワークスペースパス
        
        Returns:
            dict: パフォーマンスメトリクス
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {},
            'workspace_info': {}
        }
        
        try:
            # システム情報
            metrics['system_info'] = {
                'cpu_usage_percent': psutil.cpu_percent(),
                'memory_usage_percent': psutil.virtual_memory().percent,
                'available_memory_mb': psutil.virtual_memory().available / (1024 * 1024)
            }
        except Exception as e:
            self.logger.warning(f"Failed to collect system metrics: {e}")
        
        try:
            # ワークスペース情報
            if test_workspace.exists():
                total_size = sum(f.stat().st_size for f in test_workspace.rglob('*') if f.is_file())
                file_count = len(list(test_workspace.rglob('*')))
                
                metrics['workspace_info'] = {
                    'total_size_mb': total_size / (1024 * 1024),
                    'file_count': file_count,
                    'directory_count': len([p for p in test_workspace.rglob('*') if p.is_dir()])
                }
        except Exception as e:
            self.logger.warning(f"Failed to collect workspace metrics: {e}")
        
        return metrics
    
    def _generate_summary(self, analysis_result):
        """
        分析結果の概要生成
        
        Args:
            analysis_result (dict): 分析結果
        
        Returns:
            dict: 概要
        """
        summary = {
            'overall_status': 'unknown',
            'key_metrics': {},
            'recommendations': []
        }
        
        # 全体ステータス判定
        workflow_ok = analysis_result['workflow_analysis']['status'] == 'completed'
        validation_ok = analysis_result['validation_analysis']['overall_valid']
        
        if workflow_ok and validation_ok:
            summary['overall_status'] = 'passed'
        elif workflow_ok or validation_ok:
            summary['overall_status'] = 'partial'
        else:
            summary['overall_status'] = 'failed'
        
        # キーメトリクス
        summary['key_metrics'] = {
            'validation_score': analysis_result['validation_analysis']['validation_score'],
            'error_count': analysis_result['validation_analysis']['error_count'],
            'warning_count': analysis_result['validation_analysis']['warning_count']
        }
        
        # 推奨事項
        if analysis_result['validation_analysis']['error_count'] > 0:
            summary['recommendations'].append("Fix validation errors before proceeding")
        
        if analysis_result['validation_analysis']['warning_count'] > 0:
            summary['recommendations'].append("Review validation warnings")
        
        return summary
    
    def _generate_detailed_report(self, test_workspace, analysis_result):
        """
        詳細レポートの生成
        
        Args:
            test_workspace (Path): テストワークスペースパス
            analysis_result (dict): 分析結果
        """
        try:
            report_dir = test_workspace / "reports"
            report_dir.mkdir(exist_ok=True)
            
            # JSON形式でレポート保存
            report_file = report_dir / "test_analysis_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Detailed report generated: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate detailed report: {e}") 