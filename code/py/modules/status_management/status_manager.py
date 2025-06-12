#!/usr/bin/env python3
"""
状態管理機能 v3.0 - YAMLヘッダー方式

各論文の.mdファイルのYAMLヘッダーに処理状態を記録し、
Zoteroによる自動BibTeX再生成の影響を受けない永続的な状態管理を提供します。
"""

import os
import yaml
import re
import glob
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union
from pathlib import Path
from datetime import datetime, timezone

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
    YAMLヘッダーベースの状態管理システム v3.0
    
    各論文の処理状況（organize, sync, fetch, parse）を論文の.mdファイルの
    YAMLヘッダーに記録し、Zoteroの自動再生成に影響されない状態管理を実現します。
    """
    
    # 処理タイプ定義
    PROCESS_TYPES = ['organize', 'sync', 'fetch', 'ai-citation-support']
    
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
        
        self.logger.info("StatusManager v3.0 (YAML) initialized successfully")
    
    def get_md_file_path(self, clippings_dir: str, citation_key: str) -> Path:
        """
        citation keyに対応する.mdファイルパスを取得
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            citation_key: 論文のcitation key
            
        Returns:
            Path: .mdファイルのパス
        """
        return Path(clippings_dir) / citation_key / f"{citation_key}.md"
    
    def parse_yaml_header(self, md_file_path: Path) -> Dict[str, Any]:
        """
        .mdファイルからYAMLヘッダーを解析
        
        Args:
            md_file_path: .mdファイルのパス
            
        Returns:
            Dict: YAMLヘッダーの内容、存在しない場合は空辞書
        """
        try:
            if not md_file_path.exists():
                return {}
            
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAMLヘッダーを抽出（---で囲まれた部分）
            yaml_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            if not yaml_match:
                return {}
            
            yaml_content = yaml_match.group(1)
            
            # YAML解析
            parsed_yaml = yaml.safe_load(yaml_content)
            return parsed_yaml if parsed_yaml else {}
            
        except yaml.YAMLError as e:
            self.logger.warning(f"YAML parsing error in {md_file_path}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error parsing YAML header from {md_file_path}: {e}")
            return {}
    
    def write_yaml_header(self, md_file_path: Path, metadata: Dict[str, Any]) -> bool:
        """
        .mdファイルにYAMLヘッダーを書き込み
        
        Args:
            md_file_path: .mdファイルのパス
            metadata: 書き込むメタデータ
            
        Returns:
            bool: 書き込み成功時True
        """
        try:
            # ファイルが存在しない場合は作成せずにFalseを返す
            if not md_file_path.exists():
                self.logger.debug(f"Skipping YAML header write: file does not exist - {md_file_path}")
                return False
            
            # 既存のファイル内容を読み込み
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 既存のYAMLヘッダーを除去
            yaml_pattern = r'^---\n.*?\n---\n'
            content_without_yaml = re.sub(yaml_pattern, '', content, flags=re.DOTALL)
            
            # 新しいYAMLヘッダーを生成
            yaml_content = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
            
            # ファイルに書き込み
            new_content = f"---\n{yaml_content}---\n\n{content_without_yaml.lstrip()}"
            
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing YAML header to {md_file_path}: {e}")
            return False
    
    def ensure_yaml_header(self, md_file_path: Path, citation_key: str) -> bool:
        """
        YAMLヘッダーが存在しない場合は初期化
        
        Args:
            md_file_path: .mdファイルのパス
            citation_key: 論文のcitation key
            
        Returns:
            bool: 初期化成功時True
        """
        try:
            # ファイルが存在しない場合は初期化せずにFalseを返す
            if not md_file_path.exists():
                self.logger.debug(f"Skipping YAML header initialization: file does not exist - {md_file_path}")
                return False
                
            # 既存のYAMLヘッダーをチェック
            existing_metadata = self.parse_yaml_header(md_file_path)
            
            if 'processing_status' in existing_metadata:
                # 既に存在する場合は何もしない
                return True
            
            # 初期メタデータを作成（obsclippings_metadataなし）
            initial_metadata = {
                'citation_key': citation_key,
                'processing_status': {
                    'organize': ProcessStatus.PENDING.value,
                    'sync': ProcessStatus.PENDING.value,
                    'fetch': ProcessStatus.PENDING.value,
                    'ai-citation-support': ProcessStatus.PENDING.value
                },
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'workflow_version': '3.0'
            }
            
            # YAMLヘッダーを書き込み
            return self.write_yaml_header(md_file_path, initial_metadata)
            
        except Exception as e:
            self.logger.error(f"Error ensuring YAML header for {citation_key}: {e}")
            return False
    
    def load_md_statuses(self, clippings_dir: str) -> Dict[str, Dict[str, ProcessStatus]]:
        """
        Clippingsディレクトリから全論文の状態を読み込み
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            
        Returns:
            Dict[citation_key, Dict[process_type, status]]
        """
        try:
            statuses = {}
            
            if not os.path.exists(clippings_dir):
                self.logger.warning(f"Clippings directory does not exist: {clippings_dir}")
                return statuses
            
            # Clippingsディレクトリ内の各サブディレクトリを確認
            for item in os.listdir(clippings_dir):
                item_path = os.path.join(clippings_dir, item)
                if not os.path.isdir(item_path):
                    continue
                
                citation_key = item
                md_file_path = self.get_md_file_path(clippings_dir, citation_key)
                
                if not md_file_path.exists():
                    self.logger.debug(f"No .md file found for {citation_key}")
                    # .mdファイルがない場合は全てPENDINGとして扱う
                    statuses[citation_key] = {
                        process_type: ProcessStatus.PENDING 
                        for process_type in self.PROCESS_TYPES
                    }
                    continue
                
                # YAMLヘッダーを解析
                metadata = self.parse_yaml_header(md_file_path)
                
                if 'processing_status' not in metadata:
                    # YAMLヘッダーがない場合は初期化
                    self.ensure_yaml_header(md_file_path, citation_key)
                    metadata = self.parse_yaml_header(md_file_path)
                
                # 状態を抽出
                paper_statuses = {}
                processing_status = metadata.get('processing_status', {})
                
                for process_type in self.PROCESS_TYPES:
                    status_value = processing_status.get(process_type, ProcessStatus.PENDING.value)
                    try:
                        paper_statuses[process_type] = ProcessStatus.from_string(status_value)
                    except ValueError:
                        self.logger.warning(
                            f"Invalid status '{status_value}' for {citation_key}.{process_type}, "
                            f"defaulting to PENDING"
                        )
                        paper_statuses[process_type] = ProcessStatus.PENDING
                
                statuses[citation_key] = paper_statuses
            
            self.logger.info(f"Loaded statuses for {len(statuses)} papers from {clippings_dir}")
            return statuses
            
        except Exception as e:
            self.logger.error(f"Failed to load md statuses: {e}")
            raise ObsClippingsError(f"Failed to load md statuses: {e}")
    
    def update_status(self, clippings_dir: str, citation_key: str,
                     process_type: str, status: ProcessStatus) -> bool:
        """
        指定論文の状態を更新
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            citation_key: 論文のcitation key
            process_type: 処理タイプ ('organize', 'sync', 'fetch', 'ai-citation-support')
            status: 新しい状態
            
        Returns:
            bool: 更新成功時True
        """
        try:
            if process_type not in self.PROCESS_TYPES:
                raise ValueError(f"Invalid process type: {process_type}")
            
            md_file_path = self.get_md_file_path(clippings_dir, citation_key)
            
            # ファイルが存在しない場合は状態更新をスキップ
            if not md_file_path.exists():
                self.logger.debug(f"Skipping status update: markdown file does not exist - {citation_key}")
                return False
            
            # YAMLヘッダーが存在しない場合は初期化
            if not self.parse_yaml_header(md_file_path):
                self.ensure_yaml_header(md_file_path, citation_key)
            
            # 現在のメタデータを読み込み
            metadata = self.parse_yaml_header(md_file_path)
            
            if 'processing_status' not in metadata:
                self.logger.error(f"Failed to initialize YAML header for {citation_key}")
                return False
            
            # 状態を更新
            metadata['processing_status'][process_type] = status.value
            metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            # YAMLヘッダーを書き戻し
            success = self.write_yaml_header(md_file_path, metadata)
            
            if success:
                self.logger.info(
                    f"Updated status for {citation_key}.{process_type} = {status.value}"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")
            return False
    
    def batch_update_statuses(self, clippings_dir: str,
                            updates: Dict[str, Dict[str, ProcessStatus]]) -> bool:
        """
        複数論文の状態を一括更新
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            updates: Dict[citation_key, Dict[process_type, status]]
            
        Returns:
            bool: 更新成功時True
        """
        try:
            success_count = 0
            total_count = sum(len(statuses) for statuses in updates.values())
            
            for citation_key, status_updates in updates.items():
                for process_type, status in status_updates.items():
                    if self.update_status(clippings_dir, citation_key, process_type, status):
                        success_count += 1
            
            self.logger.info(
                f"Batch update completed: {success_count}/{total_count} updates successful"
            )
            return success_count == total_count
            
        except Exception as e:
            self.logger.error(f"Batch update failed: {e}")
            return False
    
    def get_papers_needing_processing(self, clippings_dir: str, process_type: str,
                                    target_papers: Optional[List[str]] = None,
                                    include_failed: bool = True) -> List[str]:
        """
        指定処理が必要な論文リストを取得
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            process_type: 処理タイプ
            target_papers: 対象論文リスト（None時は既存ディレクトリから取得）
            include_failed: 失敗したものも含めるか
            
        Returns:
            List[citation_key]: 処理が必要な論文のリスト
        """
        try:
            # organizeステップの場合は、既存のMarkdownファイルベースで処理対象を決定
            if process_type == 'organize':
                return self._get_papers_for_organize_step(clippings_dir, target_papers)
            
            # その他のステップは従来通り状態ベースで処理
            statuses = self.load_md_statuses(clippings_dir)
            needing_papers = []
            
            # target_papersが指定されていない場合は、既存の状態管理対象論文のみを使用
            if target_papers is None:
                target_papers = list(statuses.keys())
            
            for citation_key in target_papers:
                if citation_key not in statuses:
                    # 状態情報がない場合は処理対象とする
                    needing_papers.append(citation_key)
                    continue
                
                paper_statuses = statuses[citation_key]
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

    def _get_papers_for_organize_step(self, clippings_dir: str, 
                                     target_papers: Optional[List[str]] = None) -> List[str]:
        """
        organizeステップ専用の処理対象論文取得
        
        既存のMarkdownファイルが存在し、まだ整理されていない論文のみを対象とする
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト（None時は空リストを返す）
            
        Returns:
            List[citation_key]: organize処理が必要な論文のリスト
        """
        try:
            clippings_path = Path(clippings_dir)
            
            if not clippings_path.exists():
                self.logger.warning(f"Clippings directory does not exist: {clippings_dir}")
                return []
            
            # ルートレベルのMarkdownファイルを検索（まだ整理されていないファイル）
            root_md_files = [f for f in clippings_path.glob("*.md") if f.is_file()]
            
            if not root_md_files:
                self.logger.info("No unorganized markdown files found in root directory")
                return []
            
            self.logger.info(f"Found {len(root_md_files)} unorganized markdown files for organize step")
            
            # 既存のMarkdownファイルがある場合は、OrganizationWorkflowに処理を委ねる
            # target_papersが指定されている場合は、OrganizationWorkflowが実際のファイル照合を行う
            if target_papers:
                # OrganizationWorkflowが実際にファイル照合とマッチングを行うため、
                # target_papersをそのまま返す（実際の処理はOrganizationWorkflow内で行われる）
                return target_papers
            else:
                # target_papersが指定されていない場合は空リストを返す
                return []
            
        except Exception as e:
            self.logger.error(f"Failed to get papers for organize step: {e}")
            return []

    def reset_statuses(self, clippings_dir: str,
                      target_papers: Optional[Union[str, List[str]]] = None) -> bool:
        """
        状態をリセット
        
        Args:
            clippings_dir: Clippingsディレクトリパス
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
                        'ai-citation-support': ProcessStatus.PENDING
                    }
                
                success = self.batch_update_statuses(clippings_dir, updates)
                if success:
                    self.logger.info(f"Reset statuses for {len(target_list)} papers: {', '.join(target_list)}")
            else:
                # 全論文をリセット
                statuses = self.load_md_statuses(clippings_dir)
                updates = {}
                for key in statuses.keys():
                    updates[key] = {
                        'organize': ProcessStatus.PENDING,
                        'sync': ProcessStatus.PENDING,
                        'fetch': ProcessStatus.PENDING,
                        'ai-citation-support': ProcessStatus.PENDING
                    }
                success = self.batch_update_statuses(clippings_dir, updates)
                if success:
                    self.logger.info(f"Reset statuses for all {len(updates)} papers")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to reset statuses: {e}")
            return False
    
    def check_status_consistency(self, bibtex_file: str, 
                               clippings_dir: str) -> Dict[str, Any]:
        """
        BibTeX ↔ Clippings間の整合性チェック
        
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
            
            # BibTeX内の論文を取得
            bib_papers = set()
            if os.path.exists(bibtex_file):
                entries = self.bibtex_parser.parse_file(bibtex_file)
                bib_papers = set(entries.keys())
            
            # Clippingsディレクトリ内の論文を取得
            clippings_papers = set()
            if os.path.exists(clippings_dir):
                clippings_papers = {
                    d for d in os.listdir(clippings_dir)
                    if os.path.isdir(os.path.join(clippings_dir, d))
                }
            
            # BibTeXにあるがClippingsにないディレクトリ
            result['missing_directories'] = list(bib_papers - clippings_papers)
            
            # ClippingsにあるがBibTeXにないディレクトリ
            result['orphaned_directories'] = list(clippings_papers - bib_papers)
            
            # 状態の矛盾チェック（organize完了だがディレクトリがない等）
            statuses = self.load_md_statuses(clippings_dir)
            for citation_key, paper_statuses in statuses.items():
                organize_status = paper_statuses.get('organize', ProcessStatus.PENDING)
                
                if organize_status == ProcessStatus.COMPLETED:
                    if citation_key not in clippings_papers:
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
    
    def get_workflow_summary(self, clippings_dir: str) -> Dict[str, Any]:
        """
        ワークフロー全体の状態サマリーを取得
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            
        Returns:
            Dict: 状態サマリー
        """
        try:
            statuses = self.load_md_statuses(clippings_dir)
            
            summary = {
                'total_papers': len(statuses),
                'by_process': {},
                'ready_for_next_step': {}
            }
            
            # 各処理タイプごとの統計
            for process_type in self.PROCESS_TYPES:
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
                'ai-citation-support': len([k for k, v in statuses.items()
                                          if k in target_papers and
                                          v.get('ai-citation-support') == ProcessStatus.PENDING])
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get workflow summary: {e}")
            return {'error': str(e)}
    
    # 後方互換性のためのレガシーメソッド（BibTeX方式）
    def load_bib_statuses(self, bibtex_file: str) -> Dict[str, Dict[str, ProcessStatus]]:
        """
        後方互換性のためのレガシーメソッド
        YAMLヘッダー方式に移行してください
        """
        self.logger.warning("load_bib_statuses is deprecated. Use load_md_statuses instead.")
        return {} 