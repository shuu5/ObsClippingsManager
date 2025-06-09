#!/usr/bin/env python3
"""
状態管理機能

BibTeXエントリの処理状態を管理し、整合性チェック機能を提供します。
"""

import os
import re
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union
from pathlib import Path

from .config_manager import ConfigManager
from .logger import IntegratedLogger
from .bibtex_parser import BibTeXParser
from .exceptions import ObsClippingsError


class ProcessStatus(Enum):
    """処理状態を表すenum"""
    PENDING = "pending"      # 未実行
    COMPLETED = "completed"  # 正常完了
    FAILED = "failed"        # 異常終了
    
    @classmethod
    def from_string(cls, status_str: str) -> 'ProcessStatus':
        """文字列からProcessStatusを取得"""
        for status in cls:
            if status.value == status_str.lower():
                return status
        raise ValueError(f"Invalid status: {status_str}")


class StatusManager:
    """
    BibTeXエントリの処理状態管理クラス
    
    各論文の処理状況（organize, sync, fetch, parse）を管理し、
    CurrentManuscript.bibファイルに状態フラグとして記録します。
    """
    
    # 状態管理フィールド名
    STATUS_FIELDS = {
        'organize': 'obsclippings_organize_status',
        'sync': 'obsclippings_sync_status',
        'fetch': 'obsclippings_fetch_status',
        'parse': 'obsclippings_parse_status'
    }
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        StatusManagerの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ管理オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('StatusManager')
        self.bibtex_parser = BibTeXParser()
        
        self.logger.info("StatusManager initialized successfully")
    
    def load_bib_statuses(self, bibtex_file: str) -> Dict[str, Dict[str, ProcessStatus]]:
        """
        BibTeXファイルから全エントリの状態を読み込み
        
        Args:
            bibtex_file: BibTeXファイルパス
            
        Returns:
            Dict[citation_key, Dict[process_type, status]]
        """
        try:
            entries = self.bibtex_parser.parse_file(bibtex_file)
            statuses = {}
            
            for citation_key, entry in entries.items():
                if not citation_key:
                    continue
                
                entry_statuses = {}
                for process_type, field_name in self.STATUS_FIELDS.items():
                    status_value = entry.get(field_name, ProcessStatus.PENDING.value)
                    try:
                        entry_statuses[process_type] = ProcessStatus.from_string(status_value)
                    except ValueError:
                        self.logger.warning(
                            f"Invalid status '{status_value}' for {citation_key}.{process_type}, "
                            f"defaulting to PENDING"
                        )
                        entry_statuses[process_type] = ProcessStatus.PENDING
                
                statuses[citation_key] = entry_statuses
            
            self.logger.info(f"Loaded statuses for {len(statuses)} papers from {bibtex_file}")
            return statuses
            
        except Exception as e:
            self.logger.error(f"Failed to load bib statuses: {e}")
            raise ObsClippingsError(f"Failed to load bib statuses: {e}")
    
    def update_status(self, bibtex_file: str, citation_key: str, 
                     process_type: str, status: ProcessStatus) -> bool:
        """
        特定の論文の特定の処理状態を更新
        
        Args:
            bibtex_file: BibTeXファイルパス
            citation_key: 論文のcitation key
            process_type: 処理タイプ ('organize', 'sync', 'fetch', 'parse')
            status: 新しい状態
            
        Returns:
            bool: 更新成功時True
        """
        try:
            if process_type not in self.STATUS_FIELDS:
                raise ValueError(f"Invalid process type: {process_type}")
            
            # BibTeXファイルを読み込み
            with open(bibtex_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            field_name = self.STATUS_FIELDS[process_type]
            
            # 該当エントリを探す
            entry_pattern = rf'(@\w+\{{{re.escape(citation_key)},.*?\n\}})'
            match = re.search(entry_pattern, content, re.DOTALL)
            
            if not match:
                raise ValueError(f"Citation key '{citation_key}' not found in {bibtex_file}")
            
            entry_content = match.group(1)
            
            # 既存の状態フィールドを更新または追加
            field_pattern = rf'{re.escape(field_name)}\s*=\s*\{{[^}}]*\}}'
            field_line = f'{field_name}={{{status.value}}}'
            
            if re.search(field_pattern, entry_content):
                # 既存フィールドを更新
                new_entry = re.sub(field_pattern, field_line, entry_content)
            else:
                # 新しいフィールドを追加（最後のフィールドの後に挿入）
                lines = entry_content.split('\n')
                if lines[-1].strip() == '}':
                    # 最後のフィールドを探して、カンマを追加してから新しいフィールドを挿入
                    for i in range(len(lines) - 2, -1, -1):
                        line = lines[i].strip()
                        if line and not line.startswith('@') and '=' in line:
                            # 最後のフィールド行を見つけた
                            if not line.endswith(','):
                                lines[i] = lines[i] + ','
                            break
                    lines.insert(-1, f'    {field_line}')
                    new_entry = '\n'.join(lines)
                else:
                    new_entry = entry_content
            
            # ファイル全体を更新
            new_content = content.replace(entry_content, new_entry)
            
            # ファイルに書き戻し
            with open(bibtex_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.logger.info(
                f"Updated status for {citation_key}.{process_type} = {status.value}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")
            return False
    
    def batch_update_statuses(self, bibtex_file: str, 
                            updates: Dict[str, Dict[str, ProcessStatus]]) -> bool:
        """
        複数の論文の状態を一括更新
        
        Args:
            bibtex_file: BibTeXファイルパス
            updates: Dict[citation_key, Dict[process_type, status]]
            
        Returns:
            bool: 更新成功時True
        """
        try:
            success_count = 0
            total_count = sum(len(statuses) for statuses in updates.values())
            
            for citation_key, status_updates in updates.items():
                for process_type, status in status_updates.items():
                    if self.update_status(bibtex_file, citation_key, process_type, status):
                        success_count += 1
            
            self.logger.info(
                f"Batch update completed: {success_count}/{total_count} updates successful"
            )
            return success_count == total_count
            
        except Exception as e:
            self.logger.error(f"Batch update failed: {e}")
            return False
    
    def get_papers_needing_processing(self, bibtex_file: str, process_type: str,
                                    include_failed: bool = True) -> List[str]:
        """
        指定された処理が必要な論文のリストを取得
        
        Args:
            bibtex_file: BibTeXファイルパス
            process_type: 処理タイプ
            include_failed: 失敗したものも含めるか
            
        Returns:
            List[citation_key]: 処理が必要な論文のリスト
        """
        try:
            statuses = self.load_bib_statuses(bibtex_file)
            needing_papers = []
            
            for citation_key, paper_statuses in statuses.items():
                status = paper_statuses.get(process_type, ProcessStatus.PENDING)
                
                if status == ProcessStatus.PENDING:
                    needing_papers.append(citation_key)
                elif include_failed and status == ProcessStatus.FAILED:
                    needing_papers.append(citation_key)
            
            self.logger.info(
                f"Found {len(needing_papers)} papers needing {process_type} processing"
            )
            return needing_papers
            
        except Exception as e:
            self.logger.error(f"Failed to get papers needing processing: {e}")
            return []
    
    def check_status_consistency(self, bibtex_file: str, 
                               clippings_dir: str) -> Dict[str, Any]:
        """
        状態の整合性をチェック
        
        Args:
            bibtex_file: BibTeXファイルパス
            clippings_dir: Clippingsディレクトリパス
            
        Returns:
            Dict: 整合性チェック結果
        """
        try:
            result = {
                'missing_directories': [],
                'orphaned_directories': [],
                'status_inconsistencies': []
            }
            
            # BibTeX内の論文とClippingsディレクトリの対応チェック
            statuses = self.load_bib_statuses(bibtex_file)
            
            if os.path.exists(clippings_dir):
                existing_dirs = {
                    d for d in os.listdir(clippings_dir)
                    if os.path.isdir(os.path.join(clippings_dir, d))
                }
            else:
                existing_dirs = set()
            
            bib_papers = set(statuses.keys())
            
            # BibTeXにあるがClippingsにないディレクトリ
            result['missing_directories'] = list(bib_papers - existing_dirs)
            
            # ClippingsにあるがBibTeXにないディレクトリ
            result['orphaned_directories'] = list(existing_dirs - bib_papers)
            
            # 状態の矛盾チェック（organize完了だがディレクトリがない等）
            for citation_key, paper_statuses in statuses.items():
                organize_status = paper_statuses.get('organize', ProcessStatus.PENDING)
                
                if organize_status == ProcessStatus.COMPLETED:
                    if citation_key not in existing_dirs:
                        result['status_inconsistencies'].append({
                            'citation_key': citation_key,
                            'issue': 'organize_completed_but_no_directory',
                            'description': f'Organize completed but {citation_key}/ directory missing'
                        })
            
            total_issues = (
                len(result['missing_directories']) +
                len(result['orphaned_directories']) +
                len(result['status_inconsistencies'])
            )
            
            self.logger.info(f"Status consistency check completed: {total_issues} issues found")
            return result
            
        except Exception as e:
            self.logger.error(f"Status consistency check failed: {e}")
            return {
                'missing_directories': [],
                'orphaned_directories': [],
                'status_inconsistencies': [],
                'error': str(e)
            }
    
    def reset_statuses(self, bibtex_file: str, target_papers: Optional[Union[str, List[str]]] = None) -> bool:
        """
        指定された論文（または全論文）の状態をリセット
        
        Args:
            bibtex_file: BibTeXファイルパス
            target_papers: リセット対象のcitation key（文字列またはリスト、Noneの場合は全論文）
            
        Returns:
            bool: リセット成功時True
        """
        try:
            if target_papers:
                # 特定の論文をリセット
                if isinstance(target_papers, str):
                    target_list = [target_papers]
                else:
                    target_list = target_papers
                
                updates = {}
                for citation_key in target_list:
                    updates[citation_key] = {
                        'organize': ProcessStatus.PENDING,
                        'sync': ProcessStatus.PENDING,
                        'fetch': ProcessStatus.PENDING,
                        'parse': ProcessStatus.PENDING
                    }
                
                success = self.batch_update_statuses(bibtex_file, updates)
                if success:
                    self.logger.info(f"Reset statuses for {len(target_list)} papers: {', '.join(target_list)}")
            else:
                # 全論文をリセット
                statuses = self.load_bib_statuses(bibtex_file)
                updates = {}
                for key in statuses.keys():
                    updates[key] = {
                        'organize': ProcessStatus.PENDING,
                        'sync': ProcessStatus.PENDING,
                        'fetch': ProcessStatus.PENDING,
                        'parse': ProcessStatus.PENDING
                    }
                success = self.batch_update_statuses(bibtex_file, updates)
                if success:
                    self.logger.info(f"Reset statuses for all {len(updates)} papers")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to reset statuses: {e}")
            return False
    
    def get_workflow_summary(self, bibtex_file: str) -> Dict[str, Any]:
        """
        ワークフロー全体の状態サマリーを取得
        
        Args:
            bibtex_file: BibTeXファイルパス
            
        Returns:
            Dict: 状態サマリー
        """
        try:
            statuses = self.load_bib_statuses(bibtex_file)
            
            summary = {
                'total_papers': len(statuses),
                'by_process': {},
                'ready_for_next_step': {}
            }
            
            # 各処理タイプごとの統計
            for process_type in self.STATUS_FIELDS.keys():
                counts = {
                    'pending': 0,
                    'completed': 0,
                    'failed': 0
                }
                
                for paper_statuses in statuses.values():
                    status = paper_statuses.get(process_type, ProcessStatus.PENDING)
                    counts[status.value] += 1
                
                summary['by_process'][process_type] = counts
            
            # 次のステップの準備ができている論文数
            summary['ready_for_next_step'] = {
                'organize': len([k for k, v in statuses.items() 
                               if v.get('organize') == ProcessStatus.PENDING]),
                'sync': len([k for k, v in statuses.items() 
                           if v.get('organize') == ProcessStatus.COMPLETED and 
                              v.get('sync') == ProcessStatus.PENDING]),
                'fetch': len([k for k, v in statuses.items() 
                            if v.get('sync') == ProcessStatus.COMPLETED and 
                               v.get('fetch') == ProcessStatus.PENDING]),
                'parse': len([k for k, v in statuses.items() 
                            if v.get('fetch') == ProcessStatus.COMPLETED and 
                               v.get('parse') == ProcessStatus.PENDING])
            }
            
            self.logger.info(f"Generated workflow summary for {summary['total_papers']} papers")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate workflow summary: {e}")
            return {'error': str(e)} 