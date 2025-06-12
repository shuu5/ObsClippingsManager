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

from modules.workflows.enhanced_integrated_workflow import EnhancedIntegratedWorkflow
from modules.workflows.integrated_workflow import IntegratedWorkflow
from modules.shared.exceptions import ObsClippingsError, ConfigError


# グローバル設定
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_LOG_LEVEL = "INFO"

# CLIコンテキスト用の設定
pass_context = click.make_pass_decorator(dict, ensure=True)


@click.group(invoke_without_command=True)
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
        
        # コマンドが指定されていない場合（テスト用）
        # ctxはClick Contextオブジェクトにアクセスする必要があります
        click_ctx = click.get_current_context()
        if click_ctx.invoked_subcommand is None:
            if verbose:
                click.echo("✓ CLI initialization completed successfully")
        
    except Exception as e:
        click.echo(f"❌ Initialization failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--bibtex-file', '-b',
              help='BibTeX file to process',
              type=click.Path(exists=True))
@click.option('--clippings-dir', '-d',
              help='Clippings directory to process',
              type=click.Path(exists=True))
@click.option('--output-dir', '-o',
              help='Output directory for results (legacy mode)',
              type=click.Path())
@click.option('--max-retries', '-r',
              type=int,
              help='Maximum API retry attempts')
@click.option('--use-sync-integration/--no-sync-integration',
              default=True,
              help='Use sync integration for target paper identification')
@click.option('--backup-existing',
              is_flag=True,
              help='Create backup of existing references.bib files')
@click.option('--force-overwrite',
              is_flag=True,
              help='Force overwrite existing references.bib files')
@click.option('--request-delay',
              type=float,
              help='Delay between API requests (seconds)')
@click.option('--timeout',
              type=int,
              help='API request timeout (seconds)')
@click.option('--auto-approve', '-y',
              is_flag=True,
              help='Automatically approve all operations')
@click.option('--enable-enrichment/--no-enable-enrichment',
              default=True,
              help='Enable/disable metadata enrichment using multiple APIs (default: enabled) (v2.2)')
@click.option('--enrichment-field-type',
              type=click.Choice(['life_sciences', 'computer_science', 'general'], case_sensitive=False),
              default='general',
              help='Research field for API prioritization')
@click.option('--enrichment-quality-threshold',
              type=float,
              default=0.8,
              help='Quality score threshold for enriched metadata (0.0-1.0)')
@click.option('--enrichment-max-attempts',
              type=int,
              default=3,
              help='Maximum API attempts for metadata enrichment')
