#!/usr/bin/env python3
"""
ObsClippingsManager - 統合版メインプログラム

新しいモジュール構成を使用した統合型の学術文献管理システム。
BibTeX解析、引用文献取得、ファイル整理の全機能を提供します。
"""

import sys
import os
from pathlib import Path
import click
from typing import Dict, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 新しいモジュール構成をインポート
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.workflows.workflow_manager import WorkflowManager, WorkflowType, create_workflow_execution_summary
from modules.shared.exceptions import ObsClippingsError, ConfigError


# グローバル設定
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_LOG_LEVEL = "INFO"

# CLIコンテキスト用の設定
pass_context = click.make_pass_decorator(dict, ensure=True)


@click.group()
@click.option('--config', '-c', 
              default=DEFAULT_CONFIG_FILE,
              help='Configuration file path',
              type=click.Path(exists=False))
@click.option('--log-level', '-l',
              default=DEFAULT_LOG_LEVEL,
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              help='Logging level')
@click.option('--dry-run', '-n',
              is_flag=True,
              help='Perform a dry run without making actual changes')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Enable verbose output')
@pass_context
def cli(ctx: Dict[str, Any], config: str, log_level: str, dry_run: bool, verbose: bool):
    """
    ObsClippingsManager - 学術文献管理システム
    
    BibTeX解析、引用文献取得、Markdownファイル整理を統合管理します。
    """
    try:
        # 設定管理の初期化
        config_manager = ConfigManager(config_file=config)
        
        # ロガーの初期化
        logger = IntegratedLogger(
            log_level=log_level,
            console_output=True,
            log_file="logs/obsclippings.log"
        )
        
        # ワークフロー管理の初期化
        workflow_manager = WorkflowManager(config_manager, logger)
        
        # CLIコンテキストに共有オブジェクトを保存
        ctx['config_manager'] = config_manager
        ctx['logger'] = logger
        ctx['workflow_manager'] = workflow_manager
        ctx['dry_run'] = dry_run
        ctx['verbose'] = verbose
        
        if verbose:
            click.echo(f"✓ Configuration loaded from: {config}")
            click.echo(f"✓ Log level: {log_level}")
            if dry_run:
                click.echo("✓ Dry run mode enabled")
        
    except Exception as e:
        click.echo(f"❌ Initialization failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--bibtex-file', '-b',
              help='BibTeX file to process',
              type=click.Path(exists=True))
@click.option('--output-dir', '-o',
              help='Output directory for results',
              type=click.Path())
@click.option('--max-retries', '-r',
              type=int,
              help='Maximum API retry attempts')
@click.option('--auto-approve', '-y',
              is_flag=True,
              help='Automatically approve all operations')
@pass_context
def fetch_citations(ctx: Dict[str, Any], 
                   bibtex_file: Optional[str],
                   output_dir: Optional[str],
                   max_retries: Optional[int],
                   auto_approve: bool):
    """
    引用文献取得ワークフローを実行
    
    BibTeXファイルからDOIを抽出し、学術API経由で引用文献を取得します。
    """
    try:
        workflow_manager = ctx['workflow_manager']
        logger = ctx['logger'].get_logger('CLI')
        
        # 実行オプションの構築
        options = {
            'dry_run': ctx['dry_run'],
            'auto_approve': auto_approve
        }
        
        # コマンドライン引数で設定を上書き
        if bibtex_file:
            options['bibtex_file'] = bibtex_file
        if output_dir:
            options['output_dir'] = output_dir
        if max_retries is not None:
            options['max_retries'] = max_retries
        
        click.echo("🔍 Starting citation fetching workflow...")
        
        # ワークフロー実行
        success, results = workflow_manager.execute_workflow(
            WorkflowType.CITATION_FETCHING, 
            **options
        )
        
        # 結果表示
        if success:
            click.echo("✅ Citation fetching completed successfully!")
            
            # 詳細統計の表示
            if ctx['verbose']:
                summary = create_workflow_execution_summary(results)
                click.echo("\n" + summary)
            else:
                # 簡潔な統計
                dois_processed = results.get('successful_fetches', 0)
                total_refs = results.get('total_references', 0)
                click.echo(f"📊 Processed {dois_processed} DOIs, found {total_refs} references")
        else:
            error = results.get('error', 'Unknown error')
            click.echo(f"❌ Citation fetching failed: {error}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--clippings-dir', '-d',
              help='Clippings directory to organize',
              type=click.Path(exists=True))
@click.option('--bibtex-file', '-b',
              help='BibTeX file for matching',
              type=click.Path(exists=True))
