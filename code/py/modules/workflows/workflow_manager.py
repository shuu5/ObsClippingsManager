"""
ワークフロー管理

複数のワークフローを統合管理し、適切な順序で実行します。
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Union
from enum import Enum
from datetime import datetime

from .citation_workflow import CitationWorkflow
from .organization_workflow import OrganizationWorkflow
from .sync_check_workflow import SyncCheckWorkflow
from .citation_parser_workflow import CitationParserWorkflow


class WorkflowType(Enum):
    """ワークフロータイプ"""
    CITATION_FETCHING = "citation_fetching"
    FILE_ORGANIZATION = "file_organization"
    SYNC_CHECK = "sync_check"
    CITATION_PARSER = "citation_parser"
    INTEGRATED = "integrated"


class WorkflowManager:
    """ワークフロー管理"""
    
    def __init__(self, config_manager, logger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ロガーインスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('WorkflowManager')
        
        # ワークフローインスタンスの初期化
        self.citation_workflow = CitationWorkflow(config_manager, logger)
        self.organization_workflow = OrganizationWorkflow(config_manager, logger)
        self.sync_check_workflow = SyncCheckWorkflow(config_manager, logger)
        self.citation_parser_workflow = CitationParserWorkflow(config_manager, logger)
        
        # 実行履歴
        self.execution_history = []
        
    def execute_workflow(self, 
                        workflow_type: Union[WorkflowType, str], 
                        **options) -> Tuple[bool, Dict[str, Any]]:
        """
        指定されたワークフローを実行
        
        Args:
            workflow_type: 実行するワークフロータイプ
            **options: 実行オプション
            
        Returns:
            (成功フラグ, 実行結果詳細)
        """
        # 文字列の場合はEnumに変換
        if isinstance(workflow_type, str):
            try:
                workflow_type = WorkflowType(workflow_type)
            except ValueError:
                self.logger.error(f"Unknown workflow type: {workflow_type}")
                return False, {"error": f"Unknown workflow type: {workflow_type}"}
        
        self.logger.info(f"Starting workflow execution: {workflow_type.value}")
        start_time = datetime.now()
        
        try:
            # ワークフロータイプに応じて実行
            if workflow_type == WorkflowType.CITATION_FETCHING:
                success, results = self._execute_citation_workflow(options)
                
            elif workflow_type == WorkflowType.FILE_ORGANIZATION:
                success, results = self._execute_organization_workflow(options)
                
            elif workflow_type == WorkflowType.SYNC_CHECK:
                success, results = self._execute_sync_check_workflow(options)
                
            elif workflow_type == WorkflowType.CITATION_PARSER:
                success, results = self._execute_citation_parser_workflow(options)
                
            elif workflow_type == WorkflowType.INTEGRATED:
                success, results = self._execute_integrated_workflow(options)
                
            else:
                self.logger.error(f"Unsupported workflow type: {workflow_type}")
                return False, {"error": f"Unsupported workflow type: {workflow_type}"}
            
            # 実行時間を計算
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 結果に実行情報を追加
            results.update({
                "workflow_type": workflow_type.value,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time
            })
            
            # 履歴に記録
            self._record_execution(workflow_type, success, results, execution_time)
            
            if success:
                self.logger.info(f"Workflow completed successfully: {workflow_type.value}")
            else:
                self.logger.error(f"Workflow failed: {workflow_type.value}")
            
            return success, results
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            error_result = {
                "workflow_type": workflow_type.value,
                "error": str(e),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time
            }
            
            self._record_execution(workflow_type, False, error_result, execution_time)
            self.logger.error(f"Workflow execution failed: {workflow_type.value} - {e}")
            
            return False, error_result
    
    def _execute_citation_workflow(self, options: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Citation Workflowの実行
        
        Args:
            options: 実行オプション
            
        Returns:
            実行結果
        """
        self.logger.info("Executing citation fetching workflow")
        return self.citation_workflow.execute(**options)
    
    def _execute_organization_workflow(self, options: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Organization Workflowの実行
        
        Args:
            options: 実行オプション
            
        Returns:
            実行結果
        """
        self.logger.info("Executing file organization workflow")
        return self.organization_workflow.execute(**options)
    
    def _execute_sync_check_workflow(self, options: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Sync Check Workflowの実行
        
        Args:
            options: 実行オプション
            
        Returns:
            実行結果
        """
        self.logger.info("Executing sync check workflow")
        return self.sync_check_workflow.execute(**options)
    
    def _execute_citation_parser_workflow(self, options: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Citation Parser Workflowの実行
        
        Args:
            options: 実行オプション
            
        Returns:
            実行結果
        """
        self.logger.info("Executing citation parser workflow")
        return self.citation_parser_workflow.execute(**options)
    
    def _execute_integrated_workflow(self, options: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        統合ワークフローの実行（引用文献取得 → ファイル整理）
        
        Args:
            options: 実行オプション
            
        Returns:
            統合実行結果
        """
        self.logger.info("Executing integrated workflow")
        
        integrated_results = {
            "stage": "initialization",
            "citation_results": {},
            "organization_results": {},
            "overall_success": False
        }
        
        # Phase 1: 引用文献取得
        self.logger.info("Phase 1: Citation fetching")
        integrated_results["stage"] = "citation_fetching"
        
        citation_success, citation_results = self.citation_workflow.execute(**options)
        integrated_results["citation_results"] = citation_results
        
        if not citation_success:
            # 引用文献取得に失敗した場合でも、既存のBibTeXで整理を続行可能
            citation_error = citation_results.get("error", "Unknown error")
            self.logger.warning(f"Citation fetching failed: {citation_error}")
            
            # 続行するかどうかの判定
            if not options.get('continue_on_citation_failure', True):
                integrated_results["error"] = f"Citation fetching failed: {citation_error}"
                return False, integrated_results
        
        # Phase 2: ファイル整理
        self.logger.info("Phase 2: File organization")
        integrated_results["stage"] = "file_organization"
        
        org_success, org_results = self.organization_workflow.execute(**options)
        integrated_results["organization_results"] = org_results
        
        # 統合結果の判定
        integrated_results["overall_success"] = citation_success and org_success
        
        # 統合統計の計算
        integrated_results["statistics"] = self._calculate_integrated_statistics(
            citation_results, org_results
        )
        
        # ステージ完了
        integrated_results["stage"] = "completed"
        
        if integrated_results["overall_success"]:
            self.logger.info("Integrated workflow completed successfully")
        else:
            errors = []
            if not citation_success:
                errors.append(f"Citation: {citation_results.get('error', 'Unknown')}")
            if not org_success:
                errors.append(f"Organization: {org_results.get('error', 'Unknown')}")
            
            integrated_results["error"] = "; ".join(errors)
            self.logger.error(f"Integrated workflow failed: {integrated_results['error']}")
        
        return integrated_results["overall_success"], integrated_results
    
    def _calculate_integrated_statistics(self, 
                                       citation_results: Dict[str, Any], 
                                       org_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        統合統計の計算
        
        Args:
            citation_results: 引用文献取得結果
            org_results: ファイル整理結果
            
        Returns:
            統合統計情報
        """
        stats = {
            "citation_phase": {
                "success": citation_results.get("success", False),
                "dois_processed": citation_results.get("successful_fetches", 0),
                "total_references": citation_results.get("total_references", 0),
                "crossref_successes": citation_results.get("crossref_successes", 0),
                "opencitations_successes": citation_results.get("opencitations_successes", 0)
            },
            "organization_phase": {
                "success": org_results.get("success", False),
                "files_processed": org_results.get("organized_files", 0),
                "matches_found": org_results.get("matches_count", 0),
                "directories_created": org_results.get("created_directories", 0)
            }
        }
        
        # 全体統計
        stats["overall"] = {
            "citation_success_rate": self._calculate_success_rate(
                citation_results.get("successful_fetches", 0),
                citation_results.get("total_dois", 0)
            ),
            "organization_success_rate": self._calculate_success_rate(
                org_results.get("organized_files", 0),
                org_results.get("md_files_count", 0)
            )
        }
        
        return stats
    
    def _calculate_success_rate(self, successful: int, total: int) -> float:
        """
        成功率を計算
        
        Args:
            successful: 成功数
            total: 総数
            
        Returns:
            成功率（0.0-1.0）
        """
        if total == 0:
            return 0.0
        return successful / total
    
    def _record_execution(self, 
                         workflow_type: WorkflowType, 
                         success: bool, 
                         results: Dict[str, Any], 
                         execution_time: float):
        """
        実行履歴を記録
        
        Args:
            workflow_type: ワークフロータイプ
            success: 成功フラグ
            results: 実行結果
            execution_time: 実行時間
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "workflow_type": workflow_type.value,
            "success": success,
            "execution_time": execution_time,
            "stage": results.get("stage", "unknown"),
            "error": results.get("error") if not success else None
        }
        
        # 簡略化された統計情報のみ記録
        if workflow_type == WorkflowType.CITATION_FETCHING:
            record["summary"] = {
                "dois_processed": results.get("successful_fetches", 0),
                "total_references": results.get("total_references", 0)
            }
        elif workflow_type == WorkflowType.FILE_ORGANIZATION:
            record["summary"] = {
                "files_organized": results.get("organized_files", 0),
                "matches_found": results.get("matches_count", 0)
            }
        elif workflow_type == WorkflowType.INTEGRATED:
            record["summary"] = {
                "citation_success": results.get("citation_results", {}).get("success", False),
                "organization_success": results.get("organization_results", {}).get("success", False),
                "overall_success": results.get("overall_success", False)
            }
        
        self.execution_history.append(record)
        
        # 履歴サイズの制限（最新100件のみ保持）
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_execution_history(self, 
                             limit: Optional[int] = None, 
                             workflow_type: Optional[WorkflowType] = None) -> List[Dict[str, Any]]:
        """
        実行履歴を取得
        
        Args:
            limit: 取得件数の制限
            workflow_type: フィルタするワークフロータイプ
            
        Returns:
            実行履歴のリスト
        """
        history = self.execution_history.copy()
        
        # ワークフロータイプでフィルタ
        if workflow_type is not None:
            history = [record for record in history if record["workflow_type"] == workflow_type.value]
        
        # 最新順でソート
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # 件数制限
        if limit is not None:
            history = history[:limit]
        
        return history
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """
        ワークフロー統計情報を取得
        
        Returns:
            統計情報
        """
        if not self.execution_history:
            return {"total_executions": 0}
        
        # 基本統計
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for record in self.execution_history if record["success"])
        
        # ワークフロータイプ別統計
        type_stats = {}
        for workflow_type in WorkflowType:
            type_records = [r for r in self.execution_history if r["workflow_type"] == workflow_type.value]
            
            if type_records:
                type_stats[workflow_type.value] = {
                    "total": len(type_records),
                    "successful": sum(1 for r in type_records if r["success"]),
                    "avg_execution_time": sum(r["execution_time"] for r in type_records) / len(type_records)
                }
        
        # 最近の実行状況
        recent_executions = self.execution_history[-10:] if len(self.execution_history) >= 10 else self.execution_history
        recent_success_rate = sum(1 for r in recent_executions if r["success"]) / len(recent_executions) if recent_executions else 0
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "overall_success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "recent_success_rate": recent_success_rate,
            "by_workflow_type": type_stats,
            "last_execution": self.execution_history[-1]["timestamp"] if self.execution_history else None
        }
    
    def validate_workflow_configuration(self, 
                                      workflow_type: Union[WorkflowType, str]) -> Tuple[bool, List[str]]:
        """
        ワークフロー設定の検証
        
        Args:
            workflow_type: 検証するワークフロータイプ
            
        Returns:
            (妥当性, エラーメッセージリスト)
        """
        if isinstance(workflow_type, str):
            try:
                workflow_type = WorkflowType(workflow_type)
            except ValueError:
                return False, [f"Unknown workflow type: {workflow_type}"]
        
        if workflow_type == WorkflowType.CITATION_FETCHING:
            from .citation_workflow import validate_citation_workflow_config
            citation_config = self.config_manager.get_citation_fetcher_config()
            return validate_citation_workflow_config(citation_config)
            
        elif workflow_type == WorkflowType.FILE_ORGANIZATION:
            from .organization_workflow import validate_organization_workflow_config
            org_config = self.config_manager.get_rename_mkdir_config()
            return validate_organization_workflow_config(org_config)
            
        elif workflow_type == WorkflowType.SYNC_CHECK:
            # Sync checkワークフローは基本的な設定のみ必要
            return True, []
            
        elif workflow_type == WorkflowType.CITATION_PARSER:
            # Citation parserワークフローは現在未実装のため常に有効
            return True, []
            
        elif workflow_type == WorkflowType.INTEGRATED:
            # 統合ワークフローは両方の設定を検証
            citation_valid, citation_errors = self.validate_workflow_configuration(WorkflowType.CITATION_FETCHING)
            org_valid, org_errors = self.validate_workflow_configuration(WorkflowType.FILE_ORGANIZATION)
            
            all_errors = []
            if citation_errors:
                all_errors.extend([f"Citation: {err}" for err in citation_errors])
            if org_errors:
                all_errors.extend([f"Organization: {err}" for err in org_errors])
            
            return citation_valid and org_valid, all_errors
        
        return False, [f"Unsupported workflow type: {workflow_type}"]