@pass_context
def fetch_citations(ctx: Dict[str, Any], 
                   bibtex_file: Optional[str],
                   clippings_dir: Optional[str],
                   output_dir: Optional[str],
                   max_retries: Optional[int],
                   use_sync_integration: bool,
                   backup_existing: bool,
                   force_overwrite: bool,
                   request_delay: Optional[float],
                   timeout: Optional[int],
                   auto_approve: bool,
                   enable_enrichment: bool,
                   enrichment_field_type: str,
                   enrichment_quality_threshold: float,
                   enrichment_max_attempts: int):
    """
    引用文献取得ワークフローを実行 (v2.1)
    
    sync機能と連携し、論文ごとの個別references.bib保存を行います。
    デフォルトでは同期済み論文のみを対象とし、各citation_keyディレクトリに
    references.bibファイルを個別保存します。
    """
    try:
        workflow_manager = ctx['workflow_manager']
        logger = ctx['logger'].get_logger('CLI')
        
        # 実行オプションの構築
        options = {
            'dry_run': ctx['dry_run'],
            'auto_approve': auto_approve,
            'use_sync_integration': use_sync_integration,
            'backup_existing': backup_existing,
            'force_overwrite': force_overwrite
        }
        
        # コマンドライン引数で設定を上書き
        if bibtex_file:
            options['bibtex_file'] = bibtex_file
        if clippings_dir:
            options['clippings_dir'] = clippings_dir
        
        # 設定から必要なパスを自動取得
        config_manager = ctx['config_manager']
        if not clippings_dir and hasattr(config_manager, 'get_clippings_dir'):
            try:
                options['clippings_dir'] = config_manager.get_clippings_dir()
            except:
                pass  # 設定にない場合はスキップ
        if output_dir:
            options['output_dir'] = output_dir
        if max_retries is not None:
            options['max_retries'] = max_retries
        if request_delay is not None:
            options['request_delay'] = request_delay
        if timeout is not None:
            options['timeout'] = timeout
        
        # メタデータ補完オプション（v2.2新機能）
        options['enable_enrichment'] = enable_enrichment
        if enable_enrichment:
            options['enrichment_field_type'] = enrichment_field_type
            options['enrichment_quality_threshold'] = enrichment_quality_threshold
            options['enrichment_max_attempts'] = enrichment_max_attempts
        
        # sync連携モードの表示
        if use_sync_integration:
            click.echo("🔗 Starting citation fetching workflow with sync integration...")
            click.echo("   → Target: synchronized papers only")
            click.echo("   → Output: individual references.bib files")
        else:
            click.echo("🔍 Starting citation fetching workflow (legacy mode)...")
            click.echo("   → Target: all papers in BibTeX")
            click.echo("   → Output: centralized files")
        
        if backup_existing:
            click.echo("💾 Backup mode enabled for existing references.bib files")
        
        if enable_enrichment:
            click.echo(f"🔧 Metadata enrichment enabled: {enrichment_field_type} field prioritization")
            click.echo(f"   → Quality threshold: {enrichment_quality_threshold}")
            click.echo(f"   → Max API attempts: {enrichment_max_attempts}")
        
        # ワークフロー実行
        success, results = workflow_manager.execute(
            WorkflowType.CITATION_FETCHING, 
            **options
        )
        
        # 結果表示
        if success:
            click.echo("✅ Citation fetching v2.1 completed successfully!")
            
            # sync連携統計の表示
            if use_sync_integration and 'sync_integration' in results:
                sync_info = results['sync_integration']
                click.echo(f"🔗 Sync integration results:")
                click.echo(f"   • Synced papers: {sync_info.get('synced_papers', 0)}")
                click.echo(f"   • Sync rate: {sync_info.get('sync_rate', 0):.1f}%")
                click.echo(f"   • Papers with DOI: {sync_info.get('papers_with_valid_dois', 0)}")
            
            # 保存結果の表示
            individual_saves = results.get('successful_individual_saves', 0)
            skipped_saves = results.get('skipped_individual_saves', 0)
            total_refs = results.get('total_references_saved', 0)
            if individual_saves > 0 or skipped_saves > 0:
                save_msg = f"📁 Individual saves: {individual_saves} papers"
                if skipped_saves > 0:
                    save_msg += f", {skipped_saves} skipped"
                save_msg += f", {total_refs} references"
                click.echo(save_msg)
            
            # メタデータ補完結果の表示
            enriched_count = results.get('enriched_successes', 0)
            if enriched_count > 0:
                click.echo(f"🔧 Metadata enrichment: {enriched_count} papers enriched successfully")
            
            # 詳細統計の表示
            if ctx['verbose']:
                summary = create_workflow_execution_summary(results)
                click.echo("\n" + summary)
            else:
                # 簡潔な統計
                if not use_sync_integration:
                    dois_processed = results.get('successful_fetches', 0)
                    total_refs_legacy = results.get('total_references', 0)
                    click.echo(f"📊 Processed {dois_processed} DOIs, found {total_refs_legacy} references")
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
        success, results = workflow_manager.execute(
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
        success, results = workflow_manager.execute(
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
@click.option('--workspace', '-w',
              help='Workspace root path (auto-derives all other paths)',
              type=click.Path())
@click.option('--bibtex-file', '-b',
              help='BibTeX file path (overrides workspace-based path)',
              type=click.Path(exists=True))
@click.option('--clippings-dir', '-d',
              help='Clippings directory path (overrides workspace-based path)',
              type=click.Path(exists=True))
@click.option('--papers',
              help='Comma-separated list of specific papers to process (citation keys)',
              type=str)
@click.option('--skip-steps',
              help='Comma-separated list of steps to skip (organize,sync,fetch,section-parsing,ai-citation-support,enhanced-tagger,enhanced-translate,ochiai-format,final-sync)',
              type=str)
@click.option('--force-reprocess',
              is_flag=True,
              help='Force reprocess all papers (resets all status flags)')
@click.option('--show-plan',
              is_flag=True,
              help='Display execution plan without running the workflow')
@click.option('--disable-enrichment',
              is_flag=True,
              help='Disable automatic metadata enrichment (not recommended)')
@click.option('--enable-tagger',
              is_flag=True,
              help='Enable AI tagging functionality for automatic tag generation')
@click.option('--enable-translate-abstract',
              is_flag=True,
              help='Enable AI abstract translation functionality for Japanese translation')
@click.option('--enable-section-parsing',
              is_flag=True,
              help='Enable section parsing functionality for structured analysis')
@click.option('--enable-ochiai-format',
              is_flag=True,
              help='Enable Ochiai format summary generation functionality')
@click.option('--auto-approve', '-y',
              is_flag=True,
              help='Automatically approve all operations')
@pass_context
def run_integrated(ctx: Dict[str, Any],
                  workspace: Optional[str],
                  bibtex_file: Optional[str],
                  clippings_dir: Optional[str],
                  papers: Optional[str],
                  skip_steps: Optional[str],
                  force_reprocess: bool,
                  show_plan: bool,
                  disable_enrichment: bool,
                  enable_tagger: bool,
                  enable_translate_abstract: bool,
                  enable_section_parsing: bool,
                  enable_ochiai_format: bool,
                  auto_approve: bool):
    """
    統合ワークフローを実行 (v3.2)
    
    シンプルな設定と効率的な状態管理により、学術文献管理の全プロセスを自動化します。
    デフォルトでは引数なしで完全動作し、workspace_pathベースの統一設定を使用します。
    
    処理順序: organize → sync → fetch → section-parsing → ai-citation-support → enhanced-tagger → enhanced-translate → ochiai-format → final-sync
    
    AI理解支援機能は常に有効で、AI生成機能（tagger, translate_abstract, section-parsing, ochiai-format）はオプションで有効化します。
    """
    try:
        workflow_manager = ctx['workflow_manager']
        config_manager = ctx['config_manager']
        logger = ctx['logger'].get_logger('CLI')
        
        # workspaceオプションが指定された場合、設定を動的に更新
        if workspace:
            config_manager.update_workspace_path(workspace)
        
        # 実行オプションの構築
        options = {
            'workspace_path': workspace,
            'bibtex_file': bibtex_file,
            'clippings_dir': clippings_dir,
            'papers': papers,
            'skip_steps': skip_steps,
            'force_reprocess': force_reprocess,
            'show_plan': show_plan,
            'dry_run': ctx['dry_run'],
            'verbose': ctx.get('verbose', False),
            'auto_approve': auto_approve,
            'enable_enrichment': not disable_enrichment,  # デフォルト有効、--disable-enrichmentで無効化
            'enable_tagger': enable_tagger,
            'enable_translate_abstract': enable_translate_abstract,
            'enable_section_parsing': enable_section_parsing,
            'enable_ochiai_format': enable_ochiai_format
        }
        
        # プラン表示モード
        if show_plan:
            click.echo("📋 Analyzing execution plan...")
            # プラン表示はオプション情報のみ表示
            click.echo("📊 Execution Plan Preview")
            if workspace:
                click.echo(f"  workspace: {workspace}")
            if papers:
                click.echo(f"  papers: {papers}")
            if skip_steps:
                click.echo(f"  skip-steps: {skip_steps}")
            if enable_tagger:
                click.echo("  tagger: enabled")
            if enable_translate_abstract:
                click.echo("  translate-abstract: enabled")
            
            click.echo("⏱️  Estimated time: depends on paper count")
            return
        
        # 通常実行
        click.echo("🚀 Starting integrated workflow v3.2...")
        if workspace:
            click.echo(f"📁 Workspace: {workspace}")
        if enable_tagger:
            click.echo("🏷️  AI tagging: enabled")
        if enable_translate_abstract:
            click.echo("🌐 Abstract translation: enabled")
        if enable_section_parsing:
            click.echo("📄 Section parsing: enabled")
        if enable_ochiai_format:
            click.echo("📋 Ochiai format summary: enabled")
        
        # 統合ワークフロー v3.2を直接使用
        integrated_workflow = IntegratedWorkflow(config_manager, ctx['logger'])
        result = integrated_workflow.execute(**options)
        success = result.get('status') == 'success'
        
        # 結果表示
        if success:
            click.echo("✅ Integrated workflow completed successfully!")
            
            # 詳細統計の表示
            if ctx['verbose']:
                summary = create_workflow_execution_summary(result)
                click.echo("\n" + summary)
            else:
                # 簡潔な統計
                if 'statistics' in result:
                    stats = result['statistics']
                    click.echo(f"📊 Statistics:")
                    click.echo(f"   • Total papers: {stats.get('total_papers', 0)}")
                    click.echo(f"   • Processed papers: {stats.get('processed_papers', 0)}")
        else:
            error = result.get('error', 'Unknown error')
            click.echo(f"❌ Integrated workflow failed: {error}", err=True)
            sys.exit(1)
                
    except Exception as e:
        click.echo(f"❌ Integrated workflow failed: {e}", err=True)
        logger = ctx['logger'].get_logger('CLI')
        logger.error(f"Integrated workflow error: {e}")
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
            
            for wf_type in ['citation_fetching', 'file_organization', 'sync_check', 'integrated']:
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
        
        # ワークフロータイプでフィルタ（文字列として渡す）
        history = workflow_manager.get_execution_history(
            limit=limit,
            workflow_type=workflow_type
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