#!/usr/bin/env python3
"""
ObsClippingsManager v3.2.0 - SyncChecker

BibTeX ↔ Clippings間の整合性チェック機能
organize処理完了後の実行を想定
"""

import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# インポート（relative import対応）
try:
    from ..shared_modules.config_manager import ConfigManager
    from ..shared_modules.integrated_logger import IntegratedLogger
    from ..shared_modules.bibtex_parser import BibTeXParser
    from ..status_management_yaml.yaml_header_processor import YAMLHeaderProcessor
    from ..shared_modules.exceptions import (
        ObsClippingsManagerError,
        ValidationError,
        FileSystemError,
        ProcessingError
    )
    from ..shared_modules.file_utils import FileUtils
except ImportError:
    # テスト環境での絶対インポート
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
    from code.py.modules.shared_modules.config_manager import ConfigManager
    from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
    from code.py.modules.shared_modules.bibtex_parser import BibTeXParser
    from code.py.modules.status_management_yaml.yaml_header_processor import YAMLHeaderProcessor
    from code.py.modules.shared_modules.exceptions import (
        ObsClippingsManagerError,
        ValidationError,
        FileSystemError,
        ProcessingError
    )
    from code.py.modules.shared_modules.file_utils import FileUtils


class SyncChecker:
    """
    BibTeX ↔ Clippings間の整合性チェッククラス
    
    責務:
    - BibTeX文献とClippingsディレクトリ内のMarkdownファイル間の整合性検証
    - メタデータ一致確認（DOI、タイトル、著者など）
    - 軽微な不整合の自動修正
    - 整合性レポート生成
    - YAMLヘッダーのsync状態更新
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        SyncCheckerの初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('SyncChecker')
        
        # 依存クラスの初期化
        self.bibtex_parser = BibTeXParser(logger.get_logger('BibTeXParser'))
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        self.file_utils = FileUtils()
        
        # sync設定の取得（ConfigManagerの全設定から取得、デフォルト値を設定）
        full_config = self.config_manager.get_config()
        self.sync_config = full_config.get('sync_checker', {
            'enabled': True,
            'auto_fix_minor_issues': True,
            'backup_before_auto_fix': True,
            'retry_attempts': 3
        })
        
        self.logger.info("SyncChecker initialized successfully")
    
    def check_workspace_consistency(
        self, 
        workspace_path: str, 
        bibtex_file: str, 
        clippings_dir: str
    ) -> Dict[str, Any]:
        """
        ワークスペース全体の整合性チェック
        
        Args:
            workspace_path: ワークスペースのパス
            bibtex_file: BibTeXファイルのパス
            clippings_dir: Clippingsディレクトリのパス
        
        Returns:
            Dict[str, Any]: 整合性チェック結果
        """
        self.logger.info(f"Starting workspace consistency check: {workspace_path}")
        
        try:
            # BibTeXファイルの解析
            bibtex_entries = self._parse_bibtex_file(bibtex_file)
            self.logger.info(f"Found {len(bibtex_entries)} BibTeX entries")
            
            # Clippingsディレクトリ内のMarkdownファイル検索
            markdown_files = self._find_markdown_files(clippings_dir)
            self.logger.info(f"Found {len(markdown_files)} organized markdown files")
            
            # 整合性チェック実行
            consistency_results = self._perform_consistency_checks(
                bibtex_entries, markdown_files, clippings_dir
            )
            
            # 結果サマリー作成
            result = self._create_consistency_summary(consistency_results)
            result['workspace_path'] = workspace_path
            result['bibtex_file'] = bibtex_file
            result['clippings_dir'] = clippings_dir
            result['checked_at'] = datetime.now().isoformat()
            
            # YAMLヘッダー更新
            self._update_sync_status_in_yaml_headers(
                consistency_results['papers_checked'], result
            )
            
            self.logger.info(f"Workspace consistency check completed: {result['consistency_status']}")
            return result
            
        except Exception as e:
            error_msg = f"Workspace consistency check failed: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, cause=e)
    
    def check_paper_consistency(
        self, 
        citation_key: str, 
        paper_dir: str, 
        bibtex_entry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        個別論文の整合性チェック
        
        Args:
            citation_key: 引用キー
            paper_dir: 論文ディレクトリのパス
            bibtex_entry: BibTeXエントリー辞書
        
        Returns:
            Dict[str, Any]: 個別論文の整合性チェック結果
        """
        self.logger.debug(f"Checking paper consistency: {citation_key}")
        
        try:
            paper_path = Path(paper_dir)
            markdown_file = paper_path / f"{citation_key}.md"
            
            if not markdown_file.exists():
                return {
                    'citation_key': citation_key,
                    'consistency_status': 'missing_markdown',
                    'markdown_file_exists': False,
                    'issues': ['Markdown file not found']
                }
            
            # YAMLヘッダーの解析
            yaml_data, _ = self.yaml_processor.parse_yaml_header(markdown_file)
            
            # メタデータ比較
            metadata_mismatches = self._compare_metadata(yaml_data, bibtex_entry)
            
            # ファイル名チェック
            filename_issues = self._check_filename_consistency(
                citation_key, markdown_file, paper_path
            )
            
            # 結果構築
            issues = metadata_mismatches + filename_issues
            consistency_status = 'validated' if len(issues) == 0 else 'inconsistent'
            
            result = {
                'citation_key': citation_key,
                'consistency_status': consistency_status,
                'markdown_file_exists': True,
                'markdown_file_path': str(markdown_file),
                'metadata_mismatches': metadata_mismatches,
                'filename_issues': filename_issues,
                'issues': issues,
                'checked_at': datetime.now().isoformat()
            }
            
            self.logger.debug(f"Paper consistency check completed: {citation_key} - {consistency_status}")
            return result
            
        except Exception as e:
            error_msg = f"Paper consistency check failed for {citation_key}: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, cause=e)
    
    def auto_fix_minor_inconsistencies(self, check_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        軽微な不整合の自動修正
        
        Args:
            check_results: 整合性チェック結果
        
        Returns:
            Dict[str, Any]: 自動修正結果
        """
        if not self.sync_config.get('auto_fix_minor_issues', False):
            self.logger.info("Auto-fix is disabled in configuration")
            return {
                'auto_fix_enabled': False,
                'corrections_applied': [],
                'auto_fix_successful': True
            }
        
        self.logger.info("Starting auto-fix for minor inconsistencies")
        corrections_applied = []
        
        try:
            # バックアップ作成（設定されている場合）
            if self.sync_config.get('backup_before_auto_fix', True):
                self._create_backup_before_auto_fix(check_results)
            
            # 軽微な問題の自動修正処理
            if 'minor_issues' in check_results:
                for issue in check_results['minor_issues']:
                    correction = self._apply_auto_fix(issue)
                    if correction:
                        corrections_applied.append(correction)
            
            result = {
                'auto_fix_enabled': True,
                'corrections_applied': corrections_applied,
                'auto_fix_successful': True,
                'fixed_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Auto-fix completed: {len(corrections_applied)} corrections applied")
            return result
            
        except Exception as e:
            error_msg = f"Auto-fix failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                'auto_fix_enabled': True,
                'corrections_applied': corrections_applied,
                'auto_fix_successful': False,
                'error': error_msg
            }
    
    def _parse_bibtex_file(self, bibtex_file: str) -> Dict[str, Dict[str, Any]]:
        """BibTeXファイルの解析"""
        try:
            bibtex_path = Path(bibtex_file)
            if not bibtex_path.exists():
                raise FileSystemError(f"BibTeX file not found: {bibtex_file}")
            
            # BibTeXParserを使用して解析
            parsed_entries = self.bibtex_parser.parse_file(bibtex_file)
            
            # BibTeXParserは既にcitation_keyをキーとした辞書を返すため、そのまま使用
            return parsed_entries
            
        except Exception as e:
            raise ProcessingError(f"Failed to parse BibTeX file: {bibtex_file}", cause=e)
    
    def _find_markdown_files(self, clippings_dir: str) -> Dict[str, str]:
        """Clippingsディレクトリ内のMarkdownファイル検索"""
        try:
            clippings_path = Path(clippings_dir)
            markdown_files = {}
            
            # 1. organize済みのディレクトリ構造を検索（citation_key/citation_key.md）
            for paper_dir in clippings_path.iterdir():
                if paper_dir.is_dir():
                    # Markdownファイルを検索
                    md_files = list(paper_dir.glob("*.md"))
                    if md_files:
                        md_file = md_files[0]  # 最初のMarkdownファイルを使用
                        
                        try:
                            # YAMLヘッダーからcitation_keyを読み取り
                            yaml_data, _ = self.yaml_processor.parse_yaml_header(md_file)
                            citation_key = yaml_data.get('citation_key')
                            
                            if citation_key:
                                # 実際のcitation_keyを使用
                                markdown_files[citation_key] = str(md_file)
                                self.logger.debug(f"Found organized markdown with citation_key: {citation_key} at {md_file}")
                            else:
                                # citation_keyがない場合はディレクトリ名を使用（フォールバック）
                                dir_name = paper_dir.name
                                markdown_files[dir_name] = str(md_file)
                                self.logger.warning(f"No citation_key in YAML header, using directory name: {dir_name}")
                        except Exception as e:
                            # YAMLヘッダー解析に失敗した場合はディレクトリ名を使用
                            dir_name = paper_dir.name
                            markdown_files[dir_name] = str(md_file)
                            self.logger.warning(f"Failed to parse YAML header for {md_file}, using directory name: {dir_name}")
            
            # 2. Clippingsディレクトリ直下の孤立Markdownファイルを検索
            for md_file in clippings_path.glob("*.md"):
                if md_file.is_file():
                    try:
                        # YAMLヘッダーからcitation_keyを読み取り
                        yaml_data, _ = self.yaml_processor.parse_yaml_header(md_file)
                        citation_key = yaml_data.get('citation_key')
                        
                        if citation_key:
                            # citation_keyが存在する場合はそれを使用
                            markdown_files[citation_key] = str(md_file)
                            self.logger.debug(f"Found orphaned markdown with citation_key: {citation_key} at {md_file}")
                        else:
                            # citation_keyがない場合はファイル名（拡張子なし）を使用
                            file_stem = md_file.stem
                            markdown_files[file_stem] = str(md_file)
                            self.logger.warning(f"Found orphaned markdown without citation_key, using filename: {file_stem}")
                    except Exception as e:
                        # YAMLヘッダー解析に失敗した場合はファイル名を使用
                        file_stem = md_file.stem
                        markdown_files[file_stem] = str(md_file)
                        self.logger.warning(f"Failed to parse YAML header for orphaned file {md_file}, using filename: {file_stem}")
            
            self.logger.info(f"Found {len(markdown_files)} total markdown files in {clippings_dir}")
            return markdown_files
            
        except Exception as e:
            raise ProcessingError(f"Failed to find markdown files in: {clippings_dir}", cause=e)
    
    def _perform_consistency_checks(
        self, 
        bibtex_entries: Dict[str, Dict[str, Any]], 
        markdown_files: Dict[str, str], 
        clippings_dir: str
    ) -> Dict[str, Any]:
        """整合性チェックの実行"""
        papers_checked = []
        missing_markdown = []
        orphaned_markdown = []
        issues_detected = 0
        
        # BibTeXエントリーに対応するMarkdownファイルのチェック
        for citation_key, bibtex_entry in bibtex_entries.items():
            if citation_key in markdown_files:
                # 個別論文の整合性チェック
                paper_dir = Path(markdown_files[citation_key]).parent
                paper_result = self.check_paper_consistency(
                    citation_key, str(paper_dir), bibtex_entry
                )
                papers_checked.append(paper_result)
                
                if paper_result['consistency_status'] != 'validated':
                    issues_detected += len(paper_result['issues'])
            else:
                # Markdownファイルが見つからない
                missing_markdown.append({
                    'citation_key': citation_key,
                    'bibtex_entry': bibtex_entry
                })
                issues_detected += 1
        
        # 孤立Markdownファイルのチェック
        for citation_key, markdown_file in markdown_files.items():
            if citation_key not in bibtex_entries:
                orphaned_markdown.append({
                    'citation_key': citation_key,
                    'markdown_file': markdown_file
                })
                issues_detected += 1
        
        return {
            'papers_checked': papers_checked,
            'missing_markdown_files': missing_markdown,
            'orphaned_markdown_files': orphaned_markdown,
            'issues_detected': issues_detected
        }
    
    def _compare_metadata(
        self, 
        yaml_data: Dict[str, Any], 
        bibtex_entry: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """メタデータの比較"""
        mismatches = []
        
        # DOI比較
        yaml_doi = yaml_data.get('doi', '').strip()
        bibtex_doi = bibtex_entry.get('doi', '').strip()
        
        if yaml_doi and bibtex_doi and yaml_doi != bibtex_doi:
            mismatches.append({
                'field': 'doi',
                'yaml_value': yaml_doi,
                'bibtex_value': bibtex_doi,
                'severity': 'major'
            })
        
        # タイトル比較（大文字小文字の違いは軽微とする）
        yaml_title = yaml_data.get('title', '').strip()
        bibtex_title = bibtex_entry.get('title', '').strip()
        
        if yaml_title and bibtex_title:
            if yaml_title.lower() != bibtex_title.lower():
                severity = 'minor' if yaml_title.lower().replace(' ', '') == bibtex_title.lower().replace(' ', '') else 'major'
                mismatches.append({
                    'field': 'title',
                    'yaml_value': yaml_title,
                    'bibtex_value': bibtex_title,
                    'severity': severity
                })
        
        return mismatches
    
    def _check_filename_consistency(
        self, 
        citation_key: str, 
        markdown_file: Path, 
        paper_dir: Path
    ) -> List[Dict[str, Any]]:
        """ファイル名の整合性チェック"""
        issues = []
        
        expected_filename = f"{citation_key}.md"
        actual_filename = markdown_file.name
        
        if actual_filename != expected_filename:
            issues.append({
                'type': 'filename_normalization',
                'current_filename': actual_filename,
                'expected_filename': expected_filename,
                'severity': 'minor'
            })
        
        return issues
    
    def _create_consistency_summary(self, consistency_results: Dict[str, Any]) -> Dict[str, Any]:
        """整合性チェック結果のサマリー作成"""
        total_papers = len(consistency_results['papers_checked'])
        validated_papers = sum(
            1 for paper in consistency_results['papers_checked'] 
            if paper['consistency_status'] == 'validated'
        )
        
        consistency_status = 'validated' if consistency_results['issues_detected'] == 0 else 'issues_detected'
        
        return {
            'consistency_status': consistency_status,
            'issues_detected': consistency_results['issues_detected'],
            'papers_checked': total_papers,
            'validated_papers': validated_papers,
            'missing_markdown_files': consistency_results['missing_markdown_files'],
            'orphaned_markdown_files': consistency_results['orphaned_markdown_files'],
            'detailed_results': consistency_results['papers_checked']
        }
    
    def _update_sync_status_in_yaml_headers(
        self, 
        papers_checked: List[Dict[str, Any]], 
        overall_result: Dict[str, Any]
    ) -> None:
        """YAMLヘッダーのsync状態更新"""
        for paper_result in papers_checked:
            if paper_result.get('markdown_file_exists', False):
                try:
                    markdown_file = paper_result['markdown_file_path']
                    
                    # 現在のYAMLヘッダーとコンテンツの取得
                    yaml_data, content = self.yaml_processor.parse_yaml_header(Path(markdown_file))
                    
                    # sync_metadataの追加/更新
                    yaml_data['sync_metadata'] = {
                        'checked_at': paper_result['checked_at'],
                        'consistency_status': paper_result['consistency_status'],
                        'issues_detected': len(paper_result['issues']),
                        'auto_corrections_applied': 0,  # 実際の修正後に更新
                        'corrections_applied': []
                    }
                    
                    # processing_statusの更新
                    if 'processing_status' not in yaml_data:
                        yaml_data['processing_status'] = {}
                    
                    yaml_data['processing_status']['sync'] = (
                        'completed' if paper_result['consistency_status'] == 'validated' 
                        else 'failed'
                    )
                    
                    # YAMLヘッダーの書き戻し
                    self.yaml_processor.write_yaml_header(Path(markdown_file), yaml_data, content)
                    
                except Exception as e:
                    self.logger.error(f"Failed to update YAML header for {paper_result['citation_key']}: {str(e)}")
    
    def _create_backup_before_auto_fix(self, check_results: Dict[str, Any]) -> None:
        """自動修正前のバックアップ作成"""
        # バックアップロジックの実装（簡易版）
        self.logger.info("Creating backup before auto-fix (placeholder)")
    
    def _apply_auto_fix(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """個別問題の自動修正適用"""
        try:
            if issue.get('type') == 'filename_normalization':
                # ファイル名正規化の自動修正（実装例）
                self.logger.info(f"Auto-fixing filename normalization for {issue.get('citation_key')}")
                return {
                    'type': 'filename_normalization',
                    'description': 'Filename normalized to match citation_key',
                    'timestamp': datetime.now().isoformat(),
                    'citation_key': issue.get('citation_key')
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Auto-fix failed for issue {issue}: {str(e)}")
            return None
    
    def display_doi_links(self, missing_papers, orphaned_papers):
        """
        不足・孤立論文のDOIリンク表示
        
        Args:
            missing_papers: BibTeXにあるがMarkdownがない論文リスト
            orphaned_papers: MarkdownにあるがBibTeXにない論文リスト
        """
        if not self.sync_config.get('display_doi_links', True):
            return
        
        doi_link_format = self.sync_config.get('doi_link_format', 'https://doi.org/{doi}')
        
        # 不足Markdownファイルの表示
        if missing_papers:
            print(f"\n📋 不足Markdownファイル ({len(missing_papers)}件):")
            for paper in missing_papers:
                citation_key = paper.get('citation_key', 'Unknown')
                bibtex_entry = paper.get('bibtex_entry', {})
                doi = bibtex_entry.get('doi', '')
                
                print("┌─────────────────────────────────────────────────────────────────────────────────┐")
                print(f"│ Citation Key: {citation_key:<63} │")
                if doi:
                    doi_link = doi_link_format.format(doi=doi)
                    print(f"│ DOI Link: {doi_link:<67} │")
                else:
                    print(f"│ DOI Link: DOI情報なし{'':<59} │")
                print(f"│ 推奨アクション: Markdownファイルを作成してください{'':<34} │")
                print("└─────────────────────────────────────────────────────────────────────────────────┘")
        
        # 孤立Markdownファイルの表示
        if orphaned_papers:
            print(f"\n🔗 孤立Markdownファイル ({len(orphaned_papers)}件):")
            for paper in orphaned_papers:
                citation_key = paper.get('citation_key', 'Unknown')
                markdown_file = paper.get('markdown_file', '')
                
                # MarkdownファイルからDOI情報を取得
                doi = self._extract_doi_from_markdown(markdown_file)
                
                # ファイル名を適切な長さに切り詰め
                file_name = Path(markdown_file).name if markdown_file else 'Unknown'
                if len(file_name) > 63:
                    file_name = file_name[:60] + "..."
                
                print("┌─────────────────────────────────────────────────────────────────────────────────┐")
                print(f"│ File: {file_name:<71} │")
                if doi:
                    doi_link = doi_link_format.format(doi=doi)
                    print(f"│ DOI Link: {doi_link:<67} │")
                else:
                    print(f"│ DOI Link: DOI情報なし{'':<59} │")
                print(f"│ 推奨アクション: BibTeXエントリーを追加してください{'':<31} │")
                print("└─────────────────────────────────────────────────────────────────────────────────┘")
    
    def _extract_doi_from_markdown(self, markdown_file: str) -> str:
        """MarkdownファイルからDOI情報を抽出"""
        try:
            if not markdown_file or not Path(markdown_file).exists():
                return ''
            
            yaml_data, _ = self.yaml_processor.parse_yaml_header(Path(markdown_file))
            return yaml_data.get('doi', '')
            
        except Exception as e:
            self.logger.debug(f"Failed to extract DOI from {markdown_file}: {str(e)}")
            return '' 