# ヘルパー関数
def create_workflow_manager(config_manager, logger) -> WorkflowManager:
    """
    ワークフロー管理インスタンスを作成
    
    Args:
        config_manager: 設定管理インスタンス
        logger: 統合ロガーインスタンス
        
    Returns:
        ワークフロー管理インスタンス
    """
    return WorkflowManager(config_manager, logger)


def get_available_workflows() -> List[str]:
    """
    利用可能なワークフロータイプのリストを取得
    
    Returns:
        ワークフロータイプ名のリスト
    """
    return [workflow_type.value for workflow_type in WorkflowType]


def create_workflow_execution_summary(results: Dict[str, Any]) -> str:
    """
    ワークフロー実行結果のサマリーを作成
    
    Args:
        results: ワークフロー実行結果
        
    Returns:
        サマリー文字列
    """
    workflow_type = results.get("workflow_type", "Unknown")
    
    lines = [f"Workflow Execution Summary - {workflow_type.title()}", "=" * 50]
    
    # 基本情報
    start_time = results.get("start_time", "Unknown")
    end_time = results.get("end_time", "Unknown")
    execution_time = results.get("execution_time", 0)
    
    lines.extend([
        f"Start time: {start_time}",
        f"End time: {end_time}",
        f"Execution time: {execution_time:.2f} seconds"
    ])
    
    # ワークフロータイプ別の詳細
    if workflow_type == "citation_fetching":
        from .citation_workflow import create_citation_workflow_summary
        lines.append("\n" + create_citation_workflow_summary(results))
        
    elif workflow_type == "file_organization":
        from .organization_workflow import create_organization_workflow_summary
        lines.append("\n" + create_organization_workflow_summary(results))
        
    elif workflow_type == "integrated":
        lines.append("\nIntegrated Workflow Details:")
        lines.append("-" * 30)
        
        # Citation phase
        citation_results = results.get("citation_results", {})
        if citation_results:
            citation_success = citation_results.get("success", False)
            lines.append(f"Citation phase: {'SUCCESS' if citation_success else 'FAILED'}")
            
            if citation_success:
                successful = citation_results.get("successful_fetches", 0)
                total_dois = citation_results.get("total_dois", 0)
                total_refs = citation_results.get("total_references", 0)
                lines.append(f"  DOIs processed: {successful}/{total_dois}")
                lines.append(f"  References found: {total_refs}")
        
        # Organization phase
        org_results = results.get("organization_results", {})
        if org_results:
            org_success = org_results.get("success", False)
            lines.append(f"Organization phase: {'SUCCESS' if org_success else 'FAILED'}")
            
            if org_success:
                organized = org_results.get("organized_files", 0)
                matches = org_results.get("matches_count", 0)
                lines.append(f"  Files organized: {organized}")
                lines.append(f"  Matches found: {matches}")
        
        # Overall result
        overall_success = results.get("overall_success", False)
        lines.append(f"\nOverall result: {'SUCCESS' if overall_success else 'FAILED'}")
    
    # エラー情報
    if not results.get("success", True) and "error" in results:
        lines.append(f"\nError: {results['error']}")
    
    return "\n".join(lines)


