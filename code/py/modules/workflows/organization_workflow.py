"""
ファイル整理ワークフロー

BibTeX解析からMarkdownファイル検索、ファイル照合、整理実行までの
一連のワークフローを管理します。
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from ..shared.bibtex_parser import BibTeXParser
from ..shared.utils import ProgressTracker, confirm_action
from ..rename_mkdir_citation_key.file_matcher import FileMatcher
from ..rename_mkdir_citation_key.markdown_manager import MarkdownManager
from ..rename_mkdir_citation_key.directory_organizer import DirectoryOrganizer


class OrganizationWorkflow:
    """ファイル整理ワークフロー"""
    
    def __init__(self, config_manager, logger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ロガーインスタンス
        """
        self.config = config_manager.get_rename_mkdir_config()
        self.logger = logger.get_logger('OrganizationWorkflow')
        
        # コンポーネントの初期化
        self.bibtex_parser = BibTeXParser()
        self.file_matcher = FileMatcher(
            similarity_threshold=self.config.get('similarity_threshold', 0.8),
            case_sensitive=self.config.get('case_sensitive_matching', False),
            doi_matching_enabled=self.config.get('doi_matching_enabled', True),
            title_fallback_enabled=self.config.get('title_fallback_enabled', True),
            title_sync_enabled=self.config.get('title_sync_enabled', True)
        )
        self.markdown_manager = MarkdownManager(
            clippings_dir=self.config.get('clippings_dir'),
            backup_dir=self.config.get('backup_dir', './backups/')
        )
        self.directory_organizer = DirectoryOrganizer(
            base_dir=self.config.get('clippings_dir')
        )
        
    def execute(self, **options) -> Tuple[bool, Dict[str, Any]]:
        """
        ファイル整理ワークフローを実行
        
        Args:
            **options: 実行オプション
            
        Returns:
            (成功フラグ, 実行結果詳細)
        """
        self.logger.info("Starting file organization workflow")
        
        results = {
            "stage": "initialization",
            "success": False,
            "statistics": {}
        }
        
        try:
            # Stage 1: BibTeX解析（共通）
            results["stage"] = "bibtex_parsing"
            bib_entries = self._parse_bibtex_file()
            results["bib_entries_count"] = len(bib_entries)
            self.logger.info(f"Parsed {len(bib_entries)} BibTeX entries")
            
            if not bib_entries:
                results["error"] = "No BibTeX entries found"
                return False, results
            
            # Stage 2: Markdownファイル検索
            results["stage"] = "markdown_discovery"
            md_files = self._discover_markdown_files()
            results["md_files_count"] = len(md_files)
            self.logger.info(f"Found {len(md_files)} Markdown files to process")
            
            if not md_files:
                results["error"] = "No Markdown files found to organize"
                return False, results
            
            # Stage 3: ファイル照合
            results["stage"] = "file_matching"
            matches = self._match_files(md_files, bib_entries, options)
            results["matches_count"] = len(matches)
            self.logger.info(f"Matched {len(matches)} files")
            
            if not matches:
                results["warning"] = "No files matched the similarity threshold"
                results["success"] = True  # 技術的には成功
                return True, results
            
            # Stage 4: ユーザー確認（オプション）
            results["stage"] = "user_confirmation"
            if not options.get('auto_approve', self.config.get('auto_approve', False)):
                approved_matches = self._user_confirmation(matches, bib_entries)
            else:
                approved_matches = matches
            results["approved_count"] = len(approved_matches)
            self.logger.info(f"Approved {len(approved_matches)} file operations")
            
            if not approved_matches:
                results["warning"] = "No file operations were approved"
                results["success"] = True
                return True, results
            
            # Stage 5: ファイル整理実行
            results["stage"] = "file_organization"
            org_results = self._organize_files(approved_matches, options)
            results.update(org_results)
            
            # Stage 6: クリーンアップ
            results["stage"] = "cleanup"
            cleanup_results = self._cleanup_directories(options)
            results.update(cleanup_results)
            
            results["success"] = True
            self.logger.info("File organization workflow completed successfully")
            return True, results
            
        except Exception as e:
            self.logger.error(f"File organization workflow failed: {e}")
            results["error"] = str(e)
            return False, results
    
    def _parse_bibtex_file(self) -> Dict[str, Dict[str, str]]:
        """
        BibTeXファイル解析の実行
        
        Returns:
            解析されたBibTeXエントリ
        """
        bibtex_file = self.config.get('bibtex_file')
        if not bibtex_file:
            raise ValueError("BibTeX file path not configured")
        
        if not Path(bibtex_file).exists():
            raise FileNotFoundError(f"BibTeX file not found: {bibtex_file}")
        
        self.logger.info(f"Parsing BibTeX file: {bibtex_file}")
        return self.bibtex_parser.parse_file(bibtex_file)
    
    def _discover_markdown_files(self) -> List[str]:
        """
        Markdownファイル検索の実行
        
        Returns:
            Markdownファイルパスのリスト（ルートレベルのみ）
        """
        self.logger.info("Discovering Markdown files")
        
        # ルートレベルのファイルのみを対象（増分処理）
        all_files = self.markdown_manager.get_markdown_files(root_only=True)
        
        # 既に整理済みのファイルを除外
        unorganized_files = []
        for file_path in all_files:
            if not self.markdown_manager.is_already_organized(file_path):
                unorganized_files.append(file_path)
        
        self.logger.info(
            f"Found {len(all_files)} total Markdown files, "
            f"{len(unorganized_files)} need organization"
        )
        
        return unorganized_files
    
    def _process_title_synchronization(self, 
                                     matches: Dict[str, str], 
                                     bib_entries: Dict[str, Dict[str, str]]) -> None:
        """
        マッチしたファイルのタイトル同期処理
        
        Args:
            matches: 照合結果 {ファイルパス: citation_key}
            bib_entries: BibTeX項目の辞書
        """
        self.logger.info("Processing title synchronization for matched files")
        
        synchronized_count = 0
        for file_path, citation_key in matches.items():
            bib_entry = bib_entries.get(citation_key, {})
            
            if self.file_matcher.process_matched_file(file_path, citation_key, bib_entry):
                synchronized_count += 1
            else:
                self.logger.warning(f"Failed to synchronize title for {file_path}")
        
        self.logger.info(f"Synchronized titles for {synchronized_count}/{len(matches)} files")
    
    def _match_files(self, 
                    md_files: List[str], 
                    bib_entries: Dict[str, Dict[str, str]], 
                    options: Dict[str, Any]) -> Dict[str, str]:
        """
        ファイル照合の実行
        
        Args:
            md_files: Markdownファイルパスのリスト
            bib_entries: BibTeX項目の辞書
            options: 実行オプション
            
        Returns:
            照合結果 {ファイルパス: citation_key}
        """
        self.logger.info(f"Matching {len(md_files)} files against {len(bib_entries)} BibTeX entries")
        
        # オプションからマッチング設定を更新
        if options.get('disable_doi_matching', False):
            self.file_matcher.doi_matching_enabled = False
            self.file_matcher.title_fallback_enabled = True  # DOI無効時はタイトル照合を有効
        
        if options.get('disable_title_sync', False):
            self.file_matcher.title_sync_enabled = False
        
        # カスタム閾値の適用
        custom_threshold = options.get('threshold', options.get('similarity_threshold'))
        if custom_threshold is not None:
            self.file_matcher.similarity_threshold = float(custom_threshold)
        
        # ファイル照合を実行
        matches = self.file_matcher.match_files_to_citations(md_files, bib_entries)
        
        # タイトル同期処理（有効化されている場合）
        if self.file_matcher.title_sync_enabled:
            self._process_title_synchronization(matches, bib_entries)
        
        # 照合結果の検証
        valid_matches, warnings = self.file_matcher.validate_matches(matches, bib_entries)
        
        # 警告をログ出力
        for warning in warnings:
            self.logger.warning(warning)
        
        # 統計情報をログ出力
        self._log_matching_statistics(md_files, valid_matches, bib_entries)
        
        return valid_matches
    
    def _user_confirmation(self, 
                          matches: Dict[str, str], 
                          bib_entries: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """
        ユーザー確認の実行
        
        Args:
            matches: 照合結果
            bib_entries: BibTeX項目の辞書
            
        Returns:
            承認された照合結果
        """
        self.logger.info("Requesting user confirmation for file operations")
        
        if not matches:
            return {}
        
        # 確認用の表示を作成
        print("\nFile Organization Plan:")
        print("=" * 50)
        
        for i, (file_path, citation_key) in enumerate(matches.items(), 1):
            filename = Path(file_path).name
            title = bib_entries.get(citation_key, {}).get('title', 'Unknown title')
            
            print(f"[{i:2d}] {filename}")
            print(f"     → {citation_key}/")
            print(f"     Title: {title[:60]}{'...' if len(title) > 60 else ''}")
            print()
        
        # 全体確認
        if confirm_action(f"Organize {len(matches)} files as shown above?"):
            return matches
        else:
            # 個別確認モード
            return self._selective_confirmation(matches, bib_entries)
    
    def _selective_confirmation(self, 
                               matches: Dict[str, str], 
                               bib_entries: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """
        個別ファイル確認
        
        Args:
            matches: 照合結果
            bib_entries: BibTeX項目の辞書
            
        Returns:
            選択的に承認された照合結果
        """
        approved = {}
        
        print("\nSelective confirmation mode:")
        for file_path, citation_key in matches.items():
            filename = Path(file_path).name
            title = bib_entries.get(citation_key, {}).get('title', 'Unknown title')
            
            print(f"\nFile: {filename}")
            print(f"Destination: {citation_key}/")
            print(f"Title: {title}")
            
            if confirm_action("Organize this file?"):
                approved[file_path] = citation_key
            else:
                self.logger.info(f"Skipped: {filename}")
        
        return approved
    
    def _organize_files(self, matches: Dict[str, str], options: Dict[str, Any]) -> Dict[str, Any]:
        """
        ファイル整理の実行
        
        Args:
            matches: 承認された照合結果
            options: 実行オプション
            
        Returns:
            整理結果の詳細
        """
        self.logger.info(f"Organizing {len(matches)} files")
        
        # オプションの適用
        backup_enabled = options.get('backup', self.config.get('backup_enabled', True))
        dry_run = options.get('dry_run', self.config.get('dry_run', False))
        
        # ディレクトリの事前準備
        if self.config.get('create_directories', True):
            self._prepare_directories(matches, dry_run)
        
        # ファイル移動のリストを作成
        file_moves = [(file_path, citation_key) for file_path, citation_key in matches.items()]
        
        # 進捗追跡
        progress = ProgressTracker(len(file_moves), "Organizing files")
        
        # 一括ファイル移動を実行
        org_stats = self.markdown_manager.batch_move_files(
            file_moves,
            backup=backup_enabled,
            dry_run=dry_run
        )
        
        progress.finish(org_stats["success"], org_stats["failed"])
        
        # 結果をログ出力
        self.logger.info(
            f"File organization completed: "
            f"{org_stats['success']} successful, "
            f"{org_stats['failed']} failed, "
            f"{org_stats['skipped']} skipped"
        )
        
        return {
            "organized_files": org_stats["success"],
            "failed_files": org_stats["failed"],
            "skipped_files": org_stats["skipped"],
            "created_directories": org_stats["directories_created"],
            "backup_enabled": backup_enabled
        }
    
    def _prepare_directories(self, matches: Dict[str, str], dry_run: bool = False):
        """
        ディレクトリの事前準備
        
        Args:
            matches: 照合結果
            dry_run: ドライランモード
        """
        unique_citations = set(matches.values())
        
        if dry_run:
            self.logger.info(f"[DRY RUN] Would create {len(unique_citations)} directories")
            return
        
        # ディレクトリ作成の準備
        preparation_results = self.directory_organizer.prepare_directories_for_files(matches)
        
        success_count = sum(1 for success in preparation_results.values() if success)
        self.logger.info(f"Prepared {success_count}/{len(unique_citations)} directories")
    
    def _cleanup_directories(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        ディレクトリクリーンアップの実行
        
        Args:
            options: 実行オプション
            
        Returns:
            クリーンアップ結果
        """
        cleanup_enabled = self.config.get('cleanup_empty_dirs', True)
        dry_run = options.get('dry_run', self.config.get('dry_run', False))
        
        if not cleanup_enabled or dry_run:
            return {"cleaned_directories": 0}
        
        self.logger.info("Cleaning up empty directories")
        cleaned_count = self.directory_organizer.cleanup_empty_directories()
        
        self.logger.info(f"Cleaned up {cleaned_count} empty directories")
        
        return {"cleaned_directories": cleaned_count}
    
    def _log_matching_statistics(self, 
                                md_files: List[str], 
                                matches: Dict[str, str], 
                                bib_entries: Dict[str, Dict[str, str]]):
        """
        照合統計をログ出力
        
        Args:
            md_files: 対象Markdownファイル
            matches: 照合結果
            bib_entries: BibTeX項目
        """
        total_files = len(md_files)
        matched_files = len(matches)
        unmatched_files = total_files - matched_files
        
        self.logger.info(
            f"Matching statistics: "
            f"{matched_files}/{total_files} files matched "
            f"({(matched_files/total_files*100):.1f}% success rate)"
        )
        
        if unmatched_files > 0:
            self.logger.info(f"{unmatched_files} files did not meet similarity threshold")
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """
        ワークフローの統計情報を取得
        
        Returns:
            統計情報
        """
        return {
            "workflow_type": "file_organization",
            "similarity_threshold": self.config.get('similarity_threshold', 0.8),
            "auto_approve": self.config.get('auto_approve', False),
            "backup_enabled": self.config.get('backup_enabled', True),
            "create_directories": self.config.get('create_directories', True),
            "cleanup_empty_dirs": self.config.get('cleanup_empty_dirs', True)
        }


# ヘルパー関数
def validate_organization_workflow_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Organization Workflowの設定を検証
    
    Args:
        config: 設定辞書
        
    Returns:
        (妥当性, エラーメッセージリスト)
    """
    errors = []
    
    # 必須設定の確認
    required_configs = ['bibtex_file', 'clippings_dir']
    for key in required_configs:
        if key not in config:
            errors.append(f"Missing required config: {key}")
    
    # ディレクトリの存在確認
    if 'clippings_dir' in config:
        clippings_dir = config['clippings_dir']
        if not Path(clippings_dir).exists():
            errors.append(f"Clippings directory not found: {clippings_dir}")
    
    # BibTeXファイルの存在確認
    if 'bibtex_file' in config:
        bibtex_file = config['bibtex_file']
        if not Path(bibtex_file).exists():
            errors.append(f"BibTeX file not found: {bibtex_file}")
    
    # 数値設定の検証
    if 'similarity_threshold' in config:
        try:
            threshold = float(config['similarity_threshold'])
            if not (0.0 <= threshold <= 1.0):
                errors.append("similarity_threshold must be between 0.0 and 1.0")
        except (TypeError, ValueError):
            errors.append("similarity_threshold must be a number")
    
    return len(errors) == 0, errors


def create_organization_workflow_summary(results: Dict[str, Any]) -> str:
    """
    Organization Workflowの結果サマリーを作成
    
    Args:
        results: ワークフロー実行結果
        
    Returns:
        サマリー文字列
    """
    lines = ["File Organization Workflow Summary", "=" * 40]
    
    if results.get("success"):
        lines.append("Status: COMPLETED")
        
        # 基本統計
        total_files = results.get("md_files_count", 0)
        matches = results.get("matches_count", 0)
        approved = results.get("approved_count", 0)
        organized = results.get("organized_files", 0)
        
        lines.extend([
            f"Markdown files found: {total_files}",
            f"Files matched: {matches}",
            f"Operations approved: {approved}",
            f"Files organized: {organized}"
        ])
        
        # 成功率
        if total_files > 0:
            success_rate = (organized / total_files) * 100
            lines.append(f"Organization rate: {success_rate:.1f}%")
        
        # 詳細統計
        failed = results.get("failed_files", 0)
        skipped = results.get("skipped_files", 0)
        created_dirs = results.get("created_directories", 0)
        cleaned_dirs = results.get("cleaned_directories", 0)
        
        if failed > 0 or skipped > 0:
            lines.append(f"\nAdditional details:")
            if failed > 0:
                lines.append(f"  Failed operations: {failed}")
            if skipped > 0:
                lines.append(f"  Skipped files: {skipped}")
        
        if created_dirs > 0 or cleaned_dirs > 0:
            lines.append(f"\nDirectory operations:")
            if created_dirs > 0:
                lines.append(f"  Created directories: {created_dirs}")
            if cleaned_dirs > 0:
                lines.append(f"  Cleaned directories: {cleaned_dirs}")
                
    else:
        lines.append("Status: FAILED")
        error = results.get("error", "Unknown error")
        lines.append(f"Error: {error}")
        
        # 警告がある場合
        warning = results.get("warning")
        if warning:
            lines.append(f"Warning: {warning}")
    
    return "\n".join(lines)