@click.option('--threshold', '-t',
              type=float,
              help='Similarity threshold (0.0-1.0) for title fallback matching')
@click.option('--backup/--no-backup',
              default=True,
              help='Create backup before organizing')
@click.option('--auto-approve', '-y',
              is_flag=True,
              help='Automatically approve all operations')
@click.option('--disable-doi-matching',
              is_flag=True,
              help='Disable DOI-based matching and use title matching instead')
@click.option('--disable-title-sync',
              is_flag=True,
              help='Disable automatic title synchronization with BibTeX')
@pass_context
def organize_files(ctx: Dict[str, Any],
                  clippings_dir: Optional[str],
                  bibtex_file: Optional[str],
                  threshold: Optional[float],
                  backup: bool,
                  auto_approve: bool,
                  disable_doi_matching: bool,
                  disable_title_sync: bool):
    """
    ファイル整理ワークフローを実行
    
    MarkdownファイルのYAML frontmatter内のDOI情報を使用してBibTeX項目と照合し、
    citation_keyベースのディレクトリに整理します。
    DOI照合成功時、MarkdownのtitleがBibTeXのtitleと異なる場合は自動的に同期します。
    DOIが存在しない場合は、オプションでタイトル照合にフォールバックします。
    """
    try:
        workflow_manager = ctx['workflow_manager']
        logger = ctx['logger'].get_logger('CLI')
        
        # 実行オプションの構築
        options = {
            'dry_run': ctx['dry_run'],
            'auto_approve': auto_approve,
            'backup': backup,
            'disable_doi_matching': disable_doi_matching,
            'disable_title_sync': disable_title_sync
        }
        
        # コマンドライン引数で設定を上書き
        if clippings_dir:
            options['clippings_dir'] = clippings_dir
        if bibtex_file:
            options['bibtex_file'] = bibtex_file
        if threshold is not None:
            options['similarity_threshold'] = threshold
        
        click.echo("📁 Starting file organization workflow...")
        
        # ワークフロー実行
        success, results = workflow_manager.execute_workflow(
            WorkflowType.FILE_ORGANIZATION,
            **options
        )
        
        # 結果表示
        if success:
            click.echo("✅ File organization completed successfully!")
            
            # 詳細統計の表示
            if ctx['verbose']:
                summary = create_workflow_execution_summary(results)
                click.echo("\n" + summary)
            else:
                # 簡潔な統計
                organized = results.get('organized_files', 0)
                matches = results.get('matches_count', 0)
                click.echo(f"📊 Organized {organized} files from {matches} matches")
        else:
            error = results.get('error', 'Unknown error')
            # 警告の場合は継続
            warning = results.get('warning')
            if warning and not error:
                click.echo(f"⚠️  Warning: {warning}")
            else:
                click.echo(f"❌ File organization failed: {error}", err=True)
                sys.exit(1)
                
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--bibtex-file', '-b',
              help='BibTeX file to check',
              type=click.Path(exists=True))
@click.option('--clippings-dir', '-d',
              help='Clippings directory to check',
              type=click.Path(exists=True))
@click.option('--show-missing-in-clippings/--no-show-missing-in-clippings',
              default=True,
              help='Show papers in bib but missing in clippings')
@click.option('--show-missing-in-bib/--no-show-missing-in-bib',
              default=True,
              help='Show directories in clippings but missing in bib')
@click.option('--show-clickable-links/--no-show-clickable-links',
              default=True,
              help='Show DOI links as clickable terminal links')
@click.option('--max-displayed-files', '-m',
              type=int,
              default=10,
              help='Maximum number of files to display')
@click.option('--sort-by-year/--no-sort-by-year',
              default=True,
              help='Sort results by publication year')
