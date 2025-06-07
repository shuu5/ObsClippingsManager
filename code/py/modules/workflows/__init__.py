"""
ワークフローモジュール

Citation Fetcher機能とRename & MkDir Citation Key機能のワークフローを管理します。
"""

# Version information
__version__ = "2.0.0"
__author__ = "ObsClippingsManager Team"

# Import workflow classes
from .citation_workflow import CitationWorkflow
from .organization_workflow import OrganizationWorkflow
from .sync_check_workflow import SyncCheckWorkflow
from .citation_parser_workflow import CitationParserWorkflow
from .workflow_manager import WorkflowManager

__all__ = [
    'CitationWorkflow',
    'OrganizationWorkflow',
    'SyncCheckWorkflow',
    'CitationParserWorkflow',
    'WorkflowManager',
] 