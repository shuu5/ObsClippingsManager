"""
ObsClippingsManager CLI interface.
"""

import click
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.py.modules.integrated_workflow.integrated_workflow import IntegratedWorkflow


def validate_workspace_path(ctx, param, value):
    """ワークスペースパスのバリデーション"""
    if value:
        path = Path(value)
        if not path.exists():
            raise click.BadParameter(f"指定されたパスが存在しません: {value}")
        if not path.is_dir():
            raise click.BadParameter(f"指定されたパスはディレクトリではありません: {value}")
    return value


@click.command()
@click.option(
    '--workspace-path',
    type=click.Path(exists=False),
    callback=validate_workspace_path,
    help='ワークスペースのパス（未指定の場合は環境変数WORKSPACE_PATHを使用）'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='実際の処理を行わずシミュレーションのみ実行'
)
@click.option(
    '--force',
    is_flag=True,
    help='処理済みファイルも含めて強制的に再処理'
)
@click.option(
    '--show-plan',
    is_flag=True,
    help='実行計画を表示して終了'
)
@click.option(
    '--disable-ai',
    is_flag=True,
    help='すべてのAI機能を無効化（開発用）'
)
@click.option(
    '--enable-only-tagger',
    is_flag=True,
    help='enhanced-tagger機能のみ有効化（開発用）'
)
@click.option(
    '--enable-only-translate',
    is_flag=True,
    help='enhanced-translate機能のみ有効化（開発用）'
)
@click.option(
    '--enable-only-ochiai',
    is_flag=True,
    help='ochiai-format機能のみ有効化（開発用）'
)
@click.option(
    '--disable-tagger',
    is_flag=True,
    help='enhanced-tagger機能を無効化（開発用）'
)
@click.option(
    '--disable-translate',
    is_flag=True,
    help='enhanced-translate機能を無効化（開発用）'
)
@click.option(
    '--disable-ochiai',
    is_flag=True,
    help='ochiai-format機能を無効化（開発用）'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='詳細なログ出力を有効化'
)
def cli(workspace_path: Optional[str], dry_run: bool, force: bool, show_plan: bool,
        disable_ai: bool, enable_only_tagger: bool, enable_only_translate: bool,
        enable_only_ochiai: bool, disable_tagger: bool, disable_translate: bool,
        disable_ochiai: bool, verbose: bool):
    """
    ObsClippingsManager - 学術研究における文献管理とMarkdownファイル整理を自動化
    
    統合ワークフローを実行して以下の処理を行います：
    
    1. organize: citation_keyベースのファイル整理
    2. sync: BibTeX ↔ Clippings整合性確認
    3. fetch: 引用文献取得（CrossRef → Semantic Scholar → OpenCitations）
    4. section_parsing: Markdownセクション構造解析
    5. ai_citation_support: AI理解支援・引用文献統合
    6. enhanced-tagger: AI論文タグ生成
    7. enhanced-translate: AI論文要約翻訳
    8. ochiai-format: 落合フォーマット6項目要約
    9. citation_pattern_normalizer: 引用文献表記統一
    10. final-sync: 最終同期チェック
    """
    
    # バナー表示
    click.echo("=" * 60)
    click.echo("ObsClippingsManager v3.2.0")
    click.echo("学術研究における文献管理とMarkdownファイル整理の自動化")
    click.echo("=" * 60)
    click.echo()
    
    try:
        # 設定マネージャーとロガーの初期化
        config_manager = ConfigManager()
        logger = IntegratedLogger(config_manager)
        
        # ワークスペースパスの決定
        if not workspace_path:
            workspace_path = os.environ.get('WORKSPACE_PATH')
            if not workspace_path:
                click.echo("エラー: ワークスペースパスが指定されていません。", err=True)
                click.echo("--workspace-path オプションまたは環境変数 WORKSPACE_PATH を設定してください。", err=True)
                sys.exit(1)
        
        workspace_path = Path(workspace_path).resolve()
        click.echo(f"ワークスペース: {workspace_path}")
        click.echo()
        
        # 実行計画の表示
        if show_plan:
            display_execution_plan(workspace_path, dry_run, force, 
                                 disable_ai, enable_only_tagger, enable_only_translate,
                                 enable_only_ochiai, disable_tagger, disable_translate,
                                 disable_ochiai)
            return
        
        # AI機能制御の設定
        from code.integrated_test.ai_feature_controller import AIFeatureController
        import argparse
        
        # argparse.Namespace形式でAIFeatureControllerに渡す
        ai_args = argparse.Namespace(
            disable_ai=disable_ai,
            enable_only_tagger=enable_only_tagger,
            enable_only_translate=enable_only_translate,
            enable_only_ochiai=enable_only_ochiai,
            disable_tagger=disable_tagger,
            disable_translate=disable_translate,
            disable_ochiai=disable_ochiai
        )
        ai_controller = AIFeatureController(ai_args)
        
        # IntegratedWorkflowの初期化
        workflow = IntegratedWorkflow(config_manager, logger, ai_controller)
        
        # 進捗表示用コールバック
        def progress_callback(step: str, status: str):
            if status == 'started':
                click.echo(f"[開始] {step}")
            elif status == 'completed':
                click.echo(f"[完了] {step}")
            elif status == 'failed':
                click.echo(f"[失敗] {step}", err=True)
            elif status == 'skipped':
                click.echo(f"[スキップ] {step}")
        
        # ワークフロー実行
        click.echo("統合ワークフローを実行中...")
        if dry_run:
            click.echo("※ DRY RUN モード: 実際の変更は行われません")
        click.echo()
        
        result = workflow.execute(
            workspace_path=str(workspace_path),
            dry_run=dry_run,
            force_reprocess=force,
            disable_ai=disable_ai,
            enable_only_tagger=enable_only_tagger,
            enable_only_translate=enable_only_translate,
            enable_only_ochiai=enable_only_ochiai,
            disable_tagger=disable_tagger,
            disable_translate=disable_translate,
            disable_ochiai=disable_ochiai,
            progress_callback=progress_callback
        )
        
        # 実行結果の表示
        click.echo()
        click.echo("=" * 60)
        click.echo("実行結果")
        click.echo("=" * 60)
        
        if result['status'] == 'completed':
            click.echo(f"✅ 処理完了")
        elif result['status'] == 'completed_with_errors':
            click.echo(f"⚠️  一部エラーありで完了")
        else:
            click.echo(f"❌ 処理失敗")
        
        click.echo(f"処理対象: {result.get('processed', 0)} 件")
        click.echo(f"失敗: {result.get('failed', 0)} 件")
        
        if 'steps_completed' in result:
            click.echo(f"完了ステップ: {', '.join(result['steps_completed'])}")
        
        if result.get('failed', 0) > 0 and 'error_details' in result:
            click.echo()
            click.echo("エラー詳細:")
            for error in result['error_details']:
                click.echo(f"  - {error}")
        
        # 終了コードの決定
        if result['status'] == 'completed':
            sys.exit(0)
        elif result['status'] == 'completed_with_errors':
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        click.echo(f"エラーが発生しました: {str(e)}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(3)


def display_execution_plan(workspace_path: Path, dry_run: bool, force: bool,
                          disable_ai: bool, enable_only_tagger: bool, 
                          enable_only_translate: bool, enable_only_ochiai: bool,
                          disable_tagger: bool, disable_translate: bool,
                          disable_ochiai: bool):
    """実行計画を表示"""
    click.echo("実行計画")
    click.echo("=" * 60)
    click.echo(f"ワークスペース: {workspace_path}")
    click.echo(f"モード: {'DRY RUN' if dry_run else '実行'}")
    click.echo(f"強制再処理: {'有効' if force else '無効'}")
    click.echo()
    
    click.echo("実行予定のステップ:")
    steps = [
        "1. organize - citation_keyベースのファイル整理",
        "2. sync - BibTeX ↔ Clippings整合性確認",
        "3. fetch - 引用文献取得",
        "4. section_parsing - Markdownセクション構造解析",
        "5. ai_citation_support - AI理解支援・引用文献統合"
    ]
    
    # AI機能の有効/無効を判定
    ai_steps = []
    if not disable_ai:
        if enable_only_tagger:
            ai_steps.append("6. enhanced-tagger - AI論文タグ生成")
        elif enable_only_translate:
            ai_steps.append("7. enhanced-translate - AI論文要約翻訳")
        elif enable_only_ochiai:
            ai_steps.append("8. ochiai-format - 落合フォーマット6項目要約")
        else:
            if not disable_tagger:
                ai_steps.append("6. enhanced-tagger - AI論文タグ生成")
            if not disable_translate:
                ai_steps.append("7. enhanced-translate - AI論文要約翻訳")
            if not disable_ochiai:
                ai_steps.append("8. ochiai-format - 落合フォーマット6項目要約")
    
    steps.extend(ai_steps)
    steps.extend([
        "9. citation_pattern_normalizer - 引用文献表記統一",
        "10. final-sync - 最終同期チェック"
    ])
    
    for step in steps:
        click.echo(f"  {step}")
    
    if disable_ai or any([enable_only_tagger, enable_only_translate, enable_only_ochiai,
                         disable_tagger, disable_translate, disable_ochiai]):
        click.echo()
        click.echo("AI機能設定:")
        if disable_ai:
            click.echo("  すべてのAI機能が無効化されています（開発モード）")
        else:
            if enable_only_tagger:
                click.echo("  enhanced-taggerのみ有効")
            elif enable_only_translate:
                click.echo("  enhanced-translateのみ有効")
            elif enable_only_ochiai:
                click.echo("  ochiai-formatのみ有効")
            else:
                if disable_tagger:
                    click.echo("  enhanced-taggerが無効")
                if disable_translate:
                    click.echo("  enhanced-translateが無効")
                if disable_ochiai:
                    click.echo("  ochiai-formatが無効")


if __name__ == '__main__':
    cli()