@pass_context
def sync_check(ctx: Dict[str, Any],
              bibtex_file: Optional[str],
              clippings_dir: Optional[str],
              show_missing_in_clippings: bool,
              show_missing_in_bib: bool,
              show_clickable_links: bool,
              max_displayed_files: int,
              sort_by_year: bool):
    """
    BibTeXファイルとClippingsディレクトリの同期状態をチェック
    
    両者の整合性を確認し、不一致を報告します。
    """
    try:
        workflow_manager = ctx['workflow_manager']
        logger = ctx['logger'].get_logger('CLI')
        
        # 実行オプションの構築
        options = {
            'dry_run': ctx['dry_run'],
            'show_missing_in_clippings': show_missing_in_clippings,
            'show_missing_in_bib': show_missing_in_bib,
            'show_clickable_links': show_clickable_links,
            'max_displayed_files': max_displayed_files,
            'sort_by_year': sort_by_year
        }
        
        # コマンドライン引数で設定を上書き
        if bibtex_file:
            options['bibtex_file'] = bibtex_file
        if clippings_dir:
            options['clippings_dir'] = clippings_dir
        
        click.echo("🔍 Starting sync check workflow...")
        
        # ワークフロー実行
        success, results = workflow_manager.execute_workflow(
            WorkflowType.SYNC_CHECK,
            **options
        )
        
        # 結果表示
        if success:
            missing_in_clippings = len(results.get('missing_in_clippings', []))
            missing_in_bib = len(results.get('missing_in_bib', []))
            total_issues = missing_in_clippings + missing_in_bib
            
            if total_issues == 0:
                click.echo("\n🎉 Sync check completed - Perfect synchronization!")
            else:
                click.echo(f"\n📋 Sync check completed - {total_issues} issues found")
                click.echo(f"   • Missing in Clippings: {missing_in_clippings}")
                click.echo(f"   • Missing in BibTeX: {missing_in_bib}")
            
            # 詳細統計の表示
            if ctx['verbose']:
                summary = create_workflow_execution_summary(results)
                click.echo("\n" + summary)
            else:
                # DOI統計の簡潔表示
                stats = results.get('statistics', {})
                if stats:
                    total_papers = stats.get('total_papers', 0)
                    papers_with_doi = stats.get('papers_with_doi', 0)
                    click.echo(f"📊 Total papers: {total_papers}, DOI coverage: {papers_with_doi}/{total_papers}")
        else:
            error = results.get('error', 'Unknown error')
            click.echo(f"❌ Sync check failed: {error}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--continue-on-failure',
              is_flag=True,
              help='Continue organization even if citation fetching fails')
@click.option('--auto-approve', '-y',
              is_flag=True,
              help='Automatically approve all operations')
@pass_context
def run_integrated(ctx: Dict[str, Any],
                  continue_on_failure: bool,
                  auto_approve: bool):
    """
    統合ワークフローを実行
    
    引用文献取得とファイル整理を順次実行します。
    """
    try:
        workflow_manager = ctx['workflow_manager']
        logger = ctx['logger'].get_logger('CLI')
        
        # 実行オプションの構築
        options = {
            'dry_run': ctx['dry_run'],
            'auto_approve': auto_approve,
            'continue_on_citation_failure': continue_on_failure
        }
        
        click.echo("🚀 Starting integrated workflow...")
        
        # ワークフロー実行
        success, results = workflow_manager.execute_workflow(
            WorkflowType.INTEGRATED,
            **options
        )
        
        # 結果表示
        if success:
            click.echo("✅ Integrated workflow completed successfully!")
            
            # 統計の表示
            if ctx['verbose']:
                summary = create_workflow_execution_summary(results)
                click.echo("\n" + summary)
            else:
                # 簡潔な統計
                citation_results = results.get('citation_results', {})
                org_results = results.get('organization_results', {})
                
                citation_success = citation_results.get('success', False)
                org_success = org_results.get('success', False)
                
                click.echo(f"📊 Citation phase: {'✓' if citation_success else '✗'}")
                click.echo(f"📊 Organization phase: {'✓' if org_success else '✗'}")
                
                if citation_success:
                    total_refs = citation_results.get('total_references', 0)
                    click.echo(f"   📖 Found {total_refs} references")
                
                if org_success:
                    organized = org_results.get('organized_files', 0)
                    click.echo(f"   📁 Organized {organized} files")
        else:
            error = results.get('error', 'Unknown error')
            click.echo(f"❌ Integrated workflow failed: {error}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--workflow-type', '-w',
              type=click.Choice(['citation_fetching', 'file_organization', 'sync_check', 'integrated'], case_sensitive=False),
              help='Validate specific workflow configuration')
@pass_context
def validate_config(ctx: Dict[str, Any], workflow_type: Optional[str]):
    """
    設定ファイルの妥当性を検証
    """
    try:
        workflow_manager = ctx['workflow_manager']
        
        click.echo("🔍 Validating configuration...")
        
        if workflow_type:
            # 特定のワークフロー設定を検証
            valid, errors = workflow_manager.validate_workflow_configuration(workflow_type)
            
            if valid:
                click.echo(f"✅ {workflow_type} configuration is valid")
            else:
                click.echo(f"❌ {workflow_type} configuration is invalid:")
                for error in errors:
                    click.echo(f"   • {error}")
                sys.exit(1)
        else:
            # 全ワークフロー設定を検証
            all_valid = True
            
            for wf_type in ['citation_fetching', 'file_organization', 'sync_check']:
                valid, errors = workflow_manager.validate_workflow_configuration(wf_type)
                
                if valid:
                    click.echo(f"✅ {wf_type} configuration is valid")
                else:
                    click.echo(f"❌ {wf_type} configuration is invalid:")
                    for error in errors:
                        click.echo(f"   • {error}")
                    all_valid = False
            
            if not all_valid:
                sys.exit(1)
        
        click.echo("🎉 All validations passed!")
        
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', '-l',
              type=int,
              default=10,
              help='Number of recent executions to show')
