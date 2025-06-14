#!/usr/bin/env python3
"""
FileOrganizer - ファイル整理機能

ワークフローのorganizeステップを担当するクラス。
- citation_keyディレクトリ作成
- ファイル移動・リネーム
- 既存ファイル衝突回避
- YAMLヘッダー更新（processing_status.organize: completed）
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger
from ..shared_modules.exceptions import FileSystemError, ProcessingError, YAMLError
from ..shared_modules.file_utils import FileUtils, PathUtils, BackupManager
from ..shared_modules.bibtex_parser import BibTeXParser
from ..status_management_yaml.yaml_header_processor import YAMLHeaderProcessor


class FileOrganizer:
    """
    DOIマッチングベースのファイル整理クラス
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        FileOrganizerの初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('FileOrganizer')
        
        # 設定読み込み
        organize_config = config_manager.get_config().get('workflows', {}).get('organize', {})
        self.create_backup = organize_config.get('create_backup', True)
        self.handle_duplicates = organize_config.get('handle_duplicates', True)
        self.update_yaml_header = organize_config.get('update_yaml_header', True)
        
        # 依存モジュール初期化
        self.file_utils = FileUtils()
        self.path_utils = PathUtils()
        self.backup_manager = BackupManager()  # BackupManagerは引数なしで初期化
        self.bibtex_parser = BibTeXParser(logger.get_logger('BibTeXParser'))
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        
        self.logger.info("FileOrganizer initialized")
    
    def organize_workspace(self, workspace_path: str, bibtex_file: str, 
                          clippings_dir: str) -> Dict[str, Any]:
        """
        ワークスペース全体のorganize処理
        
        Args:
            workspace_path: ワークスペースパス
            bibtex_file: CurrentManuscript.bibファイルパス
            clippings_dir: Clippingsディレクトリパス
            
        Returns:
            Dict[str, Any]: 処理結果サマリー
        """
        try:
            self.logger.info(f"Starting workspace organize: {workspace_path}")
            
            # 1. CurrentManuscript.bibからDOI-citation_keyマッピング作成
            doi_mapping = self._create_doi_mapping(bibtex_file)
            self.logger.info(f"Created DOI mapping for {len(doi_mapping)} entries")
            
            # 2. Clippings/*.mdからDOI情報抽出
            markdown_dois = self._extract_markdown_dois(clippings_dir)
            self.logger.info(f"Found DOI information in {len(markdown_dois)} markdown files")
            
            # 3. DOIベースでの論文マッチング
            matched_papers = self._match_papers_by_doi(doi_mapping, markdown_dois)
            self.logger.info(f"Matched {len(matched_papers)} papers for processing")
            
            # 4. マッチした論文の整理処理
            results = {
                'status': 'success',
                'total_bibtex_entries': len(doi_mapping),
                'total_markdown_files': len(markdown_dois),
                'matched_papers': len(matched_papers),
                'processed_papers': 0,
                'skipped_papers': {
                    'missing_in_clippings': [],
                    'orphaned_in_clippings': [],
                    'no_doi_in_markdown': [],
                    'processing_failed': []
                },
                'execution_time': 0
            }
            
            start_time = datetime.now()
            
            # マッチした論文の処理
            for paper_info in matched_papers:
                try:
                    success = self._organize_matched_paper(paper_info, clippings_dir)
                    if success:
                        results['processed_papers'] += 1
                    else:
                        results['skipped_papers']['processing_failed'].append(paper_info)
                except Exception as e:
                    self.logger.error(f"Failed to organize paper {paper_info['citation_key']}: {e}")
                    results['skipped_papers']['processing_failed'].append(paper_info)
            
            # エッジケース検出
            self._detect_edge_cases(doi_mapping, markdown_dois, results)
            
            # 実行時間計算
            end_time = datetime.now()
            results['execution_time'] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Workspace organize completed: {results['processed_papers']} papers processed")
            return results
            
        except Exception as e:
            self.logger.error(f"Workspace organize failed: {e}")
            raise ProcessingError(
                f"Failed to organize workspace: {str(e)}",
                error_code="WORKSPACE_ORGANIZE_FAILED",
                context={
                    "workspace_path": workspace_path,
                    "bibtex_file": bibtex_file,
                    "clippings_dir": clippings_dir
                },
                cause=e
            )

    def _create_doi_mapping(self, bibtex_file: str) -> Dict[str, str]:
        """CurrentManuscript.bibからDOI-citation_keyマッピングを作成"""
        try:
            bibtex_entries = self.bibtex_parser.parse_file(bibtex_file)
            doi_mapping = {}
            
            for citation_key, entry_data in bibtex_entries.items():
                doi = entry_data.get('doi')
                if doi:
                    # DOI正規化
                    normalized_doi = self._normalize_doi(doi)
                    if normalized_doi:
                        doi_mapping[normalized_doi] = citation_key
                        
            return doi_mapping
            
        except Exception as e:
            self.logger.error(f"Failed to create DOI mapping: {e}")
            raise ProcessingError(
                f"Failed to create DOI mapping from {bibtex_file}: {str(e)}",
                error_code="DOI_MAPPING_CREATION_FAILED",
                context={"bibtex_file": bibtex_file},
                cause=e
            )

    def _extract_markdown_dois(self, clippings_dir: str) -> Dict[str, str]:
        """Clippings/*.mdからDOI情報を抽出"""
        try:
            clippings_path = Path(clippings_dir)
            markdown_dois = {}
            
            # .mdファイルを再帰的に検索
            for md_file in clippings_path.rglob("*.md"):
                try:
                    yaml_header, _ = self.yaml_processor.parse_yaml_header(md_file)
                    doi = yaml_header.get('doi')
                    
                    if doi:
                        normalized_doi = self._normalize_doi(doi)
                        if normalized_doi:
                            markdown_dois[str(md_file)] = normalized_doi
                            
                except Exception as e:
                    self.logger.warning(f"Failed to extract DOI from {md_file}: {e}")
                    continue
                    
            return markdown_dois
            
        except Exception as e:
            self.logger.error(f"Failed to extract markdown DOIs: {e}")
            raise ProcessingError(
                f"Failed to extract DOIs from {clippings_dir}: {str(e)}",
                error_code="MARKDOWN_DOI_EXTRACTION_FAILED",
                context={"clippings_dir": clippings_dir},
                cause=e
            )

    def _match_papers_by_doi(self, doi_mapping: Dict[str, str], 
                            markdown_dois: Dict[str, str]) -> List[Dict]:
        """DOIベースでの論文マッチング"""
        matched_papers = []
        
        for file_path, md_doi in markdown_dois.items():
            if md_doi in doi_mapping:
                citation_key = doi_mapping[md_doi]
                matched_papers.append({
                    'file_path': file_path,
                    'doi': md_doi,
                    'citation_key': citation_key
                })
                
        return matched_papers

    def _organize_matched_paper(self, paper_info: Dict, clippings_dir: str) -> bool:
        """マッチした論文の整理処理"""
        try:
            file_path = Path(paper_info['file_path'])
            citation_key = paper_info['citation_key']
            
            self.logger.info(f"Organizing paper: {citation_key}")
            
            # citation_keyディレクトリ作成
            target_dir = self.create_citation_directory(clippings_dir, citation_key)
            target_file_path = Path(target_dir) / f"{citation_key}.md"
            
            # YAMLヘッダー読み込みと更新
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            yaml_header['citation_key'] = citation_key
            
            if self.update_yaml_header:
                yaml_header = self._update_organize_status(yaml_header)
            
            # 衝突処理
            if target_file_path.exists() and self.handle_duplicates:
                target_file_path = self._handle_file_collision(target_file_path, file_path)
            
            # バックアップ作成（必要に応じて）
            if self.create_backup and target_file_path.exists():
                backup_path = self.backup_manager.create_backup(str(target_file_path))
                self.logger.info(f"Backup created: {backup_path}")
            
            # ファイル移動と内容更新
            self.yaml_processor.write_yaml_header(target_file_path, yaml_header, content)
            
            # 元ファイル削除（移動が成功した場合）
            if target_file_path.exists() and file_path != target_file_path:
                file_path.unlink()
                self.logger.info(f"Moved file from {file_path} to {target_file_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to organize paper {paper_info['citation_key']}: {e}")
            return False

    def _detect_edge_cases(self, doi_mapping: Dict[str, str], 
                          markdown_dois: Dict[str, str], results: Dict[str, Any]):
        """エッジケース検出"""
        # missing_in_clippings: BibTeXにあるがMarkdownにない
        bibtex_dois = set(doi_mapping.keys())
        markdown_doi_values = set(markdown_dois.values())
        
        missing_dois = bibtex_dois - markdown_doi_values
        for doi in missing_dois:
            citation_key = doi_mapping[doi]
            results['skipped_papers']['missing_in_clippings'].append({
                'citation_key': citation_key,
                'doi': doi
            })
            self.logger.warning(f"Missing markdown file for: {citation_key} (DOI: {doi})")
        
        # orphaned_in_clippings: MarkdownにあるがBibTeXにない
        orphaned_dois = markdown_doi_values - bibtex_dois
        for file_path, doi in markdown_dois.items():
            if doi in orphaned_dois:
                results['skipped_papers']['orphaned_in_clippings'].append({
                    'file_path': file_path,
                    'doi': doi
                })
                self.logger.warning(f"Orphaned markdown file: {file_path} (DOI: {doi})")

    def _normalize_doi(self, doi: str) -> Optional[str]:
        """DOI正規化"""
        if not doi:
            return None
            
        # 基本的な正規化
        normalized = doi.strip().lower()
        
        # URLプレフィックス除去
        if normalized.startswith('https://doi.org/'):
            normalized = normalized[16:]
        elif normalized.startswith('http://doi.org/'):
            normalized = normalized[15:]
        elif normalized.startswith('doi:'):
            normalized = normalized[4:]
            
        # 10.で始まらない場合は無効
        if not normalized.startswith('10.'):
            return None
            
        return normalized

    def organize_file(self, file_path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
        """
        単一ファイルのorganize処理
        
        Args:
            file_path: 整理対象ファイルのパス
            base_dir: ベースディレクトリ（通常はClippingsディレクトリ）
            
        Returns:
            bool: 処理成功時True
            
        Raises:
            FileSystemError: ファイル操作エラー
            ProcessingError: 処理エラー
        """
        try:
            file_path = Path(file_path)
            base_dir = Path(base_dir)
            
            self.logger.info(f"Starting organize process for: {file_path}")
            
            # ファイル存在確認
            if not file_path.exists():
                raise FileSystemError(
                    f"Source file not found: {file_path}",
                    error_code="SOURCE_FILE_NOT_FOUND",
                    context={"file_path": str(file_path)}
                )
            
            # YAMLヘッダー読み込みとcitation_key抽出
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            citation_key = yaml_header.get('citation_key')
            
            if not citation_key:
                # ファイル名からcitation_key推測を試行
                citation_key = self.path_utils.get_citation_key_from_filename(file_path.name)
                if not citation_key:
                    raise ProcessingError(
                        f"Cannot determine citation_key for file: {file_path}",
                        error_code="CITATION_KEY_NOT_FOUND",
                        context={"file_path": str(file_path)}
                    )
                
                # YAMLヘッダーにcitation_keyを追加
                yaml_header['citation_key'] = citation_key
                self.logger.info(f"Inferred citation_key: {citation_key}")
            
            # citation_keyディレクトリ作成
            target_dir = self.create_citation_directory(str(base_dir), citation_key)
            target_dir = Path(target_dir)
            
            # 移動先ファイルパス決定
            target_file_path = target_dir / f"{citation_key}.md"
            
            # 衝突処理
            if target_file_path.exists() and self.handle_duplicates:
                target_file_path = self._handle_file_collision(target_file_path, file_path)
            
            # バックアップ作成（必要に応じて）
            if self.create_backup and target_file_path.exists():
                backup_path = self.backup_manager.create_backup(str(target_file_path))
                self.logger.info(f"Backup created: {backup_path}")
            
            # YAMLヘッダー更新
            if self.update_yaml_header:
                yaml_header = self._update_organize_status(yaml_header)
            
            # ファイル移動と内容更新
            # アトミック書き込みで移動先に保存
            self.yaml_processor.write_yaml_header(target_file_path, yaml_header, content)
            
            # 元ファイル削除（移動が成功した場合）
            if target_file_path.exists() and file_path != target_file_path:
                file_path.unlink()
                self.logger.info(f"Moved file from {file_path} to {target_file_path}")
            
            self.logger.info(f"Organize process completed for: {citation_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to organize file {file_path}: {str(e)}")
            if isinstance(e, (FileSystemError, ProcessingError, YAMLError)):
                raise
            raise ProcessingError(
                f"Unexpected error during organize: {str(e)}",
                error_code="ORGANIZE_UNEXPECTED_ERROR",
                context={"file_path": str(file_path)},
                cause=e
            )
    
    def create_citation_directory(self, base_dir: Union[str, Path], citation_key: str) -> str:
        """
        citation_keyベースのディレクトリを作成
        
        Args:
            base_dir: ベースディレクトリパス
            citation_key: 論文の識別キー
            
        Returns:
            str: 作成されたディレクトリパス
            
        Raises:
            FileSystemError: ディレクトリ作成エラー
        """
        try:
            base_path = Path(base_dir)
            
            # 安全なディレクトリ名生成
            safe_citation_key = self.path_utils.generate_safe_directory_name(citation_key)
            target_dir = base_path / safe_citation_key
            
            # ディレクトリ作成
            self.file_utils.ensure_directory(target_dir)
            
            self.logger.debug(f"Created citation directory: {target_dir}")
            return str(target_dir)
            
        except Exception as e:
            raise FileSystemError(
                f"Failed to create citation directory: {str(e)}",
                error_code="CITATION_DIRECTORY_CREATION_FAILED",
                context={
                    "base_dir": str(base_dir),
                    "citation_key": citation_key
                },
                cause=e
            )
    
    def organize_multiple_files(self, file_paths: List[Union[str, Path]], 
                              base_dir: Union[str, Path]) -> Dict[str, bool]:
        """
        複数ファイルの一括organize処理
        
        Args:
            file_paths: 整理対象ファイルパスのリスト
            base_dir: ベースディレクトリ
            
        Returns:
            Dict[str, bool]: ファイルパス -> 処理結果の辞書
        """
        results = {}
        
        for file_path in file_paths:
            try:
                result = self.organize_file(file_path, base_dir)
                results[str(file_path)] = result
            except Exception as e:
                self.logger.error(f"Failed to organize {file_path}: {str(e)}")
                results[str(file_path)] = False
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(file_paths)
        
        self.logger.info(f"Batch organize completed: {success_count}/{total_count} files processed successfully")
        
        return results
    
    def _handle_file_collision(self, target_path: Path, source_path: Path) -> Path:
        """
        ファイル衝突時の処理
        
        Args:
            target_path: 移動先ファイルパス
            source_path: 移動元ファイルパス
            
        Returns:
            Path: 最終的な移動先パス
        """
        try:
            # タイムスタンプ付きファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = target_path.stem
            suffix = target_path.suffix
            
            # 衝突回避ファイル名生成
            collision_avoided_path = target_path.parent / f"{stem}_{timestamp}{suffix}"
            
            # 既存ファイルのバックアップ作成
            if self.create_backup:
                backup_path = self.backup_manager.create_backup(str(target_path))
                self.logger.info(f"Created backup for existing file: {backup_path}")
            
            self.logger.warning(f"File collision detected. Using alternative name: {collision_avoided_path}")
            
            return collision_avoided_path
            
        except Exception as e:
            self.logger.error(f"Failed to handle file collision: {str(e)}")
            # フォールバック: 元のパスを返す（上書きされる）
            return target_path
    
    def _update_organize_status(self, yaml_header: Dict[str, Any]) -> Dict[str, Any]:
        """
        YAMLヘッダーのorganize処理状態を更新
        
        Args:
            yaml_header: 更新対象のYAMLヘッダー
            
        Returns:
            Dict[str, Any]: 更新されたYAMLヘッダー
        """
        current_time = datetime.now().isoformat()
        
        # processing_statusセクションの確認・初期化
        if 'processing_status' not in yaml_header:
            yaml_header['processing_status'] = {}
        
        # organize処理状態を完了に設定
        yaml_header['processing_status']['organize'] = 'completed'
        
        # 最終更新時刻を更新
        yaml_header['last_updated'] = current_time
        
        # workflow_versionの確認
        if 'workflow_version' not in yaml_header:
            yaml_header['workflow_version'] = '3.2'
        
        return yaml_header
    
    def get_organize_summary(self, base_dir: Union[str, Path]) -> Dict[str, Any]:
        """
        organize処理の概要情報を取得
        
        Args:
            base_dir: ベースディレクトリ
            
        Returns:
            Dict[str, Any]: 概要情報
        """
        try:
            base_path = Path(base_dir)
            
            # 統計情報収集
            organized_dirs = [d for d in base_path.iterdir() if d.is_dir()]
            organized_files = []
            pending_files = []
            
            for md_file in base_path.rglob("*.md"):
                try:
                    yaml_header, _ = self.yaml_processor.parse_yaml_header(md_file)
                    status = yaml_header.get('processing_status', {}).get('organize', 'pending')
                    
                    if status == 'completed':
                        organized_files.append(str(md_file))
                    else:
                        pending_files.append(str(md_file))
                        
                except Exception:
                    pending_files.append(str(md_file))
            
            summary = {
                'total_directories': len(organized_dirs),
                'organized_files': len(organized_files),
                'pending_files': len(pending_files),
                'organization_rate': len(organized_files) / (len(organized_files) + len(pending_files)) if (len(organized_files) + len(pending_files)) > 0 else 0,
                'directories': [d.name for d in organized_dirs],
                'pending_file_paths': pending_files
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate organize summary: {str(e)}")
            return {
                'error': str(e),
                'total_directories': 0,
                'organized_files': 0,
                'pending_files': 0,
                'organization_rate': 0
            } 