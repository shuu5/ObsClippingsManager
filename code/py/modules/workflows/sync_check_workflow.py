"""
同期チェックワークフロー

BibTeXファイルとClippingsディレクトリの双方向整合性をチェックし、
不一致を報告する機能を提供します。
"""

from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import click

from ..shared.exceptions import (
    SyncCheckError, BibTeXParsingError, ClippingsAccessError, DOIProcessingError
)
from ..shared.bibtex_parser import BibTeXParser


class SyncCheckWorkflow:
    """同期チェックワークフロー"""
    
    def __init__(self, config_manager, logger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ロガーインスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('Workflows.SyncCheck')
        self.config = config_manager.get_sync_check_config()
        
        # BibTeX解析器の初期化
        self.bibtex_parser = BibTeXParser()
        
    def execute(self, **options) -> Tuple[bool, Dict[str, Any]]:
        """
        同期チェックワークフローを実行
        
        Args:
            **options: 実行オプション
                - show_missing_in_clippings: .bibにあってClippings/にない論文を表示
                - show_missing_in_bib: Clippings/にあって.bibにない論文を表示
                - show_clickable_links: DOIリンクをクリック可能な形式で表示
                - dry_run: ドライラン実行
                - verbose: 詳細出力
        
        Returns:
            (成功フラグ, 実行結果詳細)
        """
        try:
            self.logger.info("Starting sync check workflow")
            
            # 実行オプションのマージ
            execution_options = {**self.config, **options}
            
            # 設定を一時的に更新
            original_config = self.config.copy()
            self.config.update(execution_options)
            
            # 結果辞書の初期化
            results = {
                "missing_in_clippings": [],
                "missing_in_bib": [],
                "statistics": {},
                "execution_options": execution_options
            }
            
            # BibTeXファイルの解析
            self.logger.info("Parsing BibTeX file")
            bib_entries = self._parse_bibtex_file()
            
            # Clippingsディレクトリの解析
            self.logger.info("Scanning Clippings directory")
            clippings_dirs = self._get_clippings_directories()
            
            # 双方向チェック実行
            if execution_options.get('show_missing_in_clippings', True):
                self.logger.info("Checking papers missing in Clippings")
                missing_in_clippings = self.check_bib_to_clippings(bib_entries, clippings_dirs)
                results["missing_in_clippings"] = missing_in_clippings
                self.report_missing_in_clippings(missing_in_clippings, execution_options)
                
            if execution_options.get('show_missing_in_bib', True):
                self.logger.info("Checking directories missing in BibTeX")
                missing_in_bib = self.check_clippings_to_bib(bib_entries, clippings_dirs)
                results["missing_in_bib"] = missing_in_bib
                self.report_missing_in_bib(missing_in_bib, execution_options)
                
            # DOI統計情報の表示
            if execution_options.get('show_doi_statistics', True):
                stats = self.report_doi_statistics(bib_entries, results["missing_in_clippings"])
                results["statistics"] = stats
                
            # 完了通知
            total_issues = len(results["missing_in_clippings"]) + len(results["missing_in_bib"])
            if total_issues == 0:
                click.echo("\n✅ Perfect synchronization achieved!")
                self.logger.info("Sync check completed - no issues found")
            else:
                self.logger.info(f"Sync check completed - {total_issues} issues found")
                
            return True, results
            
        except Exception as e:
            self.logger.error(f"Sync check workflow failed: {e}")
            return False, {"error": str(e)}
        finally:
            # 設定を復元
            self.config = original_config
    
    def _parse_bibtex_file(self) -> Dict[str, Dict[str, Any]]:
        """BibTeXファイルを解析"""
        try:
            bibtex_file = self.config.get('bibtex_file')
            if not bibtex_file or not Path(bibtex_file).exists():
                raise BibTeXParsingError(f"BibTeX file not found: {bibtex_file}")
                
            return self.bibtex_parser.parse_file(bibtex_file)
            
        except Exception as e:
            raise BibTeXParsingError(f"Failed to parse BibTeX file: {e}")
    
    def _get_clippings_directories(self) -> List[str]:
        """
        Clippings内のサブディレクトリ一覧を取得
        
        Returns:
            List[str]: ディレクトリ名のリスト
        """
        try:
            clippings_path = Path(self.config.get('clippings_dir'))
            if not clippings_path.exists():
                raise ClippingsAccessError(f"Clippings directory not found: {clippings_path}")
                
            return [d.name for d in clippings_path.iterdir() if d.is_dir()]
            
        except Exception as e:
            raise ClippingsAccessError(f"Failed to access Clippings directory: {e}")
    
    def check_bib_to_clippings(self, bib_entries: Dict, clippings_dirs: List[str]) -> List[Dict]:
        """
        .bibにあってClippings/にない論文をチェック
        
        Args:
            bib_entries: BibTeX項目の辞書
            clippings_dirs: Clippings内のディレクトリリスト
        
        Returns:
            List[Dict]: 不足論文の情報リスト
        """
        missing_papers = []
        
        for citation_key, entry in bib_entries.items():
            if citation_key not in clippings_dirs:
                # DOIの処理（空白や改行を除去）
                doi_raw = entry.get('doi', '').strip()
                doi_clean = doi_raw.replace('\n', '').replace('\r', '') if doi_raw else ''
                
                paper_info = {
                    'citation_key': citation_key,
                    'title': entry.get('title', 'Unknown Title'),
                    'doi': doi_clean,
                    'authors': entry.get('author', 'Unknown Authors'),
                    'year': entry.get('year', 'Unknown Year')
                }
                missing_papers.append(paper_info)
                
        self.logger.info(f"Found {len(missing_papers)} papers in bib but missing in clippings")
        return missing_papers
    
    def check_clippings_to_bib(self, bib_entries: Dict, clippings_dirs: List[str]) -> List[Dict]:
        """
        Clippings/にあって.bibにない論文をチェック
        
        Args:
            bib_entries: BibTeX項目の辞書
            clippings_dirs: Clippings内のディレクトリリスト
        
        Returns:
            List[Dict]: 孤立ファイルの情報リスト
        """
        orphaned_papers = []
        
        for clipping_dir in clippings_dirs:
            if clipping_dir not in bib_entries:
                md_files = self._get_markdown_files_in_directory(clipping_dir)
                paper_info = {
                    'directory_name': clipping_dir,
                    'markdown_files': md_files,
                    'file_count': len(md_files)
                }
                orphaned_papers.append(paper_info)
                
        self.logger.info(f"Found {len(orphaned_papers)} orphaned directories in clippings")
        return orphaned_papers
    
    def _get_markdown_files_in_directory(self, directory_name: str) -> List[str]:
        """
        指定ディレクトリ内のMarkdownファイル一覧を取得
        
        Args:
            directory_name: ディレクトリ名
        
        Returns:
            List[str]: Markdownファイル名のリスト
        """
        try:
            dir_path = Path(self.config.get('clippings_dir')) / directory_name
            return [f.name for f in dir_path.glob('*.md')] if dir_path.exists() else []
        except Exception as e:
            self.logger.warning(f"Failed to get markdown files in {directory_name}: {e}")
            return []
    
    def report_missing_in_clippings(self, missing_papers: List[Dict], options: Dict) -> None:
        """
        .bibにあってClippings/にない論文を報告
        
        Args:
            missing_papers: 不足論文のリスト
            options: 実行オプション
        """
        if not missing_papers:
            click.echo("✅ All papers in bib file have corresponding clippings directories")
            return
            
        click.echo(f"\n📚 Papers in CurrentManuscript.bib but missing in Clippings/ ({len(missing_papers)} papers):")
        click.echo("=" * 80)
        
        # 年代順ソート（オプション）
        if options.get('sort_by_year', True):
            missing_papers = sorted(missing_papers, key=lambda x: x.get('year', '0'), reverse=True)
        
        # 表示制限
        max_displayed = options.get('max_displayed_files', 10)
        display_papers = missing_papers[:max_displayed]
        
        for i, paper in enumerate(display_papers, 1):
            click.echo(f"\n{i}. Citation Key: {paper['citation_key']}")
            click.echo(f"   Title: {paper['title']}")
            click.echo(f"   Authors: {paper['authors']}")
            click.echo(f"   Year: {paper['year']}")
            
            # DOI情報の表示とクリック可能リンク
            doi = paper['doi']
            if doi and doi.strip():  # DOIが存在し、空白でない場合
                doi_url = f"https://doi.org/{doi}"
                click.echo(f"   DOI: {doi}")
                
                # ターミナルでクリック可能なリンクを表示
                if options.get('show_clickable_links', True):
                    clickable_link = self._format_clickable_link(doi_url)
                    click.echo(f"   🔗 Link: {clickable_link}")
                else:
                    click.echo(f"   🔗 URL: {doi_url}")
            else:
                click.echo("   DOI: ❌ Not available")
                click.echo("   🔗 Link: Cannot generate DOI link")
        
        # 表示制限の通知
        if len(missing_papers) > max_displayed:
            click.echo(f"\n... and {len(missing_papers) - max_displayed} more papers")
            click.echo(f"(Use --max-displayed-files to show more)")
    
    def report_missing_in_bib(self, orphaned_papers: List[Dict], options: Dict) -> None:
        """
        Clippings/にあって.bibにない論文を報告
        
        Args:
            orphaned_papers: 孤立論文のリスト
            options: 実行オプション
        """
        if not orphaned_papers:
            click.echo("✅ All clippings directories have corresponding bib entries")
            return
            
        click.echo(f"\n📁 Directories in Clippings/ but missing in CurrentManuscript.bib ({len(orphaned_papers)} directories):")
        click.echo("=" * 80)
        
        # 表示制限
        max_displayed = options.get('max_displayed_files', 10)
        display_papers = orphaned_papers[:max_displayed]
        
        for i, paper in enumerate(display_papers, 1):
            click.echo(f"\n{i}. Directory: {paper['directory_name']}")
            click.echo(f"   Markdown files ({paper['file_count']}):")
            
            for md_file in paper['markdown_files']:
                click.echo(f"     - {md_file}")
        
        # 表示制限の通知
        if len(orphaned_papers) > max_displayed:
            click.echo(f"\n... and {len(orphaned_papers) - max_displayed} more directories")
            click.echo(f"(Use --max-displayed-files to show more)")
    
    def report_doi_statistics(self, bib_entries: Dict, missing_in_clippings: List[Dict]) -> Dict[str, Any]:
        """
        DOI統計情報を報告
        
        Args:
            bib_entries: BibTeX項目の辞書
            missing_in_clippings: 不足論文のリスト
            
        Returns:
            Dict[str, Any]: 統計情報
        """
        total_papers = len(bib_entries)
        papers_with_doi = sum(1 for entry in bib_entries.values() 
                             if entry.get('doi', '').strip())
        papers_without_doi = total_papers - papers_with_doi
        
        # 不足論文の中でDOIがない論文数をカウント
        missing_without_doi = sum(1 for paper in missing_in_clippings 
                                 if not paper.get('doi', '').strip())
        
        statistics = {
            "total_papers": total_papers,
            "papers_with_doi": papers_with_doi,
            "papers_without_doi": papers_without_doi,
            "missing_without_doi": missing_without_doi,
            "doi_coverage_percentage": (papers_with_doi / total_papers * 100) if total_papers > 0 else 0
        }
        
        click.echo(f"\n📊 DOI Statistics:")
        click.echo("=" * 50)
        click.echo(f"Total papers in bib: {total_papers}")
        click.echo(f"Papers with DOI: {papers_with_doi}")
        click.echo(f"Papers without DOI: {papers_without_doi}")
        
        if papers_without_doi > 0:
            percentage = statistics["doi_coverage_percentage"]
            click.echo(f"DOI coverage: {papers_with_doi}/{total_papers} ({100-percentage:.1f}% missing)")
            
            if missing_without_doi > 0:
                click.echo(f"⚠️  Missing papers without DOI: {missing_without_doi}")
                click.echo("   (These papers cannot be accessed via DOI links)")
        else:
            click.echo("✅ All papers have DOI information")
            
        return statistics
    
    def _format_clickable_link(self, url: str, display_text: str = None) -> str:
        """
        ターミナルでクリック可能なリンクを生成
        
        Args:
            url: リンクURL
            display_text: 表示テキスト（Noneの場合はURLを表示）
        
        Returns:
            str: ANSI escape sequenceでフォーマットされたクリック可能リンク
        """
        if display_text is None:
            display_text = url
        
        # ANSI escape sequences for clickable links (OSC 8)
        return f"\033]8;;{url}\033\\{display_text}\033]8;;\033\\"