@click.option('--workflow-type', '-w',
              type=click.Choice(['citation_fetching', 'file_organization', 'sync_check', 'integrated'], case_sensitive=False),
              help='Filter by workflow type')
@pass_context
def show_history(ctx: Dict[str, Any], limit: int, workflow_type: Optional[str]):
    """
    ワークフロー実行履歴を表示
    """
    try:
        workflow_manager = ctx['workflow_manager']
        
        # ワークフロータイプでフィルタ
        wf_type_enum = None
        if workflow_type:
            wf_type_enum = WorkflowType(workflow_type)
        
        history = workflow_manager.get_execution_history(
            limit=limit,
            workflow_type=wf_type_enum
        )
        
        if not history:
            click.echo("📭 No execution history found")
            return
        
        click.echo(f"📋 Recent workflow executions (last {len(history)}):")
        click.echo("=" * 60)
        
        for record in history:
            timestamp = record['timestamp'][:19]  # YYYY-MM-DD HH:MM:SS
            wf_type = record['workflow_type']
            success_icon = "✅" if record['success'] else "❌"
            exec_time = record['execution_time']
            
            click.echo(f"{success_icon} {timestamp} | {wf_type:<18} | {exec_time:5.1f}s")
            
            if record.get('error'):
                click.echo(f"   Error: {record['error']}")
            
            # サマリー情報
            summary = record.get('summary', {})
            if summary:
                summary_parts = []
                for key, value in summary.items():
                    if isinstance(value, bool):
                        summary_parts.append(f"{key}: {'✓' if value else '✗'}")
                    else:
                        summary_parts.append(f"{key}: {value}")
                
                if summary_parts:
                    click.echo(f"   {' | '.join(summary_parts)}")
            
            click.echo()
        
    except Exception as e:
        click.echo(f"❌ Failed to retrieve history: {e}", err=True)
        sys.exit(1)


@cli.command()
@pass_context
def show_stats(ctx: Dict[str, Any]):
    """
    システム統計情報を表示
    """
    try:
        workflow_manager = ctx['workflow_manager']
        
        stats = workflow_manager.get_workflow_statistics()
        
        click.echo("📊 Workflow Statistics:")
        click.echo("=" * 30)
        
        total = stats.get('total_executions', 0)
        successful = stats.get('successful_executions', 0)
        overall_rate = stats.get('overall_success_rate', 0)
        recent_rate = stats.get('recent_success_rate', 0)
        
        if total == 0:
            click.echo("📭 No executions recorded yet")
            return
        
        click.echo(f"Total executions: {total}")
        click.echo(f"Successful: {successful} ({overall_rate:.1%})")
        click.echo(f"Recent success rate: {recent_rate:.1%}")
        
        # ワークフロータイプ別統計
        by_type = stats.get('by_workflow_type', {})
        if by_type:
            click.echo("\nBy workflow type:")
            for wf_type, type_stats in by_type.items():
                total_type = type_stats['total']
                success_type = type_stats['successful']
                avg_time = type_stats['avg_execution_time']
                
                click.echo(f"  {wf_type}:")
                click.echo(f"    Executions: {success_type}/{total_type} ({success_type/total_type:.1%})")
                click.echo(f"    Avg time: {avg_time:.1f}s")
        
        last_execution = stats.get('last_execution')
        if last_execution:
            click.echo(f"\nLast execution: {last_execution[:19]}")
        
    except Exception as e:
        click.echo(f"❌ Failed to retrieve statistics: {e}", err=True)
        sys.exit(1)


@cli.command()
@pass_context
def version(ctx: Dict[str, Any]):
    """
    バージョン情報を表示
    """
    click.echo("ObsClippingsManager v2.0.0")
    click.echo("Academic reference management system")
    click.echo("Built with modular architecture")


if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n🛑 Operation cancelled by user")
        sys.exit(130)
    except ObsClippingsError as e:
        click.echo(f"❌ Application error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if os.getenv('DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1) 