def log_workflow_performance(execution_history: List[Dict[str, Any]], 
                           logger: Optional[logging.Logger] = None):
    """
    ワークフロー性能情報をログ出力
    
    Args:
        execution_history: 実行履歴
        logger: ロガーインスタンス
    """
    if not logger:
        logger = logging.getLogger("ObsClippingsManager.WorkflowManager")
    
    if not execution_history:
        logger.info("No workflow execution history available")
        return
    
    # 基本統計
    total = len(execution_history)
    successful = sum(1 for record in execution_history if record["success"])
    avg_time = sum(record["execution_time"] for record in execution_history) / total
    
    logger.info(f"Workflow Performance Summary:")
    logger.info(f"  Total executions: {total}")
    logger.info(f"  Successful: {successful} ({(successful/total*100):.1f}%)")
    logger.info(f"  Average execution time: {avg_time:.2f} seconds")
    
    # 最近の傾向
    recent = execution_history[-5:] if len(execution_history) >= 5 else execution_history
    recent_success = sum(1 for record in recent if record["success"])
    recent_avg_time = sum(record["execution_time"] for record in recent) / len(recent)
    
    logger.info(f"Recent performance (last {len(recent)} executions):")
    logger.info(f"  Success rate: {(recent_success/len(recent)*100):.1f}%")
    logger.info(f"  Average time: {recent_avg_time:.2f} seconds") 